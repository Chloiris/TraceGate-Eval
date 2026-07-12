from __future__ import annotations

import json

import httpx
import pytest

from tracegate.github import GitHubAPIError, GitHubNotModified, GitHubProvider


def pull_payload() -> dict[str, object]:
    return {
        "number": 42,
        "title": "Real parser change",
        "state": "open",
        "html_url": "https://github.com/acme/widget/pull/42",
        "draft": False,
        "updated_at": "2026-07-10T07:00:00Z",
        "created_at": "2026-07-09T07:00:00Z",
        "merged_at": None,
        "closed_at": None,
        "additions": 12,
        "deletions": 3,
        "changed_files": 2,
        "user": {"login": "octocat"},
        "base": {"sha": "a" * 40, "ref": "main"},
        "head": {"sha": "b" * 40, "ref": "feature/parser"},
    }


@pytest.mark.asyncio
async def test_provider_sends_etag_and_parses_rate_limit() -> None:
    seen_headers: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(
            200,
            headers={
                "etag": '"new-etag"',
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "4999",
                "content-type": "application/json",
            },
            content=json.dumps([pull_payload()]).encode(),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.test")
    provider = GitHubProvider(client=client)
    try:
        items, etag, rate_limit = await provider.list_pull_requests(
            "acme", "widget", etag='"old-etag"'
        )
    finally:
        await client.aclose()

    assert seen_headers["if-none-match"] == '"old-etag"'
    assert items[0].head_sha == "b" * 40
    assert items[0].author == "octocat"
    assert items[0].base_ref == "main"
    assert items[0].head_ref == "feature/parser"
    assert etag == '"new-etag"'
    assert rate_limit.remaining == 4999
    assert provider.request_count == 1
    assert provider.total_latency_ms >= 0
    assert provider.last_latency_ms is not None


@pytest.mark.asyncio
async def test_provider_surfaces_not_modified_without_cached_fallback() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(304, headers={"etag": '"same"', "x-ratelimit-remaining": "12"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.test")
    provider = GitHubProvider(client=client)
    try:
        with pytest.raises(GitHubNotModified) as caught:
            await provider.list_pull_requests("acme", "widget", etag='"same"')
    finally:
        await client.aclose()
    assert caught.value.etag == '"same"'
    assert caught.value.rate_limit.remaining == 12


@pytest.mark.asyncio
async def test_provider_reports_rate_limit_and_never_returns_fake_items() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1783699200"}, json={"message": "rate limit"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.test")
    provider = GitHubProvider(client=client)
    try:
        with pytest.raises(GitHubAPIError) as caught:
            await provider.list_pull_requests("acme", "widget")
    finally:
        await client.aclose()
    assert caught.value.status_code == 429
    assert caught.value.reset_at is not None


@pytest.mark.asyncio
async def test_provider_lists_and_reads_repository_metadata() -> None:
    repository = {
        "id": 42,
        "full_name": "acme/widget",
        "html_url": "https://github.com/acme/widget",
        "clone_url": "https://github.com/acme/widget.git",
        "default_branch": "main",
        "private": False,
        "archived": False,
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/user/repos":
            return httpx.Response(200, json=[repository])
        if request.url.path == "/repos/acme/widget":
            return httpx.Response(200, json=repository)
        return httpx.Response(404, json={"message": "not found"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.test")
    provider = GitHubProvider(client=client)
    try:
        listed = await provider.list_repositories()
        detail = await provider.get_repository("acme", "widget")
    finally:
        await client.aclose()
    assert listed[0].full_name == "acme/widget"
    assert detail.default_branch == "main"
    assert detail.owner == "acme"
    assert detail.name == "widget"


@pytest.mark.asyncio
async def test_provider_fetches_check_runs_with_etag_and_validates_commit_ref() -> None:
    seen_headers: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        return httpx.Response(
            200,
            headers={"etag": '"checks-new"', "x-ratelimit-remaining": "41"},
            json={
                "check_runs": [
                    {
                        "id": 123,
                        "head_sha": "b" * 40,
                        "name": "unit tests",
                        "status": "completed",
                        "conclusion": "success",
                        "details_url": "https://github.com/acme/widget/actions/runs/123",
                        "app": {"name": "GitHub Actions"},
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.github.test")
    provider = GitHubProvider(client=client)
    try:
        runs, etag, rate = await provider.get_check_runs_page(
            "acme", "widget", "b" * 40, etag='"checks-old"'
        )
        with pytest.raises(ValueError, match="commit SHA"):
            await provider.get_check_runs_page("acme", "widget", "main")
    finally:
        await client.aclose()

    assert seen_headers["if-none-match"] == '"checks-old"'
    assert runs[0].app_name == "GitHub Actions"
    assert etag == '"checks-new"'
    assert rate.remaining == 41
