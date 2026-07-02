from __future__ import annotations

import json
import os
import time
import http.client
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tracegate.core.serialization import sha256_file, write_json
from tracegate.data.sources.base import FetchResult, RealDataError


GITHUB_API_BASE = "https://api.github.com"
DEFAULT_REPOSITORIES = [
    "pallets/flask",
    "psf/requests",
    "pytest-dev/pytest",
    "pydantic/pydantic",
    "tiangolo/fastapi",
]
_GH_AUTH_TOKEN: str | None = None


def gh_auth_token() -> str | None:
    global _GH_AUTH_TOKEN
    if _GH_AUTH_TOKEN is not None:
        return _GH_AUTH_TOKEN
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        _GH_AUTH_TOKEN = ""
        return None
    _GH_AUTH_TOKEN = result.stdout.strip()
    return _GH_AUTH_TOKEN or None


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "tracegate-real-data-mvp",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or gh_auth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(url: str, attempts: int = 3) -> Any:
    request = urllib.request.Request(url, headers=github_headers())
    last_error: urllib.error.URLError | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RealDataError(f"GitHub API HTTP {exc.code} for {url}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, http.client.RemoteDisconnected) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(1.0 * attempt)
                continue
    assert last_error is not None
    reason = getattr(last_error, "reason", str(last_error))
    raise RealDataError(f"GitHub API request failed for {url}: {reason}") from last_error


def list_closed_pull_requests(repo: str, per_page: int = 12) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "state": "closed",
            "per_page": str(per_page),
            "sort": "updated",
            "direction": "desc",
        }
    )
    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls?{query}"
    data = get_json(url)
    if not isinstance(data, list):
        raise RealDataError(f"unexpected GitHub PR list response for {repo}")
    return data


def list_pull_request_files(repo: str, number: int) -> list[dict[str, Any]]:
    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}/files?per_page=100"
    data = get_json(url)
    if not isinstance(data, list):
        raise RealDataError(f"unexpected GitHub PR files response for {repo}#{number}")
    return data


def fetch_github_pull_requests(raw_dir: Path, limit: int) -> FetchResult:
    if limit < 1:
        raise RealDataError("--limit must be positive")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "github_prs.jsonl"
    fetched_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    for repo in DEFAULT_REPOSITORIES:
        if len(records) >= limit:
            break
        pulls = list_closed_pull_requests(repo, per_page=max(limit, 12))
        for pr in pulls:
            if len(records) >= limit:
                break
            if not pr.get("merged_at"):
                continue
            number = int(pr["number"])
            files = list_pull_request_files(repo, number)
            if not files:
                continue
            records.append(
                {
                    "source": "github_api",
                    "repo": repo,
                    "fetched_at": fetched_at,
                    "pull_request": pr,
                    "files": files,
                    "api_urls": {
                        "pulls": f"{GITHUB_API_BASE}/repos/{repo}/pulls",
                        "files": f"{GITHUB_API_BASE}/repos/{repo}/pulls/{number}/files",
                    },
                }
            )

    if len(records) < limit:
        raise RealDataError(
            f"GitHub API returned {len(records)} merged PR records with file provenance; requested {limit}. "
            "No fallback data was created."
        )

    with raw_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    raw_manifest_path = raw_dir / "raw_manifest.json"
    write_json(
        raw_manifest_path,
        {
            "source": "github_api",
            "records_written": len(records),
            "raw_path": str(raw_path.as_posix()),
            "raw_sha256": sha256_file(raw_path),
            "repositories": DEFAULT_REPOSITORIES,
            "fetched_at": fetched_at,
            "used_github_token": bool(os.environ.get("GITHUB_TOKEN")),
            "is_real": True,
            "is_synthetic": False,
            "used_fallback_data": False,
        },
    )
    return FetchResult(
        source="github_api",
        raw_path=raw_path,
        raw_manifest_path=raw_manifest_path,
        records_written=len(records),
    )
