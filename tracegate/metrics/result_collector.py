from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.config import BASELINE_DIRNAME, RUN_REPO_DIRNAME, RUNS_DIR
from tracegate.dataio import read_json, write_json
from tracegate.metrics.constraint_checker import check_constraints
from tracegate.metrics.git_diff_analyzer import analyze_diff
from tracegate.runners.command_runner import find_run_dirs


def _is_outside_task_module(path: str, module: str) -> bool:
    normalized = path.replace("\\", "/")
    markers = [
        "src/main/java/com/example/legacyshop/",
        "src/test/java/com/example/legacyshop/",
    ]
    for marker in markers:
        if marker in normalized:
            after = normalized.split(marker, 1)[1]
            touched_module = after.split("/", 1)[0]
            return touched_module != module
    return False


def collect_run_result(run_dir: Path) -> dict[str, Any]:
    metadata = read_json(run_dir / "metadata.json", default={}) or {}
    task = metadata.get("task", {})
    context_group = metadata.get("context_group")
    repo_dir = run_dir / RUN_REPO_DIRNAME
    baseline_dir = run_dir / BASELINE_DIRNAME
    test_result = read_json(run_dir / "results" / "test_result.json", default=None)
    deepseek_result = read_json(run_dir / "results" / "deepseek_run.json", default={}) or {}

    diff = analyze_diff(baseline_dir, repo_dir)
    constraints = check_constraints(repo_dir, task.get("hidden_constraints", []))
    junit = (test_result or {}).get("junit", {})
    modified_outside_module = any(
        _is_outside_task_module(path, task.get("module", ""))
        for path in diff.get("modified_files", [])
    )
    pollution_flag = bool(
        context_group == "irrelevant_context"
        and (modified_outside_module or constraints.get("violated"))
    )

    result = {
        "run_dir": str(run_dir),
        "task_id": task.get("id"),
        "task_module": task.get("module"),
        "task_title": task.get("title"),
        "context_group": context_group,
        "success": None if test_result is None else bool(test_result.get("success")),
        "deepseek_status": deepseek_result.get("status"),
        "skip_reason": None if test_result is None else test_result.get("skip_reason"),
        "test_returncode": None if test_result is None else test_result.get("returncode"),
        "test_fail_count": None
        if test_result is None
        else int(junit.get("failures", 0)) + int(junit.get("errors", 0)),
        "violated_history_constraint": constraints.get("violated"),
        "repeated_failed_attempt": constraints.get("violated"),
        "pollution_flag": pollution_flag,
        "context_tokens": metadata.get("prompt", {}).get("context_tokens", 0),
        "selected_context_ids": metadata.get("prompt", {}).get("selected_context_ids", []),
        **diff,
        "constraint_checks": constraints.get("checks", []),
    }
    write_json(run_dir / "results" / "metrics.json", result)
    return result


def collect_results(runs_dir: Path = RUNS_DIR) -> list[dict[str, Any]]:
    results = [collect_run_result(run_dir) for run_dir in find_run_dirs(runs_dir)]
    write_json(runs_dir / "results.json", results)
    return results
