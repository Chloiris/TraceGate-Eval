from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tracegate.core.serialization import read_jsonl, write_jsonl
from tracegate.data.sources.base import RealDataError


CANDIDATE_RE = re.compile(r"^hard_candidate:(?P<repo>[^:]+):pull:(?P<number>\d+)$")
ISSUE_REF_RE = re.compile(r"(?<![A-Za-z0-9_])#(?P<number>\d+)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GITHUB_TOKEN_RE = r"(?:gh" r"[po]_[A-Za-z0-9_]{20,}|github" r"_pat_[A-Za-z0-9_]{20,})"
SECRET_RE = re.compile(
    GITHUB_TOKEN_RE + r"|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_-]{35}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"BEGIN (RSA|OPENSSH|EC|DSA|PRIVATE) KEY|"
    r"Authorization:[ \t]*Bearer[ \t]+[A-Za-z0-9._-]{20,}"
)
LOCAL_PATH_RE = re.compile(
    r"(?:/[Uu]sers|/private/var/folders|/var/folders)/[^\s`'\"<>)]*|"
    r"[A-Za-z]:\\[^\r\n`'\"<>)]*"
)
BIDI_CONTROL_CODEPOINTS = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
INVISIBLE_TEXT_CODEPOINTS = BIDI_CONTROL_CODEPOINTS | {0x200B, 0x200C, 0x200D, 0xFEFF}

HIGH_RISK_KEYWORDS = [
    "auth",
    "token",
    "security",
    "permission",
    "config",
    "database",
    "migration",
    "public api",
    "compatibility",
    "serialization",
    "payment",
    "refund",
]
SAFETY_KEYWORDS = [
    "backward compatible",
    "backwards compatible",
    "compatibility test",
    "regression test",
    "does not break",
    "not breaking",
    "safe",
    "verified",
    "passes",
    "approved",
]
CONCERN_KEYWORDS = [
    "breaks",
    "breaking",
    "regression",
    "incompatible",
    "concern",
    "failed",
    "failure",
    "revert",
    "rollback",
    "does not address",
    "not address",
    "wrong",
]
STALE_KEYWORDS = [
    "deprecated",
    "obsolete",
    "obsoleted",
    "no longer",
    "removed",
    "drop support",
    "remove support",
    "legacy",
]
SUPERSEDING_KEYWORDS = [
    "superseded",
    "supersede",
    "replaced",
    "obsoleted",
    "no longer relevant",
    "new behavior",
    "current behavior",
    "resolved by",
    "migrated",
]
LOW_RISK_PATH_PREFIXES = ("docs/", "tests/", "test/", ".github/")
LOW_RISK_TEXT_KEYWORDS = ["typo", "documentation", "docs", "refactor", "format", "cleanup", "dependabot"]
AUDIT_LABEL_SOURCE = "codex_evidence_audit_semantic_v2"
RESOLUTION_PHRASES = [
    "addressed",
    "covered",
    "fixed",
    "good catch, fixed",
    "resolved",
    "verified",
    "tests verify",
    "added a regression test",
    "added regression coverage",
    "should be good to merge",
    "lgtm",
]
REVIEW_WAITING_PHRASES = [
    "mind taking a review",
    "could i please get a review",
    "please get a review",
    "waiting for review",
]


@dataclass(frozen=True)
class CandidateRef:
    repo: str
    number: int


def parse_candidate_id(candidate_id: str) -> CandidateRef:
    match = CANDIDATE_RE.match(candidate_id)
    if not match:
        raise RealDataError(f"cannot parse candidate_id: {candidate_id}")
    return CandidateRef(repo=match.group("repo").replace("__", "/"), number=int(match.group("number")))


def _escape_bidi(text: str) -> str:
    return "".join(f"\\u{ord(ch):04X}" if ord(ch) in INVISIBLE_TEXT_CODEPOINTS else ch for ch in text)


def sanitize_text(text: Any) -> str:
    escaped = _escape_bidi(str(text or ""))
    redacted = EMAIL_RE.sub("<redacted-email>", escaped)
    redacted = SECRET_RE.sub("<redacted-secret-pattern>", redacted)
    redacted = LOCAL_PATH_RE.sub("<redacted-local-path>", redacted)
    return " ".join(redacted.split())


def excerpt(text: Any, max_chars: int = 420) -> str:
    cleaned = sanitize_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def _run_gh(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except FileNotFoundError as exc:
        raise RealDataError("gh CLI is required for full manual label audit") from exc
    except subprocess.TimeoutExpired as exc:
        raise RealDataError(f"GitHub command timed out: gh {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        detail = excerpt(exc.stderr or exc.stdout or str(exc), max_chars=600)
        raise RealDataError(f"GitHub command failed: gh {' '.join(args)}: {detail}") from exc
    return result.stdout


def _run_gh_json(args: list[str]) -> Any:
    output = _run_gh(args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RealDataError(f"GitHub command returned invalid JSON: gh {' '.join(args)}") from exc


def _issue_refs_from_texts(texts: list[str], current_number: int, limit: int = 3) -> list[int]:
    refs: list[int] = []
    for text in texts:
        for match in ISSUE_REF_RE.finditer(text or ""):
            number = int(match.group("number"))
            if number == current_number or number in refs:
                continue
            refs.append(number)
            if len(refs) >= limit:
                return refs
    return refs


def fetch_candidate_snapshot(repo: str, number: int) -> dict[str, Any]:
    fields = ",".join(
        [
            "title",
            "body",
            "url",
            "state",
            "createdAt",
            "mergedAt",
            "labels",
            "comments",
            "reviews",
            "files",
            "commits",
            "closingIssuesReferences",
        ]
    )
    view = _run_gh_json(["pr", "view", str(number), "-R", repo, "--json", fields])
    issue_comments = _run_gh_json(["api", f"repos/{repo}/issues/{number}/comments?per_page=100"])
    review_comments = _run_gh_json(["api", f"repos/{repo}/pulls/{number}/comments?per_page=100"])
    reviews_api = _run_gh_json(["api", f"repos/{repo}/pulls/{number}/reviews?per_page=100"])
    diff_names = [line.strip() for line in _run_gh(["pr", "diff", str(number), "-R", repo, "--name-only"]).splitlines() if line.strip()]
    if not isinstance(view, dict) or not isinstance(issue_comments, list) or not isinstance(review_comments, list) or not isinstance(reviews_api, list):
        raise RealDataError(f"unexpected GitHub API shape for {repo}#{number}")

    related_texts = [str(view.get("body") or "")]
    related_texts.extend(str(item.get("body") or "") for item in issue_comments if isinstance(item, dict))
    related_refs: list[dict[str, Any]] = []
    for ref_number in _issue_refs_from_texts(related_texts, current_number=number):
        try:
            issue = _run_gh_json(["api", f"repos/{repo}/issues/{ref_number}"])
            comments = _run_gh_json(["api", f"repos/{repo}/issues/{ref_number}/comments?per_page=20"])
        except RealDataError as exc:
            related_refs.append({"number": ref_number, "error": str(exc)})
            continue
        related_refs.append({"number": ref_number, "issue": issue, "comments": comments})

    return {
        "view": view,
        "issue_comments": issue_comments,
        "review_comments": review_comments,
        "reviews_api": reviews_api,
        "diff_file_names": diff_names,
        "related_refs": related_refs,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _url_from_commit(repo: str, commit: dict[str, Any]) -> str:
    for key in ("url", "htmlUrl", "html_url"):
        value = commit.get(key)
        if value:
            return str(value)
    oid = commit.get("oid") or commit.get("sha")
    return f"https://github.com/{repo}/commit/{oid}" if oid else ""


def _timestamp_from_commit(commit: dict[str, Any]) -> str | None:
    for key in ("authoredDate", "committedDate", "createdAt"):
        if commit.get(key):
            return str(commit[key])
    nested = commit.get("commit")
    if isinstance(nested, dict):
        committer = nested.get("committer") if isinstance(nested.get("committer"), dict) else {}
        return committer.get("date")
    return None


def _timestamp(item: dict[str, Any]) -> str | None:
    for key in ("created_at", "submitted_at", "createdAt", "submittedAt", "updated_at", "updatedAt", "closed_at"):
        if item.get(key):
            return str(item[key])
    return None


def _html_url(item: dict[str, Any]) -> str:
    return str(item.get("html_url") or item.get("htmlUrl") or item.get("url") or "")


def _file_paths(snapshot: dict[str, Any]) -> list[str]:
    view = snapshot["view"]
    paths: list[str] = []
    for item in view.get("files") or []:
        if isinstance(item, dict):
            path = item.get("path") or item.get("filename") or item.get("name")
            if path:
                paths.append(str(path))
        elif item:
            paths.append(str(item))
    paths.extend(str(item) for item in snapshot.get("diff_file_names", []) if item)
    return sorted(dict.fromkeys(paths))


def evidence_items(repo: str, candidate: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, str | None]]:
    view = snapshot["view"]
    items: list[dict[str, str | None]] = [
        {
            "kind": "pr",
            "url": str(view.get("url") or candidate.get("pr_url") or ""),
            "timestamp": str(view.get("createdAt") or ""),
            "text": f"{view.get('title') or candidate.get('title') or ''}\n\n{view.get('body') or ''}",
            "author": str(((view.get("author") or {}) if isinstance(view.get("author"), dict) else {}).get("login") or ""),
            "association": "AUTHOR",
            "review_state": None,
        }
    ]
    for kind, records in [
        ("comment", snapshot.get("issue_comments", [])),
        ("review_comment", snapshot.get("review_comments", [])),
        ("review", snapshot.get("reviews_api", [])),
    ]:
        for record in records[:20]:
            if not isinstance(record, dict):
                continue
            body = record.get("body") or record.get("bodyText") or ""
            url = _html_url(record)
            if body or url:
                user = record.get("user") if isinstance(record.get("user"), dict) else record.get("author")
                items.append(
                    {
                        "kind": kind,
                        "url": url,
                        "timestamp": _timestamp(record),
                        "text": str(body),
                        "author": str((user or {}).get("login") or ""),
                        "association": str(record.get("author_association") or record.get("authorAssociation") or ""),
                        "review_state": str(record.get("state") or "") if kind == "review" else None,
                    }
                )
    for commit in (view.get("commits") or [])[:12]:
        if not isinstance(commit, dict):
            continue
        parts = [str(commit.get(key)) for key in ("messageHeadline", "messageBody", "message", "headline") if commit.get(key)]
        nested = commit.get("commit")
        if not parts and isinstance(nested, dict) and nested.get("message"):
            parts.append(str(nested["message"]))
        url = _url_from_commit(repo, commit)
        if parts or url:
            items.append({"kind": "commit", "url": url, "timestamp": _timestamp_from_commit(commit), "text": "\n".join(parts), "author": "", "association": "", "review_state": None})
    for issue in (view.get("closingIssuesReferences") or [])[:12]:
        if isinstance(issue, dict):
            items.append(
                {
                    "kind": "linked_ref",
                    "url": str(issue.get("url") or ""),
                    "timestamp": _timestamp(issue),
                    "text": f"{issue.get('title') or ''} {issue.get('state') or ''}",
                    "author": "",
                    "association": "",
                    "review_state": None,
                }
            )
    for related in snapshot.get("related_refs", [])[:3]:
        if related.get("error"):
            items.append({"kind": "related_ref_error", "url": "", "timestamp": None, "text": related["error"], "author": "", "association": "", "review_state": None})
            continue
        issue = related.get("issue") if isinstance(related.get("issue"), dict) else {}
        if issue:
            items.append(
                {
                    "kind": "related_ref",
                    "url": _html_url(issue),
                    "timestamp": _timestamp(issue),
                    "text": f"{issue.get('title') or ''}\n\n{issue.get('body') or ''}",
                    "author": str(((issue.get("user") or {}) if isinstance(issue.get("user"), dict) else {}).get("login") or ""),
                    "association": str(issue.get("author_association") or ""),
                    "review_state": None,
                }
            )
        for comment in (related.get("comments") or [])[:4]:
            if isinstance(comment, dict):
                items.append(
                    {
                        "kind": "related_ref_comment",
                        "url": _html_url(comment),
                        "timestamp": _timestamp(comment),
                        "text": str(comment.get("body") or ""),
                        "author": str(((comment.get("user") or {}) if isinstance(comment.get("user"), dict) else {}).get("login") or ""),
                        "association": str(comment.get("author_association") or ""),
                        "review_state": None,
                    }
                )
    return items


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _urls_for(items: list[dict[str, str | None]], keywords: list[str]) -> list[str]:
    urls = []
    for item in items:
        url = str(item.get("url") or "")
        if url and _contains_any(str(item.get("text") or ""), keywords):
            urls.append(url)
    return list(dict.fromkeys(urls))


def _evidence_source_key(url: str) -> str:
    root_match = re.match(r"^https://github\.com/([^/]+/[^/]+)/(pull|issues)/(\d+)/?$", url)
    if root_match:
        return f"github:{root_match.group(1)}:discussion:{root_match.group(3)}:root"
    return url


def _evidence_for(items: list[dict[str, str | None]], keywords: list[str]) -> list[dict[str, str | None]]:
    return [
        item
        for item in items
        if item.get("url") and _contains_any(str(item.get("text") or ""), keywords)
    ]


def _is_mitigated_or_resolved_context(text: str) -> bool:
    lowered = text.lower()
    if any(phrase in lowered for phrase in REVIEW_WAITING_PHRASES):
        return True
    has_resolution = any(phrase in lowered for phrase in RESOLUTION_PHRASES)
    if "concern" in lowered and has_resolution:
        return True
    if "regression" in lowered and ("tests verify no" in lowered or "regression test" in lowered or "regression coverage" in lowered):
        return True
    if "break" in lowered and ("does not break" in lowered or "not breaking" in lowered):
        return True
    return False


def _is_structural_concern_source(item: dict[str, str | None]) -> bool:
    kind = str(item.get("kind") or "")
    if kind in {"comment", "review_comment", "review"}:
        return str(item.get("review_state") or "").upper() not in {"APPROVED"}
    if kind in {"related_ref", "related_ref_comment"}:
        return True
    return False


def _has_later_resolution(items: list[dict[str, str | None]], concern: dict[str, str | None]) -> bool:
    concern_time = _parse_time(concern.get("timestamp"))
    for item in items:
        if item is concern:
            continue
        item_time = _parse_time(item.get("timestamp"))
        if concern_time is not None and item_time is not None and item_time <= concern_time:
            continue
        if _is_mitigated_or_resolved_context(str(item.get("text") or "")):
            return True
        if str(item.get("review_state") or "").upper() == "APPROVED" and item_time is not None:
            return True
    return False


def _is_unresolved_concern_item(items: list[dict[str, str | None]], item: dict[str, str | None]) -> bool:
    text = str(item.get("text") or "")
    if not _is_structural_concern_source(item):
        return False
    if _is_mitigated_or_resolved_context(text):
        return False
    if not _contains_any(text, CONCERN_KEYWORDS):
        return False
    return not _has_later_resolution(items, item)


def _conflict_pair(items: list[dict[str, str | None]]) -> tuple[dict[str, str | None], dict[str, str | None]] | None:
    support_items = _evidence_for(items, SAFETY_KEYWORDS)
    concern_items = [item for item in items if item.get("url") and _is_unresolved_concern_item(items, item)]
    for support in support_items:
        for concern in concern_items:
            support_url = str(support.get("url") or "")
            concern_url = str(concern.get("url") or "")
            if support_url and concern_url and _evidence_source_key(support_url) != _evidence_source_key(concern_url):
                return support, concern
    return None


def _stale_pair(items: list[dict[str, str | None]]) -> tuple[dict[str, str | None], dict[str, str | None]] | None:
    older_items = [item for item in items if item.get("url") and _contains_any(str(item.get("text") or ""), STALE_KEYWORDS)]
    newer_items = [item for item in items if item.get("url") and _contains_any(str(item.get("text") or ""), SUPERSEDING_KEYWORDS)]
    for older in older_items:
        older_time = _parse_time(older.get("timestamp"))
        if older_time is None:
            continue
        for newer in newer_items:
            newer_time = _parse_time(newer.get("timestamp"))
            if newer_time is None or newer.get("url") == older.get("url"):
                continue
            if older_time < newer_time:
                return older, newer
    return None


def _is_low_risk_false_positive(files: list[str], corpus: str) -> bool:
    if _contains_any("\n".join(files), HIGH_RISK_KEYWORDS) or _contains_any(corpus, HIGH_RISK_KEYWORDS):
        return False
    if files and all(path.startswith(LOW_RISK_PATH_PREFIXES) for path in files):
        return True
    return bool(_contains_any(corpus, LOW_RISK_TEXT_KEYWORDS)) and not _contains_any(corpus, CONCERN_KEYWORDS)


def decide_label(candidate: dict[str, Any], snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    ref = parse_candidate_id(str(candidate["candidate_id"]))
    view = snapshot["view"]
    items = evidence_items(ref.repo, candidate, snapshot)
    files = _file_paths(snapshot)
    corpus = "\n".join(
        [
            str(candidate.get("suspected_status") or ""),
            str(candidate.get("why_suspected") or ""),
            str(view.get("title") or ""),
            str(view.get("body") or ""),
            "\n".join(files),
            "\n".join(str(item.get("text") or "") for item in items),
        ]
    )
    suspected = str(candidate.get("suspected_status") or "unknown")
    evidence_urls = [str(item.get("url") or "") for item in items if item.get("url")]
    unique_urls = list(dict.fromkeys(evidence_urls))
    support_urls = _urls_for(items, SAFETY_KEYWORDS)
    concern_urls = _urls_for(items, CONCERN_KEYWORDS)
    conflict_pair = _conflict_pair(items)
    stale_pair = _stale_pair(items)
    high_risk_hits = sorted(set(_contains_any(corpus, HIGH_RISK_KEYWORDS) + _contains_any("\n".join(files), HIGH_RISK_KEYWORDS)))
    safety_hits = sorted(set(_contains_any(corpus, SAFETY_KEYWORDS)))
    missing: list[str] = []

    action = "needs_more_evidence"
    evidence_status = "none"
    expected_decision = "none"
    confidence = 0.35
    rationale = "Evidence was not strong enough for a Codex promote recommendation."

    if suspected == "conflicting":
        if conflict_pair is not None:
            support_item, concern_item = conflict_pair
            conflict_urls = [str(support_item.get("url")), str(concern_item.get("url"))]
            action = "promote"
            evidence_status = "conflicting"
            expected_decision = "detect_conflict"
            confidence = 0.78
            rationale = (
                "Codex found at least two GitHub URLs with opposing safety/compatibility signals: "
                f"support={support_item.get('url')} concern={concern_item.get('url')}."
            )
            unique_urls = conflict_urls + [url for url in unique_urls if url not in conflict_urls]
        elif _is_low_risk_false_positive(files, corpus):
            action = "reject"
            confidence = 0.58
            rationale = "The queue appears to be a keyword hit on ordinary low-risk maintenance, without concrete conflicting evidence."
            missing.append("No second concrete evidence URL showing a real conflict.")
        else:
            missing.append("Needs one URL with a safe/no-breaking claim and another URL with a break/regression/concern claim.")
    elif suspected == "stale":
        if stale_pair is not None:
            older, newer = stale_pair
            action = "promote"
            evidence_status = "stale"
            expected_decision = "verify_first"
            confidence = 0.74
            rationale = (
                "Codex found an older claim and newer superseding evidence with time ordering: "
                f"older={older.get('url')} newer={newer.get('url')}."
            )
            pair_urls = [str(older.get("url")), str(newer.get("url"))]
            unique_urls = pair_urls + [url for url in unique_urls if url not in pair_urls]
        elif _is_low_risk_false_positive(files, corpus):
            action = "reject"
            confidence = 0.56
            rationale = "The stale suspicion is only a keyword hit and lacks an old claim plus newer superseding evidence."
            missing.append("No older/newer evidence pair with time ordering.")
        else:
            missing.append("Needs older claim URL plus newer superseding evidence URL with timestamps.")
    elif suspected == "unknown" or high_risk_hits:
        if high_risk_hits and not safety_hits:
            action = "promote"
            evidence_status = "unknown"
            expected_decision = "verify_first"
            confidence = 0.68
            rationale = (
                "Codex found high-risk change evidence but insufficient safety/verification discussion: "
                f"high_risk_hits={', '.join(high_risk_hits)}."
            )
        elif _is_low_risk_false_positive(files, corpus):
            action = "reject"
            confidence = 0.55
            rationale = "The unknown suspicion is not supported by high-risk files or missing safety evidence."
        else:
            expected_decision = "verify_first"
            missing.append("Needs clearer evidence that the changed area is high risk and lacks validation.")
    elif _is_low_risk_false_positive(files, corpus):
        action = "reject"
        confidence = 0.56
        rationale = "The candidate looks like a keyword hit on ordinary refactor, dependency, docs, tests, or cleanup work."
    else:
        missing.append("Needs stronger concrete GitHub evidence before a final label can be recommended.")

    if action == "promote" and not unique_urls:
        action = "needs_more_evidence"
        evidence_status = "none"
        expected_decision = "none"
        confidence = 0.2
        missing.append("Promote recommendation was blocked because no concrete evidence URL was available.")

    if action in {"reject", "needs_more_evidence"}:
        evidence_status = "none"
        if action == "reject":
            expected_decision = "none"

    reviewed_at = datetime.now(timezone.utc).isoformat()
    label = {
        "candidate_id": candidate["candidate_id"],
        "action": action,
        "evidence_status": evidence_status,
        "expected_decision": expected_decision,
        "label_source": AUDIT_LABEL_SOURCE,
        "label_confidence": round(confidence, 2),
        "rationale": sanitize_text(rationale),
        "evidence_urls": unique_urls[:12],
        "evidence_summary": [
            sanitize_text(f"{item.get('kind')}: {excerpt(item.get('text'), max_chars=240)}")
            for item in items[:8]
            if item.get("url") or item.get("text")
        ],
        "missing_evidence": [sanitize_text(item) for item in missing],
        "human_review_required": True,
        "ready_for_human_final_check": True,
        "reviewed_by": "codex",
        "reviewed_at": reviewed_at,
    }
    detail = {
        "candidate": candidate,
        "repo": ref.repo,
        "number": ref.number,
        "pr_url": str(view.get("url") or candidate.get("pr_url") or ""),
        "title": sanitize_text(view.get("title") or candidate.get("title") or ""),
        "state": str(view.get("state") or ""),
        "created_at": view.get("createdAt"),
        "merged_at": view.get("mergedAt"),
        "labels": [str(item.get("name") or item) for item in (view.get("labels") or [])],
        "files": files,
        "items": items,
        "high_risk_hits": high_risk_hits,
        "safety_hits": safety_hits,
        "support_urls": support_urls,
        "concern_urls": concern_urls,
        "conflict_pair": conflict_pair,
        "stale_pair": stale_pair,
        "label": label,
        "fetch_error": None,
    }
    return label, detail


def _error_label(candidate: dict[str, Any], reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
    ref = parse_candidate_id(str(candidate["candidate_id"]))
    pr_url = str(candidate.get("pr_url") or f"https://github.com/{ref.repo}/pull/{ref.number}")
    reviewed_at = datetime.now(timezone.utc).isoformat()
    label = {
        "candidate_id": candidate["candidate_id"],
        "action": "needs_more_evidence",
        "evidence_status": "none",
        "expected_decision": "none",
        "label_source": AUDIT_LABEL_SOURCE,
        "label_confidence": 0.0,
        "rationale": sanitize_text(f"GitHub evidence fetch failed; no fallback data was used. reason={reason}"),
        "evidence_urls": [pr_url],
        "evidence_summary": [],
        "missing_evidence": [sanitize_text("GitHub API evidence could not be fetched; human review must retry the PR manually.")],
        "human_review_required": True,
        "ready_for_human_final_check": True,
        "reviewed_by": "codex",
        "reviewed_at": reviewed_at,
    }
    detail = {
        "candidate": candidate,
        "repo": ref.repo,
        "number": ref.number,
        "pr_url": pr_url,
        "title": sanitize_text(candidate.get("title") or ""),
        "state": "unknown",
        "created_at": None,
        "merged_at": None,
        "labels": [],
        "files": [],
        "items": [],
        "high_risk_hits": [],
        "safety_hits": [],
        "support_urls": [],
        "concern_urls": [],
        "conflict_pair": None,
        "stale_pair": None,
        "label": label,
        "fetch_error": sanitize_text(reason),
    }
    return label, detail


def validate_codex_audit_labels(queue_rows: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    queue_ids = [str(row.get("candidate_id")) for row in queue_rows]
    label_ids = [str(row.get("candidate_id")) for row in labels]
    if len(labels) != len(queue_rows):
        errors.append(f"expected {len(queue_rows)} labels, found {len(labels)}")
    missing = sorted(set(queue_ids) - set(label_ids))
    extra = sorted(set(label_ids) - set(queue_ids))
    if missing:
        errors.append(f"missing candidate labels: {missing}")
    if extra:
        errors.append(f"extra candidate labels: {extra}")
    for row in labels:
        cid = row.get("candidate_id")
        if row.get("label_source") != AUDIT_LABEL_SOURCE:
            errors.append(f"{cid}: label_source must be {AUDIT_LABEL_SOURCE}")
        if row.get("human_review_required") is not True:
            errors.append(f"{cid}: human_review_required must be true")
        if row.get("ready_for_human_final_check") is not True:
            errors.append(f"{cid}: ready_for_human_final_check must be true")
        if row.get("action") == "promote" and not row.get("evidence_urls"):
            errors.append(f"{cid}: promote requires evidence_urls")
        if row.get("action") == "promote" and row.get("evidence_status") == "conflicting" and len(row.get("evidence_urls") or []) < 2:
            errors.append(f"{cid}: conflicting promote requires at least 2 evidence_urls")
        if row.get("action") == "promote" and row.get("evidence_status") == "stale":
            rationale = str(row.get("rationale") or "").lower()
            if len(row.get("evidence_urls") or []) < 2:
                errors.append(f"{cid}: stale promote requires at least 2 evidence_urls")
            if not all(term in rationale for term in ["older", "newer", "time ordering"]):
                errors.append(f"{cid}: stale promote rationale must mention older/newer/time ordering")
        if row.get("action") == "promote" and row.get("evidence_status") == "unknown" and row.get("expected_decision") != "verify_first":
            errors.append(f"{cid}: unknown promote must use expected_decision=verify_first")
        if row.get("action") in {"reject", "needs_more_evidence"} and row.get("evidence_status") != "none":
            errors.append(f"{cid}: reject/needs_more_evidence must use evidence_status=none")
    return errors


def _status_table(rows: list[dict[str, Any]], key: str) -> str:
    counts = Counter(str(row.get(key) or "none") for row in rows)
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))


def _render_report(queue_rows: list[dict[str, Any]], labels: list[dict[str, Any]], details: list[dict[str, Any]]) -> str:
    action_counts = Counter(row["action"] for row in labels)
    suspected_counts = Counter(str(row.get("suspected_status") or "unknown") for row in queue_rows)
    final_counts = Counter(row["evidence_status"] for row in labels)
    lines = [
        "# Codex Full Label Audit Report",
        "",
        "This report is a Codex evidence audit for the full manual review queue. It does not promote labels into the scored dataset.",
        "",
        "## Overview",
        "",
        f"- total_candidates: `{len(queue_rows)}`",
        f"- promote: `{action_counts.get('promote', 0)}`",
        f"- reject: `{action_counts.get('reject', 0)}`",
        f"- needs_more_evidence: `{action_counts.get('needs_more_evidence', 0)}`",
        f"- suspected_status_distribution: `{dict(sorted(suspected_counts.items()))}`",
        f"- final_evidence_status_distribution: `{dict(sorted(final_counts.items()))}`",
        "- modifies_cases_jsonl: `false`",
        "- ran_promote_labels: `false`",
        "- used_mock_data: `false`",
        "- used_synthetic_data: `false`",
        "- used_fallback_data: `false`",
        "",
        "## Top Promote Candidates",
        "",
        "| candidate_id | evidence_status | confidence | key URLs |",
        "|---|---:|---:|---|",
    ]
    for row in sorted([item for item in labels if item["action"] == "promote"], key=lambda item: item["label_confidence"], reverse=True)[:10]:
        urls = "<br>".join(row["evidence_urls"][:2])
        lines.append(f"| `{row['candidate_id']}` | `{row['evidence_status']}` | `{row['label_confidence']}` | {urls} |")
    if not any(row["action"] == "promote" for row in labels):
        lines.append("| none | none | 0 | none |")
    lines.extend(["", "## Top Needs More Evidence Candidates", "", "| candidate_id | suspected_status | missing evidence |", "|---|---|---|"])
    by_id = {row["candidate_id"]: row for row in queue_rows}
    for row in [item for item in labels if item["action"] == "needs_more_evidence"][:10]:
        missing = "; ".join(row.get("missing_evidence") or ["needs human review"])
        lines.append(f"| `{row['candidate_id']}` | `{by_id[row['candidate_id']].get('suspected_status')}` | {missing} |")
    lines.extend(["", "## Candidate Details", ""])
    detail_by_id = {item["label"]["candidate_id"]: item for item in details}
    for row in labels:
        detail = detail_by_id[row["candidate_id"]]
        candidate = detail["candidate"]
        evidence_lines = []
        for url in row["evidence_urls"][:8]:
            evidence_lines.append(f"- {url}")
        file_lines = [f"- `{path}`" for path in detail["files"][:12]]
        if len(detail["files"]) > 12:
            file_lines.append(f"- ... {len(detail['files']) - 12} more files")
        if not file_lines:
            file_lines.append("- No changed files were returned.")
        lines.extend(
            [
                f"### {row['candidate_id']}",
                "",
                f"- repo: `{detail['repo']}`",
                f"- PR URL: {detail['pr_url']}",
                f"- suspected_status: `{candidate.get('suspected_status')}`",
                f"- final action: `{row['action']}`",
                f"- final evidence_status: `{row['evidence_status']}`",
                f"- expected_decision: `{row['expected_decision']}`",
                f"- confidence: `{row['label_confidence']}`",
                f"- title: {detail['title']}",
                f"- state: `{detail['state']}`",
                f"- created_at: `{detail['created_at']}`",
                f"- merged_at: `{detail['merged_at']}`",
                "",
                "Evidence URLs:",
                *evidence_lines,
                "",
                "Key discussion summary:",
                *[f"- {item}" for item in row["evidence_summary"][:5]],
                "",
                "Changed files:",
                *file_lines,
                "",
                f"Why this action: {row['rationale']}",
                "",
                "Most important human final-check point:",
            ]
        )
        if row["action"] == "promote":
            lines.append("- Confirm that the listed evidence URLs really support the suggested label before changing label_source to manual_verified.")
        elif row["action"] == "reject":
            lines.append("- Confirm this is only a keyword hit or low-risk maintenance before leaving it rejected.")
        else:
            lines.append("- Open the missing evidence items and decide whether to keep needs_more_evidence or reject.")
        if detail.get("fetch_error"):
            lines.append(f"- Fetch error: {detail['fetch_error']}")
        lines.append("")
    for status_name in ["stale", "conflicting", "unknown"]:
        title = {
            "stale": "Stale Candidate Evidence Check",
            "conflicting": "Conflicting Candidate Evidence Check",
            "unknown": "Unknown Candidate Evidence Check",
        }[status_name]
        lines.extend([f"## {title}", ""])
        matches = [item for item in labels if item["evidence_status"] == status_name]
        if not matches:
            lines.append("- No final promote candidates for this evidence_status.")
            lines.append("")
            continue
        for row in matches:
            detail = detail_by_id[row["candidate_id"]]
            if status_name == "stale":
                stale_pair = detail.get("stale_pair")
                lines.append(f"- `{row['candidate_id']}` older/newer/time ordering: `{bool(stale_pair)}`; urls: {row['evidence_urls'][:2]}")
            elif status_name == "conflicting":
                conflict_pair = detail.get("conflict_pair")
                if conflict_pair:
                    support, concern = conflict_pair
                    lines.append(
                        f"- `{row['candidate_id']}` support={support.get('url')} concern={concern.get('url')}"
                    )
                else:
                    lines.append(f"- `{row['candidate_id']}` no validated two-URL conflict pair.")
            else:
                lines.append(f"- `{row['candidate_id']}` high_risk_hits={detail.get('high_risk_hits')} missing={row.get('missing_evidence')}")
        lines.append("")
    lines.extend(
        [
            "## Safety Statement",
            "",
            "- This audit did not modify `datasets/real_min/cases.jsonl`.",
            "- This audit did not run `promote-labels`.",
            f"- `datasets/real_min/labels/manual_labels.jsonl` uses `label_source={AUDIT_LABEL_SOURCE}`, not `manual_verified`.",
            "- Human final review is required before any label can be promoted into scored metrics.",
            "",
        ]
    )
    return _escape_bidi("\n".join(lines))


def _render_checklist(labels: list[dict[str, Any]]) -> str:
    promote_rows = sorted([row for row in labels if row["action"] == "promote"], key=lambda item: item["label_confidence"], reverse=True)
    lines = [
        "# Human Final Checklist",
        "",
        "Use this checklist after reading `docs/CODEX_FULL_LABEL_AUDIT_REPORT.md`.",
        "",
        "- Only a human should change `label_source` to `manual_verified`.",
        "- If you disagree with a Codex suggestion, change the row to `reject` or `needs_more_evidence`.",
        "- Keep `cases.jsonl` unchanged until after final human verification.",
        "",
        "## Highest Priority Promote Suggestions",
        "",
    ]
    if not promote_rows:
        lines.append("- No promote suggestions were produced.")
    for row in promote_rows[:10]:
        urls = row["evidence_urls"][:2]
        lines.append(f"## `{row['candidate_id']}`")
        lines.append("")
        lines.append(f"- suggested evidence_status: `{row['evidence_status']}`")
        lines.append(f"- expected_decision: `{row['expected_decision']}`")
        lines.append(f"- confidence: `{row['label_confidence']}`")
        for url in urls:
            lines.append(f"- key URL: {url}")
        lines.append("- human decision: `[ ] manual_verified` `[ ] reject` `[ ] needs_more_evidence`")
        lines.append("")
    return _escape_bidi("\n".join(lines))


def run_full_label_audit(
    queue_path: Path = Path("datasets/real_min/labels/manual_review_queue.jsonl"),
    labels_path: Path = Path("datasets/real_min/labels/manual_labels.jsonl"),
    report_path: Path = Path("docs/CODEX_FULL_LABEL_AUDIT_REPORT.md"),
    checklist_path: Path = Path("docs/HUMAN_FINAL_CHECKLIST.md"),
    fetcher: Callable[[str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    queue_rows = read_jsonl(queue_path)
    fetch = fetcher or fetch_candidate_snapshot
    labels: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for candidate in queue_rows:
        ref = parse_candidate_id(str(candidate.get("candidate_id") or ""))
        try:
            snapshot = fetch(ref.repo, ref.number)
            label, detail = decide_label(candidate, snapshot)
        except RealDataError as exc:
            label, detail = _error_label(candidate, str(exc))
        labels.append(label)
        details.append(detail)
    errors = validate_codex_audit_labels(queue_rows, labels)
    if errors:
        raise RealDataError("; ".join(errors))
    write_jsonl(labels_path, labels)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(queue_rows, labels, details), encoding="utf-8")
    checklist_path.parent.mkdir(parents=True, exist_ok=True)
    checklist_path.write_text(_render_checklist(labels), encoding="utf-8")
    return {
        "queue_path": queue_path.as_posix(),
        "labels_path": labels_path.as_posix(),
        "report_path": report_path.as_posix(),
        "checklist_path": checklist_path.as_posix(),
        "labels_written": len(labels),
        "action_distribution": dict(sorted(Counter(row["action"] for row in labels).items())),
        "evidence_status_distribution": dict(sorted(Counter(row["evidence_status"] for row in labels).items())),
        "suspected_status_distribution": dict(sorted(Counter(str(row.get("suspected_status") or "unknown") for row in queue_rows).items())),
        "modified_cases_jsonl": False,
        "used_mock_data": False,
        "used_synthetic_data": False,
        "used_fallback_data": False,
    }
