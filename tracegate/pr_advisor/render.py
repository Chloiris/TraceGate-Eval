from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence_packet import EvidencePacket, sanitize_json_value, sanitize_text


def _evidence_used(packet: EvidencePacket, judgment: dict[str, Any]) -> list[dict[str, str]]:
    by_id = packet.evidence_by_id()
    rows = []
    for evidence_id in judgment.get("evidence_used") or []:
        item = by_id.get(str(evidence_id))
        if not item:
            continue
        rows.append(
            {
                "evidence_id": item.evidence_id,
                "source_type": item.source_type,
                "url": item.url,
                "file_path": item.file_path,
                "commit_sha": item.commit_sha,
            }
        )
    return rows


def advisory_payload(
    *,
    packet: EvidencePacket,
    judgment: dict[str, Any],
    raw_llm_json: dict[str, Any],
    provider: str,
    model: str,
    semantic_api_called: bool,
    attempts: int,
) -> dict[str, Any]:
    return {
        "repo": packet.repo,
        "pr_number": packet.pr_number,
        "pr_url": packet.pr_url,
        "provider": provider,
        "model": model,
        "semantic_api_called": semantic_api_called,
        "attempts": attempts,
        "used_real_pr": True,
        "used_real_llm": semantic_api_called,
        "used_mock": False,
        "used_fallback": False,
        "warning_only": True,
        "evidence_packet": packet.to_dict(),
        "evidence_packet_size": len(packet.evidence_items),
        "raw_llm_json": sanitize_json_value(raw_llm_json),
        "final": judgment,
        "evidence_used": _evidence_used(packet, judgment),
        "limitations": [
            "TraceGate semantic PR advisor is warning-only and does not replace human code review.",
            "Evidence retrieval is bounded by GitHub API availability and configured retrieval limits.",
            "The workflow never executes untrusted Pull Request code.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    final = payload["final"]
    lines = [
        "# TraceGate Semantic PR Advisory",
        "",
        "TraceGate is running in warning-only semantic advisory mode.",
        "",
        "## Summary",
        "",
        f"- repo: `{payload['repo']}`",
        f"- pr_number: `{payload['pr_number']}`",
        f"- pr_url: {payload['pr_url']}",
        f"- evidence_status: `{final.get('evidence_status')}`",
        f"- expected_decision: `{final.get('expected_decision')}`",
        f"- risk_level: `{final.get('risk_level')}`",
        f"- should_block: `{final.get('should_block')}`",
        f"- provider: `{payload['provider']}`",
        f"- model: `{payload['model']}`",
        f"- semantic_api_called: `{payload['semantic_api_called']}`",
        f"- used_real_pr: `{payload['used_real_pr']}`",
        f"- used_real_llm: `{payload['used_real_llm']}`",
        f"- used_mock: `{payload['used_mock']}`",
        f"- used_fallback: `{payload['used_fallback']}`",
        "",
        "## Claim Under Review",
        "",
        sanitize_text(final.get("claim_under_review"), max_chars=1200) or "None.",
        "",
        "## Rationale",
        "",
        sanitize_text(final.get("rationale"), max_chars=1600) or "None.",
        "",
        "## Evidence Used",
        "",
    ]
    evidence_used = payload.get("evidence_used") or []
    if evidence_used:
        for item in evidence_used:
            url = item.get("url") or item.get("file_path") or item.get("commit_sha") or "unknown source"
            lines.append(f"- `{item.get('evidence_id')}` `{item.get('source_type')}` {url}")
    else:
        lines.append("- No evidence IDs were cited by the final advisory.")

    lines.extend(["", "## Missing Evidence", ""])
    missing = final.get("missing_evidence") or []
    if missing:
        lines.extend(f"- {sanitize_text(item, max_chars=500)}" for item in missing)
    else:
        lines.append("- None reported.")

    lines.extend(["", "## Verification Plan", ""])
    plan = final.get("verification_plan") or []
    if plan:
        lines.extend(f"- {sanitize_text(item, max_chars=500)}" for item in plan)
    else:
        lines.append("- None reported.")

    lines.extend(["", "## Verifier Notes", ""])
    notes = final.get("verifier_notes") or []
    if notes:
        lines.extend(f"- {sanitize_text(item, max_chars=500)}" for item in notes)
    else:
        lines.append("- No verifier downgrades.")

    lines.extend(["", "## Retrieval Limits", ""])
    for item in payload["evidence_packet"].get("retrieval_limits", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Limitations", ""])
    for item in payload.get("limitations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_advisory(payload: dict[str, Any], markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
