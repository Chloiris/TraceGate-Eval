from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.dataset.real_dataset_adapters.common import normalize_claim, read_jsonl


def load_swebench_cl_claim_pairs(path: Path) -> list[dict[str, Any]]:
    rows = sorted(read_jsonl(path), key=lambda row: str(row.get("created_at") or row.get("time") or row.get("_line")))
    pairs: list[dict[str, Any]] = []
    prior_claims: list[dict[str, Any]] = []
    for row in rows:
        issue_id = str(row.get("issue_id") or row.get("id") or f"line-{row['_line']}")
        module = str(row.get("module") or row.get("repo") or "external")
        summary = str(row.get("summary") or row.get("title") or row.get("problem_statement") or "")
        if prior_claims:
            pairs.append(
                {
                    "target_issue_id": issue_id,
                    "module": module,
                    "target_task": summary,
                    "claims": prior_claims[-5:],
                }
            )
        prior_claims.append(
            normalize_claim(
                claim_id=f"swebench-cl:{issue_id}",
                module=module,
                claim_text=summary,
                source="swebench_cl",
                evidence=[str(row.get("resolution") or row.get("patch") or "")],
            )
        )
    return pairs
