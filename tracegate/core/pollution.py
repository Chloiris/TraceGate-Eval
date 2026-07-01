from __future__ import annotations

from tracegate.core.models import EvalCase, EvidenceStatus


POLLUTION_TRIGGER_STATUSES = {
    EvidenceStatus.STALE,
    EvidenceStatus.UNKNOWN,
    EvidenceStatus.CONFLICTING,
    EvidenceStatus.NEEDS_MANUAL_REVIEW,
}


def detect_pollution(case: EvalCase) -> list[str]:
    flags: list[str] = []
    text = " ".join(
        [
            case.problem_statement,
            case.diff_summary,
            case.claim.claim_text,
            " ".join(item.evidence_text_excerpt for item in case.evidence_items),
        ]
    ).lower()
    certainty_terms = ["definitely", "safe to remove", "guaranteed", "no longer needed", "obsolete"]
    if case.evidence_status in POLLUTION_TRIGGER_STATUSES and any(term in text for term in certainty_terms):
        flags.append(f"certainty_from_{case.evidence_status.value}_evidence")
    if any(item.supports_or_contradicts == "unclear" for item in case.evidence_items) and "must" in text:
        flags.append("strong_claim_from_unclear_evidence")
    if any(item.supports_or_contradicts == "contradicts" for item in case.evidence_items):
        flags.append("contradicting_evidence_present")
    return flags
