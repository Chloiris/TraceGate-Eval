from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from tracegate.repository import RepositoryBoundary

from .errors import AutofixError
from .schemas import ValidationCommand, ValidationPlan, ValidationStatus


MAX_VALIDATION_OUTPUT = 512 * 1024


@dataclass(frozen=True)
class ValidationExecution:
    status: ValidationStatus
    return_code: int | None
    stdout: str
    stderr: str
    duration_ms: int


class ValidationCommandResolver:
    """Derive validation argv from repository manifests, never model shell text."""

    def resolve(self, boundary: RepositoryBoundary, *, finding_path: str | None = None) -> ValidationPlan:
        commands: list[ValidationCommand] = [
            ValidationCommand(
                argv=["git", "diff", "--check"],
                command_purpose="Reject whitespace errors in the applied patch",
                required=True,
                timeout=60,
                expected_result="Exit code 0",
                source="controlled_preset",
            )
        ]
        notes: list[str] = []
        root = boundary.root

        if (root / "pyproject.toml").is_file() or (root / "pytest.ini").is_file():
            related = self._related_python_test(boundary, finding_path)
            prefix = ["uv", "run", "pytest"] if (root / "uv.lock").is_file() else ["python", "-m", "pytest"]
            if related:
                commands.append(
                    ValidationCommand(
                        argv=[*prefix, "-q", related],
                        command_purpose="Run the test module related to the Finding path",
                        required=True,
                        timeout=300,
                        expected_result="All selected tests pass",
                        source="repository_structure",
                    )
                )
            commands.append(
                ValidationCommand(
                    argv=[*prefix, "-q"],
                    command_purpose="Run the repository Python test suite",
                    required=True,
                    timeout=900,
                    expected_result="All Python tests pass",
                    source="pyproject.toml",
                )
            )

        package_json = root / "package.json"
        if package_json.is_file():
            try:
                payload = json.loads(package_json.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                payload = {}
            scripts = payload.get("scripts") if isinstance(payload, dict) else {}
            scripts = scripts if isinstance(scripts, dict) else {}
            manager = (
                "pnpm"
                if (root / "pnpm-lock.yaml").is_file()
                else "yarn"
                if (root / "yarn.lock").is_file()
                else "npm"
            )
            for script, purpose in (
                ("test", "Run the repository JavaScript/TypeScript tests"),
                ("lint", "Run the repository lint checks"),
                ("typecheck", "Run the repository TypeScript typecheck"),
            ):
                if script in scripts:
                    commands.append(
                        ValidationCommand(
                            argv=[manager, script],
                            command_purpose=purpose,
                            required=True,
                            timeout=900,
                            expected_result=f"{script} exits with code 0",
                            source="package.json",
                        )
                    )

        if (root / "Cargo.toml").is_file():
            commands.append(
                ValidationCommand(
                    argv=["cargo", "test"],
                    command_purpose="Run the repository Rust tests",
                    required=True,
                    timeout=900,
                    expected_result="All Rust tests pass",
                    source="Cargo.toml",
                )
            )

        if (root / "pom.xml").is_file():
            executable = "./mvnw" if (root / "mvnw").is_file() else "mvn"
            commands.append(
                ValidationCommand(
                    argv=[executable, "test"],
                    command_purpose="Run the repository Maven tests",
                    required=True,
                    timeout=900,
                    expected_result="Maven test exits with code 0",
                    source="pom.xml",
                )
            )
        elif any((root / name).is_file() for name in ("build.gradle", "build.gradle.kts")):
            executable = "./gradlew" if (root / "gradlew").is_file() else "gradle"
            commands.append(
                ValidationCommand(
                    argv=[executable, "test"],
                    command_purpose="Run the repository Gradle tests",
                    required=True,
                    timeout=900,
                    expected_result="Gradle test exits with code 0",
                    source="gradle_manifest",
                )
            )

        deduplicated: list[ValidationCommand] = []
        seen: set[tuple[str, ...]] = set()
        for command in commands:
            key = tuple(command.argv)
            if key not in seen:
                deduplicated.append(command)
                seen.add(key)
        if len(deduplicated) == 1:
            notes.append("NO_TEST_COMMAND_AVAILABLE")
        return ValidationPlan(commands=deduplicated, notes=notes)

    @staticmethod
    def _related_python_test(boundary: RepositoryBoundary, finding_path: str | None) -> str | None:
        if not finding_path or not finding_path.endswith(".py"):
            return None
        stem = Path(finding_path).stem
        candidates = (
            f"tests/test_{stem}.py",
            str(Path(finding_path).with_name(f"test_{stem}.py")).replace("\\", "/"),
        )
        for candidate in candidates:
            try:
                path = boundary.resolve(candidate)
            except (OSError, ValueError):
                continue
            if path.is_file():
                return candidate
        return None


class ValidationExecutor:
    def __init__(self, boundary: RepositoryBoundary, *, safe_home: Path) -> None:
        self.boundary = boundary
        self.safe_home = safe_home.expanduser().resolve()

    async def execute(
        self,
        command: ValidationCommand,
        *,
        cancellation_event: asyncio.Event | None = None,
        on_output: Callable[[str, str], None] | None = None,
    ) -> ValidationExecution:
        self._validate_command(command.argv)
        self.safe_home.mkdir(parents=True, mode=0o700, exist_ok=True)
        environment = self._environment()
        started = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(
                *command.argv,
                cwd=self.boundary.root,
                env=environment,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=os.name != "nt",
            )
        except OSError as exc:
            return ValidationExecution(
                ValidationStatus.FAILED,
                None,
                "",
                f"Command unavailable: {type(exc).__name__}",
                int((time.monotonic() - started) * 1000),
            )

        stdout_task = asyncio.create_task(self._read_stream(process.stdout, "stdout", on_output))
        stderr_task = asyncio.create_task(self._read_stream(process.stderr, "stderr", on_output))
        status = ValidationStatus.RUNNING
        try:
            while process.returncode is None:
                if cancellation_event and cancellation_event.is_set():
                    status = ValidationStatus.CANCELLED
                    await self._terminate(process)
                    break
                if time.monotonic() - started > command.timeout:
                    status = ValidationStatus.FAILED
                    await self._terminate(process)
                    break
                try:
                    await asyncio.wait_for(process.wait(), timeout=0.1)
                except TimeoutError:
                    continue
            await process.wait()
        finally:
            stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
        if status == ValidationStatus.RUNNING:
            status = ValidationStatus.PASSED if process.returncode == 0 else ValidationStatus.FAILED
        if status == ValidationStatus.FAILED and time.monotonic() - started > command.timeout:
            stderr = (stderr + "\nCommand timed out.").strip()
        return ValidationExecution(
            status,
            process.returncode,
            stdout,
            stderr,
            int((time.monotonic() - started) * 1000),
        )

    async def _read_stream(
        self,
        stream: asyncio.StreamReader | None,
        label: str,
        on_output: Callable[[str, str], None] | None,
    ) -> str:
        if stream is None:
            return ""
        chunks: list[str] = []
        size = 0
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                break
            text = chunk.decode("utf-8", errors="replace")
            if on_output:
                on_output(label, text[:16_384])
            encoded = text.encode("utf-8", errors="replace")
            remaining = MAX_VALIDATION_OUTPUT - size
            if remaining > 0:
                kept = encoded[:remaining].decode("utf-8", errors="replace")
                chunks.append(kept)
                size += len(kept.encode("utf-8"))
        if size >= MAX_VALIDATION_OUTPUT:
            chunks.append("\n[output truncated]")
        return "".join(chunks)

    @staticmethod
    async def _terminate(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            await asyncio.wait_for(process.wait(), timeout=2)
        except (ProcessLookupError, TimeoutError):
            if process.returncode is None:
                process.kill()
                await process.wait()

    def _environment(self) -> dict[str, str]:
        environment = {
            name: os.environ[name]
            for name in ("LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP")
            if name in os.environ
        }
        environment.update(
            {
                "CI": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "HOME": str(self.safe_home),
                "NO_COLOR": "1",
                "XDG_CACHE_HOME": str(self.safe_home / "cache"),
                "XDG_CONFIG_HOME": str(self.safe_home / "config"),
            }
        )
        return environment

    @staticmethod
    def _validate_command(argv: list[str]) -> None:
        prefixes = {
            ("git", "diff", "--check"),
            ("uv", "run", "pytest"),
            ("python", "-m", "pytest"),
            ("python3", "-m", "pytest"),
            ("pytest",),
            ("pnpm", "test"),
            ("pnpm", "lint"),
            ("pnpm", "typecheck"),
            ("npm", "test"),
            ("npm", "lint"),
            ("npm", "typecheck"),
            ("yarn", "test"),
            ("yarn", "lint"),
            ("yarn", "typecheck"),
            ("cargo", "test"),
            ("mvn", "test"),
            ("./mvnw", "test"),
            ("gradle", "test"),
            ("./gradlew", "test"),
        }
        values = tuple(argv)
        if not any(values[: len(prefix)] == prefix for prefix in prefixes):
            raise AutofixError("fix_validation_forbidden", "Validation command is not allowed")
        for argument in argv[1:]:
            normalized = argument.replace("\\", "/")
            if "\x00" in argument or any(token in argument for token in ("&&", ";", "`", "$(")):
                raise AutofixError("fix_validation_forbidden", "Validation argument is unsafe")
            if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
                raise AutofixError("fix_validation_forbidden", "Validation path argument escapes the workspace")
