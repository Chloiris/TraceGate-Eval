from __future__ import annotations

from typing import Any


def build_plain_claim(task: dict[str, Any], _contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    return (
        "Historical claim under review:\n"
        f"- {task['claim_text']}\n\n"
        "Treat this as a claim, not as proof. Its current validity depends on present-day evidence.",
        [str(task.get("claim_id"))],
    )
