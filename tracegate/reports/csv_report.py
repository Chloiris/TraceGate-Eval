from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "task_id",
    "task_module",
    "task_title",
    "context_group",
    "deepseek_status",
    "success",
    "violated_history_constraint",
    "repeated_failed_attempt",
    "pollution_flag",
    "touched_files_count",
    "patch_lines_added",
    "patch_lines_deleted",
    "test_fail_count",
    "skip_reason",
    "context_tokens",
    "run_dir",
]


def write_csv_report(results: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow({field: result.get(field) for field in CSV_FIELDS})
    return output_path
