from __future__ import annotations

import os
from pathlib import Path

import pytest

from tracegate.repository import RepositoryBoundary, RepositoryPathError


def test_boundary_rejects_traversal_absolute_and_sensitive_paths(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "safe.py").write_text("print('safe')", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")
    boundary = RepositoryBoundary(tmp_path)

    assert boundary.resolve("src/safe.py") == (tmp_path / "src" / "safe.py").resolve()
    for value in ("../outside", "/etc/passwd", ".env", ".ssh/id_rsa", "src/../../etc"):
        with pytest.raises(RepositoryPathError):
            boundary.resolve(value)


def test_boundary_rejects_symlink_escape(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    outside = tmp_path / "outside"
    repository.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    try:
        os.symlink(outside, repository / "linked")
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(RepositoryPathError, match="escapes"):
        RepositoryBoundary(repository).resolve("linked/secret.txt")


def test_iter_files_skips_generated_sensitive_and_large_content(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("value = 1", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.js").write_text("generated", encoding="utf-8")
    (tmp_path / ".env.local").write_text("secret", encoding="utf-8")
    (tmp_path / "large.txt").write_bytes(b"x" * 32)

    boundary = RepositoryBoundary(tmp_path, max_file_bytes=16)
    assert [boundary.relative(path) for path in boundary.iter_files()] == ["src/main.py"]
