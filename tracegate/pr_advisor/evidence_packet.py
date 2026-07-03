from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


BIDI_CONTROL_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069]")
LOCAL_PATH_RE = re.compile(r"/" + r"Users/[^\s)>\"]+")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
SECRET_PATTERNS = [
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[opsru]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,;]{8,}"
    ),
]

RISK_TERMS: dict[str, tuple[str, ...]] = {
    "auth": ("auth", "authentication", "authorization", "login", "oauth"),
    "token": ("token", "jwt", "bearer", "credential"),
    "security": ("security", "csrf", "xss", "cve", "vulnerability"),
    "permissions": ("permission", "acl", "rbac", "scope", "privilege"),
    "config": ("config", "setting", "environment", "env var"),
    "database": ("database", "db", "sql", "query", "schema"),
    "migration": ("migration", "migrate", "alembic", "schema change"),
    "public API": ("public api", "api", "endpoint", "route", "breaking change"),
    "compatibility": ("compat", "backward", "legacy", "regression"),
    "serialization": ("serializ", "json", "pickle", "marshal", "schema"),
    "payment": ("payment", "billing", "invoice", "charge"),
    "refund": ("refund",),
    "signature": ("signature", "signing", "signed"),
    "deletion": ("delete", "deletion", "remove", "drop"),
    "cache": ("cache", "memoiz", "redis"),
    "concurrency": ("concurrency", "race", "lock", "thread", "async"),
}


def stable_id(prefix: str, *parts: object) -> str:
    text = "\n".join(str(part) for part in parts if part is not None)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}:{digest}"


def sanitize_text(value: object, *, max_chars: int = 1400) -> str:
    text = "" if value is None else str(value)
    text = BIDI_CONTROL_RE.sub(lambda match: f"\\u{ord(match.group(0)):04X}", text)
    text = LOCAL_PATH_RE.sub("<redacted-local-path>", text)
    text = EMAIL_RE.sub("<redacted-email>", text)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<redacted-secret>", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 18].rstrip() + " ... <truncated>"
    return text


def sanitize_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {sanitize_text(key, max_chars=200): sanitize_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value, max_chars=2000)
    return value


def detect_risk_areas(*values: object) -> list[str]:
    haystack = " ".join(str(value or "") for value in values).lower()
    areas = []
    for area, terms in RISK_TERMS.items():
        if any(term in haystack for term in terms):
            areas.append(area)
    return areas


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_type: str
    url: str = ""
    file_path: str = ""
    commit_sha: str = ""
    timestamp: str = ""
    snippet: str = ""
    supports_or_contradicts: str = "unclear"
    relevance: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "url": self.url,
            "file_path": self.file_path,
            "commit_sha": self.commit_sha,
            "timestamp": self.timestamp,
            "snippet": sanitize_text(self.snippet),
            "supports_or_contradicts": self.supports_or_contradicts,
            "relevance": round(float(self.relevance), 3),
        }

    @property
    def distinct_source_key(self) -> str:
        if self.url:
            return self.url
        if self.commit_sha:
            return f"commit:{self.commit_sha}:{self.file_path}"
        if self.file_path:
            return f"file:{self.file_path}"
        return self.evidence_id


@dataclass(frozen=True)
class EvidencePacket:
    repo: str
    pr_number: int
    pr_url: str
    title: str
    changed_files: list[str]
    risk_areas: list[str]
    candidate_claims: list[str]
    evidence_items: list[EvidenceItem]
    missing_evidence: list[str] = field(default_factory=list)
    retrieval_limits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "title": sanitize_text(self.title, max_chars=500),
            "changed_files": list(self.changed_files),
            "risk_areas": list(self.risk_areas),
            "candidate_claims": [sanitize_text(item, max_chars=500) for item in self.candidate_claims],
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "missing_evidence": [sanitize_text(item, max_chars=500) for item in self.missing_evidence],
            "retrieval_limits": list(self.retrieval_limits),
        }

    def evidence_by_id(self) -> dict[str, EvidenceItem]:
        return {item.evidence_id: item for item in self.evidence_items}
