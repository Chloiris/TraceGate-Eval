from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Oracle(Protocol):
    def evaluate(self, repo_dir: Path, task: dict[str, Any]) -> dict[str, Any]:
        ...


def read(repo_dir: Path, relative_path: str) -> str:
    path = repo_dir / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def read_many(repo_dir: Path, relative_paths: list[str]) -> str:
    return "\n".join(read(repo_dir, path) for path in relative_paths)


def build_result(task: dict[str, Any], preserved: bool, optimized: bool, evidence: list[str]) -> dict[str, Any]:
    ground_truth = task.get("ground_truth")
    if ground_truth == "must_preserve":
        correct = preserved and not optimized
    else:
        correct = optimized and not preserved
    return {
        "module": task.get("module"),
        "ground_truth": ground_truth,
        "preserved": preserved,
        "optimized": optimized,
        "semantic_correct": correct,
        "evidence": evidence,
    }

