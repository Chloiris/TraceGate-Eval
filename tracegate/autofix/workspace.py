from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tracegate.repository import RepositoryBoundary

from .errors import AutofixError
from .patch_safety import prepare_patch_bytes


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

    def diff_all(self, workspace: FixWorkspace) -> str:
        """Return the authoritative full worktree diff, including new files."""
        self.verify(workspace, require_clean=False)
        untracked = self._run_git(
            workspace.worktree_root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ).stdout.split("\0")
        for relative_path in (path for path in untracked if path):
            workspace.boundary.resolve(relative_path)
            self._run_git(
                workspace.worktree_root,
                "add",
                "-N",
                "--",
                relative_path,
            )
        return self._run_git(
            workspace.worktree_root,
            "diff",
            "--binary",
            "--no-ext-diff",
            workspace.head_sha,
            "--",
        ).stdout

    def state_hash(self, workspace: FixWorkspace) -> str:
        """Hash every changed/deleted/untracked path and byte in the worktree."""
        self.verify(workspace, require_clean=False)
        paths = self._run_git(
            workspace.worktree_root,
            "ls-files",
            "-m",
            "-d",
            "-o",
            "--exclude-standard",
            "-z",
        ).stdout.split("\0")
        digest = hashlib.sha256()
        for relative_path in sorted({path for path in paths if path}):
            absolute = workspace.boundary.resolve(relative_path, allow_missing=True)
            digest.update(relative_path.encode("utf-8", errors="surrogateescape"))
            digest.update(b"\0")
            if not absolute.exists():
                digest.update(b"deleted\0")
                continue
            if absolute.is_symlink():
                raise AutofixError(
                    "fix_workspace_unavailable",
                    "Fix workspace state contains an unexpected symbolic link",
                )
            stat = absolute.stat()
            digest.update(f"{stat.st_mode & 0o777:o}:{stat.st_size}".encode("ascii"))
            digest.update(b"\0")
            if absolute.is_file():
                with absolute.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
            digest.update(b"\0")
        return digest.hexdigest()

    def project_file_versions(
        self,
        workspace: FixWorkspace,
        patch: str,
        relative_path: str,
    ) -> tuple[str | None, str | None]:
        """Project Base/Patched content without mutating the isolated worktree."""
        workspace.boundary.resolve(relative_path, allow_missing=True)
        with tempfile.TemporaryDirectory(
            prefix="patch-projection-", dir=workspace.session_root
        ) as temporary:
            environment = _git_environment()
            environment["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
            read_tree = subprocess.run(
                ["git", "-C", str(workspace.worktree_root), "read-tree", workspace.head_sha],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=30,
                env=environment,
                check=False,
            )
            if read_tree.returncode != 0:
                raise AutofixError(
                    "fix_workspace_unavailable",
                    read_tree.stderr[:2_000].strip() or "Patch projection index failed",
                )
            applied = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace.worktree_root),
                    "apply",
                    "--cached",
                    "--whitespace=nowarn",
                    "-",
                ],
                input=prepare_patch_bytes(patch, workspace.boundary),
                capture_output=True,
                timeout=30,
                env=environment,
                check=False,
            )
            if applied.returncode != 0:
                raise AutofixError(
                    "fix_patch_unsafe",
                    applied.stderr.decode("utf-8", errors="replace")[:2_000].strip()
                    or "Patch projection failed",
                )

            def show(specification: str) -> str | None:
                result = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(workspace.worktree_root),
                        "show",
                        specification,
                    ],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=30,
                    env=environment,
                    check=False,
                )
                return result.stdout if result.returncode == 0 else None

            return show(f"{workspace.head_sha}:{relative_path}"), show(
                f":{relative_path}"
            )

    def discover_residual_worktrees(self) -> list[Path]:
        if not self.root.exists():
            return list()
        return sorted(
            path
            for path in self.root.glob("*/*/worktree")
            if path.is_dir() and path.resolve().is_relative_to(self.root)
        )

    def delete_residual_worktree(self, worktree_root: Path) -> None:
        """Remove an orphaned worktree directory without trusting its Git metadata.

        Residual diagnostics can outlive the database record that identifies the
        enrolled source repository.  In that case we deliberately do not follow
        the worktree's ``.git`` pointer: it could reference a path outside the
        managed Autofix root.  The stale Git administrative entry, if any, is
        harmless and will be pruned by the source repository on its next normal
        worktree operation.
        """

        candidate = worktree_root.expanduser()
        if candidate.is_symlink() or candidate.parent.is_symlink():
            raise AutofixError("fix_workspace_unavailable", "Residual Fix workspace is a symlink")
        resolved = candidate.resolve(strict=True)
        self._require_managed(resolved)
        relative = resolved.relative_to(self.root.resolve(strict=False))
        if len(relative.parts) != 3 or relative.parts[-1] != "worktree":
            raise AutofixError(
                "fix_workspace_unavailable",
                "Residual Fix workspace does not match the managed directory layout",
            )
        session_root = resolved.parent
        if session_root.is_symlink():
            raise AutofixError("fix_workspace_unavailable", "Residual Fix session is a symlink")
        shutil.rmtree(session_root)

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
