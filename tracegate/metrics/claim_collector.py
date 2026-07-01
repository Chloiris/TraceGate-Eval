from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.config import BASELINE_DIRNAME, PROJECT_ROOT, RUN_REPO_DIRNAME, RUNS_CLAIM_DIR
from tracegate.dataio import read_json, write_json
from tracegate.metrics.claim_semantic_metrics import claim_semantic_metrics
from tracegate.metrics.evidence_metrics import evidence_decision_metrics
from tracegate.metrics.execution_metrics import execution_metrics
from tracegate.metrics.git_diff_analyzer import analyze_diff
from tracegate.metrics.plan_quality import plan_quality_metrics
from tracegate.metrics.pollution_metrics import pollution_metrics
from tracegate.oracle.claim_oracle import evaluate_claim_decision
from tracegate.oracle.code_oracle import evaluate_code_oracle
from tracegate.oracle.plan_oracle import score_verification_plan
from tracegate.runners.command_runner import find_run_dirs


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def collect_claim_run(run_dir: Path) -> dict[str, Any]:
    metadata = read_json(run_dir / "metadata.json", default={}) or {}
    task = metadata.get("task", {})
    context_group = metadata.get("context_group")
    repo_dir = run_dir / RUN_REPO_DIRNAME
    baseline_dir = run_dir / BASELINE_DIRNAME
    run_result = read_json(run_dir / "results" / "claimbench_run.json", default={}) or {}
    test_result = read_json(run_dir / "results" / "test_result.json", default=None)
    decision = read_json(run_dir / "results" / "tracegate_decision.json", default={}) or {}

    diff = analyze_diff(baseline_dir, repo_dir)
    code_oracle = evaluate_code_oracle(repo_dir, task)
    claim_decision = evaluate_claim_decision(task, decision)
    plan_oracle = score_verification_plan(task, {**decision, **claim_decision})
    plan_metrics = plan_quality_metrics(plan_oracle)
    execution = execution_metrics(run_result, test_result)
    evidence_metrics = evidence_decision_metrics(claim_decision)
    pollution = pollution_metrics(
        task=task,
        context_group=str(context_group),
        modified_files=diff.get("modified_files", []),
        decision_present=bool(claim_decision["decision_present"]),
        evidence_aware_decision=bool(evidence_metrics["evidence_aware_decision"]),
        destructive_change=bool(code_oracle["destructive_change"]),
    )
    semantic = claim_semantic_metrics(
        task=task,
        code_oracle=code_oracle,
        claim_oracle=claim_decision,
        plan_metrics=plan_metrics,
        test_success=bool(execution["test_success"]),
        pollution=bool(pollution["pollution"]),
    )
    junit = (test_result or {}).get("junit", {})
    request = run_result.get("request", {})
    result = {
        "run_dir": _display_path(run_dir),
        "model": metadata.get("model", {}).get("id"),
        "task_id": task.get("id"),
        "task_module": task.get("module"),
        "task_title": task.get("title"),
        "pitfall": task.get("pitfall"),
        "claim_id": task.get("claim_id"),
        "evidence_status": task.get("evidence_status"),
        "expected_decision": task.get("expected_decision"),
        "decision": claim_decision.get("decision"),
        "context_group": context_group,
        "claimbench_status": run_result.get("status"),
        "patch_present": request.get("patch_present"),
        "decision_present": claim_decision.get("decision_present"),
        "skip_reason": None if test_result is None else test_result.get("skip_reason"),
        "test_returncode": None if test_result is None else test_result.get("returncode"),
        "test_fail_count": None if test_result is None else int(junit.get("failures", 0)) + int(junit.get("errors", 0)),
        "context_tokens": metadata.get("prompt", {}).get("context_tokens", 0),
        "selected_context_ids": metadata.get("prompt", {}).get("selected_context_ids", []),
        "code_oracle": code_oracle,
        "claim_oracle": claim_decision,
        "plan_oracle": plan_oracle,
        "verification_plan": decision.get("verification_plan", ""),
        **execution,
        **evidence_metrics,
        **plan_metrics,
        **pollution,
        **semantic,
        **diff,
    }
    write_json(run_dir / "results" / "claim_metrics.json", result)
    return result


def collect_claim_results(runs_dir: Path = RUNS_CLAIM_DIR) -> list[dict[str, Any]]:
    results = [collect_claim_run(run_dir) for run_dir in find_run_dirs(runs_dir)]
    write_json(runs_dir / "results.json", results)
    return results
