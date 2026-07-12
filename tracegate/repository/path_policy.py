from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path, PurePath


class RepositoryPathError(ValueError):
    """Raised when a repository operation would cross its enrolled boundary."""


_SKIPPED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "target",
    "build",
    "dist",
    "artifacts",
    "runs",
    "__pycache__",
}
_SENSITIVE_NAMES = {
    ".gitconfig",
    ".npmrc",
    ".pypirc",
    "authorized_keys",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
    "netrc",
    ".netrc",
    "secrets",
    "secrets.json",
}
_SENSITIVE_PARTS = {".git", ".ssh", ".aws", ".azure", ".gnupg", ".kube", "gcloud"}
_SENSITIVE_SUFFIXES = {
    ".cer",
    ".crt",
    ".db",
    ".der",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
}


def _contains_parent_reference(path: PurePath) -> bool:
    return any(part == ".." for part in path.parts)


class RepositoryBoundary:
    """Canonical repository root plus deny-by-default path resolution."""

    def __init__(self, root: Path, *, max_file_bytes: int = 2 * 1024 * 1024) -> None:
        resolved = root.expanduser().resolve(strict=True)
        if not resolved.is_dir():
            raise RepositoryPathError("enrolled repository root must be a directory")
        self.root = resolved
        self.max_file_bytes = max_file_bytes

    def resolve(self, relative_path: str, *, allow_missing: bool = False) -> Path:
        if not relative_path or "\x00" in relative_path:
            raise RepositoryPathError("repository path must be a non-empty relative path")
        pure = PurePath(relative_path)
        if pure.is_absolute() or _contains_parent_reference(pure):
            raise RepositoryPathError("absolute paths and parent traversal are forbidden")
        self._reject_sensitive(pure)

        candidate = self.root.joinpath(*pure.parts)
        if allow_missing and not candidate.exists():
            ancestor = candidate.parent
            while ancestor != self.root and not ancestor.exists():
                ancestor = ancestor.parent
            resolved_ancestor = ancestor.resolve(strict=True)
            self._require_contained(resolved_ancestor)
            relative_tail = candidate.relative_to(ancestor)
            return resolved_ancestor / relative_tail
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise RepositoryPathError("repository path does not exist") from exc
        self._require_contained(resolved)
        return resolved

    def relative(self, path: Path) -> str:
        resolved = path.resolve(strict=True)
        self._require_contained(resolved)
        return resolved.relative_to(self.root).as_posix()

    def iter_files(self) -> Iterator[Path]:
        for directory, dirnames, filenames in os.walk(self.root, followlinks=False):
            parent = Path(directory)
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in _SKIPPED_DIRECTORIES and not (parent / name).is_symlink()
            )
            for name in sorted(filenames):
                relative = (parent / name).relative_to(self.root)
                try:
                    resolved = self.resolve(relative.as_posix())
                except RepositoryPathError:
                    continue
                if not resolved.is_file() or resolved.stat().st_size > self.max_file_bytes:
                    continue
                yield resolved

    def _require_contained(self, resolved: Path) -> None:
        if resolved != self.root and not resolved.is_relative_to(self.root):
            raise RepositoryPathError("resolved path escapes the enrolled repository")

    @staticmethod
    def _reject_sensitive(path: PurePath) -> None:
        lowered = [part.casefold() for part in path.parts]
        if any(part in _SENSITIVE_PARTS for part in lowered):
            raise RepositoryPathError("sensitive credential directory is forbidden")
        name = lowered[-1]
        if (
            name == ".env"
            or name.startswith(".env.")
            or name in _SENSITIVE_NAMES
            or PurePath(name).suffix in _SENSITIVE_SUFFIXES
        ):
            raise RepositoryPathError("sensitive credential file is forbidden")
