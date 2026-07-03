from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from .deepseek_client import DeepSeekClient, DeepSeekClientError, DeepSeekResponse
from .evidence_packet import EvidencePacket, sanitize_text


EVIDENCE_STATUSES = {
    "active",
    "stale",
    "unknown",
    "conflicting",
    "no_relevant_claim",
    "needs_more_evidence",
}
EXPECTED_DECISIONS = {"preserve", "optimize", "verify_first", "detect_conflict", "none"}
RISK_LEVELS = {"low", "medium", "high", "critical"}


class SemanticJudgeError(RuntimeError):
    """Raised when the semantic judge cannot produce a valid real result."""


class ChatJsonClient(Protocol):
    settings: Any
    call_count: int

    def chat_json(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 2000) -> DeepSeekResponse:
        ...


@dataclass(frozen=True)
class SemanticJudgeResult:
    judgment: dict[str, Any]
    raw_llm_json: dict[str, Any]
    api_response_model: str
    semantic_api_called: bool
    provider: str
    model: str
    attempts: int


def _packet_for_prompt(packet: EvidencePacket) -> dict[str, Any]:
    data = packet.to_dict()
    data["evidence_items"] = data["evidence_items"][:80]
    return data


def build_semantic_prompt(packet: EvidencePacket) -> list[dict[str, str]]:
    packet_json = json.dumps(_packet_for_prompt(packet), ensure_ascii=False, indent=2)
    system = (
        "You are TraceGate Semantic PR Advisor. Return only strict JSON. "
        "Do not include Markdown, prose, secrets, API keys, or text outside JSON. "
        "Use evidence IDs from the EvidencePacket. Do not make keyword-only judgments."
    )
    user = f"""
Analyze this real GitHub Pull Request EvidencePacket.

Required output schema:
{{
  "evidence_status": "active | stale | unknown | conflicting | no_relevant_claim | needs_more_evidence",
  "expected_decision": "preserve | optimize | verify_first | detect_conflict | none",
  "confidence": 0.0,
  "claim_under_review": "...",
  "rationale": "...",
  "evidence_used": ["evidence_id"],
  "missing_evidence": [],
  "risk_level": "low | medium | high | critical",
  "verification_plan": [],
  "should_block": false
}}

Decision rules:
- active: current evidence supports a historical claim; expected_decision=preserve.
- stale: older claim plus newer superseding evidence with timestamp ordering; expected_decision=optimize or verify_first.
- unknown: high-risk PR area but public evidence is insufficient; expected_decision=verify_first.
- conflicting: at least two real conflicting evidence items; expected_decision=detect_conflict.
- no_relevant_claim: no historical-constraint risk was found.
- needs_more_evidence: retrieval failed or evidence is insufficient to judge.
- Do not treat the PR's own proposed diff as enough historical evidence for active.
- High-risk auth, credential, security, public API, compatibility, serialization, payment, deletion, or migration changes without review/review-comment evidence should usually be unknown + verify_first.
- Do not call a resolved concern, fixed concern, or tests-verify-no-regression comment conflicting.
- Resolved concern or tests-verify-no-regression text is mitigation, not active/stale/conflicting historical proof.
- Courtesy review requests, waiting for review, or concern addressed/resolved are not conflict evidence.
- The same PR URL cannot count as two independent conflicting evidence sources.
- Every semantic judgment must cite evidence_used IDs from the packet.
- Default should_block=false because TraceGate advisory is warning-only.

EvidencePacket:
```json
{packet_json}
```
""".strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise SemanticJudgeError("DeepSeek returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise SemanticJudgeError("DeepSeek JSON response must be an object")
    return data


def _validate_and_sanitize_judgment(data: dict[str, Any]) -> dict[str, Any]:
    status = str(data.get("evidence_status") or "")
    decision = str(data.get("expected_decision") or "")
    risk = str(data.get("risk_level") or "medium")
    if status not in EVIDENCE_STATUSES:
        raise SemanticJudgeError(f"invalid evidence_status: {status}")
    if decision not in EXPECTED_DECISIONS:
        raise SemanticJudgeError(f"invalid expected_decision: {decision}")
    if risk not in RISK_LEVELS:
        raise SemanticJudgeError(f"invalid risk_level: {risk}")
    evidence_used = data.get("evidence_used") or []
    missing = data.get("missing_evidence") or []
    plan = data.get("verification_plan") or []
    if not isinstance(evidence_used, list) or not isinstance(missing, list) or not isinstance(plan, list):
        raise SemanticJudgeError("evidence_used, missing_evidence, and verification_plan must be arrays")
    return {
        "evidence_status": status,
        "expected_decision": decision,
        "confidence": max(0.0, min(1.0, float(data.get("confidence") or 0.0))),
        "claim_under_review": sanitize_text(data.get("claim_under_review"), max_chars=800),
        "rationale": sanitize_text(data.get("rationale"), max_chars=1200),
        "evidence_used": [sanitize_text(item, max_chars=120) for item in evidence_used],
        "missing_evidence": [sanitize_text(item, max_chars=500) for item in missing],
        "risk_level": risk,
        "verification_plan": [sanitize_text(item, max_chars=500) for item in plan],
        "should_block": bool(data.get("should_block") is True),
    }


def judge_with_deepseek(
    packet: EvidencePacket,
    *,
    provider: str,
    no_mock: bool,
    no_fallback: bool,
    client: ChatJsonClient | None = None,
) -> SemanticJudgeResult:
    if provider != "deepseek":
        raise SemanticJudgeError("semantic mode currently requires --provider deepseek")
    if not no_mock:
        raise SemanticJudgeError("semantic mode requires --no-mock")
    if not no_fallback:
        raise SemanticJudgeError("semantic mode requires --no-fallback")
    try:
        active_client: ChatJsonClient = client or DeepSeekClient.from_env()
    except DeepSeekClientError as exc:
        raise SemanticJudgeError(str(exc)) from exc
    messages = build_semantic_prompt(packet)
    last_error: SemanticJudgeError | None = None
    raw_json: dict[str, Any] = {}
    response_model = getattr(active_client.settings, "model", "deepseek-v4-flash")
    for attempt in range(1, 3):
        response = active_client.chat_json(messages, temperature=0.0, max_tokens=2000)
        response_model = response.model
        try:
            raw_json = _extract_json_object(response.content)
            judgment = _validate_and_sanitize_judgment(raw_json)
            return SemanticJudgeResult(
                judgment=judgment,
                raw_llm_json=raw_json,
                api_response_model=response_model,
                semantic_api_called=True,
                provider="deepseek",
                model=response_model,
                attempts=attempt,
            )
        except SemanticJudgeError as exc:
            last_error = exc
            messages = [
                *messages,
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": (
                        "Your previous response was invalid. Return only a single strict JSON object matching the schema. "
                        "No Markdown fences and no prose."
                    ),
                },
            ]
    raise SemanticJudgeError(f"DeepSeek did not return valid JSON after one retry: {last_error}")
