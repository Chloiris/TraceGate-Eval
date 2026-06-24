from __future__ import annotations

from typing import Any


def build_irrelevant_items(task: dict[str, Any], contexts: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    task_id = str(task.get("id", "S2T01"))
    try:
        offset = int(task_id.replace("S2T", "")) - 1
    except ValueError:
        offset = 0
    items = [
        item for item in contexts
        if item.get("module") != task.get("module") and item.get("type") == "process_constraint"
    ]
    if items:
        offset = offset % len(items)
        items = items[offset:] + items[:offset]
    return items[:limit]

