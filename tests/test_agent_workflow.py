from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from tracegate.agent import TraceGateAgentWorkflow
from tracegate.models import ModelResult
from tracegate.studio.database import StudioDatabase
from tracegate.studio.index_store import persist_repository_index
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import AgentRun, AgentStep, EvidenceRecord, Finding, PullRequest, Repository, ToolCallRecord
from tracegate.tools import create_read_only_registry


class RecordingModel:
    profile = "test-injected:recording-model"

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete_structured(self, *, system_prompt: str, user_prompt: str, output_schema):  # type: ignore[no-untyped-def]
        self.calls.append(output_schema.__name__)
        evidence_match = re.search(r"\[(studio-evidence:[^\]]+)\]", user_prompt)
        evidence_id = evidence_match.group(1) if evidence_match else ""
        payloads = {
            "PlanOutput": {
                "objective": "Review the indexed function",
                "retrieval_queries": ["indexed_function"],
                "focus_areas": ["security"],
            },
            "FindingsOutput": {
                "analysis_summary": "The evidence proves one review concern.",
                "findings": [
                    {
                        "severity": "medium",
                        "confidence": 0.8,
                        "category": "correctness",
                        "title": "Indexed function returns an unsafe sentinel",
                        "explanation": "The current line returns the sentinel directly.",
                        "path": "main.py",
                        "start_line": 2,
                        "end_line": 2,
                        "symbol": "indexed_function",
                        "evidence_ids": [evidence_id],
                        "suggested_action": "Validate the value before returning it.",
                    }
                ],
            },
            "RiskJudgmentOutput": {
                "evidence_status": "unknown",
                "expected_decision": "verify_first",
                "evidence_used": [evidence_id],
                "rationale": "Only repository evidence is available.",
                "missing_evidence": ["A focused test result is missing."],
                "should_block": False,
            },
            "ReportOutput": {
                "summary": "One evidence-bound concern requires review.",
                "recommended_review_order": ["main.py", "invented.py"],
            },
        }
        return ModelResult(payloads[output_schema.__name__], 10, 5, 3, 0, "test")


def _git(command: list[str], cwd: Path) -> None:
    subprocess.run(["git", *command], cwd=cwd, check=True, capture_output=True)


@pytest.mark.asyncio
async def test_langgraph_workflow_persists_steps_tools_evidence_and_verified_finding(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    _git(["init", "-q"], workspace)
    _git(["config", "user.email", "tracegate@example.invalid"], workspace)
    _git(["config", "user.name", "TraceGate Test"], workspace)
    (workspace / "main.py").write_text("def indexed_function():\n    return 0\n", encoding="utf-8")
    _git(["add", "."], workspace)
    _git(["commit", "-qm", "base fixture"], workspace)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace, check=True, capture_output=True, text=True
    ).stdout.strip()
    (workspace / "main.py").write_text("def indexed_function():\n    return -1\n", encoding="utf-8")
    _git(["add", "."], workspace)
    _git(["commit", "-qm", "agent fixture"], workspace)
    head_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace, check=True, capture_output=True, text=True
    ).stdout.strip()

    url = f"sqlite+pysqlite:///{(tmp_path / 'studio.db').as_posix()}"
    upgrade_database(url)
    database = StudioDatabase(url)
    model = RecordingModel()
    try:
        with database.session_factory() as session:
            repository = Repository(
                owner="acme",
                name="agent",
                full_name="acme/agent",
                local_path=str(workspace),
                connection_status="ready",
            )
            session.add(repository)
            session.commit()
            session.refresh(repository)
            version, _graph = persist_repository_index(session, repository)
            pull_request = PullRequest(
                repository_id=repository.id,
                number=1,
                title="Security parser change",
                state="open",
                url="https://github.com/acme/agent/pull/1",
                base_sha=base_sha,
                head_sha=head_sha,
            )
            session.add(pull_request)
            session.commit()
            session.refresh(pull_request)
            run = AgentRun(
                repository_id=repository.id,
                pull_request_id=pull_request.id,
                status="queued",
                head_sha=head_sha,
                index_version=version.id,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            run_id = run.id

        workflow = TraceGateAgentWorkflow(
            database.session_factory,
            model,
            create_read_only_registry(),
            context_scope="changed_files",
        )
        result = await workflow.run(run_id)

        assert result["report"]["recommended_review_order"] == ["main.py"]
        assert model.calls == ["PlanOutput", "FindingsOutput", "RiskJudgmentOutput", "ReportOutput"]
        with database.session_factory() as session:
            stored_run = session.get(AgentRun, run_id)
            assert stored_run is not None
            assert stored_run.status == "completed"
            assert stored_run.workflow_version == "tracegate-langgraph-v1"
            assert stored_run.input_tokens == 40
            assert stored_run.retrieval_hit_count >= 1
            assert stored_run.context_scope == "changed_files"
            assert session.scalar(select_count(AgentStep, AgentStep.agent_run_id == run_id)) == 7
            assert session.scalar(select_count(EvidenceRecord, EvidenceRecord.agent_run_id == run_id)) >= 1
            assert session.scalar(select_count(ToolCallRecord)) >= 1
            finding = session.query(Finding).filter(Finding.agent_run_id == run_id).one()
            assert finding.commit_sha == head_sha
            assert finding.verifier_status == "verified"
            assert finding.evidence_ids_json
            stored_pr = session.get(PullRequest, stored_run.pull_request_id)
            assert stored_pr is not None
            assert stored_pr.risk_level == "medium"
            assert stored_pr.risk_score == 40.0
            assert stored_pr.conclusion_summary == "One evidence-bound concern requires review."
            assert stored_pr.impact_paths_json == ["main.py"]
            assert stored_pr.recommended_review_order_json == ["main.py"]
    finally:
        database.dispose()


def select_count(model, *filters):  # type: ignore[no-untyped-def]
    from sqlalchemy import func, select

    return select(func.count()).select_from(model).where(*filters)
