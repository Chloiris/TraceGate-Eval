from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.config import BASELINE_DIRNAME, RUN_REPO_DIRNAME, RUNS_STAGE2_DIR
from tracegate.dataio import read_json, write_json
from tracegate.metrics.execution_metrics import execution_metrics
from tracegate.metrics.git_diff_analyzer import analyze_diff
from tracegate.metrics.semantic_metrics import semantic_metrics
from tracegate.oracle.oracle_runner import evaluate_oracle
from tracegate.runners.command_runner import find_run_dirs


def _is_outside_task_module(path: str, module: str) -> bool:
    normalized = path.replace("\\", "/")
    marker = "src/main/java/com/example/legacyshop/"
    if marker not in normalized:
        return False
    after = normalized.split(marker, 1)[1]
    return after.split("/", 1)[0] != module


def collect_stage2_run(run_dir: Path) -> dict[str, Any]:
    metadata = read_json(run_dir / "metadata.json", default={}) or {}
    task = metadata.get("task", {})
    context_group = metadata.get("context_group")
    repo_dir = run_dir / RUN_REPO_DIRNAME
    baseline_dir = run_dir / BASELINE_DIRNAME
    deepseek_result = read_json(run_dir / "results" / "deepseek_run.json", default={}) or {}
    test_result = read_json(run_dir / "results" / "test_result.json", default=None)
    diff = analyze_diff(baseline_dir, repo_dir)
    oracle = evaluate_oracle(repo_dir, task)
    execution = execution_metrics(deepseek_result, test_result)
    modified_outside = any(_is_outside_task_module(path, task.get("module", "")) for path in diff.get("modified_files", []))
    semantic = semantic_metrics(task, context_group, oracle, execution, modified_outside)
    junit = (test_result or {}).get("junit", {})
    result = {
        "run_dir": str(run_dir),
        "model": metadata.get("model", {}).get("id"),
        "task_id": task.get("id"),
        "task_module": task.get("module"),
        "task_title": task.get("title"),
        "lifecycle": task.get("lifecycle"),
        "ground_truth": task.get("ground_truth"),
        "context_group": context_group,
        "deepseek_status": deepseek_result.get("status"),
        "skip_reason": None if test_result is None else test_result.get("skip_reason"),
        "test_returncode": None if test_result is None else test_result.get("returncode"),
        "test_fail_count": None if test_result is None else int(junit.get("failures", 0)) + int(junit.get("errors", 0)),
        "context_tokens": metadata.get("prompt", {}).get("context_tokens", 0),
        "selected_context_ids": metadata.get("prompt", {}).get("selected_context_ids", []),
        "oracle": oracle,
        **execution,
        **semantic,
        **diff,
    }
    write_json(run_dir / "results" / "stage2_metrics.json", result)
    return result


def collect_stage2_results(runs_dir: Path = RUNS_STAGE2_DIR) -> list[dict[str, Any]]:
    results = [collect_stage2_run(run_dir) for run_dir in find_run_dirs(runs_dir)]
    write_json(runs_dir / "results.json", results)
    return results

