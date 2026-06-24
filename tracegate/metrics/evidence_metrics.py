from __future__ import annotations

from typing import Any


def evidence_decision_metrics(claim_decision: dict[str, Any]) -> dict[str, bool]:
    return {
        "decision_present": bool(claim_decision.get("decision_present")),
        "evidence_aware_decision": bool(claim_decision.get("evidence_aware_decision")),
    }
