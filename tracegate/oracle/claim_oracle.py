from __future__ import annotations

from typing import Any


VALID_DECISIONS = {"preserve", "optimize", "verify_first", "conflict_detected"}


def normalize_decision(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    return text if text in VALID_DECISIONS else ""


def evaluate_claim_decision(task: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    actual = normalize_decision(decision.get("decision"))
    expected = str(task.get("expected_decision", ""))
    return {
        "expected_decision": expected,
        "decision": actual,
        "decision_present": bool(actual),
        "evidence_aware_decision": bool(actual and actual == expected),
    }
