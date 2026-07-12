from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from tracegate.repository import RepositoryBoundary

from .errors import AutofixError


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def _git_environment() -> dict[str, str]:
    allowed = ("LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP")
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


@dataclass(frozen=True)
class FixWorkspace:
    session_id: str
    repository_id: str
    source_root: Path
    session_root: Path
    worktree_root: Path
    head_sha: str

    @property
    def boundary(self) -> RepositoryBoundary:
        return RepositoryBoundary(self.worktree_root)


class FixWorkspaceManager:
    """Own detached Git worktrees without mutating the enrolled workspace."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def create(
        self,
        *,
        session_id: str,
        repository_id: str,
        source_root: Path,
        head_sha: str,
    ) -> FixWorkspace:
        self._validate_identifier(session_id, "session")
        self._validate_identifier(repository_id, "repository")
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", head_sha):
            raise AutofixError("fix_head_stale", "Head SHA is invalid")
        source = source_root.expanduser().resolve(strict=True)
        if not source.is_dir():
            raise AutofixError("fix_workspace_unavailable", "Enrolled repository is unavailable")
        self._run_git(source, "rev-parse", "--is-inside-work-tree")
        self._run_git(source, "cat-file", "-e", f"{head_sha}^{{commit}}")

        session_root = self._session_root(repository_id, session_id)
        worktree = session_root / "worktree"
        if worktree.exists():
            workspace = FixWorkspace(
                session_id,
                repository_id,
                source,
                session_root,
                worktree,
                head_sha,
            )
            self.verify(workspace, require_clean=True)
            return workspace

        session_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        result = self._run_git(
            source,
            "worktree",
            "add",
            "--detach",
            str(worktree),
            head_sha,
            check=False,
            timeout=90,
        )
        if result.returncode != 0:
            if worktree.exists():
                shutil.rmtree(worktree, ignore_errors=True)
            raise AutofixError(
                "fix_workspace_unavailable",
                result.stderr[:2_000].strip() or "Git worktree creation failed",
            )
        workspace = FixWorkspace(
            session_id,
            repository_id,
            source,
            session_root,
            worktree,
            head_sha,
        )
        self.verify(workspace, require_clean=True)
        return workspace

    def load(
        self,
        *,
        session_id: str,
        repository_id: str,
        source_root: Path,
        head_sha: str,
    ) -> FixWorkspace:
        workspace = FixWorkspace(
            session_id,
            repository_id,
            source_root.expanduser().resolve(strict=True),
            self._session_root(repository_id, session_id),
            self._session_root(repository_id, session_id) / "worktree",
            head_sha,
        )
        self.verify(workspace, require_clean=False)
        return workspace

    def verify(self, workspace: FixWorkspace, *, require_clean: bool) -> None:
        target = workspace.worktree_root.resolve(strict=True)
        self._require_managed(target)
        actual = self._run_git(target, "rev-parse", "HEAD").stdout.strip()
        if actual != workspace.head_sha:
            raise AutofixError("fix_head_stale", "Fix worktree is no longer at the recorded Head SHA")
        if require_clean and self._run_git(target, "status", "--porcelain").stdout.strip():
            raise AutofixError("fix_workspace_unavailable", "Fix worktree is not clean")

    def rollback(self, workspace: FixWorkspace) -> None:
        self.verify(workspace, require_clean=False)
        self._run_git(workspace.worktree_root, "reset", "--hard", workspace.head_sha)
        self._run_git(workspace.worktree_root, "clean", "-fdx")
        self.verify(workspace, require_clean=True)

    def delete(self, workspace: FixWorkspace) -> None:
        self._require_managed(workspace.session_root.resolve(strict=False))
        if workspace.worktree_root.exists():
            result = self._run_git(
                workspace.source_root,
                "worktree",
                "remove",
                "--force",
                str(workspace.worktree_root),
                check=False,
                timeout=90,
            )
            if result.returncode != 0:
                raise AutofixError(
                    "fix_workspace_unavailable",
                    result.stderr[:2_000].strip() or "Git worktree removal failed",
                )
        if workspace.session_root.exists():
            shutil.rmtree(workspace.session_root)
        self._run_git(workspace.source_root, "worktree", "prune", check=False)

    def diff(self, workspace: FixWorkspace, changed_paths: list[str]) -> str:
        self.verify(workspace, require_clean=False)
        boundary = workspace.boundary
        bounded = [
            boundary.resolve(path, allow_missing=True).relative_to(boundary.root).as_posix()
            for path in changed_paths
        ]
        for relative_path in bounded:
            absolute = boundary.root / relative_path
            if absolute.exists() and not self._tracked(workspace.worktree_root, relative_path):
                self._run_git(workspace.worktree_root, "add", "-N", "--", relative_path)
        result = self._run_git(
            workspace.worktree_root,
            "diff",
            "--binary",
            "--no-ext-diff",
            workspace.head_sha,
            "--",
            *bounded,
        )
        return result.stdout

    def file_versions(self, workspace: FixWorkspace, relative_path: str) -> tuple[str, str]:
        boundary = workspace.boundary
        modified_path = boundary.resolve(relative_path)
        modified = modified_path.read_text(encoding="utf-8", errors="replace")
        original_result = self._run_git(
            workspace.worktree_root,
            "show",
            f"{workspace.head_sha}:{relative_path}",
            check=False,
        )
        original = original_result.stdout if original_result.returncode == 0 else ""
        return original, modified

    def discover_residual_worktrees(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(
            path
            for path in self.root.glob("*/*/worktree")
            if path.is_dir() and path.resolve().is_relative_to(self.root)
        )

    def _session_root(self, repository_id: str, session_id: str) -> Path:
        candidate = (self.root / repository_id / session_id).resolve(strict=False)
        self._require_managed(candidate)
        return candidate

    def _require_managed(self, path: Path) -> None:
        root = self.root.resolve(strict=False)
        resolved = path.resolve(strict=False)
        if resolved == root or not resolved.is_relative_to(root):
            raise AutofixError("fix_workspace_unavailable", "Fix workspace path escapes its managed root")

    @staticmethod
    def _validate_identifier(value: str, label: str) -> None:
        if not _SAFE_IDENTIFIER.fullmatch(value):
            raise AutofixError("fix_workspace_unavailable", f"Fix {label} identifier is invalid")

    @staticmethod
    def _tracked(root: Path, relative_path: str) -> bool:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative_path],
            capture_output=True,
            text=True,
            timeout=20,
            env=_git_environment(),
            check=False,
        )
        return result.returncode == 0

    @staticmethod
    def _run_git(
        root: Path,
        *arguments: str,
        check: bool = True,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *arguments],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout,
                env=_git_environment(),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AutofixError("fix_workspace_unavailable", "Git workspace command failed") from exc
        if check and result.returncode != 0:
            raise AutofixError(
                "fix_workspace_unavailable",
                result.stderr[:2_000].strip() or "Git workspace command failed",
            )
        return result
