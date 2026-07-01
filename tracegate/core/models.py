from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EvidenceStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class ExpectedDecision(str, Enum):
    PRESERVE = "preserve"
    OPTIMIZE = "optimize"
    VERIFY_FIRST = "verify_first"
    DETECT_CONFLICT = "detect_conflict"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_text: str
    validity_condition: str
    claim_source: str
    claim_source_url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        required = ["claim_id", "claim_text", "validity_condition", "claim_source", "claim_source_url"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"claim missing required fields: {', '.join(missing)}")
        return cls(**{key: str(data[key]) for key in required})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    evidence_type: str
    evidence_text_excerpt: str
    evidence_url: str
    file_path: str | None = None
    commit_sha: str | None = None
    timestamp: str | None = None
    supports_or_contradicts: str = "unclear"
    provenance_hash: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        required = ["evidence_id", "evidence_type", "evidence_text_excerpt", "evidence_url"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"evidence item missing required fields: {', '.join(missing)}")
        relation = data.get("supports_or_contradicts", "unclear")
        if relation not in {"supports", "contradicts", "unclear"}:
            raise ValueError(f"invalid evidence relation: {relation}")
        return cls(
            evidence_id=str(data["evidence_id"]),
            evidence_type=str(data["evidence_type"]),
            evidence_text_excerpt=str(data["evidence_text_excerpt"]),
            evidence_url=str(data["evidence_url"]),
            file_path=data.get("file_path"),
            commit_sha=data.get("commit_sha"),
            timestamp=data.get("timestamp"),
            supports_or_contradicts=str(relation),
            provenance_hash=data.get("provenance_hash"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    source_dataset: str
    source_url: str
    repo: str
    repo_url: str
    issue_url: str | None
    pr_url: str | None
    base_commit: str | None
    head_commit: str | None
    commit_sha: str | None
    created_at: str | None
    files_changed: list[str]
    diff_summary: str
    problem_statement: str
    claim: Claim
    evidence_items: list[EvidenceItem]
    evidence_status: EvidenceStatus
    expected_decision: ExpectedDecision
    label_source: str
    label_confidence: float
    is_real: bool
    is_synthetic: bool
    excluded_from_real_metrics: bool
    exclusion_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalCase":
        required = [
            "case_id",
            "source_dataset",
            "repo",
            "repo_url",
            "files_changed",
            "diff_summary",
            "problem_statement",
            "claim",
            "evidence_items",
            "evidence_status",
            "expected_decision",
            "label_source",
            "label_confidence",
            "is_real",
            "is_synthetic",
            "excluded_from_real_metrics",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"case missing required fields: {', '.join(missing)}")
        return cls(
            case_id=str(data["case_id"]),
            source_dataset=str(data["source_dataset"]),
            source_url=str(data.get("source_url") or ""),
            repo=str(data["repo"]),
            repo_url=str(data["repo_url"]),
            issue_url=data.get("issue_url"),
            pr_url=data.get("pr_url"),
            base_commit=data.get("base_commit"),
            head_commit=data.get("head_commit"),
            commit_sha=data.get("commit_sha"),
            created_at=data.get("created_at"),
            files_changed=[str(item) for item in data.get("files_changed", [])],
            diff_summary=str(data["diff_summary"]),
            problem_statement=str(data["problem_statement"]),
            claim=Claim.from_dict(data["claim"]),
            evidence_items=[EvidenceItem.from_dict(item) for item in data.get("evidence_items", [])],
            evidence_status=EvidenceStatus(str(data["evidence_status"])),
            expected_decision=ExpectedDecision(str(data["expected_decision"])),
            label_source=str(data["label_source"]),
            label_confidence=float(data["label_confidence"]),
            is_real=bool(data["is_real"]),
            is_synthetic=bool(data["is_synthetic"]),
            excluded_from_real_metrics=bool(data["excluded_from_real_metrics"]),
            exclusion_reason=data.get("exclusion_reason"),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_status"] = self.evidence_status.value
        data["expected_decision"] = self.expected_decision.value
        return data

    @property
    def is_scored_real_case(self) -> bool:
        return (
            self.is_real
            and not self.is_synthetic
            and not self.excluded_from_real_metrics
            and self.evidence_status != EvidenceStatus.NEEDS_MANUAL_REVIEW
            and self.label_source != "unknown"
            and self.label_confidence >= 0.7
        )


@dataclass(frozen=True)
class PullRequestChange:
    files_changed: list[str]
    diff_summary: str
    problem_statement: str


@dataclass(frozen=True)
class AdvisoryDecision:
    case_id: str
    risk_level: str
    risk_score: int
    evidence_status: str
    decision: str
    summary: str
    rationale: str
    evidence_used: list[str]
    verification_plan: list[str]
    pollution_flags: list[str]
    limitations: list[str]
    requires_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    case: EvalCase
    advisory: AdvisoryDecision


@dataclass(frozen=True)
class EvalReport:
    run_id: str
    metrics: dict[str, Any]
    advisories: list[AdvisoryDecision] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "metrics": self.metrics,
            "advisories": [item.to_dict() for item in self.advisories],
        }
