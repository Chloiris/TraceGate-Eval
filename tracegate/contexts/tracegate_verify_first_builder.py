from __future__ import annotations

from typing import Any

from tracegate.claims.claim_evidence_resolver import evidence_narrative
from tracegate.claims.verification_plan_builder import build_verification_plan


def build_tracegate_verify_first(task: dict[str, Any], _contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    status = task.get("evidence_status")
    plan = "\n".join(f"- {item}" for item in build_verification_plan(task))
    if status in {"unknown", "conflicting"}:
        guidance = (
            "TraceGate verification gate: do not remove or collapse the compatibility path yet. "
            "Return a verification-oriented decision with concrete checks."
        )
    else:
        guidance = (
            "TraceGate verification gate: use the attached evidence before changing compatibility behavior, "
            "and keep the change reversible if there is any remaining doubt."
        )
    return (
        "Verification-first claim packet:\n"
        f"- Claim: {task['claim_text']}\n"
        f"- Validity condition: {task['validity_condition']}\n\n"
        "Evidence considered:\n"
        f"{evidence_narrative(task)}\n\n"
        f"{guidance}\n\n"
        "Suggested verification steps if evidence is not enough:\n"
        f"{plan}",
        [str(task.get("claim_id")), f"{task.get('claim_id')}:verify_first"],
    )
