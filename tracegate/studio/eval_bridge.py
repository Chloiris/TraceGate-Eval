from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .schemas import ComponentStatus


def eval_component_status(root: Path) -> ComponentStatus:
    manifest_path = root / "datasets" / "real_min" / "manifest.json"
    claim_results_path = root / "reports_claim" / "claim_stage_results.csv"
    missing = [
        path.relative_to(root).as_posix()
        for path in (manifest_path, claim_results_path)
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
