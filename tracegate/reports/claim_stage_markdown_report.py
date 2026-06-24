from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from tracegate.config import CLAIM_CONTEXT_GROUPS, CLAIM_EVIDENCE_STATUSES


def _count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _rate(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}" if denominator else "0/0"


def _avg_quality(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "0.00"
    return f"{sum(int(row.get('verification_plan_quality') or 0) for row in rows) / len(rows):.2f}"


def build_claim_stage_markdown(results: list[dict[str, Any]]) -> str:
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_context[str(result.get("context_group"))].append(result)
        by_status[str(result.get("evidence_status"))].append(result)

    lines = [
        "# TraceGate ClaimBench Report",
        "",
        "## Summary by Context Group",
        "",
        "| Context | Runs | Safe Success | Destructive Change | Pollution | Avg Plan Quality |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for context in CLAIM_CONTEXT_GROUPS:
        rows = by_context.get(context, [])
        runs = len(rows)
        lines.append(
            "| {context} | {runs} | {safe} | {destructive} | {pollution} | {quality} |".format(
                context=context,
                runs=runs,
                safe=_rate(_count(rows, "safe_success"), runs),
                destructive=_rate(_count(rows, "destructive_change"), runs),
                pollution=_rate(_count(rows, "pollution"), runs),
                quality=_avg_quality(rows),
            )
        )

    lines.extend(
        [
            "",
            "## Summary by Evidence Status",
            "",
            "| Evidence | Runs | Correct Decision | Test Success | Destructive Change | Avg Plan Quality |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for status in CLAIM_EVIDENCE_STATUSES:
        rows = by_status.get(status, [])
        runs = len(rows)
        lines.append(
            "| {status} | {runs} | {decision} | {test} | {destructive} | {quality} |".format(
                status=status,
                runs=runs,
                decision=_rate(_count(rows, "evidence_aware_decision"), runs),
                test=_rate(_count(rows, "test_success"), runs),
                destructive=_rate(_count(rows, "destructive_change"), runs),
                quality=_avg_quality(rows),
            )
        )

    lines.extend(
        [
            "",
            "## Detail",
            "",
            "| Task | Evidence | Context | Decision | Expected | Test | Safe | Destructive | Plan Q | Pollution | Run Dir |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for result in sorted(results, key=lambda item: (str(item.get("task_id")), str(item.get("context_group")))):
        lines.append(
            "| {task} | {evidence} | {context} | {decision} | {expected} | {test} | {safe} | {destructive} | {quality} | {pollution} | `{run_dir}` |".format(
                task=result.get("task_id"),
                evidence=result.get("evidence_status"),
                context=result.get("context_group"),
                decision=result.get("decision"),
                expected=result.get("expected_decision"),
                test=result.get("test_success"),
                safe=result.get("safe_success"),
                destructive=result.get("destructive_change"),
                quality=result.get("verification_plan_quality"),
                pollution=result.get("pollution"),
                run_dir=result.get("run_dir"),
            )
        )
    return "\n".join(lines) + "\n"


def write_claim_stage_markdown(results: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_claim_stage_markdown(results), encoding="utf-8")
    return output_path
