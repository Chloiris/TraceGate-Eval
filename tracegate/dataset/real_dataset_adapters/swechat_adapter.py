from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.dataset.real_dataset_adapters.common import normalize_claim, read_jsonl


SIGNAL_KEYS = {"correction", "failed_tool_call", "rollback", "rejected_patch", "user_correction"}


def _session_events(row: dict[str, Any]) -> list[dict[str, Any]]:
    events = row.get("events") or row.get("messages") or row.get("turns") or []
    return [event for event in events if isinstance(event, dict)]


def load_swechat_claims(path: Path) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for row in read_jsonl(path):
        session_id = str(row.get("session_id") or row.get("id") or f"line-{row['_line']}")
        module = str(row.get("module") or row.get("repo") or "external")
        for index, event in enumerate(_session_events(row), start=1):
            kind = str(event.get("type") or event.get("role") or "").lower()
            text = str(event.get("content") or event.get("text") or event.get("message") or "")
            if kind not in SIGNAL_KEYS and not any(token in text.lower() for token in ["rollback", "revert", "failed", "do not"]):
                continue
            claims.append(
                normalize_claim(
                    claim_id=f"swe-chat:{session_id}:{index}",
                    module=module,
                    claim_text=text,
                    source="swechat",
                    evidence=[kind],
                )
            )
    return claims
