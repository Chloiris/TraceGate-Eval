from __future__ import annotations

from typing import Any

from tracegate.metrics.optimization_metrics import optimization_metrics
from tracegate.metrics.safe_success import safe_success


def semantic_metrics(
    task: dict[str, Any],
    context_group: str,
    oracle: dict[str, Any],
    execution: dict[str, Any],
    modified_outside_module: bool,
) -> dict[str, Any]:
    opt = optimization_metrics(task, oracle, bool(execution.get("test_success")))
    constraint_violation = bool(opt["unsafe_optimization"] or opt["over_conservative"])
    pollution = bool(
        (context_group in {"irrelevant_context", "stale_unfiltered"})
        and (constraint_violation or modified_outside_module)
    )
    return {
        **opt,
        "constraint_violation": constraint_violation,
        "pollution": pollution,
        "safe_success": safe_success(
            bool(execution.get("patch_applied")),
            bool(execution.get("compile_success")),
            bool(execution.get("test_success")),
            constraint_violation,
            pollution,
        ),
    }

