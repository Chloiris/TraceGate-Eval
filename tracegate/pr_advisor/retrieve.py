from __future__ import annotations

import base64
import json
import re
import subprocess
import urllib.parse
from typing import Any

from .collect import GitHubCollectionError, PullRequestSnapshot, collect_pull_request
from .evidence_packet import EvidenceItem, EvidencePacket, detect_risk_areas, sanitize_text, stable_id


TEXT_FILE_SUFFIXES = {".md", ".rst", ".txt", ".py", ".yml", ".yaml", ".toml", ".json"}
DOC_HINTS = ("readme", "changelog", "changes", "release", "docs/", "doc/", "test", "tests")
CLAIM_HINT_RE = re.compile(
    r"\b(compat|regression|security|auth|token|permission|migration|public api|breaking|"
    r"serialization|payment|refund|cache|concurrency|deprecated|legacy)\b",
    re.IGNORECASE,
)


def _run_gh_json(args: list[str], *, timeout_seconds: int = 120) -> Any:
    completed = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise GitHubCollectionError(f"gh {' '.join(args[:3])} failed: {detail[:800]}")
    text = completed.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GitHubCollectionError(f"gh returned invalid JSON for {' '.join(args[:3])}") from exc


def _repo_api(repo: str, path: str) -> Any:
    return _run_gh_json(["api", f"repos/{repo}/{path}"])


def _add_evidence(
    evidence: list[EvidenceItem],
    *,
    source_type: str,
    snippet: object,
    url: str = "",
    file_path: str = "",
    commit_sha: str = "",
    timestamp: str = "",
    supports_or_contradicts: str = "unclear",
    relevance: float = 0.5,
) -> None:
    clean = sanitize_text(snippet)
    if not clean:
        return
    evidence.append(
        EvidenceItem(
            evidence_id=stable_id(source_type, url, file_path, commit_sha, timestamp, clean),
            source_type=source_type,
            url=url or "",
            file_path=file_path or "",
            commit_sha=commit_sha or "",
            timestamp=timestamp or "",
            snippet=clean,
            supports_or_contradicts=supports_or_contradicts,
            relevance=relevance,
        )
    )


def _label_names(view: dict[str, Any]) -> list[str]:
    labels = []
    for item in view.get("labels") or []:
        if isinstance(item, dict) and item.get("name"):
            labels.append(str(item["name"]))
        elif isinstance(item, str):
            labels.append(item)
    return labels


def _file_paths(snapshot: PullRequestSnapshot) -> list[str]:
    paths = list(snapshot.diff_file_names)
    for item in snapshot.files_api:
        filename = item.get("filename")
        if filename and filename not in paths:
            paths.append(str(filename))
    for item in snapshot.view.get("files") or []:
        path = item.get("path") or item.get("filename")
        if path and path not in paths:
            paths.append(str(path))
    return paths


def _summarize_patch(file_item: dict[str, Any], *, max_lines: int = 40) -> str:
    filename = file_item.get("filename") or ""
    status = file_item.get("status") or ""
    additions = file_item.get("additions")
    deletions = file_item.get("deletions")
    patch = str(file_item.get("patch") or "")
    patch_lines = [line for line in patch.splitlines() if line.startswith(("@@", "+", "-"))]
    patch_summary = "\n".join(patch_lines[:max_lines])
    return (
        f"{filename} status={status} additions={additions} deletions={deletions}\n"
        f"{patch_summary}"
    ).strip()


def _commit_sha(commit: dict[str, Any]) -> str:
    for key in ("oid", "sha", "commitSha"):
        value = commit.get(key)
        if value:
            return str(value)
    return ""


def _commit_url(repo: str, sha: str, commit: dict[str, Any]) -> str:
    if commit.get("url"):
        return str(commit["url"])
    if sha:
        return f"https://github.com/{repo}/commit/{sha}"
    return ""


def _extract_candidate_claims(view: dict[str, Any], evidence: list[EvidenceItem]) -> list[str]:
    candidates: list[str] = []
    for text in [view.get("title"), view.get("body"), *(item.snippet for item in evidence[:20])]:
        clean = sanitize_text(text, max_chars=500)
        if clean and CLAIM_HINT_RE.search(clean) and clean not in candidates:
            candidates.append(clean)
    return candidates[:8]


def _tokens_from_paths(paths: list[str], risk_areas: list[str]) -> list[str]:
    tokens: list[str] = []
    for path in paths:
        for part in re.split(r"[^A-Za-z0-9_]+", path):
            part = part.lower()
            if len(part) >= 4 and part not in tokens:
                tokens.append(part)
    for area in risk_areas:
        for part in area.lower().split():
            if part not in tokens:
                tokens.append(part)
    return tokens[:20]


def _collect_git_history(repo: str, changed_files: list[str], *, max_items: int = 20) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    per_file = max(1, min(3, max_items // max(1, len(changed_files[:8]))))
    for path in changed_files[:8]:
        quoted = urllib.parse.quote(path, safe="")
        try:
            commits = _repo_api(repo, f"commits?path={quoted}&per_page={per_file}") or []
        except GitHubCollectionError:
            continue
        for commit in commits[:per_file]:
            sha = str(commit.get("sha") or "")
            commit_data = commit.get("commit") or {}
            message = (commit_data.get("message") or "").splitlines()[0]
            timestamp = ((commit_data.get("author") or {}).get("date")) or ""
            _add_evidence(
                evidence,
                source_type="git_history",
                url=commit.get("html_url") or (f"https://github.com/{repo}/commit/{sha}" if sha else ""),
                file_path=path,
                commit_sha=sha,
                timestamp=timestamp,
                snippet=f"Recent history for {path}: {message}",
                relevance=0.45,
            )
            if len(evidence) >= max_items:
                return evidence
    return evidence


def _default_branch(repo: str) -> str:
    info = _repo_api(repo, "")
    if isinstance(info, dict) and info.get("default_branch"):
        return str(info["default_branch"])
    return "main"


def _fetch_content_text(repo: str, path: str, ref: str) -> str:
    encoded_path = urllib.parse.quote(path, safe="/")
    data = _repo_api(repo, f"contents/{encoded_path}?ref={urllib.parse.quote(ref, safe='')}")
    if not isinstance(data, dict) or data.get("encoding") != "base64":
        return ""
    raw = base64.b64decode(str(data.get("content") or ""), validate=False)
    return raw.decode("utf-8", errors="replace")


def _snippet_for_tokens(text: str, tokens: list[str], *, max_chars: int = 1000) -> str:
    lowered = text.lower()
    indexes = [lowered.find(token) for token in tokens if token and lowered.find(token) >= 0]
    start = max(0, min(indexes) - 300) if indexes else 0
    return text[start : start + max_chars]


def _collect_repo_text_snippets(
    repo: str,
    changed_files: list[str],
    risk_areas: list[str],
    *,
    max_items: int = 8,
) -> list[EvidenceItem]:
    try:
        branch = _default_branch(repo)
        tree = _repo_api(repo, f"git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1")
    except GitHubCollectionError:
        return list()
    if not isinstance(tree, dict):
        return list()
    tokens = _tokens_from_paths(changed_files, risk_areas)
    scored_paths: list[tuple[int, str]] = []
    for item in tree.get("tree") or []:
        if item.get("type") != "blob":
            continue
        path = str(item.get("path") or "")
        lower = path.lower()
        if not any(lower.endswith(suffix) for suffix in TEXT_FILE_SUFFIXES):
            continue
        if not any(hint in lower for hint in DOC_HINTS):
            continue
        score = sum(1 for token in tokens if token in lower)
        if score or any(hint in lower for hint in ("readme", "changelog", "release")):
            scored_paths.append((score, path))
    evidence: list[EvidenceItem] = []
    for _, path in sorted(scored_paths, key=lambda item: (-item[0], item[1]))[:max_items]:
        try:
            content = _fetch_content_text(repo, path, branch)
        except GitHubCollectionError:
            continue
        snippet = _snippet_for_tokens(content, tokens)
        _add_evidence(
            evidence,
            source_type="doc" if "test" not in path.lower() else "test",
            url=f"https://github.com/{repo}/blob/{branch}/{path}",
            file_path=path,
            snippet=snippet,
            relevance=0.35,
        )
    return evidence


def build_evidence_packet(repo: str, pr_number: int) -> EvidencePacket:
    snapshot = collect_pull_request(repo, pr_number)
    view = snapshot.view
    changed_files = _file_paths(snapshot)
    joined_context = " ".join(
        [
            str(view.get("title") or ""),
            str(view.get("body") or ""),
            " ".join(changed_files),
            " ".join(_label_names(view)),
        ]
    )
    risk_areas = detect_risk_areas(joined_context)
    evidence: list[EvidenceItem] = []
    pr_url = str(view.get("url") or f"https://github.com/{repo}/pull/{pr_number}")

    _add_evidence(
        evidence,
        source_type="pr_body",
        url=pr_url,
        timestamp=str(view.get("createdAt") or ""),
        snippet=f"PR title: {view.get('title')}\nPR body: {view.get('body')}",
        relevance=0.8,
    )

    for comment in snapshot.issue_comments:
        _add_evidence(
            evidence,
            source_type="comment",
            url=str(comment.get("html_url") or pr_url),
            timestamp=str(comment.get("created_at") or ""),
            snippet=comment.get("body"),
            relevance=0.7,
        )

    for review in snapshot.reviews_api:
        body = review.get("body") or review.get("state")
        _add_evidence(
            evidence,
            source_type="review",
            url=str(review.get("html_url") or pr_url),
            commit_sha=str(review.get("commit_id") or ""),
            timestamp=str(review.get("submitted_at") or ""),
            snippet=body,
            relevance=0.65,
        )

    for comment in snapshot.review_comments:
        body = comment.get("body")
        diff_hunk = comment.get("diff_hunk")
        _add_evidence(
            evidence,
            source_type="review_comment",
            url=str(comment.get("html_url") or pr_url),
            file_path=str(comment.get("path") or ""),
            commit_sha=str(comment.get("commit_id") or ""),
            timestamp=str(comment.get("created_at") or ""),
            snippet=f"{body}\nDiff hunk:\n{diff_hunk}",
            relevance=0.75,
        )

    for commit in view.get("commits") or []:
        sha = _commit_sha(commit)
        message = commit.get("messageHeadline") or commit.get("message") or ""
        _add_evidence(
            evidence,
            source_type="commit",
            url=_commit_url(repo, sha, commit),
            commit_sha=sha,
            timestamp=str(commit.get("authoredDate") or commit.get("committedDate") or ""),
            snippet=message,
            relevance=0.55,
        )

    for file_item in snapshot.files_api:
        _add_evidence(
            evidence,
            source_type="file",
            url=str(file_item.get("blob_url") or file_item.get("raw_url") or pr_url),
            file_path=str(file_item.get("filename") or ""),
            snippet=_summarize_patch(file_item),
            relevance=0.8,
        )

    for related in snapshot.related_refs:
        issue = related.get("issue") or {}
        if issue:
            number = related.get("number")
            _add_evidence(
                evidence,
                source_type="issue",
                url=str(issue.get("html_url") or f"https://github.com/{repo}/issues/{number}"),
                timestamp=str(issue.get("created_at") or ""),
                snippet=f"{issue.get('title')}\n{issue.get('body')}",
                relevance=0.6,
            )
        for comment in related.get("comments") or []:
            _add_evidence(
                evidence,
                source_type="comment",
                url=str(comment.get("html_url") or ""),
                timestamp=str(comment.get("created_at") or ""),
                snippet=comment.get("body"),
                relevance=0.55,
            )

    evidence.extend(_collect_git_history(repo, changed_files))
    evidence.extend(_collect_repo_text_snippets(repo, changed_files, risk_areas))

    candidate_claims = _extract_candidate_claims(view, evidence)
    missing_evidence = []
    if risk_areas:
        missing_evidence.append(
            "High-risk touched paths require explicit public evidence before safe merge advice."
        )
    if not snapshot.review_comments and not snapshot.reviews_api:
        missing_evidence.append("No review or review-comment evidence was available from the PR APIs.")
    if not snapshot.related_refs:
        missing_evidence.append("No linked issue or referenced PR context was expanded.")

    retrieval_limits = [
        "related #issue/#PR references expanded to at most 5",
        "pull request files API limited to first page of 100 files",
        "diff hunk snippets truncated per file",
        "touched-file GitHub commit history limited to 20 total items",
        "repo docs/tests/changelog snippets limited to 8 files",
    ]
    return EvidencePacket(
        repo=repo,
        pr_number=pr_number,
        pr_url=pr_url,
        title=str(view.get("title") or ""),
        changed_files=changed_files,
        risk_areas=risk_areas,
        candidate_claims=candidate_claims,
        evidence_items=evidence,
        missing_evidence=missing_evidence,
        retrieval_limits=retrieval_limits,
    )
