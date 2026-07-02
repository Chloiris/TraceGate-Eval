from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tracegate.core.serialization import read_jsonl, write_jsonl
from tracegate.data.sources.base import RealDataError


BIDI_CONTROL_CODEPOINTS = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CANDIDATE_ID_RE = re.compile(r"^hard_candidate:(?P<repo>[^:]+):pull:(?P<number>\d+)$")

HIGH_RISK_KEYWORDS = [
    "auth",
    "token",
    "permission",
    "security",
    "payment",
    "refund",
    "migration",
    "config",
    "database",
    "public api",
    "compatibility",
    "backward",
    "serialization",
]
ORDINARY_CHANGE_KEYWORDS = [
    "refactor",
    "performance",
    "cleanup",
    "test cleanup",
    "typo",
    "docs",
    "documentation",
    "format",
]
SAFETY_EVIDENCE_KEYWORDS = [
    "backward compatible",
    "backwards compatible",
    "compatibility test",
    "regression test",
    "security review",
    "migration guide",
    "not breaking",
    "does not break",
    "approved",
]
CONFLICT_SUPPORT_KEYWORDS = [
    "does not break",
    "not breaking",
    "backward compatible",
    "safe",
    "approved",
    "works",
]
CONFLICT_CONCERN_KEYWORDS = [
    "breaks",
    "breaking",
    "regression",
    "incompatible",
    "concern",
    "failed",
    "should not",
    "revert",
    "rollback",
]
STALE_KEYWORDS = [
    "deprecated",
    "obsolete",
    "no longer",
    "removed",
    "drop support",
    "remove support",
    "legacy",
    "migration",
]
SUPERSEDING_KEYWORDS = [
    "supersede",
    "replaced",
    "now",
    "new behavior",
    "current behavior",
    "since",
    "migrated",
]


@dataclass(frozen=True)
class ParsedCandidateId:
    repo: str
    number: int


def _escape_bidi_controls(text: str) -> str:
    return "".join(f"\\u{ord(ch):04X}" if ord(ch) in BIDI_CONTROL_CODEPOINTS else ch for ch in text)


def _sanitize_text(text: str | None) -> str:
    escaped = _escape_bidi_controls(text or "")
    redacted = EMAIL_RE.sub("<redacted-email>", escaped)
    return " ".join(redacted.split())


def _excerpt(text: str | None, max_chars: int = 520) -> str:
    cleaned = _sanitize_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def parse_candidate_id(candidate_id: str) -> ParsedCandidateId:
    match = CANDIDATE_ID_RE.match(candidate_id)
    if not match:
        raise RealDataError(f"cannot parse hard candidate id: {candidate_id}")
    return ParsedCandidateId(repo=match.group("repo").replace("__", "/"), number=int(match.group("number")))


def _run_gh(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise RealDataError("gh CLI is required for evidence-pack GitHub evidence collection") from exc
    except subprocess.TimeoutExpired as exc:
        raise RealDataError(f"GitHub evidence command timed out: gh {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        detail = _excerpt(exc.stderr or exc.stdout or str(exc), max_chars=500)
        raise RealDataError(f"GitHub evidence command failed: gh {' '.join(args)}: {detail}") from exc
    return result.stdout


def _run_gh_json(args: list[str]) -> Any:
    output = _run_gh(args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RealDataError(f"GitHub evidence command returned invalid JSON: gh {' '.join(args)}") from exc


def fetch_github_evidence(repo: str, number: int) -> dict[str, Any]:
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
    issue_comments = _run_gh_json(["api", f"repos/{repo}/issues/{number}/comments?per_page=50"])
    review_comments = _run_gh_json(["api", f"repos/{repo}/pulls/{number}/comments?per_page=50"])
    reviews = _run_gh_json(["api", f"repos/{repo}/pulls/{number}/reviews?per_page=50"])
    diff_names = [line.strip() for line in _run_gh(["pr", "diff", str(number), "-R", repo, "--name-only"]).splitlines() if line.strip()]
    if not isinstance(view, dict) or not isinstance(issue_comments, list) or not isinstance(review_comments, list) or not isinstance(reviews, list):
        raise RealDataError(f"unexpected GitHub evidence shape for {repo}#{number}")
    return {
        "view": view,
        "issue_comments": issue_comments,
        "review_comments": review_comments,
        "reviews_api": reviews,
        "diff_file_names": diff_names,
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


def _evidence_items(repo: str, candidate: dict[str, Any], snapshot: dict[str, Any]) -> list[dict[str, str | None]]:
    view = snapshot["view"]
    items: list[dict[str, str | None]] = [
        {
            "kind": "pr",
            "url": str(view.get("url") or candidate.get("pr_url") or ""),
            "timestamp": view.get("createdAt"),
            "text": f"{view.get('title') or candidate.get('title') or ''}\n\n{view.get('body') or ''}",
        }
    ]
    for source_name, records in [
        ("comment", snapshot.get("issue_comments", [])),
        ("review_comment", snapshot.get("review_comments", [])),
        ("review", snapshot.get("reviews_api", [])),
    ]:
        for record in records[:12]:
            if not isinstance(record, dict):
                continue
            body = record.get("body") or record.get("bodyText") or ""
            url = record.get("html_url") or record.get("url") or record.get("htmlUrl") or ""
            timestamp = record.get("created_at") or record.get("submitted_at") or record.get("createdAt") or record.get("submittedAt")
            if body or url:
                items.append({"kind": source_name, "url": str(url), "timestamp": timestamp, "text": str(body)})
    for commit in (view.get("commits") or [])[:8]:
        if not isinstance(commit, dict):
            continue
        text = "\n".join(
            str(commit.get(key) or "")
            for key in ("messageHeadline", "messageBody", "message", "headline")
            if commit.get(key)
        )
        if not text:
            nested = commit.get("commit")
            if isinstance(nested, dict):
                text = str(nested.get("message") or "")
        url = _url_from_commit(repo, commit)
        if text or url:
            items.append({"kind": "commit", "url": url, "timestamp": _timestamp_from_commit(commit), "text": text})
    for issue in (view.get("closingIssuesReferences") or [])[:8]:
        if not isinstance(issue, dict):
            continue
        title = str(issue.get("title") or "")
        url = str(issue.get("url") or "")
        state = str(issue.get("state") or "")
        if title or url:
            items.append({"kind": "linked_ref", "url": url, "timestamp": None, "text": f"{title} {state}".strip()})
    return items


def _all_files(snapshot: dict[str, Any]) -> list[str]:
    view = snapshot["view"]
    files = []
    for item in view.get("files") or []:
        if isinstance(item, dict):
            path = item.get("path") or item.get("filename") or item.get("name")
            if path:
                files.append(str(path))
        elif item:
            files.append(str(item))
    files.extend(str(item) for item in snapshot.get("diff_file_names", []) if item)
    return sorted(dict.fromkeys(files))


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_ordinary_low_risk(files: list[str], corpus: str) -> bool:
    if _contains_any("\n".join(files), HIGH_RISK_KEYWORDS) or _contains_any(corpus, HIGH_RISK_KEYWORDS):
        return False
    if files and all(path.startswith(("docs/", "tests/", "test/", ".github/")) for path in files):
        return True
    return bool(_contains_any(corpus, ORDINARY_CHANGE_KEYWORDS)) and not _contains_any(corpus, CONFLICT_CONCERN_KEYWORDS)


def _stale_has_ordered_evidence(items: list[dict[str, str | None]]) -> bool:
    stale_items = [item for item in items if _contains_any(str(item.get("text") or ""), STALE_KEYWORDS)]
    superseding_items = [item for item in items if _contains_any(str(item.get("text") or ""), SUPERSEDING_KEYWORDS)]
    for older in stale_items:
        older_time = _parse_time(older.get("timestamp"))
        if not older.get("url") or older_time is None:
            continue
        for newer in superseding_items:
            newer_time = _parse_time(newer.get("timestamp"))
            if not newer.get("url") or newer.get("url") == older.get("url") or newer_time is None:
                continue
            if older_time < newer_time:
                return True
    return False


def _conflict_has_two_sides(items: list[dict[str, str | None]]) -> bool:
    support_urls = {
        str(item.get("url"))
        for item in items
        if item.get("url") and _contains_any(str(item.get("text") or ""), CONFLICT_SUPPORT_KEYWORDS)
    }
    concern_urls = {
        str(item.get("url"))
        for item in items
        if item.get("url") and _contains_any(str(item.get("text") or ""), CONFLICT_CONCERN_KEYWORDS)
    }
    return bool(support_urls) and bool(concern_urls) and len(support_urls | concern_urls) >= 2


def suggest_draft_label(candidate: dict[str, Any], snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed = parse_candidate_id(str(candidate["candidate_id"]))
    items = _evidence_items(parsed.repo, candidate, snapshot)
    files = _all_files(snapshot)
    view = snapshot["view"]
    evidence_text = "\n".join(str(item.get("text") or "") for item in items)
    file_text = "\n".join(files)
    corpus = "\n".join(
        [
            str(candidate.get("why_suspected") or ""),
            str(candidate.get("suspected_status") or ""),
            str(view.get("title") or candidate.get("title") or ""),
            str(view.get("body") or ""),
            evidence_text,
            file_text,
        ]
    )
    suspected = str(candidate.get("suspected_status") or "unknown")
    high_risk_hits = sorted(set(_contains_any(corpus, HIGH_RISK_KEYWORDS) + _contains_any(file_text, HIGH_RISK_KEYWORDS)))
    has_safety_evidence = bool(_contains_any(corpus, SAFETY_EVIDENCE_KEYWORDS))
    ordinary_low_risk = _is_ordinary_low_risk(files, corpus)
    evidence_urls = [str(item["url"]) for item in items if item.get("url")]
    unique_evidence_urls = list(dict.fromkeys(evidence_urls))
    missing: list[str] = []

    action = "needs_more_evidence"
    label = "none"
    expected_decision = "none"
    confidence = 0.5

    if suspected == "conflicting":
        if _conflict_has_two_sides(items):
            action = "promote"
            label = "conflicting"
            expected_decision = "detect_conflict"
            confidence = 0.78
        elif ordinary_low_risk:
            action = "reject"
            confidence = 0.63
            missing.append("No concrete conflict evidence beyond keyword-level suspicion.")
        else:
            missing.append("Need at least one supporting evidence URL and one contradicting evidence URL.")
    elif suspected == "stale":
        if _stale_has_ordered_evidence(items):
            action = "promote"
            label = "stale"
            expected_decision = "verify_first"
            confidence = 0.74
        elif ordinary_low_risk:
            action = "reject"
            confidence = 0.61
            missing.append("No old claim plus newer superseding evidence pair was found.")
        else:
            missing.append("Need an old claim URL and a newer superseding evidence URL with clear timestamps.")
    elif suspected == "unknown" or high_risk_hits:
        expected_decision = "verify_first"
        if high_risk_hits and not has_safety_evidence:
            action = "promote"
            label = "unknown"
            confidence = 0.72
            missing.append("No sufficient PR body/comment/review evidence was found for the high-risk area.")
        elif ordinary_low_risk:
            action = "reject"
            expected_decision = "none"
            confidence = 0.6
            missing.append("The available evidence looks like ordinary low-risk maintenance.")
        else:
            missing.append("Need stronger current evidence before deciding whether this is unknown.")
    elif ordinary_low_risk:
        action = "reject"
        confidence = 0.62
        missing.append("Keyword suspicion is not supported by changed files or review evidence.")
    else:
        missing.append("Need more concrete evidence before suggesting a label.")

    if action != "promote":
        label = "none"
        if action == "reject":
            expected_decision = "none"

    rationale = {
        "promote": f"AI draft found evidence consistent with `{label}`; human confirmation is still required.",
        "reject": "AI draft found the queue suspicion is not supported strongly enough by current GitHub evidence.",
        "needs_more_evidence": "AI draft could not collect enough concrete GitHub evidence for a safe label suggestion.",
    }[action]

    draft = {
        "candidate_id": candidate["candidate_id"],
        "action_suggestion": action,
        "suggested_evidence_status": label,
        "suggested_expected_decision": expected_decision,
        "ai_confidence": confidence,
        "rationale": _sanitize_text(rationale),
        "evidence_urls": unique_evidence_urls[:12],
        "missing_evidence": [_sanitize_text(item) for item in missing],
        "label_source": "ai_suggested",
        "must_not_count_as_manual_verified": True,
    }
    pack = {
        "candidate_id": candidate["candidate_id"],
        "repo": parsed.repo,
        "pr_number": parsed.number,
        "pr_url": str(view.get("url") or candidate.get("pr_url") or f"https://github.com/{parsed.repo}/pull/{parsed.number}"),
        "suspected_status": suspected,
        "why_suspected": _excerpt(str(candidate.get("why_suspected") or "")),
        "title": _excerpt(str(view.get("title") or candidate.get("title") or ""), max_chars=260),
        "body_summary": _excerpt(str(view.get("body") or ""), max_chars=720),
        "state": str(view.get("state") or ""),
        "created_at": view.get("createdAt"),
        "merged_at": view.get("mergedAt"),
        "labels": [str(item.get("name") or item) for item in (view.get("labels") or [])],
        "changed_files": files,
        "evidence_items": [
            {
                "kind": item.get("kind"),
                "url": item.get("url"),
                "timestamp": item.get("timestamp"),
                "excerpt": _excerpt(str(item.get("text") or ""), max_chars=280),
            }
            for item in items[:18]
        ],
        "linked_refs": [
            {
                "url": item.get("url"),
                "excerpt": _excerpt(str(item.get("text") or ""), max_chars=220),
            }
            for item in items
            if item.get("kind") == "linked_ref"
        ],
        "missing_evidence": draft["missing_evidence"],
        "human_questions": [
            _sanitize_text(str(question))
            for question in (candidate.get("questions_for_reviewer") or [])
        ][:6],
        "draft": draft,
        "high_risk_hits": high_risk_hits,
        "used_mock_model": False,
        "used_synthetic_data": False,
        "used_fallback_data": False,
    }
    return draft, pack


def _render_evidence_pack(packs: list[dict[str, Any]], drafts: list[dict[str, Any]]) -> str:
    action_counts = Counter(row["action_suggestion"] for row in drafts)
    label_counts = Counter(row["suggested_evidence_status"] for row in drafts)
    lines = [
        "# Evidence Pack Round 1",
        "",
        "AI-assisted draft suggestions for the manual review queue. These are not human-verified labels and are excluded from scored metrics.",
        "",
        "## Summary",
        "",
        f"- generated_at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- evidence_packs: `{len(packs)}`",
        f"- promote_suggestions: `{action_counts.get('promote', 0)}`",
        f"- reject_suggestions: `{action_counts.get('reject', 0)}`",
        f"- needs_more_evidence_suggestions: `{action_counts.get('needs_more_evidence', 0)}`",
        f"- suggested_label_distribution: `{dict(sorted(label_counts.items()))}`",
        "- label_source: `ai_suggested` only",
        "- modifies_manual_labels_jsonl: `false`",
        "- modifies_cases_jsonl: `false`",
        "- used_mock_model: `false`",
        "- used_synthetic_data: `false`",
        "- used_fallback_data: `false`",
        "",
    ]
    for index, pack in enumerate(packs, start=1):
        draft = pack["draft"]
        files = pack["changed_files"][:20]
        evidence_items = pack["evidence_items"]
        linked_refs = pack["linked_refs"]
        lines.extend(
            [
                f"## {index}. {pack['candidate_id']}",
                "",
                f"- repo: `{pack['repo']}`",
                f"- pr_url: {pack['pr_url']}",
                f"- suspected_status: `{pack['suspected_status']}`",
                f"- why_suspected: {pack['why_suspected'] or '(empty)'}",
                f"- state: `{pack['state']}`",
                f"- created_at: `{pack['created_at']}`",
                f"- merged_at: `{pack['merged_at']}`",
                f"- labels: `{pack['labels']}`",
                "",
                "### PR Summary",
                "",
                f"- title: {pack['title']}",
                f"- body: {pack['body_summary'] or '(empty)'}",
                "",
                "### Changed Files",
                "",
            ]
        )
        if files:
            lines.extend(f"- `{path}`" for path in files)
            if len(pack["changed_files"]) > len(files):
                lines.append(f"- ... {len(pack['changed_files']) - len(files)} more")
        else:
            lines.append("- Missing changed-file names from GitHub response.")
        lines.extend(["", "### Possible Evidence Items / Comments / Reviews / Commits", ""])
        for item in evidence_items[:12]:
            lines.append(f"- `{item['kind']}` {item['url'] or '(no url)'}: {item['excerpt'] or '(empty)'}")
        if len(evidence_items) > 12:
            lines.append(f"- ... {len(evidence_items) - 12} more evidence items")
        lines.extend(["", "### Linked Refs", ""])
        if linked_refs:
            for item in linked_refs:
                if item["excerpt"]:
                    lines.append(f"- {item['url'] or '(no url)'}: {item['excerpt']}")
                else:
                    lines.append(f"- {item['url'] or '(no url)'}")
        else:
            lines.append("- No closingIssuesReferences or linked refs returned by GitHub.")
        lines.extend(["", "### Draft Suggestion", ""])
        lines.extend(
            [
                f"- recommended_action: `{draft['action_suggestion']}`",
                f"- recommended_label: `{draft['suggested_evidence_status']}`",
                f"- recommended_expected_decision: `{draft['suggested_expected_decision']}`",
                f"- confidence: `{draft['ai_confidence']}`",
                f"- rationale: {draft['rationale']}",
            ]
        )
        lines.extend(["", "### Missing Evidence", ""])
        if draft["missing_evidence"]:
            lines.extend(f"- {item}" for item in draft["missing_evidence"])
        else:
            lines.append("- None identified by the AI draft.")
        lines.extend(["", "### Human Confirmation Questions", ""])
        if pack["human_questions"]:
            lines.extend(f"- {item}" for item in pack["human_questions"])
        else:
            lines.append("- Confirm whether the evidence URLs are sufficient to promote, reject, or request more evidence.")
        lines.append("")
    return _escape_bidi_controls("\n".join(lines).rstrip() + "\n")


def generate_evidence_pack(
    input_path: Path,
    limit: int,
    output_path: Path,
    draft_labels_path: Path,
    fetcher: Callable[[str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if limit < 1:
        raise RealDataError("--limit must be positive")
    rows = read_jsonl(input_path)
    selected = rows[:limit]
    fetch = fetcher or fetch_github_evidence
    drafts: list[dict[str, Any]] = []
    packs: list[dict[str, Any]] = []
    for row in selected:
        parsed = parse_candidate_id(str(row.get("candidate_id") or ""))
        snapshot = fetch(parsed.repo, parsed.number)
        draft, pack = suggest_draft_label(row, snapshot)
        if draft.get("label_source") == "manual_verified":
            raise RealDataError("draft evidence-pack must not create manual_verified labels")
        drafts.append(draft)
        packs.append(pack)

    markdown = _render_evidence_pack(packs, drafts)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    write_jsonl(draft_labels_path, drafts)
    action_counts = dict(sorted(Counter(row["action_suggestion"] for row in drafts).items()))
    label_counts = dict(sorted(Counter(row["suggested_evidence_status"] for row in drafts).items()))
    return {
        "input_path": input_path.as_posix(),
        "output_path": output_path.as_posix(),
        "draft_labels_path": draft_labels_path.as_posix(),
        "evidence_packs": len(packs),
        "action_suggestion_distribution": action_counts,
        "suggested_label_distribution": label_counts,
        "modified_manual_labels_jsonl": False,
        "modified_cases_jsonl": False,
        "used_mock_model": False,
        "used_synthetic_data": False,
        "used_fallback_data": False,
    }
