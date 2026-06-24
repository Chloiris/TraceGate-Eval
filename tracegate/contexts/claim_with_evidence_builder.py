from __future__ import annotations

from typing import Any

from tracegate.claims.claim_evidence_resolver import evidence_narrative


def build_claim_with_evidence(task: dict[str, Any], _contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return (
        "Historical claim under review:\n"
        f"- {task['claim_text']}\n\n"
        f"Validity condition:\n- {task['validity_condition']}\n\n"
        "Current evidence:\n"
        f"{evidence_narrative(task)}",
        [str(task.get("claim_id")), f"{task.get('claim_id')}:evidence"],
    )
