from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tracegate.agent import TraceGateAgentWorkflow, WorkflowCancelled
from tracegate.agent.workflow import PROMPT_VERSION, WORKFLOW_VERSION
from tracegate.models import ModelConfigurationError, OpenAICompatibleProvider
from tracegate.tools import create_read_only_registry

from .models import AgentRun, AppSettings, ModelProfile, PullRequest, Repository


logger = logging.getLogger("tracegate.studio.runs")


@dataclass(frozen=True)
class EnqueueResult:
    run: AgentRun
    reused: bool


@dataclass(frozen=True)
class AutomaticEnqueueResult:
    started: int
    skipped_reason: str | None = None


def configured_model(session: Session) -> OpenAICompatibleProvider:
    settings = session.get(AppSettings, 1)
    if settings is None or not settings.model_provider or not settings.model_name:
        raise ModelConfigurationError("Model provider and model name are not configured")
    api_key = os.environ.get("TRACEGATE_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ModelConfigurationError("Model credential is not configured")
    provider = settings.model_provider.casefold()
    base_url = settings.model_base_url
    if provider == "deepseek" and not base_url:
        base_url = "https://api.deepseek.com"
    if not base_url:
        raise ModelConfigurationError("Custom model providers require an explicit Base URL")
    return OpenAICompatibleProvider(
        api_key=SecretStr(api_key),
        base_url=base_url,
        model=settings.model_name,
        temperature=settings.model_temperature,
        max_tokens=settings.model_max_output_tokens,
        timeout_seconds=settings.model_timeout_seconds,
        max_retries=settings.model_max_retries,
        native_structured_output=settings.model_native_structured_output,
        streaming_enabled=settings.model_streaming_enabled,
        native_tool_calling=settings.model_native_tool_calling,
    )


def ensure_model_profile(
    session: Session,
    settings: AppSettings | None,
    model: OpenAICompatibleProvider,
) -> ModelProfile | None:
    """Persist a queryable, non-secret snapshot of the exact run configuration."""
    if settings is None or not settings.model_provider or not settings.model_name:
        return None
    base_url = settings.model_base_url
    if settings.model_provider.casefold() == "deepseek" and not base_url:
        base_url = "https://api.deepseek.com"
    if not base_url:
        return None
    snapshot = {
        "profile_label": model.profile,
        "provider": settings.model_provider,
        "base_url": base_url,
        "model_name": settings.model_name,
        "temperature": settings.model_temperature,
        "max_output_tokens": settings.model_max_output_tokens,
        "timeout_seconds": settings.model_timeout_seconds,
        "max_retries": settings.model_max_retries,
        "native_structured_output": settings.model_native_structured_output,
        "streaming_enabled": settings.model_streaming_enabled,
        "native_tool_calling": settings.model_native_tool_calling,
        "context_scope": settings.model_context_scope,
        "input_cost_per_million": settings.model_input_cost_per_million,
        "output_cost_per_million": settings.model_output_cost_per_million,
    }
    fingerprint = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    existing = session.scalar(
        select(ModelProfile).where(ModelProfile.fingerprint == fingerprint).limit(1)
    )
    if existing is not None:
        return existing
    profile = ModelProfile(fingerprint=fingerprint, **snapshot)
    session.add(profile)
    session.flush()
    return profile


def enqueue_analysis_run(
    session: Session,
    pull_request: PullRequest,
    repository: Repository,
    model: OpenAICompatibleProvider,
    *,
    force: bool = False,
) -> EnqueueResult:
    if not pull_request.head_sha or not repository.current_index_version:
        raise ValueError("Pull Request Head SHA and index version are required")
    settings = session.get(AppSettings, 1)
    context_scope = settings.model_context_scope if settings is not None else "changed_files"
    if settings is not None and settings.disabled_agents_json:
        raise ValueError(
            "Analysis cannot start while required workflow agents are disabled: "
            + ", ".join(sorted(settings.disabled_agents_json))
        )
    if not force:
        existing = session.scalar(
            select(AgentRun)
            .where(
                AgentRun.pull_request_id == pull_request.id,
                AgentRun.head_sha == pull_request.head_sha,
                AgentRun.index_version == repository.current_index_version,
                AgentRun.prompt_version == PROMPT_VERSION,
                AgentRun.model_profile == model.profile,
                AgentRun.context_scope == context_scope,
                AgentRun.status.in_(["queued", "running", "completed"]),
            )
            .order_by(AgentRun.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            return EnqueueResult(existing, True)
    model_profile = ensure_model_profile(session, settings, model)
    run = AgentRun(
        repository_id=repository.id,
        pull_request_id=pull_request.id,
        status="queued",
        head_sha=pull_request.head_sha,
        index_version=repository.current_index_version,
        prompt_version=PROMPT_VERSION,
        workflow_version=WORKFLOW_VERSION,
        model_profile=model.profile,
        model_profile_id=model_profile.id if model_profile is not None else None,
        context_scope=context_scope,
    )
    pull_request.analysis_status = "queued"
    pull_request.latest_model_profile = model.profile
    session.add(run)
    session.flush()
    return EnqueueResult(run, False)


class RunManager:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self._tasks: dict[str, asyncio.Task[object]] = {}

    def start(self, run_id: str, model: OpenAICompatibleProvider) -> None:
        existing = self._tasks.get(run_id)
        if existing and not existing.done():
            return
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            context_scope = run.context_scope if run is not None else "changed_files"
            settings = session.get(AppSettings, 1)
            disabled_tools = set(settings.disabled_tools_json) if settings is not None else set()
        workflow = TraceGateAgentWorkflow(
            self.session_factory,
            model,
            create_read_only_registry(disabled_tools),
            context_scope=context_scope,
        )
        task = asyncio.create_task(workflow.run(run_id), name=f"tracegate-run-{run_id}")
        self._tasks[run_id] = task
        task.add_done_callback(lambda completed, key=run_id: self._finished(key, completed))

    def enqueue_automatic(self, repository_id: str) -> AutomaticEnqueueResult:
        to_start: list[tuple[str, OpenAICompatibleProvider]] = []
        skipped_for_index = 0
        with self.session_factory() as session:
            settings = session.get(AppSettings, 1)
            if settings is None or not settings.automatic_analysis_enabled or settings.analysis_paused:
                return AutomaticEnqueueResult(0)
            if settings.disabled_agents_json:
                return AutomaticEnqueueResult(
                    0,
                    "Automatic analysis cannot start while required workflow agents are disabled: "
                    + ", ".join(sorted(settings.disabled_agents_json)),
                )
            try:
                model = configured_model(session)
            except ModelConfigurationError as exc:
                return AutomaticEnqueueResult(
                    0,
                    f"Automatic analysis is enabled but unavailable: {exc}",
                )
            repository = session.get(Repository, repository_id)
            if repository is None:
                return AutomaticEnqueueResult(0, "Automatic analysis repository no longer exists.")
            pull_requests = list(
                session.scalars(
                    select(PullRequest).where(
                        PullRequest.repository_id == repository.id,
                        PullRequest.state == "open",
                        PullRequest.analysis_status == "not_analyzed",
                    )
                )
            )
            for pull_request in pull_requests:
                if pull_request.draft and not settings.automatic_analysis_include_drafts:
                    continue
                if (
                    settings.automatic_analysis_require_checks_success
                    and pull_request.checks_status != "success"
                ):
                    continue
                if (
                    not pull_request.head_sha
                    or repository.current_commit_sha != pull_request.head_sha
                    or not repository.current_index_version
                ):
                    skipped_for_index += 1
                    continue
                result = enqueue_analysis_run(session, pull_request, repository, model)
                if not result.reused:
                    to_start.append((result.run.id, model))
            session.commit()
        for run_id, model in to_start:
            self.start(run_id, model)
        reason = (
            f"Automatic analysis skipped {skipped_for_index} Pull Request(s): index the matching Head SHA first."
            if skipped_for_index
            else None
        )
        return AutomaticEnqueueResult(len(to_start), reason)

    def cancel(self, run_id: str) -> bool:
        with self.session_factory() as session:
            run = session.get(AgentRun, run_id)
            if run is None or run.status in {"completed", "failed", "cancelled"}:
                return False
            run.cancellation_requested = True
            session.commit()
        task = self._tasks.get(run_id)
        if task and not task.done():
            task.cancel()
        return True

    def active_count(self) -> int:
        return sum(1 for task in self._tasks.values() if not task.done())

    async def shutdown(self) -> None:
        tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def _finished(self, run_id: str, task: asyncio.Task[object]) -> None:
        self._tasks.pop(run_id, None)
        try:
            task.result()
        except (WorkflowCancelled, asyncio.CancelledError):
            logger.info("agent_run_cancelled run_id=%s", run_id)
        except Exception as exc:
            logger.error("agent_run_failed run_id=%s error_type=%s", run_id, type(exc).__name__)
        else:
            logger.info("agent_run_completed run_id=%s", run_id)
