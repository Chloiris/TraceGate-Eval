from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


FIELDS = [
    "model",
    "task_id",
    "task_module",
    "lifecycle",
    "ground_truth",
    "context_group",
    "deepseek_status",
    "patch_applied",
    "compile_success",
    "test_success",
    "safe_success",
    "safe_optimization",
    "safe_preservation",
    "unsafe_optimization",
    "over_conservative",
    "constraint_violation",
    "pollution",
    "touched_files_count",
    "patch_lines_added",
    "patch_lines_deleted",
    "test_fail_count",
    "skip_reason",
    "context_tokens",
    "run_dir",
]


def write_stage2_csv(results: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow({field: result.get(field) for field in FIELDS})
    return output_path

