from __future__ import annotations

from collections import Counter
from typing import Any

from tracegate.core.models import AdvisoryDecision, EvalCase, EvidenceStatus


def distribution(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def compute_metrics(cases: list[EvalCase], advisories: list[AdvisoryDecision]) -> dict[str, Any]:
    scored_cases = [case for case in cases if case.is_scored_real_case]
    excluded_cases = [case for case in cases if not case.is_scored_real_case]
    status_distribution = distribution([case.evidence_status.value for case in cases])
    decision_distribution = distribution([item.decision for item in advisories])
    risk_level_distribution = distribution([item.risk_level for item in advisories])
    pollution_count = sum(1 for item in advisories if item.pollution_flags)
    manual_count = sum(1 for case in cases if case.evidence_status == EvidenceStatus.NEEDS_MANUAL_REVIEW)
    provenance_complete = sum(1 for case in scored_cases if (case.source_url or case.repo_url) and case.evidence_items)
    unsafe_allow_count = sum(
        1
        for item in advisories
        if item.evidence_status in {"unknown", "conflicting"} and item.decision in {"preserve", "optimize"}
    )
    verify_unknown_conflicting = [
        item
        for item in advisories
        if item.evidence_status in {"unknown", "conflicting"}
    ]
    verify_first_count = sum(1 for item in verify_unknown_conflicting if item.decision in {"verify_first", "detect_conflict"})

    total = len(cases)
    scored = len(scored_cases)
    return {
        "benchmark_note": "small real-data smoke benchmark, not a statistically significant benchmark",
        "num_cases_total": total,
        "num_cases_scored": scored,
        "num_cases_excluded": len(excluded_cases),
        "status_distribution": status_distribution,
        "decision_distribution": decision_distribution,
        "risk_level_distribution": risk_level_distribution,
        "pollution_flag_rate": pollution_count / max(len(advisories), 1),
        "needs_manual_review_rate": manual_count / max(total, 1),
        "provenance_completeness_rate": provenance_complete / max(scored, 1),
        "unsafe_allow_rate": unsafe_allow_count / max(len(advisories), 1),
        "verify_first_rate_on_unknown_or_conflicting": verify_first_count / max(len(verify_unknown_conflicting), 1),
        "excluded_cases": [
            {
                "case_id": case.case_id,
                "evidence_status": case.evidence_status.value,
                "reason": case.exclusion_reason or "not eligible for scored real metrics",
            }
            for case in excluded_cases
        ],
    }
