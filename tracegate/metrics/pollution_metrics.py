from __future__ import annotations

from typing import Any


def _outside_task_module(path: str, module: str) -> bool:
    normalized = path.replace("\\", "/")
    marker = "src/main/java/com/example/legacyshop/"
    if marker not in normalized:
        return False
    after = normalized.split(marker, 1)[1]
    return after.split("/", 1)[0] != module


def pollution_metrics(
    task: dict[str, Any],
    context_group: str,
    modified_files: list[str],
    decision_present: bool,
    evidence_aware_decision: bool,
    destructive_change: bool,
) -> dict[str, bool]:
    modified_outside_module = any(_outside_task_module(path, str(task.get("module"))) for path in modified_files)
    misleading_pollution = decision_present and context_group == "misleading_same_scope" and (
        not evidence_aware_decision or destructive_change
    )
    return {
        "modified_outside_module": modified_outside_module,
        "pollution": bool(modified_outside_module or misleading_pollution),
    }
