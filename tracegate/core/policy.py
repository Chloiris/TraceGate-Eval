from __future__ import annotations

from tracegate.core.models import AdvisoryDecision, EvalCase, EvidenceStatus, ExpectedDecision
from tracegate.core.pollution import detect_pollution


HIGH_RISK_FILE_KEYWORDS = [
    "auth",
    "payment",
    "security",
    "migration",
    "database",
    "delete",
    "deletion",
    "config",
    "ci",
    "permission",
    "token",
    "credential",
]


def evidence_supports_claim(case: EvalCase) -> bool:
    return any(item.supports_or_contradicts == "supports" for item in case.evidence_items)


def high_risk_file_hits(files_changed: list[str]) -> list[str]:
    hits: list[str] = []
    for file_path in files_changed:
        lowered = file_path.lower()
        for keyword in HIGH_RISK_FILE_KEYWORDS:
            if keyword in lowered and keyword not in hits:
                hits.append(keyword)
    return hits


def risk_level_from_score(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def expected_decision_for_status(case: EvalCase) -> ExpectedDecision:
    status = case.evidence_status
    if status == EvidenceStatus.ACTIVE and evidence_supports_claim(case):
        return ExpectedDecision.PRESERVE
    if status == EvidenceStatus.STALE:
        return ExpectedDecision.VERIFY_FIRST
    if status == EvidenceStatus.UNKNOWN:
        return ExpectedDecision.VERIFY_FIRST
    if status == EvidenceStatus.CONFLICTING:
        return ExpectedDecision.DETECT_CONFLICT
    return ExpectedDecision.NEEDS_MANUAL_REVIEW


def build_verification_plan(case: EvalCase, file_hits: list[str]) -> list[str]:
    touched = ", ".join(case.files_changed[:5]) if case.files_changed else "the touched files"
    if case.evidence_status == EvidenceStatus.ACTIVE:
        return [
            f"Inspect the current implementation around {touched}.",
            "Confirm the merged Pull Request evidence still describes the behavior being preserved.",
            "Run or add focused regression coverage before changing the claimed behavior.",
        ]
    if case.evidence_status == EvidenceStatus.STALE:
        return [
            "Verify whether the historical claim has been superseded by newer code, tests, or documentation.",
            f"Review recent changes around {touched} before optimizing.",
            "Only optimize after current evidence shows the old constraint no longer applies.",
        ]
    if case.evidence_status == EvidenceStatus.CONFLICTING:
        return [
            "Compare the supporting and contradicting evidence side by side.",
            "Ask the code owner to resolve the conflict or approve a feature flag / migration path.",
            "Avoid irreversible changes until the conflict is resolved.",
        ]
    if file_hits:
        return [
            f"Treat {', '.join(file_hits)}-sensitive files as requiring explicit verification.",
            "Find current tests, incident notes, or owner confirmation before changing behavior.",
            "Record the evidence used before merging.",
        ]
    return [
        "Find current repo evidence before changing the claimed behavior.",
        "Prefer a small compatibility test or owner confirmation before merge.",
    ]


def advise_case(case: EvalCase) -> AdvisoryDecision:
    decision = expected_decision_for_status(case)
    file_hits = high_risk_file_hits(case.files_changed)
    risk_score = 15
    requires_human_review = False

    if case.evidence_status == EvidenceStatus.ACTIVE:
        risk_score += 15
        if file_hits:
            risk_score += 20
    elif case.evidence_status == EvidenceStatus.STALE:
        risk_score += 35
        requires_human_review = True
    elif case.evidence_status == EvidenceStatus.UNKNOWN:
        risk_score += 45
        requires_human_review = True
    elif case.evidence_status == EvidenceStatus.CONFLICTING:
        risk_score += 65
        requires_human_review = True
    else:
        risk_score += 55
        requires_human_review = True

    risk_score += min(len(file_hits) * 5, 20)
    risk_score = min(risk_score, 100)
    risk_level = risk_level_from_score(risk_score)
    if case.evidence_status in {EvidenceStatus.UNKNOWN, EvidenceStatus.CONFLICTING} and risk_level == "low":
        risk_level = "medium"
    if case.evidence_status == EvidenceStatus.CONFLICTING and risk_level in {"low", "medium"}:
        risk_level = "high"

    pollution_flags = detect_pollution(case)
    limitations = [
        "Rule-based advisory only; no LLM or semantic judge was used.",
        "Small real-data smoke benchmark, not a statistically significant benchmark.",
    ]
    if case.label_source == "heuristic_verified":
        limitations.append("Evidence status is heuristic and should be manually reviewed before governance use.")

    touched = ", ".join(case.files_changed[:3]) if case.files_changed else "no files listed"
    return AdvisoryDecision(
        case_id=case.case_id,
        risk_level=risk_level,
        risk_score=risk_score,
        evidence_status=case.evidence_status.value,
        decision=decision.value,
        summary=f"{decision.value} for {case.repo}; touched files: {touched}",
        rationale=(
            f"Evidence status is {case.evidence_status.value}. "
            f"The baseline used {len(case.evidence_items)} evidence item(s) and {len(file_hits)} high-risk file signal(s)."
        ),
        evidence_used=[item.evidence_id for item in case.evidence_items],
        verification_plan=build_verification_plan(case, file_hits),
        pollution_flags=pollution_flags,
        limitations=limitations,
        requires_human_review=requires_human_review,
    )
