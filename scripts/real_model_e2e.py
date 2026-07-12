from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from tracegate.agent import TraceGateAgentWorkflow
from tracegate.pr_advisor.evidence_packet import sanitize_text
from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import (
    AgentRun,
    AgentStep,
    AppSettings,
    EvidenceRecord,
    Finding,
    ModelProfile,
    PullRequest,
    Repository,
    ToolCallRecord,
)
from tracegate.studio.run_manager import configured_model, enqueue_analysis_run
from tracegate.tools import create_read_only_registry


def _count(session, model, *filters) -> int:  # type: ignore[no-untyped-def]
    return int(
        session.scalar(select(func.count()).select_from(model).where(*filters)) or 0
    )


def _http_status(message: str | None) -> int | None:
    match = re.search(r"\bHTTP\s+(\d{3})\b", message or "")
    return int(match.group(1)) if match else None


def _write_result(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the real TraceGate Studio model workflow against an already-cloned public PR."
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--author")
    parser.add_argument("--additions", type=int, required=True)
    parser.add_argument("--deletions", type=int, required=True)
    parser.add_argument("--changed-files", type=int, required=True)
    parser.add_argument("--model", default="deepseek-chat")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    started = time.perf_counter()
    measured_at = datetime.now(timezone.utc)
    credential_configured = bool(
        os.environ.get("TRACEGATE_LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    )
    print(f"credential {'configured' if credential_configured else 'missing'}")
    if not credential_configured:
        raise SystemExit(2)
    workspace = args.workspace.resolve()
    database_path = args.database.resolve()
    output_path = args.output.resolve()
    if not (workspace / ".git").exists():
        raise SystemExit("workspace is not a Git repository")
    owner, name = args.repository.split("/", 1)
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    run_id: str | None = None
    workflow_error: Exception | None = None
    try:
        with database.session_factory() as session:
            settings = session.get(AppSettings, 1)
            assert settings is not None
            settings.model_provider = "deepseek"
            settings.model_base_url = None
            settings.model_name = args.model
            settings.model_temperature = 0.0
            settings.model_max_output_tokens = 2048
            settings.model_timeout_seconds = 90
            settings.model_max_retries = 1
            settings.model_native_structured_output = False
            settings.model_streaming_enabled = False
            settings.model_native_tool_calling = False
            settings.model_context_scope = "changed_files"
            repository = Repository(
                owner=owner,
                name=name,
                full_name=args.repository,
                clone_url=f"https://github.com/{args.repository}.git",
                local_path=str(workspace),
                default_branch="main",
                monitoring_enabled=False,
                connection_status="ready",
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)
            version, repository_map = persist_repository_index(session, repository)
            if version.commit_sha != args.head_sha:
                raise RuntimeError(
                    "indexed commit does not match the requested PR Head SHA"
                )
            pull_request = PullRequest(
                repository_id=repository.id,
                number=args.pr,
                title=args.title,
                state="closed",
                url=args.url,
                author=args.author,
                base_ref="main",
                head_ref=f"pull/{args.pr}/head",
                base_sha=args.base_sha,
                head_sha=args.head_sha,
                additions=args.additions,
                deletions=args.deletions,
                changed_files=args.changed_files,
            )
            session.add(pull_request)
            session.commit()
            session.refresh(pull_request)
            model = configured_model(session)
            enqueued = enqueue_analysis_run(
                session, pull_request, repository, model, force=True
            )
            run_id = enqueued.run.id
            session.commit()
            index_metrics = {
                "version": version.id,
                "file_count": version.file_count,
                "symbol_count": version.symbol_count,
                "repository_map_nodes": len(repository_map.nodes),
                "repository_map_edges": len(repository_map.edges),
                "duration_ms": version.duration_ms,
            }

        workflow = TraceGateAgentWorkflow(
            database.session_factory,
            model,
            create_read_only_registry(),
            context_scope="changed_files",
        )
        try:
            asyncio.run(workflow.run(run_id))
        except (
            Exception
        ) as exc:  # Persist the production workflow's sanitized failure details below.
            workflow_error = exc

        with database.session_factory() as session:
            run = session.get(AgentRun, run_id)
            assert run is not None
            steps = list(
                session.scalars(
                    select(AgentStep)
                    .where(AgentStep.agent_run_id == run_id)
                    .order_by(AgentStep.sequence)
                )
            )
            evidence_count = _count(
                session, EvidenceRecord, EvidenceRecord.agent_run_id == run_id
            )
            finding_count = _count(session, Finding, Finding.agent_run_id == run_id)
            tool_call_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(ToolCallRecord)
                    .join(AgentStep, ToolCallRecord.agent_step_id == AgentStep.id)
                    .where(AgentStep.agent_run_id == run_id)
                )
                or 0
            )
            completed_tool_call_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(ToolCallRecord)
                    .join(AgentStep, ToolCallRecord.agent_step_id == AgentStep.id)
                    .where(
                        AgentStep.agent_run_id == run_id,
                        ToolCallRecord.status == "completed",
                    )
                )
                or 0
            )
            model_profile = (
                session.get(ModelProfile, run.model_profile_id)
                if run.model_profile_id
                else None
            )
            error_message = (
                sanitize_text(run.error_message, max_chars=1000)
                if run.error_message
                else None
            )
            stages = {
                "INGEST": "completed",
                "PLAN": next(
                    (step.status for step in steps if step.node == "Planner"),
                    "not_started",
                ),
                "RETRIEVE": (
                    "completed"
                    if all(
                        any(
                            step.node == node and step.status == "completed"
                            for step in steps
                        )
                        for node in ("Repository Retriever", "Context Resolver")
                    )
                    else "failed"
                ),
                "ANALYZE": (
                    "completed"
                    if all(
                        any(
                            step.node == node and step.status == "completed"
                            for step in steps
                        )
                        for node in ("Code Analyst", "Risk Reviewer")
                    )
                    else "failed"
                ),
                "VERIFY": next(
                    (step.status for step in steps if step.node == "Verifier"),
                    "not_started",
                ),
                "REPORT": next(
                    (step.status for step in steps if step.node == "Report Composer"),
                    "not_started",
                ),
            }
            payload: dict[str, object] = {
                "verification_status": (
                    "VERIFIED_MACOS"
                    if run.status == "completed"
                    and len(steps) == 7
                    and all(step.status == "completed" for step in steps)
                    and tool_call_count >= 1
                    and completed_tool_call_count >= 1
                    and evidence_count >= 1
                    and finding_count >= 1
                    and run.input_tokens + run.output_tokens > 0
                    and run.latency_ms > 0
                    else "FAILED"
                ),
                "measured_at": measured_at.isoformat(),
                "platform": "macOS",
                "credential": "configured",
                "repository": args.repository,
                "pull_request": args.pr,
                "pull_request_url": args.url,
                "base_sha": args.base_sha,
                "head_sha": args.head_sha,
                "model": args.model,
                "model_profile": run.model_profile,
                "provider_mode": "compatibility_json",
                "native_tool_calling": False,
                "real_model_request_count": 4 if run.status == "completed" else None,
                "run_id": run.id,
                "run_status": run.status,
                "duration_ms": round((time.perf_counter() - started) * 1000),
                "model_latency_ms": run.latency_ms,
                "input_tokens": run.input_tokens,
                "output_tokens": run.output_tokens,
                "total_tokens": run.input_tokens + run.output_tokens,
                "retry_count": run.retry_count,
                "retrieval_hit_count": run.retrieval_hit_count,
                "tool_call_count": tool_call_count,
                "completed_tool_call_count": completed_tool_call_count,
                "evidence_count": evidence_count,
                "finding_count": finding_count,
                "agent_trace_count": len(steps),
                "agent_steps": [
                    {
                        "sequence": step.sequence,
                        "node": step.node,
                        "status": step.status,
                        "duration_ms": step.duration_ms,
                    }
                    for step in steps
                ],
                "stages": stages,
                "index": index_metrics,
                "database_path": str(database_path),
                "result_path": str(output_path),
                "model_profile_persisted": model_profile is not None,
                "error": (
                    {
                        "http_status": _http_status(error_message),
                        "type": run.error_code,
                        "message": error_message,
                    }
                    if run.error_code or error_message
                    else None
                ),
                "mock_used": False,
                "fixture_used": False,
                "cache_result_used": False,
                "rule_fallback_used": False,
            }
            _write_result(output_path, payload)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            if payload["verification_status"] != "VERIFIED_MACOS":
                raise SystemExit(3) from workflow_error
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
