from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    project: str
    version: str


class ContextGroupSummary(BaseModel):
    name: str
    description: str
    runs: int
    safe_success: int
    destructive_change: int
    pollution: int
    avg_plan_quality: float
    data_source: str


class EvidenceStatusSummary(BaseModel):
    evidence_status: str
    description: str
    expected_decision: str
    runs: int
    correct_decision: int
    test_success: int
    destructive_change: int
    pollution: int
    avg_plan_quality: float
    data_source: str


class TaskSummary(BaseModel):
    task_id: str
    module: str
    evidence_status: str
    historical_claim: str
    expected_decision: str
    data_source: str


class TaskDetail(TaskSummary):
    title: str | None = None
    pitfall: str | None = None
    context_groups: list[str]
    available_results: list[dict[str, Any]]


class OverviewResponse(BaseModel):
    project_name: str
    one_sentence_intro: str
    current_stage: str
    total_tasks: int
    total_runs: int
    model: str
    key_metrics: dict[str, Any]
    context_groups: list[ContextGroupSummary]
    evidence_statuses: list[EvidenceStatusSummary]
    data_source: str


class ResultsResponse(BaseModel):
    data_source: str
    count: int
    filters: dict[str, str | None]
    results: list[dict[str, Any]]


class AnalyzeDemoRequest(BaseModel):
    claim: str = Field(..., min_length=1)
    evidence: str = ""
    context_group: str = "claim_with_evidence"


class AnalyzeDemoResponse(BaseModel):
    suggested_decision: str
    reason: str
    verification_plan: list[str]
    risk_flags: list[str]
    data_source: str = "rule_based_demo"

