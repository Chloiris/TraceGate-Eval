from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator


_REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class GitHubAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, *, reset_at: datetime | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.reset_at = reset_at


class GitHubNotModified(Exception):
    def __init__(self, etag: str | None, rate_limit: "GitHubRateLimit") -> None:
        super().__init__("GitHub resource was not modified")
        self.etag = etag
        self.rate_limit = rate_limit


@dataclass(frozen=True)
class GitHubRateLimit:
    limit: int | None
    remaining: int | None
    reset_at: datetime | None


@dataclass(frozen=True)
class GitHubPage:
    items: list[dict[str, Any]]
    etag: str | None
    rate_limit: GitHubRateLimit


class PullRequestData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    number: int = Field(ge=1)
    title: str
    state: str
    html_url: str
    draft: bool = False
    updated_at: datetime
    created_at: datetime
    merged_at: datetime | None = None
    closed_at: datetime | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    user: dict[str, Any]
    base: dict[str, Any]
    head: dict[str, Any]

    @property
    def author(self) -> str | None:
        value = self.user.get("login")
        return value if isinstance(value, str) else None

    @property
    def base_sha(self) -> str:
        value = self.base.get("sha")
        if not isinstance(value, str) or not value:
            raise ValueError("GitHub Pull Request response is missing base.sha")
        return value

    @property
    def base_ref(self) -> str | None:
        value = self.base.get("ref")
        return value if isinstance(value, str) and value else None

    @property
    def head_sha(self) -> str:
        value = self.head.get("sha")
        if not isinstance(value, str) or not value:
            raise ValueError("GitHub Pull Request response is missing head.sha")
        return value

    @property
    def head_ref(self) -> str | None:
        value = self.head.get("ref")
        return value if isinstance(value, str) and value else None


class CheckRunData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(ge=1)
    head_sha: str = Field(min_length=7, max_length=64)
    name: str = Field(min_length=1, max_length=500)
    status: str = Field(min_length=1, max_length=32)
    conclusion: str | None = Field(default=None, max_length=64)
    details_url: str | None = Field(default=None, max_length=2048)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    app: dict[str, Any] | None = None

    @property
    def app_name(self) -> str | None:
        value = self.app.get("name") if self.app else None
        return value if isinstance(value, str) else None


class RepositoryData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int = Field(ge=1)
    full_name: str = Field(min_length=3, max_length=201)
    html_url: str = Field(min_length=1, max_length=2048)
    clone_url: str = Field(min_length=1, max_length=2048)
    default_branch: str = Field(min_length=1, max_length=255)
    private: bool
    archived: bool = False

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        parts = value.split("/", 1)
        if len(parts) != 2 or not all(_REPOSITORY_PART.fullmatch(part) for part in parts):
            raise ValueError("GitHub repository full_name is invalid")
        return value

    @property
    def owner(self) -> str:
        return self.full_name.split("/", 1)[0]

    @property
    def name(self) -> str:
        return self.full_name.split("/", 1)[1]


class ChangedFileData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str = Field(min_length=7, max_length=64)
    filename: str = Field(min_length=1, max_length=2048)
    status: str = Field(min_length=1, max_length=32)
    additions: int = Field(default=0, ge=0)
    deletions: int = Field(default=0, ge=0)
    changes: int = Field(default=0, ge=0)
    blob_url: str | None = Field(default=None, max_length=2048)
    raw_url: str | None = Field(default=None, max_length=2048)
    contents_url: str | None = Field(default=None, max_length=2048)
    patch: str | None = Field(default=None, max_length=2 * 1024 * 1024)
    previous_filename: str | None = Field(default=None, max_length=2048)


class CommitData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sha: str = Field(min_length=7, max_length=64)
    html_url: str | None = Field(default=None, max_length=2048)
    commit: dict[str, Any]
    author: dict[str, Any] | None = None

    @property
    def message(self) -> str:
        value = self.commit.get("message")
        return value if isinstance(value, str) else ""

    @property
    def author_name(self) -> str | None:
        author = self.commit.get("author")
        value = author.get("name") if isinstance(author, dict) else None
        return value if isinstance(value, str) else None

    @property
    def author_email(self) -> str | None:
        author = self.commit.get("author")
        value = author.get("email") if isinstance(author, dict) else None
        return value if isinstance(value, str) else None

    @property
    def authored_at(self) -> datetime | None:
        author = self.commit.get("author")
        value = author.get("date") if isinstance(author, dict) else None
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @property
    def login(self) -> str | None:
        value = self.author.get("login") if self.author else None
        return value if isinstance(value, str) else None


class GitHubProvider:
    """Bounded GitHub REST client with explicit ETag and rate-limit state."""

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = "https://api.github.com",
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._owns_client = client is None
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "TraceGate-Studio/0.1",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
        )
        self.request_count = 0
        self.total_latency_ms = 0
        self.last_latency_ms: int | None = None

    async def __aenter__(self) -> "GitHubProvider":
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.close()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def list_pull_requests(
        self,
        owner: str,
        repository: str,
        *,
        state: str = "all",
        etag: str | None = None,
        per_page: int = 50,
    ) -> tuple[list[PullRequestData], str | None, GitHubRateLimit]:
        self._validate_repository(owner, repository)
        if state not in {"open", "closed", "all"}:
            raise ValueError("Pull Request state must be open, closed, or all")
        page = await self._get_json_list(
            f"/repos/{owner}/{repository}/pulls",
            params={"state": state, "sort": "updated", "direction": "desc", "per_page": min(per_page, 100)},
            etag=etag,
        )
        return [PullRequestData.model_validate(item) for item in page.items], page.etag, page.rate_limit

    async def get_pull_request(self, owner: str, repository: str, number: int) -> PullRequestData:
        payload, _etag, _rate = await self._get_json_object(
            self._pull_path(owner, repository, number)
        )
        return PullRequestData.model_validate(payload)

    async def list_repositories(self, *, per_page: int = 100) -> list[RepositoryData]:
        page = await self._get_json_list(
            "/user/repos",
            params={
                "affiliation": "owner,collaborator,organization_member",
                "sort": "updated",
                "per_page": min(max(per_page, 1), 100),
            },
        )
        return [RepositoryData.model_validate(item) for item in page.items]

    async def get_repository(self, owner: str, repository: str) -> RepositoryData:
        self._validate_repository(owner, repository)
        payload, _etag, _rate = await self._get_json_object(f"/repos/{owner}/{repository}")
        parsed = RepositoryData.model_validate(payload)
        if parsed.owner != owner or parsed.name != repository:
            raise GitHubAPIError(502, "GitHub repository response identity does not match the request")
        return parsed

    async def test_authenticated_connection(self) -> tuple[str, GitHubRateLimit]:
        payload, _etag, rate_limit = await self._get_json_object("/user")
        login = payload.get("login")
        if not isinstance(login, str) or not login:
            raise GitHubAPIError(502, "GitHub authenticated user response is malformed")
        return login, rate_limit

    async def get_pull_request_files(self, owner: str, repository: str, number: int) -> list[dict[str, Any]]:
        return (await self._get_json_list(f"{self._pull_path(owner, repository, number)}/files")).items

    async def get_pull_request_files_data(
        self, owner: str, repository: str, number: int
    ) -> list[ChangedFileData]:
        return [
            ChangedFileData.model_validate(item)
            for item in await self.get_pull_request_files(owner, repository, number)
        ]

    async def get_pull_request_commits(self, owner: str, repository: str, number: int) -> list[dict[str, Any]]:
        return (await self._get_json_list(f"{self._pull_path(owner, repository, number)}/commits")).items

    async def get_pull_request_commits_data(
        self, owner: str, repository: str, number: int
    ) -> list[CommitData]:
        return [
            CommitData.model_validate(item)
            for item in await self.get_pull_request_commits(owner, repository, number)
        ]

    async def get_review_comments(self, owner: str, repository: str, number: int) -> list[dict[str, Any]]:
        return (await self._get_json_list(f"{self._pull_path(owner, repository, number)}/comments")).items

    async def get_issue_comments(self, owner: str, repository: str, number: int) -> list[dict[str, Any]]:
        self._validate_repository(owner, repository)
        return (await self._get_json_list(f"/repos/{owner}/{repository}/issues/{number}/comments")).items

    async def get_check_runs(self, owner: str, repository: str, ref: str) -> list[dict[str, Any]]:
        runs, _etag, _rate_limit = await self.get_check_runs_page(owner, repository, ref)
        return [run.model_dump(mode="json") for run in runs]

    async def get_check_runs_page(
        self,
        owner: str,
        repository: str,
        ref: str,
        *,
        etag: str | None = None,
    ) -> tuple[list[CheckRunData], str | None, GitHubRateLimit]:
        self._validate_repository(owner, repository)
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", ref):
            raise ValueError("GitHub check run ref must be a commit SHA")
        payload, response_etag, rate_limit = await self._get_json_object(
            f"/repos/{owner}/{repository}/commits/{ref}/check-runs",
            etag=etag,
        )
        runs = payload.get("check_runs")
        if not isinstance(runs, list):
            raise GitHubAPIError(502, "GitHub check-runs response is malformed")
        return [CheckRunData.model_validate(item) for item in runs], response_etag, rate_limit

    async def _get_json_list(
        self,
        path: str,
        *,
        params: dict[str, object] | None = None,
        etag: str | None = None,
    ) -> GitHubPage:
        payload, response_etag, rate_limit = await self._request(path, params=params, etag=etag)
        if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
            raise GitHubAPIError(502, "GitHub response is not a list of objects")
        return GitHubPage(payload, response_etag, rate_limit)

    async def _get_json_object(
        self, path: str, *, etag: str | None = None
    ) -> tuple[dict[str, Any], str | None, GitHubRateLimit]:
        payload, response_etag, rate_limit = await self._request(path, etag=etag)
        if not isinstance(payload, dict):
            raise GitHubAPIError(502, "GitHub response is not an object")
        return payload, response_etag, rate_limit

    async def _request(
        self,
        path: str,
        *,
        params: dict[str, object] | None = None,
        etag: str | None = None,
    ) -> tuple[Any, str | None, GitHubRateLimit]:
        headers = {"If-None-Match": etag} if etag else None
        started = time.monotonic()
        try:
            response = await self._client.get(path, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise GitHubAPIError(503, f"GitHub request failed: {type(exc).__name__}") from exc
        finally:
            latency_ms = int((time.monotonic() - started) * 1000)
            self.request_count += 1
            self.total_latency_ms += latency_ms
            self.last_latency_ms = latency_ms
        rate_limit = self._rate_limit(response)
        response_etag = response.headers.get("etag")
        if response.status_code == 304:
            raise GitHubNotModified(response_etag or etag, rate_limit)
        if response.status_code == 403 and rate_limit.remaining == 0:
            raise GitHubAPIError(
                429,
                "GitHub API rate limit is exhausted",
                reset_at=rate_limit.reset_at,
            )
        if response.status_code >= 400:
            raise GitHubAPIError(response.status_code, f"GitHub API returned HTTP {response.status_code}")
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise GitHubAPIError(502, "GitHub response exceeded the configured size limit")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GitHubAPIError(502, "GitHub response is not valid JSON") from exc
        return payload, response_etag, rate_limit

    @staticmethod
    def _rate_limit(response: httpx.Response) -> GitHubRateLimit:
        def integer(name: str) -> int | None:
            value = response.headers.get(name)
            try:
                return int(value) if value is not None else None
            except ValueError:
                return None

        reset = integer("x-ratelimit-reset")
        return GitHubRateLimit(
            limit=integer("x-ratelimit-limit"),
            remaining=integer("x-ratelimit-remaining"),
            reset_at=datetime.fromtimestamp(reset).astimezone() if reset is not None else None,
        )

    @staticmethod
    def _validate_repository(owner: str, repository: str) -> None:
        if not _REPOSITORY_PART.fullmatch(owner) or not _REPOSITORY_PART.fullmatch(repository):
            raise ValueError("GitHub owner and repository names contain unsupported characters")

    def _pull_path(self, owner: str, repository: str, number: int) -> str:
        self._validate_repository(owner, repository)
        if number < 1:
            raise ValueError("Pull Request number must be positive")
        return f"/repos/{owner}/{repository}/pulls/{number}"
