from __future__ import annotations

from typing import Any


def build_misleading_same_scope(task: dict[str, Any], _contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return (
        "Same-scope historical note from a cleanup thread:\n"
        f"- Claim discussed: {task['claim_text']}\n"
        f"- Note: {task['misleading_evidence']}\n\n"
        "This note may be incomplete. Cross-check it against code behavior and avoid irreversible changes without evidence.",
        [f"{task.get('claim_id')}:misleading"],
    )
