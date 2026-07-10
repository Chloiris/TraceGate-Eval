from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .schemas import ComponentStatus


class EvalArtifactError(RuntimeError):
    """Raised when checked-in evaluation evidence is missing or invalid."""


def _required_paths(root: Path) -> tuple[Path, Path, Path]:
    return (
        root / "datasets" / "real_min" / "manifest.json",
        root / "runs" / "latest" / "metrics.json",
        root / "reports_claim" / "claim_stage_results.csv",
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EvalArtifactError(f"{path.name} must contain a JSON object")
    return payload


def _bool_field(row: dict[str, str], name: str) -> bool:
    value = row.get(name, "").strip().lower()
    if value not in {"true", "false"}:
        raise EvalArtifactError(f"ClaimBench column {name} must contain true or false")
    return value == "true"


def evaluation_summary(root: Path) -> dict[str, Any]:
    """Load real, checked-in TraceGate Eval and ClaimBench evidence.

    This function never substitutes defaults for missing metrics. Every value in
    the response is either read from an artifact or derived from its rows.
    """

    manifest_path, metrics_path, claim_results_path = _required_paths(root)
    missing = [path.relative_to(root).as_posix() for path in _required_paths(root) if not path.is_file()]
    if missing:
        raise EvalArtifactError("Missing checked-in artifact(s): " + ", ".join(missing))

    try:
        manifest = _load_json_object(manifest_path)
        metrics = _load_json_object(metrics_path)
        with claim_results_path.open(newline="", encoding="utf-8") as handle:
            raw_rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error, json.JSONDecodeError) as exc:
        raise EvalArtifactError(f"Evaluation artifact could not be read: {type(exc).__name__}") from exc

    if manifest.get("is_real_dataset") is not True:
        raise EvalArtifactError("The dataset manifest is not marked as real")
    if manifest.get("contains_synthetic") is not False or manifest.get("used_fallback_data") is not False:
        raise EvalArtifactError("The real-data manifest reports synthetic or fallback data")
    if not raw_rows:
        raise EvalArtifactError("ClaimBench results contain no runs")

    required_columns = {
        "model",
        "task_id",
        "evidence_status",
        "expected_decision",
        "decision",
        "context_group",
        "claimbench_status",
        "safe_success",
        "evidence_aware_decision",
        "context_tokens",
        "run_dir",
    }
    if not required_columns.issubset(raw_rows[0]):
        missing_columns = sorted(required_columns.difference(raw_rows[0]))
        raise EvalArtifactError("ClaimBench results are missing column(s): " + ", ".join(missing_columns))

    cases: list[dict[str, Any]] = []
    model_counts: Counter[str] = Counter()
    context_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    decision_counts: Counter[str] = Counter()
    safe_successes = 0
    evidence_aware = 0
    for row in raw_rows:
        try:
            context_tokens = int(row["context_tokens"])
        except (TypeError, ValueError) as exc:
            raise EvalArtifactError("ClaimBench context_tokens must be an integer") from exc
        safe_success = _bool_field(row, "safe_success")
        aware = _bool_field(row, "evidence_aware_decision")
        model_counts[row["model"]] += 1
        context_counts[row["context_group"]] += 1
        status_counts[row["evidence_status"]] += 1
        decision_counts[row["decision"]] += 1
        safe_successes += int(safe_success)
        evidence_aware += int(aware)
        cases.append(
            {
                "model": row["model"],
                "task_id": row["task_id"],
                "evidence_status": row["evidence_status"],
                "expected_decision": row["expected_decision"],
                "decision": row["decision"],
                "context_group": row["context_group"],
                "claimbench_status": row["claimbench_status"],
                "safe_success": safe_success,
                "evidence_aware_decision": aware,
                "context_tokens": context_tokens,
                "run_dir": row["run_dir"].replace("\\", "/"),
            }
        )

    artifact_paths = (manifest_path, metrics_path, claim_results_path)
    return {
        "benchmark_name": str(metrics["benchmark_name"]),
        "benchmark_note": str(metrics["benchmark_note"]),
        "dataset_sha256": str(manifest["dataset_sha256"]),
        "is_real_dataset": True,
        "case_count": int(manifest["num_cases_scored"]),
        "claimbench_run_count": len(cases),
        "status_distribution": dict(manifest["status_distribution"]),
        "risk_distribution": dict(metrics["risk_level_distribution"]),
        "decision_distribution": dict(metrics["decision_distribution"]),
        "metrics": {
            "provenance_completeness_rate": float(metrics["provenance_completeness_rate"]),
            "unsafe_allow_rate": float(metrics["unsafe_allow_rate"]),
            "verify_first_rate_on_unknown_or_conflicting": float(
                metrics["verify_first_rate_on_unknown_or_conflicting"]
            ),
            "pollution_flag_rate": float(metrics["pollution_flag_rate"]),
            "claimbench_safe_success_rate": safe_successes / len(cases),
            "claimbench_evidence_aware_rate": evidence_aware / len(cases),
        },
        "models": dict(sorted(model_counts.items())),
        "context_groups": dict(sorted(context_counts.items())),
        "claimbench_status_distribution": dict(sorted(status_counts.items())),
        "claimbench_decision_distribution": dict(sorted(decision_counts.items())),
        "limitations": [str(item) for item in metrics["limitations"]],
        "artifacts": [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in artifact_paths
        ],
        "cases": cases,
    }


def eval_component_status(root: Path) -> ComponentStatus:
    manifest_path, _metrics_path, claim_results_path = _required_paths(root)
    missing = [
        path.relative_to(root).as_posix()
        for path in _required_paths(root)
        if not path.exists()
    ]
    if missing:
        return ComponentStatus(
            state="unavailable",
            configured=False,
            message="TraceGate Eval artifacts are unavailable.",
            detail="Missing checked-in artifact(s): " + ", ".join(missing),
        )
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        with claim_results_path.open(newline="", encoding="utf-8") as handle:
            claimbench_runs = sum(1 for _ in csv.DictReader(handle))
        real_cases = int(manifest["num_cases_scored"])
        is_real = manifest["is_real_dataset"] is True
    except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
        return ComponentStatus(
            state="error",
            configured=True,
            message="TraceGate Eval artifacts could not be validated.",
            detail=f"{type(exc).__name__}: artifact metadata is invalid",
        )
    if not is_real:
        return ComponentStatus(
            state="error",
            configured=True,
            message="TraceGate real-data manifest is not marked as real.",
            detail="No replacement metrics were substituted.",
        )
    return ComponentStatus(
        state="ready",
        configured=True,
        message="TraceGate Eval artifacts are available.",
        detail=f"checked_in_artifacts: real_cases={real_cases}, claimbench_runs={claimbench_runs}",
    )
