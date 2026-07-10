from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import (
    AgentRun,
    AgentStep,
    AppSettings,
    EvidenceRecord,
    Finding,
    OnboardingState,
    PullRequest,
    Repository,
    ToolCallRecord,
)


def git(workspace: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(workspace), *arguments], text=True).strip()


def prepare_workspace(workspace: Path) -> tuple[str, str]:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    git(workspace, "config", "user.email", "tracegate-e2e@example.invalid")
    git(workspace, "config", "user.name", "TraceGate E2E")
    (workspace / "service.py").write_text(
        "def calculate_total(value: int) -> int:\n    return value\n",
        encoding="utf-8",
    )
    git(workspace, "add", ".")
    git(workspace, "commit", "-qm", "base")
    base_sha = git(workspace, "rev-parse", "HEAD")
    (workspace / "service.py").write_text(
        "def calculate_total(value: int) -> int:\n    return value * 2\n",
        encoding="utf-8",
    )
    (workspace / "test_service.py").write_text(
        "from service import calculate_total\n\ndef test_total():\n    assert calculate_total(2) == 4\n",
        encoding="utf-8",
    )
    git(workspace, "add", ".")
    git(workspace, "commit", "-qm", "head")
    return base_sha, git(workspace, "rev-parse", "HEAD")


def seed(database_path: Path, workspace: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.unlink(missing_ok=True)
    base_sha, head_sha = prepare_workspace(workspace)
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    upgrade_database(database_url)
    database = StudioDatabase(database_url)
    now = datetime.now(timezone.utc)
    with database.session_factory() as session:
        settings = session.get(AppSettings, 1)
        onboarding = session.get(OnboardingState, 1)
        assert settings is not None and onboarding is not None
        settings.background_monitoring = False
        onboarding.completed = True
        onboarding.current_step = "complete"
        onboarding.completed_at = now
        repository = Repository(
            owner="tracegate-e2e",
            name="fixture",
            full_name="tracegate-e2e/fixture",
            clone_url="https://github.com/tracegate-e2e/fixture.git",
            local_path=str(workspace.resolve()),
            default_branch="main",
            monitoring_enabled=False,
            connection_status="ready",
            last_synced_at=now,
        )
        session.add(repository)
        session.commit()
        session.refresh(repository)
        version, _repository_map = persist_repository_index(session, repository)
        pull_request = PullRequest(
            repository_id=repository.id,
            number=17,
            title="Double the calculated total",
            state="open",
            url="https://github.com/tracegate-e2e/fixture/pull/17",
            author="tracegate-e2e",
            base_sha=base_sha,
            head_sha=head_sha,
            additions=5,
            deletions=1,
            changed_files=2,
            analysis_status="failed",
            updated_at_github=now,
        )
        session.add(pull_request)
        session.flush()
        run = AgentRun(
            repository_id=repository.id,
            pull_request_id=pull_request.id,
            status="failed",
            current_node="Verifier",
            head_sha=head_sha,
            index_version=version.id,
            workflow_version="tracegate-langgraph-v1",
            prompt_version="tracegate-pr-review-v1",
            model_profile="e2e-recorded-provider",
            input_tokens=120,
            output_tokens=30,
            latency_ms=420,
            error_code="verification_failed",
            error_message="Recorded E2E fixture: verification rejected an unsupported line claim.",
            started_at=now,
            finished_at=now,
        )
        session.add(run)
        session.flush()
        step = AgentStep(
            agent_run_id=run.id,
            sequence=1,
            node="Repository Retriever",
            status="completed",
            input_summary="service total change",
            output_summary="Read service.py at the indexed Head SHA.",
            started_at=now,
            finished_at=now,
            duration_ms=12,
        )
        session.add(step)
        session.flush()
        session.add(
            ToolCallRecord(
                agent_step_id=step.id,
                tool_name="read_file",
                permission="REPOSITORY_READ",
                arguments_summary='{"path":"service.py"}',
                output_summary="Read 2 lines.",
                status="completed",
                duration_ms=3,
            )
        )
        evidence_id = "e2e-" + hashlib.sha256(f"{head_sha}:service.py".encode()).hexdigest()[:24]
        session.add(
            EvidenceRecord(
                id=evidence_id,
                agent_run_id=run.id,
                source_type="file",
                source_uri=f"git:{head_sha}:service.py",
                file_path="service.py",
                commit_sha=head_sha,
                content_hash=hashlib.sha256((workspace / "service.py").read_bytes()).hexdigest(),
                payload_json={"start_line": 1, "end_line": 2, "fixture_scope": "playwright-only"},
            )
        )
        session.add(
            Finding(
                agent_run_id=run.id,
                severity="medium",
                confidence=0.82,
                category="behavior-change",
                title="Return value semantics changed",
                message="The indexed diff changes the returned value from identity to multiplication.",
                file_path="service.py",
                line_start=2,
                line_end=2,
                commit_sha=head_sha,
                symbol="calculate_total",
                evidence_ids_json=[evidence_id],
                suggested_action="Confirm every caller expects the doubled value.",
                verifier_status="verified",
                model_profile="e2e-recorded-provider",
            )
        )
        session.commit()
    database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    seed(arguments.database.resolve(), arguments.workspace.resolve())


if __name__ == "__main__":
    main()
