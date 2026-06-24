from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line"] = line_no
        rows.append(row)
    return rows


def normalize_claim(
    *,
    claim_id: str,
    module: str,
    claim_text: str,
    source: str,
    validity_condition: str = "Imported claim; resolve validity with task-local evidence.",
    evidence: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "id": claim_id,
        "module": module,
        "pitfall": "imported",
        "claim_text": claim_text,
        "validity_condition": validity_condition,
        "source": source,
        "evidence": list(evidence),
    }
