from __future__ import annotations

from typing import Any

from tracegate.config import CLAIM_CONTEXT_GROUPS
from tracegate.web.data_loader import load_dataset
from tracegate.web.schemas import AnalyzeDemoRequest


def overview() -> dict[str, Any]:
    data = load_dataset()
    return {
        "project_name": data["project_name"],
        "one_sentence_intro": data["one_sentence_intro"],
        "current_stage": data["current_stage"],
        "total_tasks": data["total_tasks"],
        "total_runs": data["total_runs"],
        "model": data["model"],
        "key_metrics": data["key_metrics"],
        "context_groups": data["context_groups"],
        "evidence_statuses": data["evidence_statuses"],
        "data_source": data["data_source"],
    }


def context_groups() -> list[dict[str, Any]]:
    return load_dataset()["context_groups"]


def evidence_statuses() -> list[dict[str, Any]]:
    return load_dataset()["evidence_statuses"]


def tasks() -> list[dict[str, Any]]:
    return load_dataset()["tasks"]


def task_detail(task_id: str) -> dict[str, Any] | None:
    data = load_dataset()
    task = next((item for item in data["tasks"] if item["task_id"].lower() == task_id.lower()), None)
    if task is None:
        return None
    results = [row for row in data["results"] if str(row.get("task_id", "")).lower() == task_id.lower()]
    return {
        **task,
        "context_groups": list(CLAIM_CONTEXT_GROUPS),
        "available_results": results,
    }


def results(context_group: str | None = None, evidence_status: str | None = None, module: str | None = None) -> dict[str, Any]:
    rows = list(load_dataset()["results"])
    if context_group:
        rows = [row for row in rows if row.get("context_group") == context_group]
    if evidence_status:
        rows = [row for row in rows if row.get("evidence_status") == evidence_status]
    if module:
        rows = [row for row in rows if row.get("module") == module]
    return {
        "data_source": "real_results" if rows else load_dataset()["data_source"],
        "count": len(rows),
        "filters": {
            "context_group": context_group,
            "evidence_status": evidence_status,
            "module": module,
        },
        "results": rows,
    }


def analyze_demo(request: AnalyzeDemoRequest) -> dict[str, Any]:
    evidence = request.evidence.lower()
    claim = request.claim.lower()
    risk_flags: list[str] = []

    conflict_terms = {"conflict", "conflicting", "contradict", "disagree", "both", "however", "but"}
    unknown_terms = {"unknown", "unavailable", "missing", "no owner", "insufficient", "not recorded", "no current"}
    stale_terms = {"stale", "retired", "no longer", "completed migration", "blocked", "exactly-once", "obsolete"}
    active_terms = {"still", "active", "confirmed", "requires", "logs show", "production", "current"}

    if request.context_group == "misleading_same_scope":
        risk_flags.append("misleading_same_scope_context")
    if not evidence.strip():
        risk_flags.append("missing_evidence")

    if any(term in evidence for term in conflict_terms) and any(term in evidence for term in active_terms | stale_terms):
        decision = "conflict_detected"
        reason = "The evidence appears to contain competing signals, so the safe action is escalation before code changes."
        risk_flags.append("conflicting_evidence")
    elif request.context_group == "tracegate_verify_first" or any(term in evidence for term in unknown_terms):
        decision = "verify_first"
        reason = "The evidence is incomplete, so a destructive compatibility change should wait for verification."
        risk_flags.append("insufficient_evidence")
    elif any(term in evidence for term in stale_terms):
        decision = "optimize"
        reason = "The evidence suggests the historical claim may be stale and the legacy path can be considered for cleanup."
    elif any(term in evidence for term in active_terms) or any(term in claim for term in {"must not", "must keep", "still"}):
        decision = "preserve"
        reason = "The evidence supports preserving the historical compatibility claim."
    else:
        decision = "verify_first"
        reason = "The rule-based demo cannot establish current claim validity from the provided evidence."
        risk_flags.append("low_confidence")

    if decision in {"verify_first", "conflict_detected"}:
        verification_plan = [
            "Check current telemetry or owner-confirmed evidence for the claim.",
            "Add or run a characterization test around the compatibility behavior.",
            "Use a feature flag or human review before any destructive cleanup.",
        ]
    elif decision == "preserve":
        verification_plan = [
            "Run the relevant regression tests.",
            "Confirm the compatibility path remains present in the target module.",
        ]
    else:
        verification_plan = [
            "Run regression tests after cleanup.",
            "Confirm current evidence shows the old compatibility dependency is retired.",
        ]

    return {
        "suggested_decision": decision,
        "reason": reason,
        "verification_plan": verification_plan,
        "risk_flags": risk_flags,
        "data_source": "rule_based_demo",
    }

