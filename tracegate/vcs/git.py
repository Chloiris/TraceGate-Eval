from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

from tracegate.repository import RepositoryBoundary


MAX_GIT_OUTPUT = 2 * 1024 * 1024
_GIT_ENV_ALLOWLIST = ("HOME", "LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TMP", "TEMP")


class GitCommandError(RuntimeError):
    """Raised when a bounded read-only Git command does not complete successfully."""


@dataclass(frozen=True)
class GitResult:
    arguments: tuple[str, ...]
    stdout: str
    stderr: str
    return_code: int


class GitProvider:
    """Read-only Git operations using argument vectors and a filtered environment."""

    def __init__(self, boundary: RepositoryBoundary, *, timeout_seconds: float = 20.0) -> None:
        self.boundary = boundary
        self.timeout_seconds = timeout_seconds

    def run(self, *arguments: str, check: bool = True) -> GitResult:
        if not arguments or any("\x00" in item for item in arguments):
            raise GitCommandError("git arguments are invalid")
        environment = {name: os.environ[name] for name in _GIT_ENV_ALLOWLIST if name in os.environ}
        environment.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"})
        try:
            process = subprocess.run(
                ["git", "-C", str(self.boundary.root), *arguments],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=self.timeout_seconds,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitCommandError("git command timed out") from exc
        stdout = process.stdout[:MAX_GIT_OUTPUT]
        stderr = process.stderr[:MAX_GIT_OUTPUT]
        result = GitResult(tuple(arguments), stdout, stderr, process.returncode)
        if check and process.returncode != 0:
            raise GitCommandError(f"git command failed with exit code {process.returncode}: {stderr.strip()}")
        return result

    def status(self) -> GitResult:
        return self.run("status", "--short", "--branch")

    def diff(self, base: str | None = None, head: str | None = None) -> GitResult:
        arguments = ["diff", "--no-ext-diff", "--unified=3"]
        if base and head:
            arguments.append(f"{base}...{head}")
        elif base:
            arguments.append(base)
        return self.run(*arguments)

    def log(self, limit: int = 50) -> GitResult:
        bounded = max(1, min(limit, 200))
        return self.run(
            "log",
            f"--max-count={bounded}",
            "--date=iso-strict",
            "--pretty=format:%H%x09%aI%x09%an%x09%s",
        )

    def show(self, revision: str, relative_path: str) -> GitResult:
        if not re.fullmatch(r"[0-9A-Fa-f]{7,64}", revision):
            raise GitCommandError("revision must be a hexadecimal commit identifier")
        path = self.boundary.resolve(relative_path, allow_missing=True)
        return self.run("show", f"{revision}:{path.relative_to(self.boundary.root).as_posix()}")

    def head_sha(self) -> str:
        return self.run("rev-parse", "HEAD").stdout.strip()

    def branch(self) -> str:
        return self.run("branch", "--show-current").stdout.strip()
