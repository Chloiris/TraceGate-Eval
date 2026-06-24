from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any


IGNORE_PARTS = {"target", ".git", ".idea", ".mvn", "results"}


def _iter_files(root: Path) -> set[str]:
    files: set[str] = set()
    if not root.exists():
        return files
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORE_PARTS for part in rel.parts):
            continue
        files.add(rel.as_posix())
    return files


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return ["<binary>"]


def analyze_diff(baseline_dir: Path, repo_dir: Path) -> dict[str, Any]:
    baseline_files = _iter_files(baseline_dir)
    repo_files = _iter_files(repo_dir)
    changed_files = sorted(baseline_files | repo_files)

    modified_files: list[str] = []
    added = 0
    deleted = 0

    for rel in changed_files:
        baseline_path = baseline_dir / rel
        repo_path = repo_dir / rel
        old_lines = _read_lines(baseline_path) if baseline_path.exists() else []
        new_lines = _read_lines(repo_path) if repo_path.exists() else []
        if old_lines == new_lines:
            continue
        modified_files.append(rel)
        if not baseline_path.exists():
            added += len(new_lines)
            continue
        if not repo_path.exists():
            deleted += len(old_lines)
            continue
        for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                deleted += 1

    return {
        "touched_files_count": len(modified_files),
        "patch_lines_added": added,
        "patch_lines_deleted": deleted,
        "modified_files": modified_files,
    }
