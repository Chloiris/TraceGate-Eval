from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.core.models import EvalCase, EvidenceStatus
from tracegate.core.serialization import load_cases, read_jsonl


class DatasetValidationError(ValueError):
    """Raised when normalized data is not eligible for real metrics."""


def is_concrete_github_url(url: str | None) -> bool:
    if not url:
        return False
    if not url.startswith("https://github.com/"):
        return False
    concrete_markers = ["/pull/", "/issues/", "/commit/", "#discussion_r", "/files"]
    return any(marker in url for marker in concrete_markers)


def _default_manual_labels_path(dataset_path: Path) -> Path:
    return dataset_path.parent / "labels" / "manual_labels.jsonl"


def _default_review_queue_path(dataset_path: Path) -> Path:
    return dataset_path.parent / "labels" / "manual_review_queue.jsonl"


def _read_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return list()
    return read_jsonl(path)


def confirmed_manual_label_ids(labels_path: Path) -> set[str]:
    confirmed: set[str] = set()
    for row in _read_optional_jsonl(labels_path):
        if row.get("review_decision") != "promote":
            continue
        if row.get("label_source") != "manual_verified":
            continue
        try:
            confidence = float(row.get("label_confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < 0.7:
            continue
        candidate_id = row.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id:
            confirmed.add(candidate_id)
        case_data = row.get("case")
        if isinstance(case_data, dict) and case_data.get("case_id"):
            confirmed.add(str(case_data["case_id"]))
        case_id = row.get("case_id")
        if isinstance(case_id, str) and case_id:
            confirmed.add(case_id)
    return confirmed


def queued_candidate_ids(queue_path: Path) -> set[str]:
    ids: set[str] = set()
    for row in _read_optional_jsonl(queue_path):
        candidate_id = row.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id:
            ids.add(candidate_id)
    return ids


def validate_case(
    case: EvalCase,
    strict: bool,
    manual_label_ids: set[str] | None = None,
    review_queue_candidate_ids: set[str] | None = None,
) -> list[str]:
    manual_label_ids = manual_label_ids or set()
    review_queue_candidate_ids = review_queue_candidate_ids or set()
    errors: list[str] = []
    if case.is_synthetic and not case.excluded_from_real_metrics:
        errors.append("synthetic case must be excluded from real metrics")
    if case.is_real and case.is_synthetic:
        errors.append("case cannot be both real and synthetic")
    if case.label_source == "manual_verified" and case.case_id not in manual_label_ids:
        errors.append("manual_verified case missing manual_labels.jsonl confirmation")
    if case.is_scored_real_case:
        if case.case_id.startswith("hard_candidate:") and case.case_id not in manual_label_ids:
            errors.append("hard candidate cannot be scored before manual_labels.jsonl confirmation")
        if case.case_id in review_queue_candidate_ids and case.case_id not in manual_label_ids:
            errors.append("manual review queue candidate cannot be scored before manual confirmation")
        if not (case.source_url or case.repo_url):
            errors.append("scored case missing source_url or repo_url")
        concrete_urls = [
            case.source_url,
            case.issue_url,
            case.pr_url,
            case.claim.claim_source_url,
            *(item.evidence_url for item in case.evidence_items),
        ]
        if not any(is_concrete_github_url(url) for url in concrete_urls):
            errors.append("scored case missing concrete github.com PR/issue/comment/review/commit URL")
        if case.source_url and case.source_url.startswith("https://docs.github.com/"):
            errors.append("scored case source_url cannot be GitHub API documentation")
        if not case.evidence_items:
            errors.append("scored case missing evidence_items")
        if case.evidence_status in {EvidenceStatus.STALE, EvidenceStatus.CONFLICTING} and len(case.evidence_items) < 2:
            errors.append("stale/conflicting scored case requires at least 2 evidence_items")
        if case.evidence_status == EvidenceStatus.UNKNOWN and not case.rationale:
            errors.append("unknown scored case requires explicit insufficient-evidence rationale")
        if not case.rationale:
            errors.append("scored case missing rationale")
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


def validate_dataset(
    dataset_path: Path,
    strict: bool,
    min_cases: int,
    manual_labels_path: Path | None = None,
    review_queue_path: Path | None = None,
) -> tuple[list[EvalCase], dict[str, object]]:
    cases = load_cases(dataset_path)
    errors: list[str] = []
    labels_path = manual_labels_path or _default_manual_labels_path(dataset_path)
    queue_path = review_queue_path or _default_review_queue_path(dataset_path)
    manual_label_ids = confirmed_manual_label_ids(labels_path)
    review_queue_ids = queued_candidate_ids(queue_path)
    for case in cases:
        for error in validate_case(
            case,
            strict=strict,
            manual_label_ids=manual_label_ids,
            review_queue_candidate_ids=review_queue_ids,
        ):
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
        "manual_labels_path": labels_path.as_posix(),
        "confirmed_manual_labels": len(manual_label_ids),
    }
