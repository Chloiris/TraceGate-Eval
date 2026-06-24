from __future__ import annotations

from typing import Any


def context_line(item: dict[str, Any]) -> str:
    return f"- [{item.get('id')} / {item.get('status')}] {item.get('content')}"


def render_context(title: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return "无额外历史上下文。"
    return title + "\n" + "\n".join(context_line(item) for item in items)

