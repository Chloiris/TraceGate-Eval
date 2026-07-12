from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from tracegate.autofix.confirmation import FixConfirmationService
from tracegate.autofix.workspace import FixWorkspaceManager
from tracegate.studio.app import create_app
from tracegate.studio.config import StudioSettings
from tracegate.studio.fix_manager import FixManager
from tracegate.studio.models import (
    AgentRun,
    Finding,
    FixConfirmation,
    FixEvent,
    FixResult,
    FixSession,
    IndexVersion,
    PatchProposalRecord,
    PullRequest,
    Repository,
    ValidationRun,
)


TOKEN = "autofix-api-test-token-0123456789abcdef"
HEAD_SHA = "b" * 40
BASE_SHA = "a" * 40
PATCH = """diff --git a/service.py b/service.py
--- a/service.py
+++ b/service.py
@@ -1 +1 @@
-return value * 2
+return value
"""
PATCH_HASH = "b0c1f6d7fc7e26a7b5f4dae7563cf6452a916ceed74baa9ff38c2cf65a849caa"


def _settings(tmp_path: Path) -> StudioSettings:
    return StudioSettings(
        local_api_token=SecretStr(TOKEN),
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'studio.db').as_posix()}",
        eval_root=tmp_path,
        model_api_key_configured=True,
    )


def _headers(key: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if key:
        headers["Idempotency-Key"] = key
    return headers


class FakeFixWorkflow:
    def __init__(self, session_factory, calls: Counter[str]) -> None:  # type: ignore[no-untyped-def]
        self.session_factory = session_factory
        self.calls = calls

    async def initialize(self, finding_id: str, permission_mode: str) -> str:
        self.calls["initialize"] += 1
        with self.session_factory() as session:
            finding = session.get(Finding, finding_id)
            assert finding is not None
            run = session.get(AgentRun, finding.agent_run_id)
            assert run is not None and run.pull_request_id is not None
            pull_request = session.get(PullRequest, run.pull_request_id)
            assert pull_request is not None and pull_request.base_sha and pull_request.head_sha
            repository = session.get(Repository, run.repository_id)
            assert repository is not None
            item = FixSession(
                repository_id=repository.id,
                pull_request_id=pull_request.id,
                finding_id=finding.id,
                source_agent_run_id=run.id,
                base_sha=pull_request.base_sha,
                head_sha=pull_request.head_sha,
                index_version_id=repository.current_index_version,
                status="CREATED",
                permission_mode=permission_mode,
                workflow_version="fix-test-v1",
                started_at=datetime.now(timezone.utc),
            )
            session.add(item)
            session.flush()
            session.add(
                FixEvent(
                    fix_session_id=item.id,
                    sequence=1,
                    event_type="session",
                    payload_json={},
                )
            )
            session.commit()
            return item.id

    async def plan(self, session_id: str, force_eligibility: bool = False) -> None:
        self.calls["plan"] += 1
        if force_eligibility:
            self.calls["plan_forced"] += 1
        with self.session_factory() as session:
            item = session.get(FixSession, session_id)
            assert item is not None
            item.status = "PLAN_READY"
            item.current_node = "PLAN_FIX"
            item.plan_json = {
                "finding_id": item.finding_id,
                "objective": "Remove the incorrect multiplier.",
                "root_cause": "The function doubles an already normalized value.",
                "affected_files": ["service.py"],
                "affected_symbols": ["normalize"],
                "constraints": ["Preserve the public signature."],
                "proposed_steps": ["Return the normalized value directly."],
                "expected_behavior": "The value is returned once.",
                "validation_strategy": ["Run pytest."],
                "risk_notes": [],
                "confidence": 0.92,
            }
            self._event(session, item, "workflow_step", "Fix plan is ready.")
            session.commit()

    async def generate(self, session_id: str) -> None:
        self.calls["generate"] += 1
        with self.session_factory() as session:
            item = session.get(FixSession, session_id)
            assert item is not None
            item.status = "AWAITING_USER_CONFIRMATION"
            item.current_node = "AWAIT_USER_CONFIRMATION"
            validation_plan = {
                "commands": [
                    {
                        "argv": ["pytest", "-q"],
                        "command_purpose": "Run the focused Python tests.",
                        "required": True,
                        "timeout": 180,
                        "expected_result": "All tests pass.",
                        "source": "pyproject.toml",
                    }
                ],
                "notes": [],
            }
            session.add(
                PatchProposalRecord(
                    fix_session_id=item.id,
                    proposal_version=1,
                    base_sha=item.base_sha,
                    head_sha=item.head_sha,
                    patch=PATCH,
                    patch_hash=PATCH_HASH,
                    rationale="Remove the incorrect multiplier.",
                    changed_files_json=["service.py"],
                    changed_lines=2,
                    confidence=0.91,
                    validation_plan_json=validation_plan,
                    assumptions_json=[],
                    risk_notes_json=[],
                )
            )
            self._event(session, item, "patch_ready", "Patch Proposal is ready.", payload={
                "patch_hash": PATCH_HASH,
                "changed_files": ["service.py"],
                "changed_lines": 2,
                "additions": 1,
                "deletions": 1,
                "warnings": [],
                "requires_confirmation": True,
            })
            session.commit()

    async def apply(self, session_id: str, patch_hash: str) -> None:
        self.calls["apply"] += 1
        with self.session_factory() as session:
            item = session.get(FixSession, session_id)
            assert item is not None
            FixConfirmationService().consume_bound(
                session,
                item,
                patch_hash=patch_hash,
                current_head_sha=item.head_sha,
            )
            item.status = "PATCH_APPLIED"
            item.current_node = "APPLY_PATCH"
            self._event(session, item, "workflow_step", "Patch applied in an isolated workspace.")
            session.commit()

    async def validate(self, session_id: str) -> None:
        self.calls["validate"] += 1
        with self.session_factory() as session:
            item = session.get(FixSession, session_id)
            assert item is not None
            item.status = "VALIDATION_COMPLETE"
            item.current_node = "RUN_VALIDATION"
            run = ValidationRun(
                fix_session_id=item.id,
                sequence=1,
                command=["pytest", "-q"],
                purpose="Run the focused Python tests.",
                required=True,
                status="PASSED",
                return_code=0,
                stdout_summary="1 passed",
                stderr_summary="",
                output_truncated=False,
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                duration_ms=12,
            )
            session.add(run)
            session.flush()
            self._event(
                session,
                item,
                "validation_finished",
                "Validation passed.",
                payload=_validation_payload(run),
            )
            session.commit()

    async def re_review(self, session_id: str) -> None:
        self.calls["re_review"] += 1
        with self.session_factory() as session:
            item = session.get(FixSession, session_id)
            assert item is not None
            item.status = "COMPLETED"
            item.current_node = None
            item.finished_at = datetime.now(timezone.utc)
            report = {
                "fix_session_id": item.id,
                "finding_id": item.finding_id,
                "patch_hash": PATCH_HASH,
                "applied": True,
                "validation_status": "PASSED",
                "commands_run": [["pytest", "-q"]],
                "passed_commands": [["pytest", "-q"]],
                "failed_commands": [],
                "re_review_status": "completed",
                "finding_resolution": "RESOLVED",
                "residual_findings": [],
                "residual_risks": [],
                "final_summary": "Resolved with passing validation and deterministic verification.",
            }
            result = FixResult(
                fix_session_id=item.id,
                resolution="RESOLVED",
                validation_status="PASSED",
                re_review_status="completed",
                residual_findings_json=[],
                residual_risks_json=[],
                report_json={
                    **report,
                    "final_diff": PATCH,
                    "facts": {
                        "committed": False,
                        "pushed": False,
                        "source_workspace_mutated": False,
                    },
                },
            )
            session.add(result)
            session.flush()
            self._event(session, item, "report", "Post-Fix Report is ready.", payload={
                "id": result.id,
                "fix_session_id": item.id,
                "resolution": "RESOLVED",
                "validation_status": "PASSED",
                "re_review_status": "completed",
                "residual_findings": [],
                "residual_risks": [],
                "report": report,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
            session.flush()
            self._event(session, item, "terminal", "Fix Session completed.", payload={
                "status": "COMPLETED",
                "error_code": None,
                "error_message": None,
            })
            session.commit()

    @staticmethod
    def _event(session, item: FixSession, event_type: str, message: str, payload=None) -> None:  # type: ignore[no-untyped-def]
        sequence = session.scalar(
            select(FixEvent.sequence)
            .where(FixEvent.fix_session_id == item.id)
            .order_by(FixEvent.sequence.desc())
            .limit(1)
        ) or 0
        session.add(
            FixEvent(
                fix_session_id=item.id,
                sequence=sequence + 1,
                event_type=event_type,
                payload_json=payload or {
                    "status": item.status,
                    "current_node": item.current_node,
                    "message": message,
                },
            )
        )


def _validation_payload(run: ValidationRun) -> dict[str, object]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": run.id,
        "fix_session_id": run.fix_session_id,
        "sequence": run.sequence,
        "command": run.command,
        "purpose": run.purpose,
        "required": run.required,
        "status": run.status,
        "return_code": run.return_code,
        "stdout_summary": run.stdout_summary,
        "stderr_summary": run.stderr_summary,
        "output_truncated": run.output_truncated,
        "error_code": run.error_code,
        "started_at": now,
        "finished_at": now,
        "duration_ms": run.duration_ms,
        "created_at": now,
    }


@pytest.fixture
def autofix_client(tmp_path: Path) -> Iterator[tuple[TestClient, Counter[str], str]]:
    app = create_app(_settings(tmp_path))
    with TestClient(app) as client:
        calls: Counter[str] = Counter()
        manager = FixManager(
            app.state.database.session_factory,
            FixWorkspaceManager(tmp_path / "fix-workspaces"),
            workflow_factory=lambda: FakeFixWorkflow(app.state.database.session_factory, calls),
        )
        previous = app.state.fix_manager
        app.state.fix_manager = manager
        with app.state.database.session_factory() as session:
            repository = Repository(
                owner="example",
                name="tiny",
                full_name="example/tiny",
                local_path=str(tmp_path),
                connection_status="ready",
                current_commit_sha=HEAD_SHA,
            )
            session.add(repository)
            session.flush()
            index = IndexVersion(
                repository_id=repository.id,
                commit_sha=HEAD_SHA,
                status="ready",
                file_count=1,
                symbol_count=1,
                changed_count=1,
                deleted_count=0,
                duration_ms=1,
                index_duration_ms=1,
                graph_duration_ms=0,
            )
            session.add(index)
            session.flush()
            repository.current_index_version = index.id
            pull_request = PullRequest(
                repository_id=repository.id,
                number=7,
                title="Fix normalization",
                state="open",
                url="https://github.com/example/tiny/pull/7",
                base_sha=BASE_SHA,
                head_sha=HEAD_SHA,
            )
            session.add(pull_request)
            session.flush()
            run = AgentRun(
                repository_id=repository.id,
                pull_request_id=pull_request.id,
                status="completed",
                head_sha=HEAD_SHA,
                index_version=index.id,
            )
            session.add(run)
            session.flush()
            finding = Finding(
                agent_run_id=run.id,
                severity="high",
                confidence=0.95,
                category="correctness",
                title="Value is doubled",
                message="The normalized value is multiplied twice.",
                file_path="service.py",
                line_start=1,
                line_end=1,
                commit_sha=HEAD_SHA,
                suggested_action="Return value directly.",
                verifier_status="verified",
            )
            session.add(finding)
            session.commit()
            finding_id = finding.id
        try:
            yield client, calls, finding_id
        finally:
            import asyncio

            asyncio.run(manager.shutdown())
            app.state.fix_manager = previous


def _create(client: TestClient, finding_id: str, key: str = "create-fix-0001") -> dict[str, object]:
    response = client.post(
        "/api/v1/fix-sessions",
        headers=_headers(key),
        json={"finding_id": finding_id, "permission_mode": "APPLY_IN_ISOLATED_WORKSPACE"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_sqlite_autofix_workspace_root_is_colocated_with_temporary_database(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    assert app.state.fix_manager.workspace_manager.root == (tmp_path / "autofix-workspaces").resolve()
    app.state.database.dispose()


def test_fix_api_requires_auth_and_create_is_idempotent_with_real_database(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, calls, finding_id = autofix_client
    assert client.post(
        "/api/v1/fix-sessions",
        json={"finding_id": finding_id, "permission_mode": "PROPOSE_ONLY"},
    ).status_code == 401

    created = _create(client, finding_id)
    repeated = _create(client, finding_id)
    assert repeated["id"] == created["id"]
    assert calls["initialize"] == 1
    assert created["status"] == "CREATED"
    assert created["allowed_actions"] == ["PLAN", "CANCEL"]
    assert "nonce" not in json.dumps(created).casefold()

    conflict = client.post(
        "/api/v1/fix-sessions",
        headers=_headers("create-fix-0001"),
        json={"finding_id": finding_id, "permission_mode": "PROPOSE_ONLY"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "fix_idempotency_conflict"


def test_plan_can_resume_after_explicit_eligibility_risk_acknowledgement(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, calls, finding_id = autofix_client
    created = _create(client, finding_id, "create-fix-risk-ack")
    session_id = str(created["id"])
    with client.app.state.database.session_factory() as session:
        item = session.get(FixSession, session_id)
        assert item is not None
        item.status = "ELIGIBLE"
        item.eligibility_status = "NEEDS_CONFIRMATION"
        item.eligibility_reasons_json = ["Finding requires explicit confirmation"]
        item.eligibility_warnings_json = ["Low-confidence semantic conclusion"]
        session.commit()

    response = client.post(
        f"/api/v1/fix-sessions/{session_id}/plan",
        headers=_headers("plan-fix-risk-ack"),
        json={"expected_lock_version": 0, "force_eligibility": True},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "PLAN_READY"
    assert calls["plan"] == 1
    assert calls["plan_forced"] == 1


def test_fix_lifecycle_uses_cas_hash_bound_confirmation_and_authoritative_exports(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, calls, finding_id = autofix_client
    created = _create(client, finding_id, "create-fix-lifecycle")
    session_id = str(created["id"])

    planned = client.post(
        f"/api/v1/fix-sessions/{session_id}/plan",
        headers=_headers("plan-fix-0001"),
        json={"expected_lock_version": 0, "force_eligibility": False},
    )
    assert planned.status_code == 200, planned.text
    assert planned.json()["lock_version"] == 1
    assert planned.json()["status"] == "PLAN_READY"
    assert calls["plan"] == 1

    repeated = client.post(
        f"/api/v1/fix-sessions/{session_id}/plan",
        headers=_headers("plan-fix-0001"),
        json={"expected_lock_version": 0, "force_eligibility": False},
    )
    assert repeated.status_code == 200
    assert repeated.json()["lock_version"] == 1
    assert calls["plan"] == 1

    stale = client.post(
        f"/api/v1/fix-sessions/{session_id}/plan",
        headers=_headers("plan-fix-stale"),
        json={"expected_lock_version": 0, "force_eligibility": False},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "fix_lock_conflict"

    generated = client.post(
        f"/api/v1/fix-sessions/{session_id}/generate",
        headers=_headers("generate-fix-0001"),
        json={"expected_lock_version": 1},
    )
    assert generated.status_code == 200, generated.text
    body = generated.json()
    assert body["proposal"]["patch_hash"] == PATCH_HASH
    assert body["patch_inspection"]["changed_files"] == ["service.py"]
    assert body["allowed_actions"] == ["CONFIRM", "EXPORT_PATCH", "CANCEL"]

    wrong_hash = client.post(
        f"/api/v1/fix-sessions/{session_id}/confirm",
        headers=_headers("confirm-fix-wrong"),
        json={"expected_lock_version": 2, "patch_hash": "0" * 64},
    )
    assert wrong_hash.status_code == 409
    assert wrong_hash.json()["error"]["code"] == "fix_patch_hash_mismatch"

    confirmed = client.post(
        f"/api/v1/fix-sessions/{session_id}/confirm",
        headers=_headers("confirm-fix-0001"),
        json={"expected_lock_version": 2, "patch_hash": PATCH_HASH},
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_body = confirmed.json()
    assert confirmed_body["lock_version"] == 3
    assert confirmed_body["confirmation"]["patch_hash"] == PATCH_HASH
    assert confirmed_body["allowed_actions"] == ["EXPORT_PATCH", "CANCEL", "APPLY"]
    assert "nonce" not in confirmed.text.casefold()

    with client.app.state.database.session_factory() as session:
        confirmation = session.scalar(
            select(FixConfirmation).where(FixConfirmation.fix_session_id == session_id)
        )
        assert confirmation is not None
        assert len(confirmation.nonce_hash) == 64
        assert confirmation.consumed_at is None

    applied = client.post(
        f"/api/v1/fix-sessions/{session_id}/apply",
        headers=_headers("apply-fix-0001"),
        json={"expected_lock_version": 3, "patch_hash": PATCH_HASH},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "PATCH_APPLIED"
    with client.app.state.database.session_factory() as session:
        confirmation = session.scalar(
            select(FixConfirmation).where(FixConfirmation.fix_session_id == session_id)
        )
        assert confirmation is not None and confirmation.consumed_at is not None

    patch_json = client.get(
        f"/api/v1/fix-sessions/{session_id}/patch?path=service.py",
        headers=_headers(),
    )
    assert patch_json.status_code == 200
    assert patch_json.json()["unified_diff"] == PATCH
    patch_download = client.get(
        f"/api/v1/fix-sessions/{session_id}/patch?download=true",
        headers=_headers(),
    )
    assert patch_download.status_code == 200
    assert patch_download.content.decode() == PATCH
    assert patch_download.headers["x-tracegate-patch-hash"] == PATCH_HASH
    assert "attachment" in patch_download.headers["content-disposition"]

    validated = client.post(
        f"/api/v1/fix-sessions/{session_id}/validate",
        headers=_headers("validate-fix-0001"),
        json={"expected_lock_version": 4},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["validation_runs"][0]["status"] == "PASSED"

    completed = client.post(
        f"/api/v1/fix-sessions/{session_id}/re-review",
        headers=_headers("rereview-fix-0001"),
        json={"expected_lock_version": 5},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["result"]["resolution"] == "RESOLVED"
    report = client.get(f"/api/v1/fix-sessions/{session_id}/report", headers=_headers())
    assert report.status_code == 200
    assert report.json()["report"]["finding_resolution"] == "RESOLVED"
    report_download = client.get(
        f"/api/v1/fix-sessions/{session_id}/report?download=true", headers=_headers()
    )
    assert report_download.status_code == 200
    assert "attachment" in report_download.headers["content-disposition"]
    exported = report_download.json()
    assert exported["artifacts"]["final_diff"] == PATCH
    assert exported["artifacts"]["facts"]["source_workspace_mutated"] is False

    listing = client.get(
        f"/api/v1/fix-sessions?finding_id={finding_id}&limit=20&offset=0",
        headers=_headers(),
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["status"] == "COMPLETED"


def test_fix_sse_envelope_resume_and_workspace_delete_are_controlled(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, _calls, finding_id = autofix_client
    created = _create(client, finding_id, "create-fix-events")
    session_id = str(created["id"])
    cancelled = client.post(
        f"/api/v1/fix-sessions/{session_id}/cancel",
        headers=_headers("cancel-fix-events"),
        json={"expected_lock_version": 0},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    with client.app.state.database.session_factory() as session:
        events = list(
            session.scalars(
                select(FixEvent)
                .where(FixEvent.fix_session_id == session_id)
                .order_by(FixEvent.sequence)
            )
        )
        assert len(events) == 2
        events[0].event_type = "fix_session.created"
        events[1].event_type = "fix_step.started"
        events[1].payload_json = {"node": "PLAN_FIX", "message": "PLAN_FIX started."}
        session.add(
            FixEvent(
                fix_session_id=session_id,
                sequence=3,
                event_type="terminal",
                payload_json={"status": "CANCELLED", "error_code": None, "error_message": None},
            )
        )
        session.commit()
        step_id = events[1].id
        terminal_id = session.scalar(
            select(FixEvent.id).where(
                FixEvent.fix_session_id == session_id, FixEvent.sequence == 3
            )
        )
        assert terminal_id is not None

    complete_stream = client.get(
        f"/api/v1/fix-sessions/{session_id}/events",
        headers=_headers(),
    )
    assert "event: session" in complete_stream.text
    assert "event: workflow_step" in complete_stream.text

    response = client.get(
        f"/api/v1/fix-sessions/{session_id}/events",
        headers={**_headers(), "Last-Event-ID": step_id},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert f"id: {terminal_id}" in response.text
    assert "event: terminal" in response.text
    data_line = next(line for line in response.text.splitlines() if line.startswith("data: "))
    envelope = json.loads(data_line.removeprefix("data: "))
    assert envelope["created_at"].endswith(("+00:00", "Z"))
    assert envelope == {
        "event_id": terminal_id,
        "sequence": 3,
        "fix_session_id": session_id,
        "created_at": envelope["created_at"],
        "type": "terminal",
        "data": {"status": "CANCELLED", "error_code": None, "error_message": None},
    }

    invalid_cursor = client.get(
        f"/api/v1/fix-sessions/{session_id}/events",
        headers={**_headers(), "Last-Event-ID": "ffffffff-ffff-4fff-8fff-ffffffffffff"},
    )
    assert invalid_cursor.status_code == 409
    assert invalid_cursor.json()["error"]["code"] == "fix_event_cursor_invalid"

    deleted = client.request(
        "DELETE",
        f"/api/v1/fix-sessions/{session_id}/workspace",
        headers=_headers("delete-workspace-events"),
        json={"expected_lock_version": 1},
    )
    assert deleted.status_code == 204
    detail = client.get(f"/api/v1/fix-sessions/{session_id}", headers=_headers()).json()
    assert detail["cleanup_status"] == "DELETED"
    assert detail["workspace_path"] is None


def test_fix_workspace_diagnostics_are_authenticated_and_bounded_to_managed_root(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, _calls, finding_id = autofix_client
    created = _create(client, finding_id, "create-fix-diagnostics")
    session_id = str(created["id"])
    with client.app.state.database.session_factory() as session:
        item = session.get(FixSession, session_id)
        assert item is not None
        worktree = (
            client.app.state.fix_manager.workspace_manager.root
            / item.repository_id
            / item.id
            / "worktree"
        )
        worktree.mkdir(parents=True)
        item.workspace_path = str(worktree)
        item.cleanup_status = "ACTIVE"
        session.commit()

    assert client.get("/api/v1/fix-workspaces").status_code == 401
    response = client.get("/api/v1/fix-workspaces", headers=_headers())
    assert response.status_code == 200
    assert response.json()["total"] == 1
    entry = response.json()["items"][0]
    assert entry["fix_session_id"] == session_id
    assert entry["cleanup_status"] == "ACTIVE"
    assert Path(entry["path"]).is_relative_to(
        client.app.state.fix_manager.workspace_manager.root
    )


def test_fix_workspace_diagnostics_can_safely_cleanup_an_orphan(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, _calls, _finding_id = autofix_client
    workspace_root = client.app.state.fix_manager.workspace_manager.root
    session_id = "orphan-session-0001"
    worktree = workspace_root / "orphan-repository" / session_id / "worktree"
    worktree.mkdir(parents=True)
    (worktree / "residual.txt").write_text("residual", encoding="utf-8")

    listed = client.get("/api/v1/fix-workspaces", headers=_headers()).json()
    assert listed["total"] == 1
    assert listed["items"][0]["fix_session_id"] == session_id
    assert listed["items"][0]["cleanup_status"] == "ORPHANED"

    assert client.delete(f"/api/v1/fix-workspaces/{session_id}").status_code == 401
    headers = _headers("cleanup-orphan-workspace-0001")
    response = client.delete(f"/api/v1/fix-workspaces/{session_id}", headers=headers)
    assert response.status_code == 204, response.text
    assert not worktree.exists()
    assert client.get("/api/v1/fix-workspaces", headers=_headers()).json()["total"] == 0

    # A transport retry with the same idempotency key remains successful while
    # a new request accurately reports that the workspace is already gone.
    assert client.delete(f"/api/v1/fix-workspaces/{session_id}", headers=headers).status_code == 204
    missing = client.delete(
        f"/api/v1/fix-workspaces/{session_id}",
        headers=_headers("cleanup-orphan-workspace-0002"),
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "fix_workspace_not_found"


def test_confirmation_marks_session_stale_when_pull_request_head_changed(
    autofix_client: tuple[TestClient, Counter[str], str],
) -> None:
    client, _calls, finding_id = autofix_client
    created = _create(client, finding_id, "create-fix-stale-head")
    session_id = str(created["id"])
    planned = client.post(
        f"/api/v1/fix-sessions/{session_id}/plan",
        headers=_headers("plan-fix-stale-head"),
        json={"expected_lock_version": 0, "force_eligibility": False},
    ).json()
    generated = client.post(
        f"/api/v1/fix-sessions/{session_id}/generate",
        headers=_headers("generate-fix-stale-head"),
        json={"expected_lock_version": planned["lock_version"]},
    ).json()
    with client.app.state.database.session_factory() as session:
        item = session.get(FixSession, session_id)
        assert item is not None
        pull_request = session.get(PullRequest, item.pull_request_id)
        assert pull_request is not None
        pull_request.head_sha = "c" * 40
        session.commit()

    response = client.post(
        f"/api/v1/fix-sessions/{session_id}/confirm",
        headers=_headers("confirm-fix-stale-head"),
        json={"expected_lock_version": generated["lock_version"], "patch_hash": PATCH_HASH},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "fix_head_stale"
    detail = client.get(f"/api/v1/fix-sessions/{session_id}", headers=_headers()).json()
    assert detail["status"] == "STALE"
    assert detail["proposal"]["stale_at"] is not None
