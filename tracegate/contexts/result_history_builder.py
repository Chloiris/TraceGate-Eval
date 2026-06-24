from __future__ import annotations

from typing import Any


def build_result_history(task: dict[str, Any], contexts: list[dict[str, Any]]) -> tuple[str, list[str]]:
    module = task.get("module")
    selected = [item for item in contexts if item.get("module") == module and item.get("type") == "result_history"]
    if not selected:
        return "No historical result notes were supplied.", []
    lines = ["Historical result notes:"]
    lines.extend(f"- {item['content']}" for item in selected)
    return "\n".join(lines), [str(item["id"]) for item in selected]
