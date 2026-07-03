from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tracegate.pr_advisor.cli import validate_live_smoke_payload
from tracegate.pr_advisor.deepseek_client import DeepSeekClientError, DeepSeekResponse, load_deepseek_settings_from_env
from tracegate.pr_advisor.evidence_packet import EvidenceItem, EvidencePacket, sanitize_json_value
from tracegate.pr_advisor.llm_judge import SemanticJudgeError, judge_with_deepseek
from tracegate.pr_advisor.render import advisory_payload
from tracegate.pr_advisor.verifier import verify_judgment


@dataclass
class FakeSettings:
    model: str = "deepseek-v4-flash"


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.settings = FakeSettings()
        self.call_count = 0

    def chat_json(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 2000) -> DeepSeekResponse:
        response = self.responses[min(self.call_count, len(self.responses) - 1)]
        self.call_count += 1
        return DeepSeekResponse(
            model=self.settings.model,
            content=response,
            raw_response={"choices": [{"message": {"content": response}}]},
            duration_seconds=0.01,
        )


def packet_with_evidence(
    *,
    risk_areas: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    items: list[EvidenceItem] | None = None,
) -> EvidencePacket:
    evidence = items or [
        EvidenceItem(
            evidence_id="e1",
            source_type="pr_body",
            url="https://github.com/example/repo/pull/1",
            timestamp="2026-01-01T00:00:00Z",
            snippet="Change auth behavior.",
            relevance=0.8,
        ),
        EvidenceItem(
            evidence_id="e2",
            source_type="review_comment",
            url="https://github.com/example/repo/pull/1#discussion_r2",
            timestamp="2026-01-02T00:00:00Z",
            snippet="Concern resolved; tests verify no regression.",
            relevance=0.8,
        ),
    ]
    return EvidencePacket(
        repo="example/repo",
        pr_number=1,
        pr_url="https://github.com/example/repo/pull/1",
        title="Change auth behavior",
        changed_files=["src/auth.py"],
        risk_areas=risk_areas if risk_areas is not None else ["auth"],
        candidate_claims=[],
        evidence_items=evidence,
        missing_evidence=missing_evidence if missing_evidence is not None else ["Need explicit auth compatibility evidence."],
        retrieval_limits=[],
    )


def base_judgment(status: str = "conflicting", decision: str = "detect_conflict") -> dict[str, Any]:
    return {
        "evidence_status": status,
        "expected_decision": decision,
        "confidence": 0.8,
        "claim_under_review": "Auth compatibility claim.",
        "rationale": "Evidence appears risky.",
        "evidence_used": ["e1", "e2"],
        "missing_evidence": [],
        "risk_level": "high",
        "verification_plan": ["Inspect auth tests."],
        "should_block": False,
    }


def test_deepseek_key_missing_fails_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("TRACEGATE_LLM_API_KEY", raising=False)
    with pytest.raises(DeepSeekClientError, match="no fallback"):
        load_deepseek_settings_from_env()


def test_invalid_llm_json_retries_once_then_fails() -> None:
    packet = packet_with_evidence()
    client = FakeClient(["not-json", "{still-not-json"])
    with pytest.raises(SemanticJudgeError, match="one retry"):
        judge_with_deepseek(packet, provider="deepseek", no_mock=True, no_fallback=True, client=client)
    assert client.call_count == 2


def test_invalid_llm_json_can_recover_on_retry() -> None:
    packet = packet_with_evidence()
    valid = json.dumps(base_judgment(status="unknown", decision="verify_first"))
    client = FakeClient(["not-json", valid])
    result = judge_with_deepseek(packet, provider="deepseek", no_mock=True, no_fallback=True, client=client)
    assert result.semantic_api_called is True
    assert result.attempts == 2
    assert result.judgment["evidence_status"] == "unknown"


def test_resolved_concern_is_not_conflicting() -> None:
    verified = verify_judgment(packet_with_evidence(), base_judgment())
    assert verified["evidence_status"] != "conflicting"
    assert any("resolved concern" in note for note in verified["verifier_notes"])


def test_resolved_concern_downgrades_active() -> None:
    verified = verify_judgment(
        packet_with_evidence(),
        base_judgment(status="active", decision="preserve"),
    )
    assert verified["evidence_status"] == "unknown"
    assert verified["expected_decision"] == "verify_first"
    assert any("no-regression evidence is mitigation" in note for note in verified["verifier_notes"])


def test_high_risk_active_requires_cited_review_evidence() -> None:
    packet = packet_with_evidence(
        items=[
            EvidenceItem("e1", "pr_body", url="https://github.com/example/repo/pull/1", snippet="Auth fix"),
            EvidenceItem("e2", "file", url="https://github.com/example/repo/blob/main/auth.py", snippet="Auth diff"),
        ]
    )
    verified = verify_judgment(packet, base_judgment(status="active", decision="preserve"))
    assert verified["evidence_status"] == "unknown"
    assert any("lacks cited review" in note for note in verified["verifier_notes"])


def test_same_pr_url_cannot_satisfy_conflicting_evidence_count() -> None:
    packet = packet_with_evidence(
        items=[
            EvidenceItem("e1", "pr_body", url="https://github.com/example/repo/pull/1", snippet="Concern A"),
            EvidenceItem("e2", "comment", url="https://github.com/example/repo/pull/1", snippet="Concern B"),
        ]
    )
    verified = verify_judgment(packet, base_judgment())
    assert verified["evidence_status"] != "conflicting"
    assert any("distinct concrete sources" in note for note in verified["verifier_notes"])


def test_conflicting_requires_two_distinct_evidence_urls() -> None:
    judgment = base_judgment()
    judgment["evidence_used"] = ["e1"]
    verified = verify_judgment(packet_with_evidence(), judgment)
    assert verified["evidence_status"] != "conflicting"
    assert any("fewer than two evidence items" in note for note in verified["verifier_notes"])


def test_stale_requires_older_newer_time_ordering() -> None:
    packet = packet_with_evidence(
        items=[
            EvidenceItem("e1", "issue", url="https://github.com/example/repo/issues/1", snippet="Old claim"),
            EvidenceItem("e2", "comment", url="https://github.com/example/repo/issues/2", snippet="New evidence"),
        ]
    )
    judgment = base_judgment(status="stale", decision="verify_first")
    verified = verify_judgment(packet, judgment)
    assert verified["evidence_status"] == "needs_more_evidence"
    assert any("timestamp ordering" in note for note in verified["verifier_notes"])


def test_unknown_requires_risk_area_and_missing_evidence() -> None:
    judgment = base_judgment(status="unknown", decision="verify_first")
    verified = verify_judgment(packet_with_evidence(risk_areas=[], missing_evidence=[]), judgment)
    assert verified["evidence_status"] == "no_relevant_claim"

    verified_missing = verify_judgment(
        packet_with_evidence(risk_areas=["auth"], missing_evidence=[]),
        judgment,
    )
    assert verified_missing["evidence_status"] == "needs_more_evidence"


def test_fork_pr_workflow_does_not_access_llm_secret() -> None:
    workflow = Path(".github/workflows/tracegate-semantic-advisory.yml").read_text(encoding="utf-8")
    assert "semantic advisor skipped for fork PR because secrets are unavailable" in workflow
    assert "pull_request_target" not in workflow
    assert "head.repo.full_name != github.event.pull_request.base.repo.full_name" in workflow


def test_live_smoke_payload_requires_real_deepseek_call() -> None:
    payload = advisory_payload(
        packet=packet_with_evidence(),
        judgment=base_judgment(status="unknown", decision="verify_first"),
        raw_llm_json={},
        provider="deepseek",
        model="deepseek-v4-flash",
        semantic_api_called=False,
        attempts=0,
    )
    errors = validate_live_smoke_payload("psf/requests#7545", payload)
    assert any("real DeepSeek API was not called" in error for error in errors)


def test_pytest_live_smoke_case_rejects_active_status() -> None:
    payload = advisory_payload(
        packet=packet_with_evidence(),
        judgment=base_judgment(status="active", decision="preserve"),
        raw_llm_json={},
        provider="deepseek",
        model="deepseek-v4-flash",
        semantic_api_called=True,
        attempts=1,
    )
    errors = validate_live_smoke_payload("pytest-dev/pytest#14662", payload)
    assert any("expected no_relevant_claim" in error for error in errors)


def test_advisory_json_contains_evidence_urls_and_verifier_notes() -> None:
    judgment = verify_judgment(packet_with_evidence(), base_judgment())
    payload = advisory_payload(
        packet=packet_with_evidence(),
        judgment=judgment,
        raw_llm_json=base_judgment(),
        provider="deepseek",
        model="deepseek-v4-flash",
        semantic_api_called=True,
        attempts=1,
    )
    assert payload["evidence_used"][0]["url"].startswith("https://github.com/")
    assert "verifier_notes" in payload["final"]


def test_raw_llm_json_sanitization_redacts_secret_like_values() -> None:
    fake_secret = "token=" + "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
    sanitized = sanitize_json_value({"rationale": fake_secret})
    assert sanitized["rationale"] == "<redacted-secret>"
