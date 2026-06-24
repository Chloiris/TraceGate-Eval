from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.dataset.real_dataset_adapters.common import normalize_claim, read_jsonl


def load_swe_contextbench_claims(path: Path) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for row in read_jsonl(path):
        task_id = str(row.get("task_id") or row.get("id") or f"line-{row['_line']}")
        module = str(row.get("module") or row.get("repo") or "external")
        experiences = row.get("experience") or row.get("experiences") or row.get("base_task_experience") or []
        if isinstance(experiences, str):
            experiences = [experiences]
        for index, experience in enumerate(experiences, start=1):
            claims.append(
                normalize_claim(
                    claim_id=f"swe-contextbench:{task_id}:{index}",
                    module=module,
                    claim_text=str(experience),
                    source="swe_contextbench",
                    evidence=[str(row.get("target_task") or row.get("task") or "")],
                )
            )
    return claims
