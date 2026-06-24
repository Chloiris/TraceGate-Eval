from __future__ import annotations

from typing import Any

from tracegate.context.compressor import compress_text


def _target_file_names(task: dict[str, Any]) -> set[str]:
    return {str(path).replace("\\", "/").split("/")[-1] for path in task.get("target_files", [])}


def score_context(task: dict[str, Any], context: dict[str, Any], include_inactive: bool = False) -> int:
    if not include_inactive and context.get("status") != "active":
        return -1

    score = 0
    if context.get("module") == task.get("module"):
        score += 3

    target_names = _target_file_names(task)
    relevance_names = {str(path).replace("\\", "/").split("/")[-1] for path in context.get("relevance_files", [])}
    if target_names & relevance_names:
        score += 3

    if context.get("status") == "active":
        score += 1

    if context.get("type") == "retained_constraint":
        score += 2
    elif context.get("type") == "failed_attempt":
        score += 1

    return score


def select_routed_context(
    task: dict[str, Any],
    context_items: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    scored = [
        (score_context(task, item), item)
        for item in context_items
        if item.get("status") == "active"
    ]
    scored = [(score, item) for score, item in scored if score > 0]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def select_result_history_context(
    task: dict[str, Any],
    context_items: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    items = [
        item
        for item in context_items
        if item.get("module") == task.get("module")
        and item.get("type") == "result_history"
        and item.get("status") == "active"
    ]
    return items[:limit]


def select_full_process_context(
    task: dict[str, Any],
    context_items: list[dict[str, Any]],
    historical_failures: list[dict[str, Any]],
    limit: int = 6,
) -> list[dict[str, Any]]:
    module = task.get("module")
    items = [item for item in context_items if item.get("module") == module]
    failure_items = [
        {
            "id": failure.get("id"),
            "module": failure.get("module"),
            "type": "historical_failure",
            "status": "process_record",
            "content": (
                f"历史失败：{failure.get('failed_attempt')} "
                f"失败原因：{failure.get('failure_reason')} "
                f"最终决策：{failure.get('final_decision')}"
            ),
            "relevance_files": [],
        }
        for failure in historical_failures
        if failure.get("module") == module
    ]
    return (items + failure_items)[:limit]


def select_irrelevant_context(
    task: dict[str, Any],
    context_items: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    module = task.get("module")
    other_items = [
        item
        for item in context_items
        if item.get("module") != module
        and item.get("status") == "active"
        and item.get("type") in {"retained_constraint", "failed_attempt"}
    ]
    # Keep deterministic contamination: rotate by task id so every module sees a different neighbor.
    task_num = int(str(task.get("id", "T01")).lstrip("T") or 1)
    if other_items:
        offset = (task_num - 1) % len(other_items)
        other_items = other_items[offset:] + other_items[:offset]
    return other_items[:limit]


def render_context_block(items: list[dict[str, Any]], title: str) -> str:
    if not items:
        return "无额外历史上下文。"
    lines = [f"{title}："]
    for item in items:
        marker = item.get("id", "context")
        status = item.get("status", "unknown")
        content = compress_text(str(item.get("content", "")))
        lines.append(f"- [{marker} / {status}] {content}")
    return "\n".join(lines)


def build_context_block(
    task: dict[str, Any],
    group: str,
    context_items: list[dict[str, Any]],
    historical_failures: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    if group == "no_context":
        return "无额外历史上下文。", []
    if group == "result_history":
        items = select_result_history_context(task, context_items)
        return render_context_block(items, "历史结果上下文"), items
    if group == "full_process":
        items = select_full_process_context(task, context_items, historical_failures)
        return render_context_block(items, "完整编码过程上下文"), items
    if group == "routed_process":
        items = select_routed_context(task, context_items)
        return render_context_block(items, f"{task.get('module')} 模块关键上下文"), items
    if group == "irrelevant_context":
        items = select_irrelevant_context(task, context_items)
        return render_context_block(items, "无关或污染上下文"), items
    raise ValueError(f"Unknown context group: {group}")

