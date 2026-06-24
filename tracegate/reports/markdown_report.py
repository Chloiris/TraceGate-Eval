from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from tracegate.config import CONTEXT_GROUPS, CONTEXT_LABELS


def _bool_count(results: list[dict[str, Any]], key: str) -> int:
    return sum(1 for result in results if result.get(key) is True)


def _not_run_count(results: list[dict[str, Any]]) -> int:
    return sum(1 for result in results if result.get("success") is None)


def build_markdown_report(results: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result.get("context_group"))].append(result)

    lines = [
        "# TraceGate Eval Report",
        "",
        "## Summary by Context Group",
        "",
            "| Context | Runs | Success | Failed | Not Run | Constraint Violations | Pollution | Avg Context Tokens |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in CONTEXT_GROUPS:
        rows = grouped.get(group, [])
        avg_tokens = round(sum(int(row.get("context_tokens") or 0) for row in rows) / len(rows), 1) if rows else 0
        lines.append(
            "| {label} | {runs} | {success} | {failed} | {not_run} | {violations} | {pollution} | {tokens} |".format(
                label=CONTEXT_LABELS.get(group, group),
                runs=len(rows),
                success=_bool_count(rows, "success"),
                failed=sum(1 for row in rows if row.get("success") is False),
                not_run=_not_run_count(rows),
                violations=_bool_count(rows, "violated_history_constraint"),
                pollution=_bool_count(rows, "pollution_flag"),
                tokens=avg_tokens,
            )
        )

    lines.extend(
        [
            "",
            "## Run Details",
            "",
            "| Task | Context | Run Status | Success | Constraint Violation | Diff | Tests | Run Dir |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for result in sorted(results, key=lambda row: (str(row.get("task_id")), str(row.get("context_group")))):
        diff = f"+{result.get('patch_lines_added', 0)}/-{result.get('patch_lines_deleted', 0)} in {result.get('touched_files_count', 0)} files"
        if result.get("success") is None:
            tests = "not run"
        elif result.get("skip_reason"):
            tests = str(result.get("skip_reason"))
        else:
            tests = f"failures={result.get('test_fail_count')}"
        lines.append(
            "| {task} | {context} | {status} | {success} | {violation} | {diff} | {tests} | `{run_dir}` |".format(
                task=result.get("task_id"),
                context=result.get("context_group"),
                status=result.get("deepseek_status"),
                success=result.get("success"),
                violation=result.get("violated_history_constraint"),
                diff=diff,
                tests=tests,
                run_dir=result.get("run_dir"),
            )
        )
    return "\n".join(lines) + "\n"


def write_markdown_report(results: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_markdown_report(results), encoding="utf-8")
    return output_path
