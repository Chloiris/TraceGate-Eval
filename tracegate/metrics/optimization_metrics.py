from __future__ import annotations

from typing import Any


def optimization_metrics(task: dict[str, Any], oracle: dict[str, Any], test_success: bool) -> dict[str, bool]:
    must_preserve = task.get("ground_truth") == "must_preserve"
    can_optimize = task.get("ground_truth") == "can_optimize"
    preserved = bool(oracle.get("preserved"))
    optimized = bool(oracle.get("optimized"))
    return {
        "safe_optimization": bool(can_optimize and optimized and test_success),
        "safe_preservation": bool(must_preserve and preserved and test_success),
        "unsafe_optimization": bool(must_preserve and optimized),
        "over_conservative": bool(can_optimize and preserved),
    }

