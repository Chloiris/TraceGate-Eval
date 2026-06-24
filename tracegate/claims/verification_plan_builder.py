from __future__ import annotations

from typing import Any


def build_verification_plan(task: dict[str, Any]) -> list[str]:
    module = str(task.get("module"))
    if module == "auth":
        return [
            "Check login gateway telemetry for clients that read legacyToken.",
            "Add a characterization test around the login response before removing compatibility fields.",
            "Use a feature flag if legacyToken removal must be staged.",
        ]
    if module == "order":
        return [
            "Inventory refund reconciliation jobs that read refundStatus.",
            "Add a characterization test for paid orders with refundStatus transitions.",
            "Coordinate rollout behind a finance-reporting feature flag.",
        ]
    if module == "user":
        return [
            "Confirm audit snapshots cover both new and historical user actions.",
            "Add a characterization test for deleted-user audit drilldown.",
            "Gate physical deletion behind compliance approval or a feature flag.",
        ]
    if module == "payment":
        return [
            "Replay recent provider callbacks with amountInCent and amountInYuan payloads.",
            "Add a characterization test for the current signature contract.",
            "Use a feature flag while switching canonical amount units.",
        ]
    if module == "job":
        return [
            "Confirm queue exactly-once delivery for bill sync messages.",
            "Run a rerun drill that sends the same syncBatchId twice.",
            "Keep the local idempotency check behind a feature flag until duplicate delivery is disproven.",
        ]
    return [
        "Collect current owner confirmation for the claim.",
        "Add a characterization test for the current behavior.",
        "Use a feature flag for any destructive compatibility change.",
    ]
