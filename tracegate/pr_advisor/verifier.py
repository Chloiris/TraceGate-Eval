from __future__ import annotations

from datetime import datetime
from typing import Any

from .evidence_packet import EvidenceItem, EvidencePacket, sanitize_text


RESOLVED_MARKERS = (
    "concern resolved",
    "concern addressed",
    "resolved the concern",
    "addressed the concern",
    "fixed the concern",
    "tests verify no regression",
    "tests verify no regressions",
    "tests verify no typing regressions",
    "test verifies no regression",
    "no regression",
    "no regressions",
    "verified no regression",
    "since that was a concern",
)
HIGH_RISK_REVIEW_AREAS = {
    "auth",
    "token",
    "security",
    "permissions",
    "database",
    "migration",
    "public API",
    "compatibility",
    "serialization",
    "payment",
    "refund",
    "deletion",
}


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _downgrade(
    judgment: dict[str, Any],
    *,
    status: str,
    decision: str,
    note: str,
    notes: list[str],
) -> None:
    judgment["evidence_status"] = status
    judgment["expected_decision"] = decision
    judgment["should_block"] = False
    notes.append(note)


def _used_items(packet: EvidencePacket, judgment: dict[str, Any], notes: list[str]) -> list[EvidenceItem]:
    by_id = packet.evidence_by_id()
    items: list[EvidenceItem] = []
    valid_ids: list[str] = []
    for evidence_id in judgment.get("evidence_used") or []:
        item = by_id.get(str(evidence_id))
        if item is None:
            notes.append(f"ignored unknown evidence id: {sanitize_text(evidence_id, max_chars=120)}")
            continue
        items.append(item)
        valid_ids.append(item.evidence_id)
    judgment["evidence_used"] = valid_ids
    return items


def _has_resolved_marker(judgment: dict[str, Any], items: list[EvidenceItem]) -> bool:
    text = " ".join(
        [
            str(judgment.get("claim_under_review") or ""),
            str(judgment.get("rationale") or ""),
            *(item.snippet for item in items),
        ]
    ).lower()
    return any(marker in text for marker in RESOLVED_MARKERS)


def _distinct_source_count(items: list[EvidenceItem]) -> int:
    return len({item.distinct_source_key for item in items})


def _fallback_status_for_packet(packet: EvidencePacket) -> tuple[str, str]:
    if packet.risk_areas:
        return "unknown", "verify_first"
    return "no_relevant_claim", "none"


def _has_cited_review_evidence(items: list[EvidenceItem]) -> bool:
    return any(item.source_type in {"review", "review_comment"} for item in items)


def _has_review_required_risk(packet: EvidencePacket) -> bool:
    return bool(set(packet.risk_areas) & HIGH_RISK_REVIEW_AREAS)


def _ensure_missing_evidence(verified: dict[str, Any], message: str) -> None:
    current = list(verified.get("missing_evidence") or [])
    if message not in current:
        current.append(message)
    verified["missing_evidence"] = current


def verify_judgment(packet: EvidencePacket, judgment: dict[str, Any]) -> dict[str, Any]:
    verified = dict(judgment)
    notes: list[str] = []
    items = _used_items(packet, verified, notes)
    status = verified.get("evidence_status")

    if status == "conflicting":
        if len(items) < 2:
            next_status, next_decision = _fallback_status_for_packet(packet)
            _downgrade(
                verified,
                status=next_status,
                decision=next_decision,
                note="conflicting downgraded: fewer than two evidence items were cited",
                notes=notes,
            )
        elif _distinct_source_count(items) < 2:
            next_status, next_decision = _fallback_status_for_packet(packet)
            _downgrade(
                verified,
                status=next_status,
                decision=next_decision,
                note="conflicting downgraded: evidence does not use two distinct concrete sources",
                notes=notes,
            )
        elif all(item.source_type == "pr_body" for item in items):
            next_status, next_decision = _fallback_status_for_packet(packet)
            _downgrade(
                verified,
                status=next_status,
                decision=next_decision,
                note="conflicting downgraded: PR body text alone cannot establish conflict",
                notes=notes,
            )
        elif _has_resolved_marker(verified, items):
            next_status, next_decision = _fallback_status_for_packet(packet)
            _downgrade(
                verified,
                status=next_status,
                decision=next_decision,
                note="conflicting downgraded: resolved concern or no-regression evidence is mitigation, not conflict",
                notes=notes,
            )

    if verified.get("evidence_status") in {"active", "stale"} and _has_resolved_marker(verified, items):
        next_status, next_decision = _fallback_status_for_packet(packet)
        _downgrade(
            verified,
            status=next_status,
            decision=next_decision,
            note=(
                f"{status} downgraded: resolved concern or no-regression evidence is mitigation, "
                "not active/stale historical proof"
            ),
            notes=notes,
        )
        _ensure_missing_evidence(
            verified,
            "Resolved-concern or no-regression text requires independent review evidence before preserve advice.",
        )

    if verified.get("evidence_status") == "active" and _has_review_required_risk(packet) and not _has_cited_review_evidence(items):
        _downgrade(
            verified,
            status="unknown",
            decision="verify_first",
            note="active downgraded: high-risk PR lacks cited review or review-comment evidence",
            notes=notes,
        )
        _ensure_missing_evidence(
            verified,
            "High-risk PR needs cited review or review-comment evidence before preserve advice.",
        )

    if verified.get("evidence_status") == "stale":
        timestamps = [_parse_timestamp(item.timestamp) for item in items]
        concrete = sorted(item for item in timestamps if item is not None)
        if len(concrete) < 2 or concrete[0] >= concrete[-1]:
            _downgrade(
                verified,
                status="needs_more_evidence",
                decision="verify_first",
                note="stale downgraded: missing older/newer timestamp ordering",
                notes=notes,
            )

    if verified.get("evidence_status") == "unknown":
        if not packet.risk_areas:
            _downgrade(
                verified,
                status="no_relevant_claim",
                decision="none",
                note="unknown downgraded: no risk area was detected in touched paths or PR evidence",
                notes=notes,
            )
        elif not verified.get("missing_evidence") and not packet.missing_evidence:
            _downgrade(
                verified,
                status="needs_more_evidence",
                decision="verify_first",
                note="unknown downgraded: missing-evidence rationale is absent",
                notes=notes,
            )
        elif not verified.get("missing_evidence"):
            verified["missing_evidence"] = list(packet.missing_evidence)
            notes.append("unknown completed with retrieval missing-evidence rationale")

    if verified.get("evidence_status") == "no_relevant_claim" and packet.risk_areas and packet.missing_evidence:
        _downgrade(
            verified,
            status="unknown",
            decision="verify_first",
            note="no_relevant_claim upgraded: high-risk touched area lacks enough public evidence",
            notes=notes,
        )
        if not verified.get("missing_evidence"):
            verified["missing_evidence"] = list(packet.missing_evidence)

    verified["should_block"] = False
    verified["verifier_notes"] = [sanitize_text(note, max_chars=500) for note in notes]
    return verified
