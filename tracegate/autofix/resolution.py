from __future__ import annotations

from dataclasses import dataclass

from .schemas import FixResolution, ReReviewAssessment, ValidationStatus


@dataclass(frozen=True)
class ValidationOutcome:
    required: bool
    status: ValidationStatus


def decide_resolution(
    *,
    patch_applied: bool,
    validation_outcomes: list[ValidationOutcome],
    test_command_available: bool,
    targeted_test_passed: bool,
    finding_path_changed: bool,
    reindex_succeeded: bool,
    re_review: ReReviewAssessment | None,
) -> FixResolution:
    """Resolve from observed facts; model prose alone can never produce RESOLVED."""
    if not patch_applied or not reindex_succeeded:
        return FixResolution.VERIFICATION_FAILED
    if any(
        outcome.required
        and outcome.status
        not in {ValidationStatus.PASSED}
        for outcome in validation_outcomes
    ):
        return FixResolution.VERIFICATION_FAILED
    if (
        not test_command_available
        or not targeted_test_passed
        or not finding_path_changed
        or re_review is None
        or re_review.confidence < 0.6
    ):
        return FixResolution.NEEDS_HUMAN_REVIEW
    if re_review.original_finding_supported:
        return FixResolution.NOT_RESOLVED
    if re_review.new_high_risk or re_review.residual_findings or re_review.residual_risks:
        return FixResolution.PARTIALLY_RESOLVED
    return FixResolution.RESOLVED
