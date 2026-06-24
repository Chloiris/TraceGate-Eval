from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


FIELDS = [
    "model",
    "task_id",
    "task_module",
    "pitfall",
    "claim_id",
    "evidence_status",
    "expected_decision",
    "decision",
    "context_group",
    "claimbench_status",
    "patch_present",
    "patch_applied",
    "compile_success",
    "tests_executed",
    "test_success",
    "junit_failures",
    "apply_failed",
    "safe_success",
    "safe_optimization",
    "safe_preservation",
    "unsafe_optimization",
    "over_conservative",
    "destructive_change",
    "evidence_aware_decision",
    "verification_plan_present",
    "verification_plan_quality",
    "pollution",
    "modified_outside_module",
    "touched_files_count",
    "patch_lines_added",
    "patch_lines_deleted",
    "context_tokens",
    "run_dir",
]


def write_claim_stage_csv(results: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow({field: result.get(field) for field in FIELDS})
    return output_path


def write_rows_csv(rows: list[dict[str, Any]], output_path: Path, fields: list[str]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})
    return output_path
