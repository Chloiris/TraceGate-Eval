from __future__ import annotations

from pathlib import Path

from tracegate.core.models import EvalCase, EvidenceStatus
from tracegate.core.serialization import load_cases


class DatasetValidationError(ValueError):
    """Raised when normalized data is not eligible for real metrics."""


def validate_case(case: EvalCase, strict: bool) -> list[str]:
    errors: list[str] = []
    if case.is_synthetic and not case.excluded_from_real_metrics:
        errors.append("synthetic case must be excluded from real metrics")
    if case.is_real and case.is_synthetic:
        errors.append("case cannot be both real and synthetic")
    if case.is_scored_real_case:
        if not (case.source_url or case.repo_url):
            errors.append("scored case missing source_url or repo_url")
        if not case.evidence_items:
            errors.append("scored case missing evidence_items")
        if case.label_source == "unknown":
            errors.append("scored case label_source is unknown")
        if case.evidence_status == EvidenceStatus.NEEDS_MANUAL_REVIEW:
            errors.append("needs_manual_review case cannot be scored")
        if case.label_confidence < 0.7:
            errors.append("scored case label_confidence below 0.7")
        if not case.is_real:
            errors.append("scored case must be real")
        if case.is_synthetic:
            errors.append("scored case must not be synthetic")
    if strict and case.is_real and not case.excluded_from_real_metrics and not case.is_scored_real_case:
        errors.append("real included case failed scored-case eligibility")
    return errors


def validate_dataset(dataset_path: Path, strict: bool, min_cases: int) -> tuple[list[EvalCase], dict[str, object]]:
    cases = load_cases(dataset_path)
    errors: list[str] = []
    for case in cases:
        for error in validate_case(case, strict=strict):
            errors.append(f"{case.case_id}: {error}")
    scored = [case for case in cases if case.is_scored_real_case]
    excluded = [case for case in cases if not case.is_scored_real_case]
    if strict and len(scored) < min_cases:
        errors.append(f"strict mode requires at least {min_cases} scored real cases; found {len(scored)}")
    if errors:
        raise DatasetValidationError("\n".join(errors))
    return cases, {
        "num_cases_total": len(cases),
        "num_cases_scored": len(scored),
        "num_cases_excluded": len(excluded),
        "min_cases": min_cases,
        "strict": strict,
    }
