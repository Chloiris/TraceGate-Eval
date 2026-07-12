from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tracegate.models import ModelProvider
from tracegate.pr_advisor.evidence_packet import (
    EvidenceItem,
    EvidencePacket,
    detect_risk_areas,
    sanitize_text,
    stable_id,
)
from tracegate.pr_advisor.verifier import verify_judgment
from tracegate.repository import RepositoryBoundary, RepositoryPathError
from tracegate.retrieval import hybrid_retrieve
from tracegate.tools import ToolContext, ToolExecutionError, ToolRegistry
from tracegate.vcs import GitCommandError, GitProvider

from tracegate.studio.models import (
    AgentRun,
    AgentStep,
    EvidenceRecord,
    Finding,
    IndexVersion,
    IndexedFile,
    PullRequest,
    Repository,
    ToolCallRecord,
)


WORKFLOW_VERSION = "tracegate-langgraph-v1"
PROMPT_VERSION = "tracegate-pr-review-v1"
NODE_NAMES = (
    "Planner",
    "Repository Retriever",
    "Context Resolver",
    "Code Analyst",
    "Risk Reviewer",
    "Verifier",
    "Report Composer",
)


class WorkflowCancelled(RuntimeError):
    """Raised after cancellation state has been persisted."""


class WorkflowExecutionError(RuntimeError):
    """Raised when an Agent workflow terminates without a successful report."""


class PlanOutput(BaseModel):
    objective: str
    retrieval_queries: list[str] = Field(min_length=1, max_length=8)
    focus_areas: list[str] = Field(default_factory=list, max_length=12)


class FindingDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    severity: Literal["info", "low", "medium", "high", "critical"]
    confidence: float = Field(ge=0, le=1)
    category: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=6000)
    path: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    symbol: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    suggested_action: str = Field(min_length=1, max_length=4000)


class FindingsOutput(BaseModel):
    findings: list[FindingDraft] = Field(default_factory=list, max_length=50)
    analysis_summary: str = Field(min_length=1, max_length=6000)


class RiskJudgmentOutput(BaseModel):
    evidence_status: Literal[
        "active",
        "stale",
        "unknown",
        "conflicting",
        "needs_more_evidence",
        "no_relevant_claim",
    ]
    expected_decision: Literal["preserve", "revise", "verify_first", "none"]
    evidence_used: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=4000)
    missing_evidence: list[str] = Field(default_factory=list)
    should_block: bool = False


class ReportOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=6000)
    recommended_review_order: list[str] = Field(default_factory=list, max_length=30)


class WorkflowState(TypedDict, total=False):
    run_id: str
    repository_id: str
    pull_request_id: str
    head_sha: str
    index_version: str
    sequence: int
    plan: dict[str, Any]
    retrieval: list[dict[str, Any]]
    evidence_ids: list[str]
    findings: list[dict[str, Any]]
    analysis_summary: str
    judgment: dict[str, Any]
    report: dict[str, Any]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    retry_count: int
    retrieval_hit_count: int


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_evidence_reference(value: str) -> str:
    """Accept an exact Evidence ID with optional display brackets only."""
    if len(value) >= 2 and value.startswith("[") and value.endswith("]"):
        return value[1:-1]
    return value


class TraceGateAgentWorkflow:
    """Seven real LangGraph nodes with durable Studio step/evidence/finding records."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        model: ModelProvider,
        tools: ToolRegistry,
        *,
        context_scope: Literal[
            "changed_files", "retrieved_context"
        ] = "retrieved_context",
    ) -> None:
        self.session_factory = session_factory
        self.model = model
        self.tools = tools
        self.context_scope = context_scope
        builder = StateGraph(WorkflowState)
        handlers = (
            ("Planner", self._planner),
            ("Repository Retriever", self._retriever),
            ("Context Resolver", self._context_resolver),
            ("Code Analyst", self._code_analyst),
            ("Risk Reviewer", self._risk_reviewer),
            ("Verifier", self._verifier),
            ("Report Composer", self._report_composer),
        )
        for name, handler in handlers:
            builder.add_node(name, self._observed_node(name, handler))
        builder.add_edge(START, NODE_NAMES[0])
        for source, target in zip(NODE_NAMES[:-1], NODE_NAMES[1:], strict=True):
            builder.add_edge(source, target)
        builder.add_edge(NODE_NAMES[-1], END)
        self.graph = builder.compile()

    async def run(self, run_id: str) -> WorkflowState:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run is None:
                raise WorkflowExecutionError("Agent Run was not found")
            if not run.pull_request_id or not run.head_sha or not run.index_version:
                raise WorkflowExecutionError(
                    "Agent Run is missing PR, Head SHA, or Index Version"
                )
            run.status = "running"
            run.workflow_version = WORKFLOW_VERSION
            run.prompt_version = PROMPT_VERSION
            run.model_profile = self.model.profile
            run.started_at = utcnow()
            pull_request = session.get(PullRequest, run.pull_request_id)
            if pull_request:
                pull_request.analysis_status = "running"
            session.commit()
            initial: WorkflowState = {
                "run_id": run.id,
                "repository_id": run.repository_id,
                "pull_request_id": run.pull_request_id,
                "head_sha": run.head_sha,
                "index_version": run.index_version,
                "sequence": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": 0,
                "retry_count": 0,
            }
        try:
            result = await self.graph.ainvoke(initial)
        except (WorkflowCancelled, asyncio.CancelledError) as exc:
            with self.session_factory() as session:
                run = session.get(AgentRun, run_id)
                if run:
                    run.status = "cancelled"
                    run.current_node = None
                    run.finished_at = utcnow()
                    pull_request = (
                        session.get(PullRequest, run.pull_request_id)
                        if run.pull_request_id
                        else None
                    )
                    if pull_request:
                        pull_request.analysis_status = "cancelled"
                    session.commit()
            if isinstance(exc, asyncio.CancelledError):
                raise WorkflowCancelled("Agent Run task was cancelled") from exc
            raise
        except Exception as exc:
            with self.session_factory() as session:
                run = session.get(AgentRun, run_id)
                if run:
                    run.status = "failed"
                    run.current_node = None
                    run.error_code = type(exc).__name__
                    run.error_message = sanitize_text(exc, max_chars=2000)
                    run.finished_at = utcnow()
                    pull_request = (
                        session.get(PullRequest, run.pull_request_id)
                        if run.pull_request_id
                        else None
                    )
                    if pull_request:
                        pull_request.analysis_status = "failed"
                    session.commit()
            raise WorkflowExecutionError(
                f"Agent workflow failed: {type(exc).__name__}"
            ) from exc
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run:
                run.status = "completed"
                run.current_node = None
                run.input_tokens = result.get("input_tokens", 0)
                run.output_tokens = result.get("output_tokens", 0)
                run.latency_ms = result.get("latency_ms", 0)
                run.retry_count = result.get("retry_count", 0)
                run.retrieval_hit_count = result.get("retrieval_hit_count", 0)
                run.finished_at = utcnow()
                pull_request = (
                    session.get(PullRequest, run.pull_request_id)
                    if run.pull_request_id
                    else None
                )
                if pull_request:
                    pull_request.analysis_status = "completed"
                session.commit()
        return result

    def _observed_node(self, name: str, handler):  # type: ignore[no-untyped-def]
        async def observed(state: WorkflowState) -> WorkflowState:
            sequence = state.get("sequence", 0) + 1
            started = time.monotonic()
            with self.session_factory() as session:
                run = session.get(AgentRun, state["run_id"])
                if run is None:
                    raise WorkflowExecutionError("Agent Run disappeared")
                if run.cancellation_requested:
                    raise WorkflowCancelled("Agent Run cancellation was requested")
                run.current_node = name
                step = AgentStep(
                    agent_run_id=run.id,
                    sequence=sequence,
                    node=name,
                    status="running",
                    input_summary=self._state_summary(state),
                    started_at=utcnow(),
                )
                session.add(step)
                session.commit()
                session.refresh(step)
                step_id = step.id
            try:
                update = await handler(state, step_id)
            except Exception as exc:
                with self.session_factory() as session:
                    step = session.get(AgentStep, step_id)
                    if step:
                        step.status = (
                            "cancelled"
                            if isinstance(exc, WorkflowCancelled)
                            else "failed"
                        )
                        step.error_code = type(exc).__name__
                        step.error_message = sanitize_text(exc, max_chars=2000)
                        step.finished_at = utcnow()
                        step.duration_ms = int((time.monotonic() - started) * 1000)
                        session.commit()
                raise
            with self.session_factory() as session:
                step = session.get(AgentStep, step_id)
                if step:
                    step.status = "completed"
                    step.output_summary = self._state_summary(update)
                    step.finished_at = utcnow()
                    step.duration_ms = int((time.monotonic() - started) * 1000)
                    session.commit()
            return {**update, "sequence": sequence}

        return observed

    async def _planner(self, state: WorkflowState, _step_id: str) -> WorkflowState:
        repository, pull_request = self._repository_and_pr(state)
        result = await self.model.complete_structured(
            system_prompt="Plan an evidence-first Pull Request review. Use concrete retrieval queries.",
            user_prompt=(
                f"Repository: {repository.full_name}\nPR: {pull_request.number} {sanitize_text(pull_request.title)}\n"
                f"Base: {pull_request.base_sha}\nHead: {pull_request.head_sha}"
            ),
            output_schema=PlanOutput,
        )
        return {"plan": result.payload, **self._usage_update(state, result)}

    async def _retriever(self, state: WorkflowState, step_id: str) -> WorkflowState:
        repository, pull_request = self._repository_and_pr(state)
        plan = PlanOutput.model_validate(state["plan"])
        results: list[dict[str, Any]] = []
        with self.session_factory() as session:
            for query in plan.retrieval_queries[:5]:
                retrieved = hybrid_retrieve(session, repository.id, query, limit=10)
                results.extend(hit.__dict__ for hit in retrieved.hits)
        if repository.local_path:
            boundary = RepositoryBoundary(Path(repository.local_path))
            context = ToolContext(
                repository.id,
                boundary,
                "Repository Retriever",
                session_factory=self.session_factory,
                pull_request_id=state.get("pull_request_id"),
                github_token=os.environ.get("GITHUB_TOKEN")
                or os.environ.get("GH_TOKEN"),
            )
            for query in plan.retrieval_queries[:3]:
                before = len(self.tools.invocations)
                try:
                    output = await self.tools.execute(
                        "search_code", {"query": query, "max_results": 20}, context
                    )
                    results.extend(
                        {**item, "kind": "text", "source": "ripgrep", "score": 60.0}
                        for item in output["matches"]
                    )
                    status, error_code = "completed", None
                except ToolExecutionError as exc:
                    output = {"error": exc.code}
                    status, error_code = "failed", exc.code
                invocation = (
                    self.tools.invocations[-1]
                    if len(self.tools.invocations) > before
                    else None
                )
                with self.session_factory() as session:
                    session.add(
                        ToolCallRecord(
                            agent_step_id=step_id,
                            tool_name="search_code",
                            permission="REPOSITORY_READ",
                            arguments_summary=json.dumps(
                                {"query": query}, ensure_ascii=False
                            ),
                            output_summary=sanitize_text(output, max_chars=2000),
                            status=status,
                            duration_ms=invocation.duration_ms if invocation else None,
                            error_code=error_code,
                        )
                    )
                    session.commit()
        deduplicated: dict[tuple[str, str | None], dict[str, Any]] = {}
        for item in results:
            key = (str(item.get("path")), item.get("symbol"))
            if key[0] and key not in deduplicated:
                deduplicated[key] = item
        if self.context_scope == "changed_files":
            if (
                not repository.local_path
                or not pull_request.base_sha
                or not pull_request.head_sha
            ):
                raise WorkflowExecutionError(
                    "Changed-file-only model context requires a local workspace and Base/Head SHAs"
                )
            try:
                boundary = RepositoryBoundary(Path(repository.local_path))
                git = GitProvider(boundary)
                changed_paths = {
                    line.strip()
                    for line in git.run(
                        "diff",
                        "--name-only",
                        "--find-renames",
                        f"{pull_request.base_sha}...{pull_request.head_sha}",
                    ).stdout.splitlines()
                    if line.strip()
                }
            except (OSError, RepositoryPathError, GitCommandError) as exc:
                raise WorkflowExecutionError(
                    "Could not resolve changed-file-only model context"
                ) from exc
            changed_context: dict[tuple[str, str | None], dict[str, Any]] = {}
            if changed_paths:
                with self.session_factory() as session:
                    rows = list(
                        session.scalars(
                            select(IndexedFile).where(
                                IndexedFile.index_version_id == state["index_version"],
                                IndexedFile.path.in_(sorted(changed_paths)),
                            )
                        )
                    )
                for row in rows:
                    diff_snippet = git.run(
                        "diff",
                        "--unified=12",
                        f"{pull_request.base_sha}...{pull_request.head_sha}",
                        "--",
                        row.path,
                    ).stdout
                    changed_context[(row.path, None)] = {
                        "path": row.path,
                        "symbol": None,
                        "snippet": diff_snippet or row.content,
                        "source": "changed_file_diff"
                        if diff_snippet
                        else "changed_file_index",
                        "score": 100.0,
                    }
            deduplicated = changed_context
        bounded = list(deduplicated.values())[:30]
        return {"retrieval": bounded, "retrieval_hit_count": len(bounded)}

    async def _context_resolver(
        self, state: WorkflowState, _step_id: str
    ) -> WorkflowState:
        repository, pull_request = self._repository_and_pr(state)
        if pull_request.head_sha != state["head_sha"]:
            raise WorkflowExecutionError(
                "Pull Request Head SHA changed after this run was queued"
            )
        evidence_ids: list[str] = []
        seen_paths: set[str] = set()
        with self.session_factory() as session:
            version = session.get(IndexVersion, state["index_version"])
            if (
                version is None
                or version.repository_id != repository.id
                or version.commit_sha != state["head_sha"]
            ):
                raise WorkflowExecutionError(
                    "Index Version is not bound to the Pull Request Head SHA"
                )
            for item in state.get("retrieval", [])[:20]:
                path = item.get("path")
                if not isinstance(path, str):
                    continue
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                indexed = session.scalar(
                    select(IndexedFile).where(
                        IndexedFile.index_version_id == state["index_version"],
                        IndexedFile.path == path,
                    )
                )
                if indexed is None:
                    continue
                evidence_id = stable_id(
                    "studio-evidence", state["run_id"], path, indexed.content_hash
                )
                if session.get(EvidenceRecord, evidence_id) is None:
                    session.add(
                        EvidenceRecord(
                            id=evidence_id,
                            agent_run_id=state["run_id"],
                            source_type="indexed_file",
                            source_uri=f"repository://{repository.full_name}/{path}",
                            file_path=path,
                            commit_sha=state["head_sha"],
                            content_hash=indexed.content_hash,
                            payload_json={
                                "snippet": sanitize_text(
                                    item.get("snippet")
                                    or item.get("text")
                                    or indexed.content,
                                    max_chars=2000,
                                ),
                                "source": item.get("source"),
                                "score": item.get("score"),
                            },
                        )
                    )
                evidence_ids.append(evidence_id)
            session.commit()
        if not evidence_ids:
            raise WorkflowExecutionError("Retrieval produced no commit-bound evidence")
        return {"evidence_ids": evidence_ids}

    async def _code_analyst(self, state: WorkflowState, _step_id: str) -> WorkflowState:
        repository, pull_request = self._repository_and_pr(state)
        evidence = self._evidence_prompt(state)
        result = await self.model.complete_structured(
            system_prompt=(
                "Analyze code evidence for concrete defects. Empty findings are valid "
                "when evidence does not prove a defect. Every evidence_ids value must "
                "copy the complete bracketed Evidence ID exactly, including its namespace "
                "prefix and punctuation; never shorten or rewrite an Evidence ID. "
                "start_line and end_line must refer to the numbered CURRENT_HEAD_CONTENT, "
                "not removed lines or diff display positions."
            ),
            user_prompt=(
                f"Repository {repository.full_name}; PR #{pull_request.number}; Head {state['head_sha']}\n"
                f"UNTRUSTED_EVIDENCE\n{evidence}\nEND_UNTRUSTED_EVIDENCE"
            ),
            output_schema=FindingsOutput,
        )
        output = FindingsOutput.model_validate(result.payload)
        return {
            "findings": [item.model_dump(mode="json") for item in output.findings],
            "analysis_summary": output.analysis_summary,
            **self._usage_update(state, result),
        }

    async def _risk_reviewer(
        self, state: WorkflowState, _step_id: str
    ) -> WorkflowState:
        result = await self.model.complete_structured(
            system_prompt=(
                "Classify whether the supplied evidence is active, stale, unknown, or "
                "conflicting under TraceGate semantics. Every evidence_used value must "
                "copy the complete bracketed Evidence ID exactly, including its namespace "
                "prefix and punctuation; never shorten or rewrite an Evidence ID."
            ),
            user_prompt=(
                "UNTRUSTED_EVIDENCE\n"
                + self._evidence_prompt(state)
                + "\nCANDIDATE_FINDINGS\n"
                + json.dumps(state.get("findings", []), ensure_ascii=False)
                + "\nEND_UNTRUSTED_EVIDENCE"
            ),
            output_schema=RiskJudgmentOutput,
        )
        return {"judgment": result.payload, **self._usage_update(state, result)}

    async def _verifier(self, state: WorkflowState, _step_id: str) -> WorkflowState:
        repository, pull_request = self._repository_and_pr(state)
        with self.session_factory() as session:
            evidence = list(
                session.scalars(
                    select(EvidenceRecord).where(
                        EvidenceRecord.agent_run_id == state["run_id"]
                    )
                )
            )
        packet = EvidencePacket(
            repo=repository.full_name,
            pr_number=pull_request.number,
            pr_url=pull_request.url,
            title=pull_request.title,
            changed_files=sorted(
                {item.file_path for item in evidence if item.file_path}
            ),
            risk_areas=detect_risk_areas(
                pull_request.title, *(item.file_path for item in evidence)
            ),
            candidate_claims=[
                item.get("title", "") for item in state.get("findings", [])
            ],
            evidence_items=[
                EvidenceItem(
                    evidence_id=item.id,
                    source_type=item.source_type,
                    url=item.source_uri,
                    file_path=item.file_path or "",
                    commit_sha=item.commit_sha or "",
                    snippet=str(item.payload_json.get("snippet") or ""),
                    supports_or_contradicts="unclear",
                    relevance=float(item.payload_json.get("score") or 0) / 100,
                )
                for item in evidence
            ],
            missing_evidence=[]
            if evidence
            else ["No commit-bound repository evidence was retrieved."],
        )
        judgment = dict(state["judgment"])
        judgment["evidence_used"] = [
            _normalize_evidence_reference(value)
            for value in judgment.get("evidence_used", [])
            if isinstance(value, str)
        ]
        verified_judgment = verify_judgment(packet, judgment)
        evidence_by_id = {item.id: item for item in evidence}
        with self.session_factory() as session:
            indexed_rows = list(
                session.scalars(
                    select(IndexedFile).where(
                        IndexedFile.index_version_id == state["index_version"]
                    )
                )
            )
        line_counts = {
            item.path: len(item.content.splitlines()) for item in indexed_rows
        }
        verified_findings: list[dict[str, Any]] = []
        for raw in state.get("findings", []):
            finding = FindingDraft.model_validate(raw)
            normalized_ids = [
                _normalize_evidence_reference(evidence_id)
                for evidence_id in finding.evidence_ids
            ]
            valid_ids = [
                evidence_id
                for evidence_id in normalized_ids
                if evidence_id in evidence_by_id
                and evidence_by_id[evidence_id].commit_sha == state["head_sha"]
            ]
            path_is_cited = finding.path is None or any(
                evidence_by_id[evidence_id].file_path == finding.path
                for evidence_id in valid_ids
            )
            line_range_valid = (
                finding.start_line is None
                or finding.end_line is None
                or (
                    finding.path in line_counts
                    and finding.start_line
                    <= finding.end_line
                    <= line_counts[finding.path]
                )
            )
            verifier_status = (
                "verified"
                if valid_ids and path_is_cited and line_range_valid
                else "needs_confirmation"
            )
            updated = finding.model_dump(mode="json")
            updated["evidence_ids"] = valid_ids
            updated["verifier_status"] = verifier_status
            verified_findings.append(updated)
        return {"findings": verified_findings, "judgment": verified_judgment}

    async def _report_composer(
        self, state: WorkflowState, _step_id: str
    ) -> WorkflowState:
        result = await self.model.complete_structured(
            system_prompt="Compose a concise evidence-bound review report and file review order.",
            user_prompt=json.dumps(
                {
                    "analysis_summary": state.get("analysis_summary"),
                    "findings": state.get("findings", []),
                    "judgment": state.get("judgment"),
                },
                ensure_ascii=False,
            ),
            output_schema=ReportOutput,
        )
        report = ReportOutput.model_validate(result.payload)
        evidence_paths = {
            item.get("path")
            for item in state.get("findings", [])
            if isinstance(item.get("path"), str)
        }
        verified_report = report.model_copy(
            update={
                "recommended_review_order": [
                    path
                    for path in report.recommended_review_order
                    if path in evidence_paths
                ]
            }
        )
        with self.session_factory() as session:
            persisted_findings: list[FindingDraft] = []
            for item in state.get("findings", []):
                finding = FindingDraft.model_validate(
                    {key: item.get(key) for key in FindingDraft.model_fields}
                )
                persisted_findings.append(finding)
                session.add(
                    Finding(
                        agent_run_id=state["run_id"],
                        severity=finding.severity,
                        confidence=finding.confidence,
                        category=finding.category,
                        title=finding.title,
                        message=finding.explanation,
                        file_path=finding.path,
                        line_start=finding.start_line,
                        line_end=finding.end_line,
                        commit_sha=state["head_sha"],
                        symbol=finding.symbol,
                        evidence_ids_json=item.get("evidence_ids", []),
                        suggested_action=finding.suggested_action,
                        verifier_status=item.get(
                            "verifier_status", "needs_confirmation"
                        ),
                        model_profile=self.model.profile,
                    )
                )
            pull_request = session.get(PullRequest, state["pull_request_id"])
            if pull_request is not None:
                severity_weight = {
                    "info": 10,
                    "low": 25,
                    "medium": 50,
                    "high": 75,
                    "critical": 100,
                }
                highest = max(
                    persisted_findings,
                    key=lambda item: (severity_weight[item.severity], item.confidence),
                    default=None,
                )
                pull_request.risk_level = highest.severity if highest else None
                pull_request.risk_score = (
                    round(severity_weight[highest.severity] * highest.confidence, 2)
                    if highest
                    else 0.0
                )
                pull_request.conclusion_summary = verified_report.summary
                pull_request.impact_paths_json = sorted(
                    {item.path for item in persisted_findings if item.path}
                )
                pull_request.recommended_review_order_json = list(
                    verified_report.recommended_review_order
                )
            session.commit()
        return {
            "report": verified_report.model_dump(mode="json"),
            **self._usage_update(state, result),
        }

    def _repository_and_pr(
        self, state: WorkflowState
    ) -> tuple[Repository, PullRequest]:
        with self.session_factory() as session:
            repository = session.get(Repository, state["repository_id"])
            pull_request = session.get(PullRequest, state["pull_request_id"])
            if repository is None or pull_request is None:
                raise WorkflowExecutionError("Repository or Pull Request was not found")
            session.expunge(repository)
            session.expunge(pull_request)
            return repository, pull_request

    def _evidence_prompt(self, state: WorkflowState) -> str:
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(EvidenceRecord).where(
                        EvidenceRecord.agent_run_id == state["run_id"]
                    )
                )
            )
            indexed = {
                item.path: item
                for item in session.scalars(
                    select(IndexedFile).where(
                        IndexedFile.index_version_id == state["index_version"],
                        IndexedFile.path.in_([row.file_path for row in rows if row.file_path]),
                    )
                )
            }
        return "\n".join(
            (
                f"[{row.id}] commit={row.commit_sha} path={row.file_path}\n"
                f"DIFF_EVIDENCE\n{row.payload_json.get('snippet', '')}\n"
                "CURRENT_HEAD_CONTENT\n"
                + "\n".join(
                    f"{number}: {line}"
                    for number, line in enumerate(
                        (indexed[row.file_path].content if row.file_path in indexed else "").splitlines(),
                        start=1,
                    )
                )[:6_000]
                + "\nEND_CURRENT_HEAD_CONTENT"
            )
            for row in rows
        )[:40_000]

    @staticmethod
    def _usage_update(state: WorkflowState, result) -> WorkflowState:  # type: ignore[no-untyped-def]
        return {
            "input_tokens": state.get("input_tokens", 0) + result.input_tokens,
            "output_tokens": state.get("output_tokens", 0) + result.output_tokens,
            "latency_ms": state.get("latency_ms", 0) + result.latency_ms,
            "retry_count": state.get("retry_count", 0) + result.retries,
        }

    @staticmethod
    def _state_summary(value: dict[str, Any]) -> str:
        safe = {key: item for key, item in value.items() if key not in {"retrieval"}}
        return sanitize_text(
            json.dumps(safe, ensure_ascii=False, default=str), max_chars=2000
        )
