from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def _case_lines(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        f"# {title}",
        "",
        "| Task | Evidence | Context | Decision | Expected | Destructive | Pollution | Plan Q | Run Dir |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in sorted(rows, key=lambda item: (str(item.get("task_id")), str(item.get("context_group")))):
        lines.append(
            "| {task} | {evidence} | {context} | {decision} | {expected} | {destructive} | {pollution} | {quality} | `{run_dir}` |".format(
                task=row.get("task_id"),
                evidence=row.get("evidence_status"),
                context=row.get("context_group"),
                decision=row.get("decision"),
                expected=row.get("expected_decision"),
                destructive=row.get("destructive_change"),
                pollution=row.get("pollution"),
                quality=row.get("verification_plan_quality"),
                run_dir=row.get("run_dir"),
            )
        )
    if not rows:
        lines.append("| none |  |  |  |  |  |  |  |  |")
    return lines


def write_case_report(
    results: list[dict[str, Any]],
    output_path: Path,
    title: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> Path:
    rows = [row for row in results if predicate(row)]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(_case_lines(title, rows)) + "\n", encoding="utf-8")
    return output_path
