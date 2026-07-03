from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any


PR_VIEW_FIELDS = (
    "title,body,url,state,createdAt,mergedAt,labels,comments,reviews,files,"
    "commits,closingIssuesReferences"
)
REFERENCE_RE = re.compile(r"(?<![\w/])#(\d+)\b")


class GitHubCollectionError(RuntimeError):
    """Raised when live GitHub evidence cannot be collected."""


@dataclass(frozen=True)
class PullRequestSnapshot:
    repo: str
    pr_number: int
    view: dict[str, Any]
    issue_comments: list[dict[str, Any]]
    review_comments: list[dict[str, Any]]
    reviews_api: list[dict[str, Any]]
    files_api: list[dict[str, Any]]
    diff_file_names: list[str]
    related_refs: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "view": self.view,
            "issue_comments": self.issue_comments,
            "review_comments": self.review_comments,
            "reviews_api": self.reviews_api,
            "files_api": self.files_api,
            "diff_file_names": self.diff_file_names,
            "related_refs": self.related_refs,
        }


def _run_gh(args: list[str], *, timeout_seconds: int = 120) -> str:
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
    return completed.stdout


def _run_gh_json(args: list[str], *, timeout_seconds: int = 120) -> Any:
    text = _run_gh(args, timeout_seconds=timeout_seconds).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GitHubCollectionError(f"gh returned invalid JSON for {' '.join(args[:3])}") from exc


def _api_json(repo: str, path: str) -> Any:
    return _run_gh_json(["api", f"repos/{repo}/{path}"])


def _extract_reference_numbers(view: dict[str, Any]) -> list[int]:
    texts: list[str] = []
    for key in ("title", "body"):
        value = view.get(key)
        if value:
            texts.append(str(value))
    for collection_name in ("comments", "reviews"):
        for item in view.get(collection_name) or []:
            body = item.get("body")
            if body:
                texts.append(str(body))
    numbers: list[int] = []
    for text in texts:
        for match in REFERENCE_RE.finditer(text):
            number = int(match.group(1))
            if number not in numbers:
                numbers.append(number)
    return numbers


def _collect_related_refs(repo: str, pr_number: int, view: dict[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    numbers = _extract_reference_numbers(view)
    for issue in view.get("closingIssuesReferences") or []:
        number = issue.get("number")
        if isinstance(number, int) and number not in numbers:
            numbers.append(number)

    related: list[dict[str, Any]] = []
    for number in [item for item in numbers if item != pr_number][:limit]:
        try:
            issue = _api_json(repo, f"issues/{number}")
            comments = _api_json(repo, f"issues/{number}/comments?per_page=20") or []
        except GitHubCollectionError as exc:
            related.append({"number": number, "error": str(exc)})
            continue
        related.append({"number": number, "issue": issue, "comments": comments})
    return related


def collect_pull_request(repo: str, pr_number: int) -> PullRequestSnapshot:
    view = _run_gh_json(
        ["pr", "view", str(pr_number), "-R", repo, "--json", PR_VIEW_FIELDS],
        timeout_seconds=120,
    )
    if not isinstance(view, dict):
        raise GitHubCollectionError("gh pr view did not return an object")

    issue_comments = _api_json(repo, f"issues/{pr_number}/comments?per_page=100") or []
    review_comments = _api_json(repo, f"pulls/{pr_number}/comments?per_page=100") or []
    reviews_api = _api_json(repo, f"pulls/{pr_number}/reviews?per_page=100") or []
    files_api = _api_json(repo, f"pulls/{pr_number}/files?per_page=100") or []

    diff_names_text = _run_gh(
        ["pr", "diff", str(pr_number), "-R", repo, "--name-only"],
        timeout_seconds=120,
    )
    diff_file_names = [line.strip() for line in diff_names_text.splitlines() if line.strip()]
    related_refs = _collect_related_refs(repo, pr_number, view)
    return PullRequestSnapshot(
        repo=repo,
        pr_number=pr_number,
        view=view,
        issue_comments=issue_comments,
        review_comments=review_comments,
        reviews_api=reviews_api,
        files_api=files_api,
        diff_file_names=diff_file_names,
        related_refs=related_refs,
    )
