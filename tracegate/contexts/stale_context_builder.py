from __future__ import annotations

from typing import Any


def build_stale_items(task: dict[str, Any], contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    module = task.get("module")
    items = [item for item in contexts if item.get("module") == module and item.get("type") == "process_constraint"]
    # Put the misleading status first to make stale/active conflict visible.
    if task.get("ground_truth") == "must_preserve":
        items.sort(key=lambda item: 0 if item.get("status") == "stale" else 1)
    else:
        items.sort(key=lambda item: 0 if item.get("status") == "active" else 1)
    return items

