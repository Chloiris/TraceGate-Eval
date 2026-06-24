from __future__ import annotations

from typing import Any


def plan_quality_metrics(plan_oracle: dict[str, Any]) -> dict[str, Any]:
    quality = int(plan_oracle.get("verification_plan_quality", 0) or 0)
    return {
        "verification_plan_present": bool(plan_oracle.get("verification_plan_present")),
        "verification_plan_quality": max(0, min(3, quality)),
    }
