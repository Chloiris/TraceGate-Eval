from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import select

from tracegate.agent.fix_workflow import (
    FIX_NODE_NAMES,
    FixWorkflowCancelled,
    TraceGateFixWorkflow,
)
from tracegate.autofix.confirmation import FixConfirmationService
from tracegate.autofix.errors import AutofixError
from tracegate.autofix.schemas import (
    FixPermissionMode,
    FixSessionStatus,
    ValidationStatus,
)
from tracegate.autofix.validation import ValidationCommandResolver
from tracegate.autofix.workspace import FixWorkspaceManager
from tracegate.models import ModelResult
from tracegate.repository import RepositoryBoundary
from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import (
    AgentRun,
    AppSettings,
    EvidenceRecord,
    FixConfirmation,
    FixEvent,
    FixResult,
    FixSession,
    FixStep,
    FixToolCallRecord,
    Finding,
    PatchProposalRecord,
    PullRequest,
    Repository,
    ValidationRun,
)
from tracegate.tools import create_read_only_registry


PATCH = """diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
 def value():
-    return -1
+    return 1
"""


class FixRecordingModel:
    profile = "test-injected:fix-recording-model"

    def __init__(self, *, base_sha: str, head_sha: str) -> None:
        self.base_sha = base_sha
        self.head_sha = head_sha
        self.calls: list[str] = []

    async def complete_structured(
        self, *, system_prompt: str, user_prompt: str, output_schema
    ):  # type: ignore[no-untyped-def]
        self.calls.append(output_schema.__name__)
        payloads = {
            "FixPlan": {
                "finding_id": "finding-fix-workflow",
                "objective": "Return the valid positive value.",
                "root_cause": "The reviewed function returns a negative sentinel.",
                "affected_files": ["main.py"],
                "affected_symbols": ["value"],
                "constraints": ["Keep the change minimal."],
                "proposed_steps": ["Replace the negative sentinel."],
                "expected_behavior": "value() returns 1.",
                "validation_strategy": ["Run repository tests."],
                "risk_notes": [],
                "confidence": 0.95,
            },
            "PatchProposal": {
                "finding_id": "finding-fix-workflow",
                "base_sha": self.base_sha,
                "head_sha": self.head_sha,
                "patch": PATCH,
                "changed_files": ["main.py"],
                "estimated_changed_lines": 2,
                "rationale": "Replace only the evidence-bound sentinel.",
                "assumptions": [],
                "validation_commands": [
                    {
                        "argv": ["totally-untrusted-model-command"],
                        "command_purpose": "This must never run.",
                        "required": True,
                        "timeout": 10,
                        "expected_result": "Ignored by the controlled resolver.",
                        "source": "model_suggestion",
                    }
                ],
                "residual_risks": [],
                "confidence": 0.93,
            },
            "ReReviewAssessment": {
                "original_finding_supported": False,
                "residual_findings": [],
                "residual_risks": [],
                "new_high_risk": False,
                "summary": "The bounded diff removes the reviewed sentinel.",
                "confidence": 0.92,
            },
        }
        return ModelResult(
            payload=payloads[output_schema.__name__],
            input_tokens=11,
            output_tokens=7,
            latency_ms=4,
            retries=0,
            provider_mode="test",
        )


@dataclass
class WorkflowFixture:
    database: StudioDatabase
    workflow: TraceGateFixWorkflow
    model: FixRecordingModel
    workspace: Path
    workspace_root: Path


def _git(workspace: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _fixture(
    tmp_path: Path,
    *,
    passing_test: bool = True,
    python_project: bool = True,
    large_main: bool = False,
    verified_finding: bool = True,
) -> WorkflowFixture:
    workspace = tmp_path / "source-repository"
    workspace.mkdir()
    _git(workspace, "init", "-q")
    _git(workspace, "config", "user.email", "tracegate@example.invalid")
    _git(workspace, "config", "user.name", "TraceGate Test")
    (workspace / "main.py").write_text("def value():\n    return 0\n", encoding="utf-8")
    if python_project:
        (workspace / "pyproject.toml").write_text(
            "[project]\nname='fix-workflow-fixture'\nversion='0.0.0'\n",
            encoding="utf-8",
        )
        (workspace / "test_main.py").write_text(
            (
                "from main import value\n\n"
                + (
                    "def test_value():\n    assert value() == 1\n"
                    if passing_test
                    else "def test_value():\n    assert value() == 2\n"
                )
            ),
            encoding="utf-8",
        )
    else:
        (workspace / "package.json").write_text(
            '{"scripts":{"lint":"ignored","typecheck":"ignored"}}',
            encoding="utf-8",
        )
    _git(workspace, "add", ".")
    _git(workspace, "commit", "-qm", "base fixture")
    base_sha = _git(workspace, "rev-parse", "HEAD")
    head_content = "def value():\n    return -1\n"
    if large_main:
        head_content += "# bounded filler\n" * 10_000
    (workspace / "main.py").write_text(head_content, encoding="utf-8")
    _git(workspace, "add", "main.py")
    _git(workspace, "commit", "-qm", "introduce reviewed finding")
    head_sha = _git(workspace, "rev-parse", "HEAD")

    url = f"sqlite+pysqlite:///{(tmp_path / 'studio.db').as_posix()}"
    upgrade_database(url)
    database = StudioDatabase(url)
    with database.session_factory() as session:
        repository = Repository(
            owner="acme",
            name="fix-workflow",
            full_name="acme/fix-workflow",
            local_path=str(workspace),
            connection_status="ready",
        )
        session.add(repository)
        session.commit()
        session.refresh(repository)
        version, _repository_map = persist_repository_index(session, repository)
        pull_request = PullRequest(
            repository_id=repository.id,
            number=7,
            title="Fix a negative sentinel",
            state="open",
            url="https://github.com/acme/fix-workflow/pull/7",
            base_sha=base_sha,
            head_sha=head_sha,
        )
        session.add(pull_request)
        session.flush()
        run = AgentRun(
            repository_id=repository.id,
            pull_request_id=pull_request.id,
            status="completed",
            head_sha=head_sha,
            index_version=version.id,
        )
        session.add(run)
        session.flush()
        evidence = EvidenceRecord(
            id="evidence-fix-workflow",
            agent_run_id=run.id,
            source_type="indexed_file",
            source_uri="repository://acme/fix-workflow/main.py",
            file_path="main.py",
            commit_sha=head_sha,
            content_hash="1" * 64,
            payload_json={"snippet": "return -1"},
        )
        finding = Finding(
            id="finding-fix-workflow",
            agent_run_id=run.id,
            severity="medium",
            confidence=0.95,
            category="correctness",
            title="Negative sentinel escapes",
            message="value() returns the invalid negative sentinel.",
            file_path="main.py",
            line_start=2,
            line_end=2,
            commit_sha=head_sha,
            symbol="value",
            suggested_action="Return the valid value.",
            verifier_status="verified" if verified_finding else "needs_confirmation",
            evidence_ids_json=[evidence.id],
        )
        session.add_all([evidence, finding])
        session.commit()

    model = FixRecordingModel(base_sha=base_sha, head_sha=head_sha)
    workspace_root = tmp_path / "fix-workspaces"
    workflow = TraceGateFixWorkflow(
        database.session_factory,
        model,
        create_read_only_registry(),
        FixWorkspaceManager(workspace_root),
    )
    return WorkflowFixture(database, workflow, model, workspace, workspace_root)


async def _reach_patch_applied(fixture: WorkflowFixture) -> tuple[str, str]:
    session_id = await fixture.workflow.initialize(
        "finding-fix-workflow",
        FixPermissionMode.APPLY_IN_ISOLATED_WORKSPACE,
    )
    await fixture.workflow.plan(session_id)
    generated = await fixture.workflow.generate(session_id)
    patch_hash = generated["patch_hash"]
    with fixture.database.session_factory() as session:
        fix_session = session.get(FixSession, session_id)
        assert fix_session is not None
        FixConfirmationService().issue(
            session, fix_session, patch_hash=patch_hash, ttl_seconds=900
        )
        session.commit()
    await fixture.workflow.apply(session_id, patch_hash)
    return session_id, patch_hash


@pytest.mark.asyncio
async def test_fix_workflow_runs_real_staged_graph_and_persists_facts(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    try:
        session_id, patch_hash = await _reach_patch_applied(fixture)
        validated = await fixture.workflow.validate(session_id)
        assert validated["validation_status"] == "PASSED"
        finished = await fixture.workflow.re_review(session_id)

        assert finished["report"]["finding_resolution"] == "RESOLVED"
        assert finished["report"]["validation_status"] == "PASSED"
        assert "return 1" in finished["final_diff"]
        assert fixture.model.calls == [
            "FixPlan",
            "PatchProposal",
            "ReReviewAssessment",
        ]
        assert (fixture.workspace / "main.py").read_text(encoding="utf-8") == (
            "def value():\n    return -1\n"
        )
        assert _git(fixture.workspace, "status", "--porcelain") == ""

        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert fix_session.status == FixSessionStatus.COMPLETED.value
            assert fix_session.model_profile == fixture.model.profile
            assert fix_session.workspace_index_version_id is not None
            assert fix_session.input_tokens == 33
            assert fix_session.output_tokens == 21
            assert fix_session.latency_ms == 12
            proposal = session.scalar(
                select(PatchProposalRecord).where(
                    PatchProposalRecord.fix_session_id == session_id
                )
            )
            assert proposal is not None
            assert proposal.patch_hash == patch_hash
            assert proposal.changed_files_json == ["main.py"]
            assert [
                command["argv"] for command in proposal.validation_plan_json["commands"]
            ] == [
                ["git", "diff", "--check"],
                ["python", "-m", "pytest", "-q", "test_main.py"],
                ["python", "-m", "pytest", "-q"],
            ]
            assert proposal.validation_plan_json["model_suggested_only"][0]["argv"] == [
                "totally-untrusted-model-command"
            ]
            assert proposal.validation_plan_json["model_suggestions_executed"] is False
            assert (
                session.scalar(
                    select(FixToolCallRecord)
                    .join(FixStep, FixStep.id == FixToolCallRecord.fix_step_id)
                    .where(FixStep.fix_session_id == session_id)
                ).tool_name
                == "read_file"
            )  # type: ignore[union-attr]
            steps = list(
                session.scalars(
                    select(FixStep)
                    .where(FixStep.fix_session_id == session_id)
                    .order_by(FixStep.sequence)
                )
            )
            assert [step.node for step in steps] == list(FIX_NODE_NAMES)
            assert all(step.status == "COMPLETED" for step in steps)
            validations = list(
                session.scalars(
                    select(ValidationRun)
                    .where(ValidationRun.fix_session_id == session_id)
                    .order_by(ValidationRun.sequence)
                )
            )
            assert all(row.status == "PASSED" for row in validations)
            assert all(
                row.command[0] != "totally-untrusted-model-command"
                for row in validations
            )
            result = session.scalar(
                select(FixResult).where(FixResult.fix_session_id == session_id)
            )
            assert result is not None
            assert result.resolution == "RESOLVED"
            event_types = {
                event.event_type
                for event in session.scalars(
                    select(FixEvent).where(FixEvent.fix_session_id == session_id)
                )
            }
            assert {
                "workflow_step",
                "patch_ready",
                "validation_started",
                "validation_finished",
                "re_review",
                "report",
                "terminal",
            }.issubset(event_types)
            events = list(
                session.scalars(
                    select(FixEvent)
                    .where(FixEvent.fix_session_id == session_id)
                    .order_by(FixEvent.sequence)
                )
            )
            output_sequences = [
                event.sequence
                for event in events
                if event.event_type == "validation_output"
            ]
            output_events = [
                event for event in events if event.event_type == "validation_output"
            ]
            finished_sequences = [
                event.sequence
                for event in events
                if event.event_type == "validation_finished"
            ]
            assert output_sequences
            assert all(
                len(event.payload_json["chunk"]) <= 16_384 for event in output_events
            )
            assert sum(len(event.payload_json["chunk"]) for event in output_events) <= (
                64_000 * len(validations)
            )
            assert finished_sequences
            assert min(output_sequences) < max(finished_sequences)
            confirmation = session.scalar(
                select(FixConfirmation).where(
                    FixConfirmation.fix_session_id == session_id
                )
            )
            assert confirmation is not None
            assert confirmation.consumed_at is not None
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_validation_marks_session_stale_when_pr_head_changes(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    try:
        session_id, _patch_hash = await _reach_patch_applied(fixture)
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            pull_request = session.get(PullRequest, fix_session.pull_request_id)
            assert pull_request is not None
            pull_request.head_sha = "f" * 40
            session.commit()

        with pytest.raises(AutofixError) as caught:
            await fixture.workflow.validate(session_id)
        assert caught.value.code == "fix_head_stale"
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert fix_session.status == FixSessionStatus.STALE.value
            proposal = session.scalar(
                select(PatchProposalRecord).where(
                    PatchProposalRecord.fix_session_id == session_id
                )
            )
            assert proposal is not None and proposal.stale_at is not None
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_validation_rejects_and_restores_workspace_drift(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    try:
        session_id, _patch_hash = await _reach_patch_applied(fixture)
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None and fix_session.workspace_path
            worktree = Path(fix_session.workspace_path)
        test_path = worktree / "test_main.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8") + "\n# unapproved validation drift\n",
            encoding="utf-8",
        )

        validated = await fixture.workflow.validate(session_id)
        assert validated["validation_status"] == ValidationStatus.FAILED.value
        with fixture.database.session_factory() as session:
            rows = list(
                session.scalars(
                    select(ValidationRun)
                    .where(ValidationRun.fix_session_id == session_id)
                    .order_by(ValidationRun.sequence)
                )
            )
            assert rows[0].status == ValidationStatus.FAILED.value
            assert "changed the isolated workspace" in (rows[0].stderr_summary or "")
        assert "unapproved validation drift" not in test_path.read_text(encoding="utf-8")
        assert "return 1" in (worktree / "main.py").read_text(encoding="utf-8")
    finally:
        fixture.database.dispose()


def test_lint_and_typecheck_do_not_count_as_test_commands(tmp_path: Path) -> None:
    repository = tmp_path / "lint-only-repository"
    repository.mkdir()
    (repository / "package.json").write_text(
        '{"scripts":{"lint":"eslint .","typecheck":"tsc --noEmit"}}',
        encoding="utf-8",
    )
    plan = ValidationCommandResolver().resolve(RepositoryBoundary(repository))

    assert [command.argv for command in plan.commands] == [
        ["git", "diff", "--check"],
        ["npm", "lint"],
        ["npm", "typecheck"],
    ]
    assert plan.notes == ["NO_TEST_COMMAND_AVAILABLE"]


@pytest.mark.asyncio
async def test_lint_only_validation_cannot_be_resolved_by_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_npm = fake_bin / ("npm.cmd" if os.name == "nt" else "npm")
    fake_npm.write_text(
        "@echo off\r\nexit /b 0\r\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n",
        encoding="utf-8",
    )
    if os.name != "nt":
        fake_npm.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    fixture = _fixture(tmp_path, python_project=False)
    try:
        session_id, _patch_hash = await _reach_patch_applied(fixture)
        validated = await fixture.workflow.validate(session_id)
        assert validated["validation_status"] == "NO_TEST_COMMAND_AVAILABLE"
        finished = await fixture.workflow.re_review(session_id)
        assert finished["report"]["finding_resolution"] == "NEEDS_HUMAN_REVIEW"
        assert finished["report"]["validation_status"] == "NO_TEST_COMMAND_AVAILABLE"
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_generate_rejects_unbounded_model_file_context(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path, large_main=True)
    try:
        session_id = await fixture.workflow.initialize("finding-fix-workflow")
        await fixture.workflow.plan(session_id)
        with pytest.raises(AutofixError) as raised:
            await fixture.workflow.generate(session_id)
        assert raised.value.code == "fix_model_context_too_large"
        assert fixture.model.calls == ["FixPlan"]
        with fixture.database.session_factory() as session:
            assert (
                session.scalar(
                    select(PatchProposalRecord).where(
                        PatchProposalRecord.fix_session_id == session_id
                    )
                )
                is None
            )
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_eligibility_confirmation_is_recoverable_before_model_plan(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, verified_finding=False)
    try:
        session_id = await fixture.workflow.initialize("finding-fix-workflow")
        paused = await fixture.workflow.plan(session_id)
        assert paused["eligibility"]["status"] == "NEEDS_CONFIRMATION"
        assert fixture.model.calls == []
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert fix_session.status == FixSessionStatus.ELIGIBLE.value
            assert [
                step.node
                for step in session.scalars(
                    select(FixStep)
                    .where(FixStep.fix_session_id == session_id)
                    .order_by(FixStep.sequence)
                )
            ] == ["LOAD_FINDING", "CHECK_FIX_ELIGIBILITY"]

        planned = await fixture.workflow.plan(session_id, force_eligibility=True)
        assert planned["plan"]["finding_id"] == "finding-fix-workflow"
        assert fixture.model.calls == ["FixPlan"]
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert fix_session.status == FixSessionStatus.PLAN_READY.value
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_apply_requires_bound_confirmation_without_poisoning_session(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    try:
        session_id = await fixture.workflow.initialize(
            "finding-fix-workflow",
            FixPermissionMode.APPLY_IN_ISOLATED_WORKSPACE,
        )
        await fixture.workflow.plan(session_id)
        generated = await fixture.workflow.generate(session_id)

        with pytest.raises(AutofixError, match="confirmation") as raised:
            await fixture.workflow.apply(session_id, generated["patch_hash"])
        assert raised.value.code == "fix_confirmation_required"
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert (
                fix_session.status == FixSessionStatus.AWAITING_USER_CONFIRMATION.value
            )
        isolated = next(fixture.workspace_root.glob("*/*/worktree"))
        assert (
            (isolated / "main.py").read_text(encoding="utf-8").endswith("return -1\n")
        )
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_patch_limit_accepts_small_valid_global_setting(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    try:
        session_id = await fixture.workflow.initialize("finding-fix-workflow")
        await fixture.workflow.plan(session_id)
        with fixture.database.session_factory() as session:
            settings = session.get(AppSettings, 1)
            assert settings is not None
            settings.autofix_max_changed_lines = 50
            session.commit()

        generated = await fixture.workflow.generate(session_id)
        assert generated["inspection"]["changed_lines"] == 2
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert (
                fix_session.status == FixSessionStatus.AWAITING_USER_CONFIRMATION.value
            )
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_model_cannot_override_failed_validation(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path, passing_test=False)
    try:
        session_id, _patch_hash = await _reach_patch_applied(fixture)
        validated = await fixture.workflow.validate(session_id)
        assert validated["validation_status"] == "FAILED"
        finished = await fixture.workflow.re_review(session_id)
        assert finished["report"]["finding_resolution"] == "VERIFICATION_FAILED"
        assert finished["report"]["validation_status"] == "FAILED"
    finally:
        fixture.database.dispose()


@pytest.mark.asyncio
async def test_cancellation_before_validation_is_explicit(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    try:
        session_id, _patch_hash = await _reach_patch_applied(fixture)
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            fix_session.cancellation_requested = True
            session.commit()

        with pytest.raises(FixWorkflowCancelled):
            await fixture.workflow.validate(session_id)
        with fixture.database.session_factory() as session:
            fix_session = session.get(FixSession, session_id)
            assert fix_session is not None
            assert fix_session.status == FixSessionStatus.CANCELLED.value
            terminal = session.scalar(
                select(FixEvent)
                .where(
                    FixEvent.fix_session_id == session_id,
                    FixEvent.event_type == "terminal",
                )
                .order_by(FixEvent.sequence.desc())
            )
            assert terminal is not None
            assert terminal.payload_json["status"] == "CANCELLED"
    finally:
        fixture.database.dispose()
