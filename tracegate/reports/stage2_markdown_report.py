from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from tracegate.config import STAGE2_CONTEXT_GROUPS


def _count(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _rate(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}" if denominator else "0/0"


def build_stage2_markdown(results: list[dict[str, Any]]) -> str:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[(str(result.get("ground_truth")), str(result.get("context_group")))].append(result)
    lines = [
        "# TraceGate Stage2 Report",
        "",
        "## Summary by Ground Truth and Context",
        "",
        "| Ground Truth | Context | Runs | Success Rate | Safe Success Rate | Safe Optimization Rate | Safe Preservation Rate | Unsafe Optimization Rate | Over-Conservative Rate | Pollution Rate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for truth in ["must_preserve", "can_optimize"]:
        for context in STAGE2_CONTEXT_GROUPS:
            rows = grouped.get((truth, context), [])
            runs = len(rows)
            lines.append(
                "| {truth} | {context} | {runs} | {success} | {safe_success} | {safe_opt} | {safe_pres} | {unsafe} | {over} | {pollution} |".format(
                    truth=truth,
                    context=context,
                    runs=runs,
                    success=_rate(_count(rows, "test_success"), runs),
                    safe_success=_rate(_count(rows, "safe_success"), runs),
                    safe_opt=_rate(_count(rows, "safe_optimization"), runs),
                    safe_pres=_rate(_count(rows, "safe_preservation"), runs),
                    unsafe=_rate(_count(rows, "unsafe_optimization"), runs),
                    over=_rate(_count(rows, "over_conservative"), runs),
                    pollution=_rate(_count(rows, "pollution"), runs),
                )
            )
    lines.extend(
        [
            "",
            "## Detail",
            "",
            "| Task | Truth | Context | Status | Test | Oracle | Safe | Unsafe Opt | Over Conservative | Pollution | Run Dir |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for result in sorted(results, key=lambda item: (str(item.get("task_id")), str(item.get("context_group")))):
        oracle = result.get("oracle", {})
        lines.append(
            "| {task} | {truth} | {context} | {status} | {test} | preserved={preserved}, optimized={optimized} | {safe} | {unsafe} | {over} | {pollution} | `{run_dir}` |".format(
                task=result.get("task_id"),
                truth=result.get("ground_truth"),
                context=result.get("context_group"),
                status=result.get("deepseek_status"),
                test=result.get("test_success"),
                preserved=oracle.get("preserved"),
                optimized=oracle.get("optimized"),
                safe=result.get("safe_success"),
                unsafe=result.get("unsafe_optimization"),
                over=result.get("over_conservative"),
                pollution=result.get("pollution"),
                run_dir=result.get("run_dir"),
            )
        )
    return "\n".join(lines) + "\n"


def write_stage2_markdown(results: list[dict[str, Any]], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_stage2_markdown(results), encoding="utf-8")
    return output_path

