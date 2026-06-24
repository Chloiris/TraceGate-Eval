from __future__ import annotations

from typing import Any

from tracegate.claims.claim_schema import expected_decision_for_status


def route_claim(task: dict[str, Any]) -> dict[str, Any]:
    status = str(task.get("evidence_status", "unknown"))
    decision = expected_decision_for_status(status)
    return {
        "claim_id": task.get("claim_id"),
        "module": task.get("module"),
        "decision": decision,
        "needs_verification": decision in {"verify_first", "conflict_detected"},
        "allow_destructive_change": decision == "optimize",
    }
