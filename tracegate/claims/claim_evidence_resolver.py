from __future__ import annotations

from typing import Any


def evidence_profile(task: dict[str, Any]) -> dict[str, Any]:
    status = str(task.get("evidence_status", "unknown"))
    evidence = [str(item) for item in task.get("evidence", [])]
    return {
        "status": status,
        "has_supporting_signal": status == "active",
        "has_retirement_signal": status == "stale",
        "has_missing_signal": status == "unknown",
        "has_disagreement": status == "conflicting",
        "evidence": evidence,
    }


def evidence_narrative(task: dict[str, Any]) -> str:
    profile = evidence_profile(task)
    evidence = profile["evidence"]
    if not evidence:
        return "No current evidence was attached to this claim."
    return "\n".join(f"- {item}" for item in evidence)
