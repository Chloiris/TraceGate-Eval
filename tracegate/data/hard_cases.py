from __future__ import annotations

import re
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tracegate.core.models import EvalCase
from tracegate.core.serialization import load_cases, read_jsonl, stable_hash_text, write_cases, write_jsonl
from tracegate.data.manifest import build_dataset_manifest
from tracegate.data.sources.base import RealDataError
from tracegate.data.sources.github_adapter import GITHUB_API_BASE, get_json, list_pull_request_files


STALE_KEYWORDS = [
    "deprecated",
    "removed",
    "no longer",
    "migrate",
    "migration",
    "legacy",
    "breaking change",
    "cleanup",
    "drop support",
    "remove support",
    "obsolete",
]

UNKNOWN_HIGH_RISK_KEYWORDS = [
    "auth",
    "token",
    "permission",
    "security",
    "payment",
    "refund",
    "migration",
    "config",
    "database",
    "serialization",
    "backwards compatibility",
    "public api",
]

CONFLICTING_KEYWORDS = [
    "regression",
    "breaks",
    "incompatible",
    "contradiction",
    "not true",
    "wrong assumption",
    "should not",
    "revert",
    "rollback",
    "failed",
    "flaky",
    "concern",
]

ACCEPTED_LABEL_SOURCES = {"manual_verified", "human_accepted_codex_audit"}
CODEX_AUDIT_SOURCES = {"codex_evidence_audit", "codex_evidence_audit_semantic_v2"}
HARD_EVIDENCE_STATUSES = {"unknown", "conflicting", "stale"}
CANDIDATE_ID_RE = re.compile(r"^hard_candidate:(?P<repo>[^:]+):pull:(?P<number>\d+)$")
BIDI_CONTROL_CODEPOINTS = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))
INVISIBLE_TEXT_CODEPOINTS = BIDI_CONTROL_CODEPOINTS | {0x200B, 0x200C, 0x200D, 0xFEFF}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_RE = re.compile(
    r"(?:gh[po]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})|"
    r"sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|"
    r"AIza[0-9A-Za-z_-]{35}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY|"
    r"Authorization:[ \t]*Bearer[ \t]+[A-Za-z0-9._-]{20,}"
)
LOCAL_PATH_RE = re.compile(
    r"(?:/[Uu]sers|/private/var/folders|/var/folders)/[^\s`'\"<>)]*|"
    r"[A-Za-z]:\\[^\r\n`'\"<>)]*"
)


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def _sanitize_public_text(text: Any) -> str:
    escaped = "".join(f"\\u{ord(ch):04X}" if ord(ch) in INVISIBLE_TEXT_CODEPOINTS else ch for ch in str(text or ""))
    redacted = EMAIL_RE.sub("<redacted-email>", escaped)
    redacted = SECRET_RE.sub("<redacted-secret-pattern>", redacted)
    redacted = LOCAL_PATH_RE.sub("<redacted-local-path>", redacted)
    return " ".join(redacted.split())


def _excerpt(text: str | None, max_chars: int = 420) -> str:
    cleaned = _sanitize_public_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def _search_prs(repo: str, keyword: str, per_page: int) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "q": f"repo:{repo} is:pr {keyword}",
            "sort": "updated",
            "order": "desc",
            "per_page": str(per_page),
        }
    )
    data = get_json(f"{GITHUB_API_BASE}/search/issues?{query}")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise RealDataError(f"unexpected GitHub search response for {repo} keyword {keyword!r}")
    return items


def _pull_request(repo: str, number: int) -> dict[str, Any]:
    data = get_json(f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}")
    if not isinstance(data, dict):
        raise RealDataError(f"unexpected GitHub PR response for {repo}#{number}")
    return data


def _issue_comments(repo: str, number: int) -> list[dict[str, Any]]:
    data = get_json(f"{GITHUB_API_BASE}/repos/{repo}/issues/{number}/comments?per_page=20")
    if not isinstance(data, list):
        raise RealDataError(f"unexpected GitHub issue comments response for {repo}#{number}")
    return data


def _review_comments(repo: str, number: int) -> list[dict[str, Any]]:
    data = get_json(f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}/comments?per_page=20")
    if not isinstance(data, list):
        raise RealDataError(f"unexpected GitHub review comments response for {repo}#{number}")
    return data


def _commits(repo: str, number: int) -> list[dict[str, Any]]:
    data = get_json(f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}/commits?per_page=20")
    if not isinstance(data, list):
        raise RealDataError(f"unexpected GitHub commits response for {repo}#{number}")
    return data


def _evidence_item(
    candidate_id: str,
    suffix: str,
    evidence_type: str,
    text: str,
    url: str,
    timestamp: str | None = None,
    relation: str = "unclear",
) -> dict[str, Any]:
    excerpt = _excerpt(text)
    return {
        "evidence_id": f"{candidate_id}:evidence:{suffix}",
        "evidence_type": evidence_type,
        "evidence_text_excerpt": excerpt,
        "evidence_url": url,
        "file_path": None,
        "commit_sha": None,
        "timestamp": timestamp,
        "supports_or_contradicts": relation,
        "provenance_hash": stable_hash_text(f"{candidate_id}|{suffix}|{url}|{excerpt}"),
    }


def _candidate_from_pr(repo: str, number: int, suspected_from: str) -> dict[str, Any] | None:
    pr = _pull_request(repo, number)
    files = list_pull_request_files(repo, number)
    comments = _issue_comments(repo, number)
    review_comments = _review_comments(repo, number)
    commits = _commits(repo, number)

    html_url = str(pr.get("html_url") or f"https://github.com/{repo}/pull/{number}")
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")
    file_paths = [str(item.get("filename")) for item in files if item.get("filename")]
    comment_text = "\n".join(str(item.get("body") or "") for item in comments[:8])
    review_text = "\n".join(str(item.get("body") or "") for item in review_comments[:8])
    commit_text = "\n".join(str((item.get("commit") or {}).get("message") or "") for item in commits[:8])
    corpus = "\n".join([title, body, " ".join(file_paths), comment_text, review_text, commit_text])

    conflicting_hits = _contains_any(corpus, CONFLICTING_KEYWORDS)
    stale_hits = _contains_any(corpus, STALE_KEYWORDS)
    high_risk_hits = _contains_any(corpus, UNKNOWN_HIGH_RISK_KEYWORDS)

    candidate_id = f"hard_candidate:{repo.replace('/', '__')}:pull:{number}"
    evidence_items = [
        _evidence_item(
            candidate_id,
            "pr",
            "pr",
            f"{title}\n\n{body}",
            html_url,
            timestamp=pr.get("created_at"),
            relation="supports",
        )
    ]
    for index, item in enumerate(comments[:3], start=1):
        url = str(item.get("html_url") or "")
        if url:
            evidence_items.append(
                _evidence_item(
                    candidate_id,
                    f"issue-comment-{index}",
                    "comment",
                    str(item.get("body") or ""),
                    url,
                    timestamp=item.get("created_at"),
                )
            )
    for index, item in enumerate(review_comments[:3], start=1):
        url = str(item.get("html_url") or "")
        if url:
            evidence_items.append(
                _evidence_item(
                    candidate_id,
                    f"review-comment-{index}",
                    "review",
                    str(item.get("body") or ""),
                    url,
                    timestamp=item.get("created_at"),
                    relation="contradicts" if conflicting_hits else "unclear",
                )
            )
    for index, item in enumerate(commits[:2], start=1):
        url = str(item.get("html_url") or "")
        message = str((item.get("commit") or {}).get("message") or "")
        if url and message:
            evidence_items.append(
                _evidence_item(
                    candidate_id,
                    f"commit-{index}",
                    "commit",
                    message,
                    url,
                    timestamp=(item.get("commit") or {}).get("committer", {}).get("date"),
                )
            )

    if conflicting_hits:
        suspected_status = "conflicting"
        questions = [
            "Which evidence source is authoritative for the current behavior?",
            "Does the PR introduce a regression or only discuss one?",
            "Should this be scored as detect_conflict or needs_manual_review?",
        ]
        why = f"Conflict keywords found: {', '.join(conflicting_hits)}"
    elif stale_hits and len(evidence_items) >= 2:
        suspected_status = "stale"
        questions = [
            "Does newer PR/comment/commit evidence supersede the older claim?",
            "Are the evidence timestamps ordered clearly enough to mark stale?",
            "Should this be scored as verify_first after manual review?",
        ]
        why = f"Stale/deprecation keywords found with multiple evidence URLs: {', '.join(stale_hits)}"
    elif high_risk_hits or any(_contains_any(path, UNKNOWN_HIGH_RISK_KEYWORDS) for path in file_paths):
        suspected_status = "unknown"
        questions = [
            "Is there enough evidence to preserve or optimize safely?",
            "Which current test, owner note, or doc confirms the behavior?",
            "Should this remain excluded until manual confirmation?",
        ]
        why = f"High-risk path/topic keywords found without enough scored evidence: {', '.join(high_risk_hits) or 'file path match'}"
    else:
        return None

    return {
        "candidate_id": candidate_id,
        "repo": repo,
        "pr_url": html_url,
        "issue_url": pr.get("issue_url"),
        "comment_url": next((item["evidence_url"] for item in evidence_items if item["evidence_type"] == "comment"), None),
        "review_url": next((item["evidence_url"] for item in evidence_items if item["evidence_type"] == "review"), None),
        "commit_url": next((item["evidence_url"] for item in evidence_items if item["evidence_type"] == "commit"), None),
        "suspected_status": suspected_status,
        "why_suspected": why,
        "suspected_from": suspected_from,
        "title": title,
        "files_changed": file_paths,
        "evidence_items": evidence_items,
        "questions_for_reviewer": questions,
        "excluded_from_real_metrics": True,
        "exclusion_reason": "hard candidate requires manual review before promotion to scored real metrics",
        "is_real": True,
        "is_synthetic": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _candidate_from_search_item(repo: str, item: dict[str, Any], suspected_from: str) -> dict[str, Any] | None:
    number = int(item["number"])
    html_url = str(item.get("html_url") or f"https://github.com/{repo}/pull/{number}")
    title = str(item.get("title") or "")
    body = str(item.get("body") or "")
    corpus = f"{title}\n{body}"
    conflicting_hits = _contains_any(corpus, CONFLICTING_KEYWORDS)
    stale_hits = _contains_any(corpus, STALE_KEYWORDS)
    high_risk_hits = _contains_any(corpus, UNKNOWN_HIGH_RISK_KEYWORDS)
    candidate_id = f"hard_candidate:{repo.replace('/', '__')}:pull:{number}"

    if conflicting_hits:
        suspected_status = "conflicting"
        why = f"Conflict keywords found in PR title/body: {', '.join(conflicting_hits)}"
        relation = "contradicts"
        questions = [
            "Find the supporting evidence URL and the contradicting evidence URL.",
            "Does the conflict affect current behavior or only historical discussion?",
            "Should this be detect_conflict or needs_manual_review?",
        ]
    elif stale_hits:
        suspected_status = "stale"
        why = f"Stale/deprecation keywords found in PR title/body: {', '.join(stale_hits)}"
        relation = "unclear"
        questions = [
            "Find the older claim URL and the newer superseding evidence URL.",
            "Are the timestamps clearly ordered?",
            "Should this remain excluded until both evidence URLs are present?",
        ]
    elif high_risk_hits:
        suspected_status = "unknown"
        why = f"High-risk topic keywords found in PR title/body: {', '.join(high_risk_hits)}"
        relation = "unclear"
        questions = [
            "Is there enough evidence to preserve or optimize safely?",
            "Which current test, owner note, or doc confirms the behavior?",
            "Should this be scored as verify_first after review?",
        ]
    else:
        return None

    evidence_items = [
        _evidence_item(
            candidate_id,
            "pr-search",
            "pr",
            f"{title}\n\n{body}",
            html_url,
            timestamp=item.get("updated_at"),
            relation=relation,
        )
    ]
    return {
        "candidate_id": candidate_id,
        "repo": repo,
        "pr_url": html_url,
        "issue_url": html_url.replace("/pull/", "/issues/"),
        "comment_url": None,
        "review_url": None,
        "commit_url": None,
        "suspected_status": suspected_status,
        "why_suspected": why,
        "suspected_from": suspected_from,
        "title": title,
        "files_changed": [],
        "evidence_items": evidence_items,
        "questions_for_reviewer": questions,
        "excluded_from_real_metrics": True,
        "exclusion_reason": "hard candidate requires manual review before promotion to scored real metrics",
        "is_real": True,
        "is_synthetic": False,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def write_data_insufficient(
    queue_path: Path,
    candidate_counts: dict[str, int],
    scored_counts: dict[str, int],
    output_path: Path = Path("docs/DATA_INSUFFICIENT.md"),
) -> Path:
    lines = [
        "# Data Insufficient: hard real-data mini benchmark",
        "",
        f"Generated on: {datetime.now(timezone.utc).isoformat()}",
        "",
        "The current committed scored dataset remains the active-only real-data smoke dataset. "
        "Automatically mined hard candidates were not promoted into scored metrics because they require manual review.",
        "",
        "## Current Scored Dataset",
        "",
        f"- active: `{scored_counts.get('active', 0)}`",
        f"- stale: `{scored_counts.get('stale', 0)}`",
        f"- unknown: `{scored_counts.get('unknown', 0)}`",
        f"- conflicting: `{scored_counts.get('conflicting', 0)}`",
        "",
        "## Manual Review Queue",
        "",
        f"- queue_path: `{queue_path.as_posix()}`",
        f"- stale candidates: `{candidate_counts.get('stale', 0)}`",
        f"- unknown candidates: `{candidate_counts.get('unknown', 0)}`",
        f"- conflicting candidates: `{candidate_counts.get('conflicting', 0)}`",
        "",
        "## Why hard_benchmark_ready is false",
        "",
        "- Minimum scored distribution is `active>=8`, `unknown>=3`, `conflicting>=2`, `stale>=1`, `scored_cases>=14`.",
        "- Hard candidates need manual adjudication before promotion.",
        "- TraceGate does not fill missing hard cases with synthetic, mock, or fallback data.",
        "",
        "## Next Fix",
        "",
        "Review `datasets/real_min/labels/manual_review_queue.jsonl`, write confirmed labels to "
        "`datasets/real_min/labels/manual_labels.jsonl`, then run `python -m tracegate data promote-labels`.",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_data_blocked(reason: str, output_path: Path = Path("docs/DATA_BLOCKED.md")) -> Path:
    scored_counts: dict[str, int] = {}
    dataset_path = Path("datasets/real_min/cases.jsonl")
    if dataset_path.exists():
        scored_counts = dict(
            sorted(Counter(case.evidence_status.value for case in load_cases(dataset_path) if case.is_scored_real_case).items())
        )
    insufficient_path = write_data_insufficient(
        queue_path=Path("datasets/real_min/labels/manual_review_queue.jsonl"),
        candidate_counts={},
        scored_counts=scored_counts,
    )
    lines = [
        "# Data Blocked: hard real-data mining",
        "",
        f"Generated on: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Hard-case mining could not complete against the GitHub REST API.",
        "",
        f"- reason: `{reason}`",
        "- used_fallback_data: `false`",
        "- used_synthetic_data: `false`",
        f"- data_insufficient_path: `{insufficient_path.as_posix()}`",
        "",
        "No replacement candidates were created.",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def mine_hard_candidates(
    repos: list[str],
    limit: int,
    queue_path: Path = Path("datasets/real_min/labels/manual_review_queue.jsonl"),
    labels_path: Path = Path("datasets/real_min/labels/manual_labels.jsonl"),
    dataset_path: Path = Path("datasets/real_min/cases.jsonl"),
) -> dict[str, Any]:
    if limit < 1:
        raise RealDataError("--limit must be positive")
    if not repos:
        raise RealDataError("at least one repo is required")

    queue_path.parent.mkdir(parents=True, exist_ok=True)
    if not labels_path.exists():
        labels_path.write_text("", encoding="utf-8")

    candidates: dict[str, dict[str, Any]] = {}
    search_plan = [
        ("conflicting", CONFLICTING_KEYWORDS),
        ("stale", STALE_KEYWORDS),
        ("unknown", UNKNOWN_HIGH_RISK_KEYWORDS),
    ]
    per_query = min(3, limit)
    for repo in repos:
        for suspected_from, keywords in search_plan:
            for keyword in keywords[:3]:
                if len(candidates) >= limit:
                    break
                for item in _search_prs(repo, keyword, per_page=per_query):
                    if len(candidates) >= limit:
                        break
                    candidate = _candidate_from_search_item(repo, item, suspected_from=suspected_from)
                    if candidate is not None:
                        candidates.setdefault(candidate["candidate_id"], candidate)
                if len(candidates) >= limit:
                    break
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break

    rows = list(candidates.values())
    write_jsonl(queue_path, rows)
    counts = dict(sorted(Counter(row["suspected_status"] for row in rows).items()))
    scored_counts: dict[str, int] = {}
    if dataset_path.exists():
        scored_counts = dict(sorted(Counter(case.evidence_status.value for case in load_cases(dataset_path) if case.is_scored_real_case).items()))
    insufficient_path = write_data_insufficient(queue_path=queue_path, candidate_counts=counts, scored_counts=scored_counts)
    blocked_path = Path("docs/DATA_BLOCKED.md")
    if blocked_path.exists():
        blocked_path.unlink()
    return {
        "queue_path": queue_path.as_posix(),
        "manual_labels_path": labels_path.as_posix(),
        "candidates": len(rows),
        "candidate_status_distribution": counts,
        "data_insufficient_path": insufficient_path.as_posix(),
        "used_fallback_data": False,
        "used_synthetic_data": False,
    }


def summarize_review_queue(input_path: Path) -> dict[str, Any]:
    rows = read_jsonl(input_path)
    return {
        "queue_path": input_path.as_posix(),
        "num_candidates": len(rows),
        "suspected_status_distribution": dict(sorted(Counter(row.get("suspected_status", "unknown") for row in rows).items())),
        "candidate_ids": [row.get("candidate_id") for row in rows[:10]],
    }


def _case_from_manual_label(row: dict[str, Any]) -> EvalCase:
    if "case" in row:
        return EvalCase.from_dict(row["case"])
    return EvalCase.from_dict(row)


def _parse_candidate(candidate_id: str) -> tuple[str, int]:
    match = CANDIDATE_ID_RE.match(candidate_id)
    if not match:
        raise RealDataError(f"cannot parse hard candidate id: {candidate_id}")
    return match.group("repo").replace("__", "/"), int(match.group("number"))


def _evidence_source_key(url: str) -> str:
    root_match = re.match(r"^https://github\.com/([^/]+/[^/]+)/(pull|issues)/(\d+)/?$", url)
    if root_match:
        return f"github:{root_match.group(1)}:discussion:{root_match.group(3)}:root"
    return url


def _is_concrete_github_url(url: str) -> bool:
    if not url.startswith("https://github.com/"):
        return False
    return any(marker in url for marker in ["/pull/", "/issues/", "/commit/", "#issuecomment-", "#discussion_r", "#pullrequestreview-"])


def _validate_accepted_label(row: dict[str, Any], accepted_sources: set[str]) -> None:
    cid = str(row.get("candidate_id") or row.get("case_id") or "unknown")
    source = str(row.get("label_source") or "")
    action = str(row.get("action") or "")
    status = str(row.get("evidence_status") or "")
    decision = str(row.get("expected_decision") or "")
    urls = [str(url) for url in row.get("evidence_urls") or [] if str(url)]
    if source not in accepted_sources:
        raise RealDataError(f"{cid}: label_source={source} is not accepted; accepted={sorted(accepted_sources)}")
    if source in CODEX_AUDIT_SOURCES:
        raise RealDataError(f"{cid}: raw Codex audit labels cannot be promoted directly")
    if source == "human_accepted_codex_audit" and row.get("audit_source") != "codex_evidence_audit_semantic_v2":
        raise RealDataError(f"{cid}: human_accepted_codex_audit requires audit_source=codex_evidence_audit_semantic_v2")
    if action != "promote":
        raise RealDataError(f"{cid}: only action=promote labels can be promoted")
    if status not in HARD_EVIDENCE_STATUSES:
        raise RealDataError(f"{cid}: promoted hard label must be unknown, conflicting, or stale")
    if float(row.get("label_confidence") or 0.0) < 0.7:
        raise RealDataError(f"{cid}: label_confidence must be >= 0.7")
    if not urls or not all(_is_concrete_github_url(url) for url in urls):
        raise RealDataError(f"{cid}: promoted label requires concrete GitHub evidence URLs")
    if status == "unknown" and decision != "verify_first":
        raise RealDataError(f"{cid}: unknown labels require expected_decision=verify_first")
    if status == "conflicting":
        if decision != "detect_conflict":
            raise RealDataError(f"{cid}: conflicting labels require expected_decision=detect_conflict")
        if len({_evidence_source_key(url) for url in urls}) < 2:
            raise RealDataError(f"{cid}: conflicting labels require at least 2 distinct evidence URLs")
    if status == "stale":
        rationale = str(row.get("rationale") or "").lower()
        if len({_evidence_source_key(url) for url in urls}) < 2:
            raise RealDataError(f"{cid}: stale labels require at least 2 distinct evidence URLs")
        if not all(term in rationale for term in ["older", "newer", "time ordering"]):
            raise RealDataError(f"{cid}: stale rationale must mention older/newer/time ordering")


def _evidence_type(url: str) -> str:
    if "/commit/" in url:
        return "commit"
    if "#discussion_r" in url:
        return "review_comment"
    if "#pullrequestreview-" in url:
        return "review"
    if "#issuecomment-" in url:
        return "comment"
    if "/issues/" in url:
        return "issue"
    if "/pull/" in url:
        return "pr"
    return "github"


def _case_from_accepted_audit_label(row: dict[str, Any]) -> EvalCase:
    cid = str(row["candidate_id"])
    repo, number = _parse_candidate(cid)
    pr_url = next((str(url) for url in row.get("evidence_urls", []) if f"/pull/{number}" in str(url)), f"https://github.com/{repo}/pull/{number}")
    issue_url = next((str(url) for url in row.get("evidence_urls", []) if "/issues/" in str(url)), None)
    evidence_summaries = [str(item) for item in row.get("evidence_summary") or []]
    evidence_items = []
    for index, url in enumerate([str(item) for item in row.get("evidence_urls") or [] if str(item)], start=1):
        excerpt = evidence_summaries[index - 1] if index <= len(evidence_summaries) else str(row.get("rationale") or "")
        evidence_items.append(
            {
                "evidence_id": f"{cid}:accepted:evidence:{index}",
                "evidence_type": _evidence_type(url),
                "evidence_text_excerpt": _excerpt(excerpt, max_chars=420),
                "evidence_url": url,
                "file_path": None,
                "commit_sha": None,
                "timestamp": row.get("reviewed_at"),
                "supports_or_contradicts": "contradicts" if row.get("evidence_status") == "conflicting" and index == 2 else "supports",
                "provenance_hash": stable_hash_text(f"{cid}|{index}|{url}|{excerpt}"),
            }
        )
    status = str(row["evidence_status"])
    if status == "conflicting":
        claim_text = f"Human accepted Codex semantic audit found unresolved conflicting GitHub evidence for {repo} PR #{number}."
    elif status == "stale":
        claim_text = f"Human accepted Codex semantic audit found older GitHub evidence superseded by newer evidence for {repo} PR #{number}."
    else:
        claim_text = f"Human accepted Codex semantic audit found high-risk unknown evidence that requires verification for {repo} PR #{number}."
    return EvalCase.from_dict(
        {
            "case_id": cid,
            "source_dataset": "github_api_hard_semantic_v2",
            "source_url": pr_url,
            "repo": repo,
            "repo_url": f"https://github.com/{repo}",
            "issue_url": issue_url,
            "pr_url": pr_url,
            "base_commit": None,
            "head_commit": None,
            "commit_sha": None,
            "created_at": row.get("reviewed_at") or row.get("accepted_at"),
            "files_changed": [],
            "diff_summary": f"Human accepted semantic audit promoted {status} hard label for {repo} PR #{number}.",
            "problem_statement": str(row.get("rationale") or ""),
            "claim": {
                "claim_id": f"{cid}:claim",
                "claim_text": claim_text,
                "validity_condition": "Applies to future changes whose behavior depends on the accepted hard-case GitHub evidence.",
                "claim_source": "human_accepted_codex_audit",
                "claim_source_url": pr_url,
            },
            "evidence_items": evidence_items,
            "evidence_status": status,
            "expected_decision": row["expected_decision"],
            "label_source": row["label_source"],
            "label_confidence": row["label_confidence"],
            "rationale": row.get("rationale") or "",
            "is_real": True,
            "is_synthetic": False,
            "excluded_from_real_metrics": False,
            "exclusion_reason": None,
        }
    )


def write_accepted_labels(
    labels_path: Path,
    output_path: Path,
    accepted_by: str = "Chloiris",
    source: str = "codex_evidence_audit_semantic_v2",
) -> dict[str, Any]:
    rows = read_jsonl(labels_path)
    accepted_at = datetime.now(timezone.utc).isoformat()
    accepted: list[dict[str, Any]] = []
    for row in rows:
        if row.get("action") != "promote":
            continue
        if row.get("label_source") != source:
            raise RealDataError(f"{row.get('candidate_id', 'unknown')}: expected label_source={source}")
        accepted.append(
            {
                "action": "promote",
                "candidate_id": row["candidate_id"],
                "evidence_status": row["evidence_status"],
                "expected_decision": row["expected_decision"],
                "label_source": "human_accepted_codex_audit",
                "label_confidence": row["label_confidence"],
                "rationale": _sanitize_public_text(row["rationale"]),
                "evidence_urls": row.get("evidence_urls", []),
                "evidence_summary": [_sanitize_public_text(item) for item in row.get("evidence_summary", [])],
                "missing_evidence": [_sanitize_public_text(item) for item in row.get("missing_evidence", [])],
                "reviewed_by": row.get("reviewed_by"),
                "reviewed_at": row.get("reviewed_at"),
                "human_final_check": True,
                "accepted_by": accepted_by,
                "accepted_at": accepted_at,
                "audit_source": source,
            }
        )
    write_jsonl(output_path, accepted)
    return {
        "input_path": labels_path.as_posix(),
        "output_path": output_path.as_posix(),
        "accepted_labels_count": len(accepted),
        "accepted_by": accepted_by,
        "audit_source": source,
    }


def promote_manual_labels(
    labels_path: Path,
    output_path: Path,
    dataset_path: Path | None = None,
    accepted_sources: set[str] | None = None,
) -> dict[str, Any]:
    accepted = accepted_sources or {"manual_verified"}
    labels = read_jsonl(labels_path)
    input_dataset = dataset_path or output_path
    existing = load_cases(input_dataset) if input_dataset.exists() else []
    by_id = {case.case_id: case for case in existing}
    promoted = 0
    for row in labels:
        raw_source = row.get("label_source")
        if raw_source == "human_accepted_codex_audit":
            _validate_accepted_label(row, accepted)
            case = _case_from_accepted_audit_label(row)
        else:
            if raw_source is not None and raw_source not in accepted:
                raise RealDataError(
                    f"{row.get('candidate_id', row.get('case_id', 'unknown'))}: "
                    f"promote-labels only accepts label_source in {sorted(accepted)}"
                )
            case = _case_from_manual_label(row)
            if case.label_source not in accepted:
                raise RealDataError(f"{case.case_id}: promote-labels only accepts label_source in {sorted(accepted)}")
            if case.label_source in CODEX_AUDIT_SOURCES:
                raise RealDataError(f"{case.case_id}: raw Codex audit labels cannot be promoted directly")
        by_id[case.case_id] = case
        promoted += 1
    cases = list(by_id.values())
    write_cases(output_path, cases)
    manifest = build_dataset_manifest(output_path)
    return {
        "labels_read": len(labels),
        "promoted_cases": promoted,
        "output_path": output_path.as_posix(),
        "num_cases_scored": manifest["num_cases_scored"],
        "status_distribution": manifest["status_distribution"],
    }
