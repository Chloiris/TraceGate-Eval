from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from tracegate.agent import TraceGateAgentWorkflow
from tracegate.agent.fix_workflow import TraceGateFixWorkflow
from tracegate.autofix.schemas import FixPermissionMode, FixSessionStatus
from tracegate.autofix.workspace import FixWorkspaceManager
from tracegate.pr_advisor.evidence_packet import sanitize_text
from tracegate.studio.database import StudioDatabase
from tracegate.studio.fix_manager import FixManager
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.logging_config import redact_text
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import (
    AgentRun,
    AgentStep,
    AppSettings,
    EvidenceRecord,
    Finding,
    FixResult,
    FixSession,
    FixStep,
    FixToolCallRecord,
    PatchProposalRecord,
    PullRequest,
    Repository,
    ToolCallRecord,
    ValidationRun,
)
from tracegate.studio.run_manager import configured_model, enqueue_analysis_run
from tracegate.tools import create_read_only_registry


MODEL_REVIEW_NODES = {
    "Planner",
    "Code Analyst",
    "Risk Reviewer",
    "Report Composer",
}
MODEL_FIX_NODES = {"PLAN_FIX", "GENERATE_PATCH", "RE_REVIEW"}


class InstrumentedProductionModel:
    """Count logical requests while delegating every call to the production provider."""

    def __init__(self, provider: Any) -> None:
        self.provider = provider
        self.profile = provider.profile
        self.request_count = 0
        self.retry_count = 0
        self.provider_modes: list[str] = []
        self.outputs: list[dict[str, Any]] = []

    async def complete_structured(
        self, *, system_prompt: str, user_prompt: str, output_schema: Any
    ) -> Any:
        self.request_count += 1
        result = await self.provider.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
        )
        self.retry_count += result.retries
        self.provider_modes.append(result.provider_mode)
        self.outputs.append(
            {"schema": output_schema.__name__, "payload": result.payload}
        )
        return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the production Review and Autofix workflows with a real model "
            "against an isolated temporary Git repository."
        )
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--worktree-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="deepseek-chat")
    return parser.parse_args()


def _run_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=60,
        check=False,
        env={
            **{
                name: os.environ[name]
                for name in ("LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TEMP", "TMP")
                if name in os.environ
            },
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if result.returncode != 0:
        raise RuntimeError(
            redact_text(result.stderr[:1_000].strip() or "Git command failed")
        )
    return result.stdout.strip()


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _safe_error(exc: BaseException) -> dict[str, str]:
    message = redact_text(sanitize_text(exc, max_chars=2_000))
    status = re.search(r"\bHTTP\s+(\d{3})\b", message)
    payload = {
        "type": type(exc).__name__,
        "message": message,
    }
    if status:
        payload["http_status"] = status.group(1)
    return payload


def _prepare_repository(workspace: Path) -> tuple[str, str, str]:
    if workspace.exists():
        if any(workspace.iterdir()):
            raise RuntimeError("E2E workspace must be absent or empty")
    else:
        workspace.mkdir(parents=True)
    _run_git(workspace, "init", "-q")
    _run_git(workspace, "config", "user.email", "tracegate-e2e@example.invalid")
    _run_git(workspace, "config", "user.name", "TraceGate Real Model E2E")
    (workspace / "calculator.py").write_text(
        """def safe_divide(numerator: float, denominator: float) -> float | None:
    \"\"\"Return None when the requested division is undefined.\"\"\"
    if denominator == 0:
        return None
    return numerator / denominator
""",
        encoding="utf-8",
    )
    tests = workspace / "tests"
    tests.mkdir()
    (tests / "test_calculator.py").write_text(
        """from calculator import safe_divide


def test_safe_divide_returns_quotient() -> None:
    assert safe_divide(8, 2) == 4


def test_safe_divide_handles_zero() -> None:
    assert safe_divide(8, 0) is None
""",
        encoding="utf-8",
    )
    (workspace / "pyproject.toml").write_text(
        """[project]
name = "tracegate-real-autofix-e2e"
version = "0.0.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
        encoding="utf-8",
    )
    _run_git(workspace, "add", ".")
    _run_git(workspace, "commit", "-qm", "base: handle undefined division")
    base_sha = _run_git(workspace, "rev-parse", "HEAD")

    (workspace / "calculator.py").write_text(
        """def safe_divide(numerator: float, denominator: float) -> float | None:
    \"\"\"Return the requested quotient.\"\"\"
    return numerator / denominator
""",
        encoding="utf-8",
    )
    _run_git(workspace, "add", "calculator.py")
    _run_git(workspace, "commit", "-qm", "regression: simplify division")
    head_sha = _run_git(workspace, "rev-parse", "HEAD")
    original_content = (workspace / "calculator.py").read_text(encoding="utf-8")
    return base_sha, head_sha, original_content


def _lock_version(database: StudioDatabase, session_id: str) -> int:
    with database.session_factory() as session:
        fix_session = session.get(FixSession, session_id)
        if fix_session is None:
            raise RuntimeError("Fix Session disappeared")
        return fix_session.lock_version


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

    workspace = args.workspace.expanduser().resolve()
    database_path = args.database.expanduser().resolve()
    worktree_root = args.worktree_root.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists() or worktree_root.exists():
        raise SystemExit("database and worktree root must not already exist")

    base_sha, head_sha, original_content = _prepare_repository(workspace)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    workspace_manager = FixWorkspaceManager(worktree_root)
    run_id: str | None = None
    finding_id: str | None = None
    session_id: str | None = None
    patch_hash: str | None = None
    failure: BaseException | None = None
    manager: FixManager | None = None
    instrumented_model: InstrumentedProductionModel | None = None
    rollback_recorded = False
    cleanup_recorded = False
    try:
        with database.session_factory() as session:
            settings = session.get(AppSettings, 1)
            if settings is None:
                raise RuntimeError("App Settings were not initialized")
            settings.model_provider = "deepseek"
            settings.model_base_url = None
            settings.model_name = args.model
            settings.model_temperature = 0.0
            settings.model_max_output_tokens = 4096
            settings.model_timeout_seconds = 120
            settings.model_max_retries = 1
            settings.model_native_structured_output = False
            settings.model_streaming_enabled = False
            settings.model_native_tool_calling = False
            settings.model_context_scope = "changed_files"
            repository = Repository(
                owner="tracegate-e2e",
                name="real-model-autofix-repository",
                full_name="tracegate-e2e/real-model-autofix-repository",
                clone_url=None,
                local_path=str(workspace),
                default_branch="main",
                monitoring_enabled=False,
                connection_status="ready",
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)
            version, _repository_map = persist_repository_index(session, repository)
            if version.commit_sha != head_sha:
                raise RuntimeError("Index is not bound to the temporary repository Head")
            pull_request = PullRequest(
                repository_id=repository.id,
                number=1,
                title="Remove undefined-division behavior",
                state="open",
                url="local://tracegate-real-model-autofix-e2e/pr/1",
                author="tracegate-e2e",
                base_ref="main",
                head_ref="regression/remove-zero-guard",
                base_sha=base_sha,
                head_sha=head_sha,
                additions=1,
                deletions=4,
                changed_files=1,
            )
            session.add(pull_request)
            session.commit()
            session.refresh(pull_request)
            instrumented_model = InstrumentedProductionModel(configured_model(session))
            enqueued = enqueue_analysis_run(
                session, pull_request, repository, instrumented_model.provider, force=True
            )
            run_id = enqueued.run.id
            session.commit()

        review = TraceGateAgentWorkflow(
            database.session_factory,
            instrumented_model,
            create_read_only_registry(),
            context_scope="changed_files",
        )
        asyncio.run(review.run(run_id))

        with database.session_factory() as session:
            finding = session.scalar(
                select(Finding)
                .where(
                    Finding.agent_run_id == run_id,
                    Finding.file_path == "calculator.py",
                    Finding.line_start.is_not(None),
                    Finding.line_end.is_not(None),
                )
                .order_by(
                    (Finding.verifier_status == "verified").desc(),
                    Finding.confidence.desc(),
                )
                .limit(1)
            )
            if finding is None or not finding.evidence_ids_json:
                raise RuntimeError(
                    "Real Review workflow did not produce an evidence-bound calculator.py Finding"
                )
            finding_id = finding.id

        fix_workflow = TraceGateFixWorkflow(
            database.session_factory,
            instrumented_model,
            create_read_only_registry(),
            workspace_manager,
        )
        manager = FixManager(
            database.session_factory,
            workspace_manager,
            workflow_factory=lambda: fix_workflow,
        )

        async def run_fix() -> None:
            nonlocal session_id, patch_hash
            session_id = await manager.initialize(
                finding_id=finding_id,
                permission_mode=FixPermissionMode.APPLY_IN_ISOLATED_WORKSPACE.value,
            )
            await manager.plan(
                session_id,
                expected_lock_version=_lock_version(database, session_id),
                force_eligibility=False,
            )
            with database.session_factory() as session:
                current = session.get(FixSession, session_id)
                if current is None:
                    raise RuntimeError("Fix Session disappeared after eligibility")
                needs_force = (
                    current.status == FixSessionStatus.ELIGIBLE.value
                    and current.eligibility_status == "NEEDS_CONFIRMATION"
                )
            if needs_force:
                await manager.plan(
                    session_id,
                    expected_lock_version=_lock_version(database, session_id),
                    force_eligibility=True,
                )
            await manager.generate(
                session_id,
                expected_lock_version=_lock_version(database, session_id),
            )
            with database.session_factory() as session:
                proposal = session.scalar(
                    select(PatchProposalRecord)
                    .where(PatchProposalRecord.fix_session_id == session_id)
                    .order_by(PatchProposalRecord.proposal_version.desc())
                    .limit(1)
                )
                if proposal is None:
                    raise RuntimeError("Production Fix workflow produced no Patch Proposal")
                patch_hash = proposal.patch_hash
            if patch_hash is None:
                raise RuntimeError("Patch Hash disappeared")
            await manager.confirm(
                session_id,
                expected_lock_version=_lock_version(database, session_id),
                patch_hash=patch_hash,
            )
            await manager.apply(
                session_id,
                expected_lock_version=_lock_version(database, session_id),
                patch_hash=patch_hash,
            )
            await manager.validate(
                session_id,
                expected_lock_version=_lock_version(database, session_id),
            )
            await manager.re_review(
                session_id,
                expected_lock_version=_lock_version(database, session_id),
            )

        asyncio.run(run_fix())
    except BaseException as exc:
        failure = exc

    if session_id is None and finding_id is not None:
        with database.session_factory() as session:
            recovered = session.scalar(
                select(FixSession)
                .where(FixSession.finding_id == finding_id)
                .order_by(FixSession.created_at.desc())
                .limit(1)
            )
            if recovered is not None:
                session_id = recovered.id

    try:
        with database.session_factory() as session:
            run = session.get(AgentRun, run_id) if run_id else None
            review_steps = (
                list(
                    session.scalars(
                        select(AgentStep)
                        .where(AgentStep.agent_run_id == run_id)
                        .order_by(AgentStep.sequence)
                    )
                )
                if run_id
                else []
            )
            fix_session = session.get(FixSession, session_id) if session_id else None
            fix_steps = (
                list(
                    session.scalars(
                        select(FixStep)
                        .where(FixStep.fix_session_id == session_id)
                        .order_by(FixStep.sequence)
                    )
                )
                if session_id
                else []
            )
            evidence_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(EvidenceRecord)
                    .where(EvidenceRecord.agent_run_id == run_id)
                )
                or 0
            )
            finding_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(Finding)
                    .where(Finding.agent_run_id == run_id)
                )
                or 0
            )
            review_tool_calls = int(
                session.scalar(
                    select(func.count())
                    .select_from(ToolCallRecord)
                    .join(AgentStep, ToolCallRecord.agent_step_id == AgentStep.id)
                    .where(AgentStep.agent_run_id == run_id)
                )
                or 0
            )
            fix_tool_calls = int(
                session.scalar(
                    select(func.count())
                    .select_from(FixToolCallRecord)
                    .join(FixStep, FixToolCallRecord.fix_step_id == FixStep.id)
                    .where(FixStep.fix_session_id == session_id)
                )
                or 0
            )
            proposal = (
                session.scalar(
                    select(PatchProposalRecord)
                    .where(PatchProposalRecord.fix_session_id == session_id)
                    .order_by(PatchProposalRecord.proposal_version.desc())
                    .limit(1)
                )
                if session_id
                else None
            )
            validation_rows = (
                list(
                    session.scalars(
                        select(ValidationRun)
                        .where(ValidationRun.fix_session_id == session_id)
                        .order_by(ValidationRun.sequence)
                    )
                )
                if session_id
                else []
            )
            result = (
                session.scalar(
                    select(FixResult).where(FixResult.fix_session_id == session_id)
                )
                if session_id
                else None
            )
            selected_finding = session.get(Finding, finding_id) if finding_id else None

            original_workspace_unchanged = (
                (workspace / "calculator.py").read_text(encoding="utf-8")
                == original_content
                and _run_git(workspace, "status", "--porcelain") == ""
                and _run_git(workspace, "rev-parse", "HEAD") == head_sha
            )
            all_validations_passed = bool(validation_rows) and all(
                row.status == "PASSED" and row.return_code == 0
                for row in validation_rows
                if row.required
            )
            completed_model_nodes = sum(
                step.node in MODEL_REVIEW_NODES and step.status == "completed"
                for step in review_steps
            ) + sum(
                step.node in MODEL_FIX_NODES and step.status == "COMPLETED"
                for step in fix_steps
            )
            model_request_count = (
                instrumented_model.request_count if instrumented_model is not None else 0
            )
            verified = (
                failure is None
                and run is not None
                and run.status == "completed"
                and fix_session is not None
                and fix_session.status == FixSessionStatus.COMPLETED.value
                and result is not None
                and result.resolution == "RESOLVED"
                and proposal is not None
                and proposal.patch_hash == patch_hash
                and all_validations_passed
                and original_workspace_unchanged
                and evidence_count >= 1
                and finding_count >= 1
                and review_tool_calls >= 1
                and fix_tool_calls >= 1
                and model_request_count >= 7
                and completed_model_nodes >= 7
                and (run.input_tokens + run.output_tokens) > 0
                and (fix_session.input_tokens + fix_session.output_tokens) > 0
            )
            payload: dict[str, Any] = {
                "verification_status": "VERIFIED_MACOS" if verified else "FAILED",
                "public_pr_fix_e2e_status": "BLOCKED",
                "public_pr_fix_e2e_reason": (
                    "No small public PR with a reproducible, evidence-proven defect and stable "
                    "local validation was selected; no random public PR was auto-modified."
                ),
                "scope": "real_model_temporary_git_repository",
                "measured_at": measured_at.isoformat(),
                "platform": "macOS",
                "credential": "configured",
                "repository": "tracegate-e2e/real-model-autofix-repository",
                "repository_source": "locally constructed temporary Git repository",
                "pull_request": 1,
                "base_sha": base_sha,
                "head_sha": head_sha,
                "model": args.model,
                "model_profile": fix_session.model_profile if fix_session else None,
                "provider_mode": "compatibility_json",
                "review_run_id": run_id,
                "fix_session_id": session_id,
                "finding": (
                    {
                        "id": selected_finding.id,
                        "title": selected_finding.title,
                        "path": selected_finding.file_path,
                        "line_start": selected_finding.line_start,
                        "line_end": selected_finding.line_end,
                        "severity": selected_finding.severity,
                        "confidence": selected_finding.confidence,
                        "verifier_status": selected_finding.verifier_status,
                    }
                    if selected_finding
                    else None
                ),
                "real_model_request_count": model_request_count,
                "completed_model_node_count": completed_model_nodes,
                "provider_retry_count": (
                    instrumented_model.retry_count if instrumented_model else 0
                ),
                "provider_modes_observed": sorted(
                    set(instrumented_model.provider_modes if instrumented_model else [])
                ),
                "tool_call_count": review_tool_calls + fix_tool_calls,
                "review_tool_call_count": review_tool_calls,
                "fix_tool_call_count": fix_tool_calls,
                "evidence_count": evidence_count,
                "finding_count": finding_count,
                "patch_hash": proposal.patch_hash if proposal else patch_hash,
                "changed_files": proposal.changed_files_json if proposal else [],
                "changed_lines": proposal.changed_lines if proposal else None,
                "validation_commands": [
                    {
                        "argv": row.command,
                        "required": row.required,
                        "status": row.status,
                        "return_code": row.return_code,
                        "duration_ms": row.duration_ms,
                    }
                    for row in validation_rows
                ],
                "test_result": "passed" if all_validations_passed else "failed",
                "re_review_result": result.re_review_status if result else None,
                "resolution": result.resolution if result else None,
                "residual_findings": result.residual_findings_json if result else [],
                "review_input_tokens": run.input_tokens if run else 0,
                "review_output_tokens": run.output_tokens if run else 0,
                "fix_input_tokens": fix_session.input_tokens if fix_session else 0,
                "fix_output_tokens": fix_session.output_tokens if fix_session else 0,
                "total_tokens": (
                    (run.input_tokens + run.output_tokens if run else 0)
                    + (
                        fix_session.input_tokens + fix_session.output_tokens
                        if fix_session
                        else 0
                    )
                ),
                "model_latency_ms": (
                    (run.latency_ms if run else 0)
                    + (fix_session.latency_ms if fix_session else 0)
                ),
                "duration_ms": round((time.perf_counter() - started) * 1000),
                "original_workspace_unchanged": original_workspace_unchanged,
                "explicit_e2e_hash_authorization": True,
                "automatic_commit": False,
                "automatic_push": False,
                "review_steps": [
                    {
                        "sequence": step.sequence,
                        "node": step.node,
                        "status": step.status,
                        "duration_ms": step.duration_ms,
                    }
                    for step in review_steps
                ],
                "fix_steps": [
                    {
                        "sequence": step.sequence,
                        "node": step.node,
                        "status": step.status,
                        "duration_ms": step.duration_ms,
                    }
                    for step in fix_steps
                ],
                "database_path": str(database_path),
                "workspace_path": str(workspace),
                "worktree_root": str(worktree_root),
                "result_path": str(output_path),
                "mock_used": False,
                "fixture_used": True,
                "synthetic_test_repository_used": True,
                "cache_result_used": False,
                "rule_fallback_used": False,
                "error": _safe_error(failure) if failure else None,
            }

        patch_artifact_path: Path | None = None
        report_artifact_path: Path | None = None
        if proposal is not None:
            patch_artifact_path = output_path.parent / "autofix.patch"
            patch_artifact_path.write_text(proposal.patch, encoding="utf-8")
        if result is not None:
            report_artifact_path = output_path.parent / "post-fix-report.json"
            _write_result(report_artifact_path, result.report_json)
        payload["patch_artifact_path"] = (
            str(patch_artifact_path) if patch_artifact_path else None
        )
        payload["report_artifact_path"] = (
            str(report_artifact_path) if report_artifact_path else None
        )
        model_outputs_path: Path | None = None
        if instrumented_model is not None:
            model_outputs_path = output_path.parent / "model-output-records.json"
            _write_result(
                model_outputs_path,
                {"outputs": instrumented_model.outputs},
            )
        payload["model_outputs_artifact_path"] = (
            str(model_outputs_path) if model_outputs_path else None
        )

        if session_id and worktree_root.exists() and manager is not None:
            try:
                asyncio.run(
                    manager.rollback(
                        session_id,
                        expected_lock_version=_lock_version(database, session_id),
                    )
                )
                rollback_recorded = True
                asyncio.run(
                    manager.delete_workspace(
                        session_id,
                        expected_lock_version=_lock_version(database, session_id),
                    )
                )
                cleanup_recorded = True
            except BaseException as cleanup_error:
                payload["cleanup_error"] = _safe_error(cleanup_error)
        payload["rollback_recorded"] = rollback_recorded
        payload["workspace_cleanup_recorded"] = cleanup_recorded
        if payload["verification_status"] == "VERIFIED_MACOS" and not (
            rollback_recorded and cleanup_recorded
        ):
            payload["verification_status"] = "FAILED"
        _write_result(output_path, payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if payload["verification_status"] != "VERIFIED_MACOS":
            raise SystemExit(3) from failure
    finally:
        database.dispose()
        if worktree_root.exists() and not any(worktree_root.rglob("worktree")):
            shutil.rmtree(worktree_root, ignore_errors=True)


if __name__ == "__main__":
    main()
