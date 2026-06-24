from __future__ import annotations

from typing import Any

from tracegate.claims.claim_evidence_resolver import evidence_narrative


def build_tracegate_routed(task: dict[str, Any], _contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    status = task.get("evidence_status")
    if status == "active":
        guidance = "TraceGate routing note: current signals support keeping the compatibility path while refactoring nearby code carefully."
    elif status == "stale":
        guidance = "TraceGate routing note: current signals support simplifying the compatibility path if tests keep the new contract safe."
    elif status == "conflicting":
        guidance = "TraceGate routing note: signals disagree. Avoid destructive changes until a human or feature-flagged rollout resolves the dispute."
    else:
        guidance = "TraceGate routing note: evidence is insufficient. Prefer a verification plan and non-destructive cleanup."
    return (
        "Claim routing packet:\n"
        f"- Claim: {task['claim_text']}\n"
        f"- Validity condition: {task['validity_condition']}\n\n"
        "Evidence considered:\n"
        f"{evidence_narrative(task)}\n\n"
        f"{guidance}",
        [str(task.get("claim_id")), f"{task.get('claim_id')}:routed"],
    )
