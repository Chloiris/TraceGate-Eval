from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FixEligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NEEDS_CONFIRMATION = "NEEDS_CONFIRMATION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE_HEAD = "STALE_HEAD"
    UNSUPPORTED_FILE = "UNSUPPORTED_FILE"
    SENSITIVE_PATH = "SENSITIVE_PATH"
    BLOCKED = "BLOCKED"


class FixPermissionMode(StrEnum):
    PROPOSE_ONLY = "PROPOSE_ONLY"
    APPLY_IN_ISOLATED_WORKSPACE = "APPLY_IN_ISOLATED_WORKSPACE"


class FixSessionStatus(StrEnum):
    CREATED = "CREATED"
    CHECKING_ELIGIBILITY = "CHECKING_ELIGIBILITY"
    ELIGIBLE = "ELIGIBLE"
    PLANNING = "PLANNING"
    PLAN_READY = "PLAN_READY"
    GENERATING_PATCH = "GENERATING_PATCH"
    VALIDATING_PATCH = "VALIDATING_PATCH"
    AWAITING_USER_CONFIRMATION = "AWAITING_USER_CONFIRMATION"
    APPLYING_PATCH = "APPLYING_PATCH"
    PATCH_APPLIED = "PATCH_APPLIED"
    RUNNING_VALIDATION = "RUNNING_VALIDATION"
    VALIDATION_COMPLETE = "VALIDATION_COMPLETE"
    REINDEXING_CHANGES = "REINDEXING_CHANGES"
    RE_REVIEWING = "RE_REVIEWING"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"
    STALE = "STALE"


class ValidationStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    NO_TEST_COMMAND_AVAILABLE = "NO_TEST_COMMAND_AVAILABLE"


class FixResolution(StrEnum):
    RESOLVED = "RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    NOT_RESOLVED = "NOT_RESOLVED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class FixEligibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FixEligibilityStatus
    reasons: list[str] = Field(default_factory=list, max_length=32)
    warnings: list[str] = Field(default_factory=list, max_length=32)
    force_allowed: bool = False


class FixPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1, max_length=64)
    objective: str = Field(min_length=1, max_length=4_000)
    root_cause: str = Field(min_length=1, max_length=8_000)
    affected_files: list[str] = Field(min_length=1, max_length=32)
    affected_symbols: list[str] = Field(default_factory=list, max_length=32)
    constraints: list[str] = Field(default_factory=list, max_length=32)
    proposed_steps: list[str] = Field(min_length=1, max_length=24)
    expected_behavior: str = Field(min_length=1, max_length=4_000)
    validation_strategy: list[str] = Field(min_length=1, max_length=24)
    risk_notes: list[str] = Field(default_factory=list, max_length=32)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("affected_files")
    @classmethod
    def validate_relative_paths(cls, values: list[str]) -> list[str]:
        if any(not value or value.startswith(("/", "\\")) or ".." in value.replace("\\", "/").split("/") for value in values):
            raise ValueError("affected_files must contain bounded relative paths")
        return list(dict.fromkeys(values))


class ValidationCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argv: list[str] = Field(min_length=1, max_length=32)
    command_purpose: str = Field(min_length=1, max_length=1_000)
    required: bool = True
    timeout: int = Field(default=180, ge=1, le=900)
    expected_result: str = Field(min_length=1, max_length=1_000)
    source: str = Field(min_length=1, max_length=128)

    @field_validator("argv")
    @classmethod
    def validate_argv(cls, values: list[str]) -> list[str]:
        if any(not value or "\x00" in value for value in values):
            raise ValueError("validation argv contains an invalid argument")
        return values


class ValidationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commands: list[ValidationCommand] = Field(default_factory=list, max_length=16)
    notes: list[str] = Field(default_factory=list, max_length=16)


class PatchProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1, max_length=64)
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    head_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    patch: str = Field(min_length=1, max_length=1_000_000)
    changed_files: list[str] = Field(min_length=1, max_length=32)
    estimated_changed_lines: int = Field(ge=1, le=10_000)
    rationale: str = Field(min_length=1, max_length=8_000)
    assumptions: list[str] = Field(default_factory=list, max_length=32)
    validation_commands: list[ValidationCommand] = Field(default_factory=list, max_length=16)
    residual_risks: list[str] = Field(default_factory=list, max_length=32)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("changed_files")
    @classmethod
    def validate_changed_files(cls, values: list[str]) -> list[str]:
        if any(not value or value.startswith(("/", "\\")) or ".." in value.replace("\\", "/").split("/") for value in values):
            raise ValueError("changed_files must contain bounded relative paths")
        return list(dict.fromkeys(values))


class PatchInspection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed_files: list[str]
    changed_lines: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True


class ReReviewAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_finding_supported: bool
    residual_findings: list[str] = Field(default_factory=list, max_length=32)
    residual_risks: list[str] = Field(default_factory=list, max_length=32)
    new_high_risk: bool = False
    summary: str = Field(min_length=1, max_length=8_000)
    confidence: float = Field(ge=0.0, le=1.0)


class PostFixReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fix_session_id: str = Field(min_length=1, max_length=64)
    finding_id: str = Field(min_length=1, max_length=64)
    patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    applied: bool
    validation_status: ValidationStatus
    commands_run: list[list[str]] = Field(default_factory=list, max_length=16)
    passed_commands: list[list[str]] = Field(default_factory=list, max_length=16)
    failed_commands: list[list[str]] = Field(default_factory=list, max_length=16)
    re_review_status: str = Field(min_length=1, max_length=128)
    finding_resolution: FixResolution
    residual_findings: list[str] = Field(default_factory=list, max_length=64)
    residual_risks: list[str] = Field(default_factory=list, max_length=64)
    final_summary: str = Field(min_length=1, max_length=8_000)

    @model_validator(mode="after")
    def resolved_requires_applied_and_passed(self) -> "PostFixReport":
        if self.finding_resolution == FixResolution.RESOLVED and (
            not self.applied or self.validation_status != ValidationStatus.PASSED
        ):
            raise ValueError("RESOLVED requires an applied patch and passed validation")
        return self
