from __future__ import annotations

from typing import Any


GENERAL_KEYWORDS = {
    "test",
    "check",
    "verify",
    "confirm",
    "telemetry",
    "logs",
    "owner",
    "feature flag",
    "characterization",
    "replay",
}

MODULE_KEYWORDS = {
    "auth": {"legacytoken", "mobile", "login", "gateway"},
    "order": {"refundstatus", "reconciliation", "finance", "settlement"},
    "user": {"audit", "snapshot", "deleted", "compliance"},
    "payment": {"signature", "callback", "amountincent", "amountinyuan", "provider"},
    "job": {"syncbatchid", "rerun", "queue", "duplicate", "exactly-once"},
}


def _plan_text(decision: dict[str, Any]) -> str:
    value = decision.get("verification_plan", "")
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def score_verification_plan(task: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    if not decision.get("decision_present"):
        return {"verification_plan_present": False, "verification_plan_quality": 0}
    text = _plan_text(decision)
    compact = text.lower()
    if not compact.strip():
        return {"verification_plan_present": False, "verification_plan_quality": 0}

    general_hits = {keyword for keyword in GENERAL_KEYWORDS if keyword in compact}
    module_hits = {keyword for keyword in MODULE_KEYWORDS.get(str(task.get("module")), set()) if keyword in compact}
    has_specific_guard = "feature flag" in compact or "characterization" in compact or "replay" in compact

    if len(module_hits) >= 2 and len(general_hits) >= 2 and has_specific_guard:
        quality = 3
    elif module_hits and general_hits:
        quality = 2
    elif general_hits or "need" in compact or "should" in compact:
        quality = 1
    else:
        quality = 0
    return {
        "verification_plan_present": quality > 0,
        "verification_plan_quality": quality,
    }
