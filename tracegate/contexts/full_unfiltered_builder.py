from __future__ import annotations

from typing import Any

from tracegate.claims.claim_evidence_resolver import evidence_narrative


def build_full_unfiltered_claims(task: dict[str, Any], contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    selected_ids: list[str] = []
    lines = [
        "Unfiltered claim archive:",
        "The following notes may include unrelated modules, old records, and incomplete claims.",
    ]
    for item in contexts:
        selected_ids.append(str(item["id"]))
        lines.append(f"- [{item['module']}/{item['type']}] {item['content']}")
    lines.extend(
        [
            "",
            "Current task evidence packet:",
            f"- Claim: {task['claim_text']}",
            f"- Validity condition: {task['validity_condition']}",
            evidence_narrative(task),
            "",
            "Additional same-scope note:",
            f"- {task['misleading_evidence']}",
        ]
    )
    selected_ids.append(f"{task.get('claim_id')}:full_packet")
    return "\n".join(lines), selected_ids
