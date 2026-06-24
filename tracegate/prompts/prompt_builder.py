from __future__ import annotations

from importlib.resources import files
from typing import Any

from tracegate.config import CONTEXT_LABELS
from tracegate.context.selector import build_context_block
from tracegate.context.token_estimator import estimate_tokens


def _load_template(name: str) -> str:
    return (files("tracegate.prompts.templates") / name).read_text(encoding="utf-8")


def _replace(template: str, values: dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace("{{" + key + "}}", value)
    return result


def build_prompt(
    task: dict[str, Any],
    context_group: str,
    context_items: list[dict[str, Any]],
    historical_failures: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    context_block, selected_items = build_context_block(
        task=task,
        group=context_group,
        context_items=context_items,
        historical_failures=historical_failures,
    )

    base = _load_template("base_prompt.md")
    group_template = _load_template(f"{context_group}.md")
    required_tests = "\n".join(f"- {test}" for test in task.get("required_tests", [])) or "- mvn test"
    target_files = "\n".join(f"- {path}" for path in task.get("target_files", [])) or "- 由你判断"
    hidden_constraints = "\n".join(f"- {item}" for item in task.get("hidden_constraints", [])) or "- 无"

    values = {
        "task_id": str(task.get("id", "")),
        "task_title": str(task.get("title", "")),
        "task_module": str(task.get("module", "")),
        "task_instruction": str(task.get("instruction", "")),
        "context_group": context_group,
        "context_group_label": CONTEXT_LABELS.get(context_group, context_group),
        "context_block": context_block,
        "group_guidance": group_template.strip(),
        "required_tests": required_tests,
        "target_files": target_files,
        "hidden_constraints": hidden_constraints,
    }
    prompt = _replace(base, values)
    metadata = {
        "context_tokens": estimate_tokens(context_block),
        "selected_context_ids": [item.get("id") for item in selected_items],
    }
    return prompt, metadata

