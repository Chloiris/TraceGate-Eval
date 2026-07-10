from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from tracegate.repository import RepositoryBoundary


MAX_GIT_OUTPUT = 2 * 1024 * 1024
_GIT_ENV_ALLOWLIST = ("HOME", "LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TMP", "TEMP")


class GitCommandError(RuntimeError):
    pass


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
        path = self.boundary.resolve(relative_path)
        return self.run("show", f"{revision}:{self.boundary.relative(path)}")

    def head_sha(self) -> str:
        return self.run("rev-parse", "HEAD").stdout.strip()

    def branch(self) -> str:
        return self.run("branch", "--show-current").stdout.strip()
