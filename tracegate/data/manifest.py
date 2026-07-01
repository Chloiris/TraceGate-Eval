from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tracegate.core.serialization import load_cases, sha256_file, write_json


def build_dataset_manifest(dataset_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    cases = load_cases(dataset_path)
    scored = [case for case in cases if case.is_scored_real_case]
    excluded = [case for case in cases if not case.is_scored_real_case]
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": dataset_path.as_posix(),
        "dataset_sha256": sha256_file(dataset_path),
        "num_cases_total": len(cases),
        "num_cases_scored": len(scored),
        "num_cases_excluded": len(excluded),
        "source_datasets": sorted({case.source_dataset for case in cases}),
        "repos": sorted({case.repo for case in cases}),
        "status_distribution": dict(sorted(Counter(case.evidence_status.value for case in cases).items())),
        "is_real_dataset": all(case.is_real for case in cases),
        "contains_synthetic": any(case.is_synthetic for case in cases),
        "excluded_cases": [
            {
                "case_id": case.case_id,
                "reason": case.exclusion_reason or "not eligible for scored real metrics",
            }
            for case in excluded
        ],
        "used_fallback_data": False,
    }
    target = output_path or dataset_path.with_name("manifest.json")
    write_json(target, manifest)
    return manifest
