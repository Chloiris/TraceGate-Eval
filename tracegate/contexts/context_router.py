from __future__ import annotations

from typing import Any

from tracegate.context.token_estimator import estimate_tokens
from tracegate.contexts.context_builder import render_context
from tracegate.contexts.irrelevant_context_builder import build_irrelevant_items
from tracegate.contexts.stale_context_builder import build_stale_items


def _module_items(task: dict[str, Any], contexts: list[dict[str, Any]], status: str | None = None) -> list[dict[str, Any]]:
    items = [item for item in contexts if item.get("module") == task.get("module")]
    if status is not None:
        items = [item for item in items if item.get("status") == status]
    return items


def build_stage2_context(task: dict[str, Any], group: str, contexts: list[dict[str, Any]]) -> tuple[str, list[str], int]:
    if group == "no_context":
        text = "无额外历史上下文。"
        return text, [], estimate_tokens(text)
    if group == "result_history":
        items = [item for item in _module_items(task, contexts, "active") if item.get("type") == "result_history"]
        text = render_context("结果型历史上下文：", items)
        return text, [item["id"] for item in items], estimate_tokens(text)
    if group == "full_process":
        items = _module_items(task, contexts)
        text = render_context("完整过程上下文（可能包含过期记录）：", items)
        return text, [item["id"] for item in items], estimate_tokens(text)
    if group == "routed_process":
        desired_status = "active" if task.get("ground_truth") == "must_preserve" else "stale"
        items = [
            item for item in _module_items(task, contexts, desired_status)
            if item.get("type") in {"process_constraint", "failed_attempt"}
        ]
        text = render_context("按当前任务路由后的关键上下文：", items[:3])
        return text, [item["id"] for item in items[:3]], estimate_tokens(text)
    if group == "stale_unfiltered":
        items = build_stale_items(task, contexts)
        text = render_context("未过滤的陈旧/冲突上下文：", items)
        return text, [item["id"] for item in items], estimate_tokens(text)
    if group == "irrelevant_context":
        items = build_irrelevant_items(task, contexts)
        text = render_context("无关模块上下文：", items)
        return text, [item["id"] for item in items], estimate_tokens(text)
    raise ValueError(f"Unknown stage2 context group: {group}")

