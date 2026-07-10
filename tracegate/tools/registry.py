from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tracegate.repository import RepositoryBoundary, RepositoryPathError
from tracegate.vcs import GitCommandError, GitProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class PermissionLevel(StrEnum):
    SAFE_READ = "SAFE_READ"
    REPOSITORY_READ = "REPOSITORY_READ"
    COMMAND_RESTRICTED = "COMMAND_RESTRICTED"
    WRITE_CONFIRMATION = "WRITE_CONFIRMATION"
    NETWORK = "NETWORK"
    DESTRUCTIVE_FORBIDDEN = "DESTRUCTIVE_FORBIDDEN"


class ToolExecutionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ListDirectoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = "."
    limit: int = Field(default=200, ge=1, le=1000)


class ReadFileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    start_line: int = Field(default=1, ge=1)
    end_line: int = Field(default=400, ge=1, le=5000)


class SearchCodeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    path: str = "."
    max_results: int = Field(default=100, ge=1, le=500)


class GitDiffInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: str | None = None
    head: str | None = None


class GitLogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=50, ge=1, le=200)


class RunCommandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    argv: list[str] = Field(min_length=1, max_length=16)
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=300.0)


class SearchSymbolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=50, ge=1, le=200)


class SymbolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=1024)
    path: str | None = Field(default=None, max_length=2048)
    limit: int = Field(default=100, ge=1, le=500)


class DependencyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(min_length=1, max_length=256)
    depth: int = Field(default=1, ge=1, le=2)
    limit: int = Field(default=200, ge=1, le=800)


class RepositoryMapInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=800, ge=1, le=2000)


class RunTestsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str = Field(pattern="^(python|frontend|rust)$")
    timeout_seconds: float = Field(default=180.0, ge=1.0, le=300.0)


class ApplyPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patch: str = Field(min_length=1, max_length=1_000_000)
    confirmation_id: str = Field(min_length=16, max_length=256)


@dataclass(frozen=True)
class ToolContext:
    repository_id: str
    boundary: RepositoryBoundary
    caller_agent: str
    cancellation_event: asyncio.Event | None = None
    session_factory: Callable[[], "Session"] | None = None
    pull_request_id: str | None = None
    github_token: str | None = None
    write_enabled: bool = False
    patch_confirmation_id: str | None = None


@dataclass(frozen=True)
class ToolInvocation:
    name: str
    caller_agent: str
    permission: PermissionLevel
    started_at: float
    duration_ms: int
    succeeded: bool
    error_code: str | None


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    description: str
    permission: PermissionLevel
    timeout_seconds: float
    max_output_bytes: int
    input_schema: dict[str, Any]
    enabled: bool


InputT = TypeVar("InputT", bound=BaseModel)
Handler = Callable[[InputT, ToolContext], Any]


class _RegisteredTool(Generic[InputT]):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        permission: PermissionLevel,
        input_model: type[InputT],
        handler: Handler[InputT],
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> None:
        self.name = name
        self.description = description
        self.permission = permission
        self.input_model = input_model
        self.handler = handler
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def descriptor(self, *, enabled: bool) -> ToolDescriptor:
        return ToolDescriptor(
            name=self.name,
            description=self.description,
            permission=self.permission,
            timeout_seconds=self.timeout_seconds,
            max_output_bytes=self.max_output_bytes,
            input_schema=self.input_model.model_json_schema(),
            enabled=enabled,
        )


class ToolRegistry:
    def __init__(self, disabled_names: set[str] | None = None) -> None:
        self._tools: dict[str, _RegisteredTool[Any]] = {}
        self._disabled_names = disabled_names or set()
        self.invocations: list[ToolInvocation] = []

    def register(
        self,
        *,
        name: str,
        description: str,
        permission: PermissionLevel,
        input_model: type[InputT],
        handler: Handler[InputT],
        timeout_seconds: float = 20.0,
        max_output_bytes: int = 512 * 1024,
    ) -> None:
        if name in self._tools:
            raise ValueError(f"tool {name} is already registered")
        self._tools[name] = _RegisteredTool(
            name=name,
            description=description,
            permission=permission,
            input_model=input_model,
            handler=handler,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )

    def descriptors(self) -> list[ToolDescriptor]:
        return [
            self._tools[name].descriptor(enabled=name not in self._disabled_names)
            for name in sorted(self._tools)
        ]

    async def execute(self, name: str, payload: dict[str, Any], context: ToolContext) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError("tool_not_found", f"Tool {name} is not registered")
        if name in self._disabled_names:
            raise ToolExecutionError("tool_disabled", f"Tool {name} is disabled by the local Registry policy")
        if context.cancellation_event and context.cancellation_event.is_set():
            raise ToolExecutionError("cancelled", "Tool call was cancelled before execution")
        try:
            arguments = tool.input_model.model_validate(payload)
        except ValidationError as exc:
            raise ToolExecutionError("invalid_arguments", "Tool arguments failed schema validation") from exc

        started = time.monotonic()
        error_code: str | None = None
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(tool.handler, arguments, context),
                timeout=tool.timeout_seconds,
            )
            if len(str(result).encode("utf-8", errors="replace")) > tool.max_output_bytes:
                raise ToolExecutionError("output_limit", "Tool output exceeded its configured limit")
            return result
        except TimeoutError as exc:
            error_code = "timeout"
            raise ToolExecutionError("timeout", "Tool execution timed out") from exc
        except ToolExecutionError as exc:
            error_code = exc.code
            raise
        except (OSError, RepositoryPathError, GitCommandError) as exc:
            error_code = "execution_failed"
            raise ToolExecutionError("execution_failed", str(exc)) from exc
        except Exception as exc:
            error_code = "internal_error"
            raise ToolExecutionError("internal_error", "Tool execution failed unexpectedly") from exc
        finally:
            self.invocations.append(
                ToolInvocation(
                    name=name,
                    caller_agent=context.caller_agent,
                    permission=tool.permission,
                    started_at=started,
                    duration_ms=int((time.monotonic() - started) * 1000),
                    succeeded=error_code is None,
                    error_code=error_code,
                )
            )


def _list_directory(arguments: ListDirectoryInput, context: ToolContext) -> dict[str, Any]:
    directory = context.boundary.root if arguments.path == "." else context.boundary.resolve(arguments.path)
    if not directory.is_dir():
        raise ToolExecutionError("not_directory", "Requested path is not a directory")
    items = []
    for child in sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold())):
        relative = child.relative_to(context.boundary.root).as_posix()
        try:
            context.boundary.resolve(relative)
        except RepositoryPathError:
            continue
        items.append({"path": relative, "kind": "directory" if child.is_dir() else "file"})
        if len(items) >= arguments.limit:
            break
    return {"items": items, "truncated": len(items) == arguments.limit}


def _read_file(arguments: ReadFileInput, context: ToolContext) -> dict[str, Any]:
    if arguments.end_line < arguments.start_line:
        raise ToolExecutionError("invalid_line_range", "end_line must not precede start_line")
    path = context.boundary.resolve(arguments.path)
    if not path.is_file():
        raise ToolExecutionError("not_file", "Requested path is not a file")
    if path.stat().st_size > context.boundary.max_file_bytes:
        raise ToolExecutionError("file_too_large", "File exceeds the configured read limit")
    raw = path.read_bytes()
    if b"\0" in raw[:4096]:
        raise ToolExecutionError("binary_file", "Binary files are not readable through this tool")
    lines = raw.decode("utf-8", errors="replace").splitlines()
    selected = lines[arguments.start_line - 1 : arguments.end_line]
    return {
        "path": arguments.path,
        "start_line": arguments.start_line,
        "end_line": arguments.start_line + max(0, len(selected) - 1),
        "content": "\n".join(selected),
        "truncated": arguments.end_line < len(lines),
    }


def _search_code(arguments: SearchCodeInput, context: ToolContext) -> dict[str, Any]:
    search_root = context.boundary.root if arguments.path == "." else context.boundary.resolve(arguments.path)
    command = [
        "rg",
        "--json",
        "--fixed-strings",
        "--max-count",
        str(arguments.max_results),
        "--glob",
        "!.git/**",
        "--glob",
        "!node_modules/**",
        arguments.query,
        str(search_root),
    ]
    process = subprocess.run(
        command,
        cwd=context.boundary.root,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
        env={name: os.environ[name] for name in ("PATH", "HOME", "LANG") if name in os.environ},
    )
    if process.returncode not in {0, 1}:
        raise ToolExecutionError("search_failed", "ripgrep search failed")
    matches = []
    import json

    for line in process.stdout.splitlines():
        event = json.loads(line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        absolute = Path(data["path"]["text"])
        matches.append(
            {
                "path": context.boundary.relative(absolute),
                "line": data["line_number"],
                "text": data["lines"]["text"].rstrip("\r\n")[:2000],
            }
        )
        if len(matches) >= arguments.max_results:
            break
    return {"matches": matches, "truncated": len(matches) == arguments.max_results}


def _git_status(_arguments: BaseModel, context: ToolContext) -> dict[str, Any]:
    result = GitProvider(context.boundary).status()
    return {"stdout": result.stdout, "return_code": result.return_code}


def _git_diff(arguments: GitDiffInput, context: ToolContext) -> dict[str, Any]:
    result = GitProvider(context.boundary).diff(arguments.base, arguments.head)
    return {"stdout": result.stdout, "return_code": result.return_code}


def _git_log(arguments: GitLogInput, context: ToolContext) -> dict[str, Any]:
    result = GitProvider(context.boundary).log(arguments.limit)
    return {"stdout": result.stdout, "return_code": result.return_code}


def _session_factory(context: ToolContext) -> Callable[[], "Session"]:
    if context.session_factory is None:
        raise ToolExecutionError("index_context_missing", "This tool requires an indexed repository context")
    return context.session_factory


def _index_version(session: "Session", repository_id: str):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from tracegate.studio.models import IndexVersion

    version = session.scalar(
        select(IndexVersion)
        .where(IndexVersion.repository_id == repository_id, IndexVersion.status == "ready")
        .order_by(IndexVersion.created_at.desc())
        .limit(1)
    )
    if version is None:
        raise ToolExecutionError("repository_not_indexed", "Repository has no ready index")
    return version


def _search_symbol(arguments: SearchSymbolInput, context: ToolContext) -> dict[str, Any]:
    from sqlalchemy import select

    from tracegate.studio.models import IndexedFile, IndexedSymbol

    with _session_factory(context)() as session:
        version = _index_version(session, context.repository_id)
        rows = session.execute(
            select(IndexedSymbol, IndexedFile)
            .join(IndexedFile, IndexedFile.id == IndexedSymbol.indexed_file_id)
            .where(
                IndexedFile.index_version_id == version.id,
                IndexedSymbol.name.contains(arguments.query),
            )
            .limit(arguments.limit)
        ).all()
        return {
            "index_version": version.id,
            "commit_sha": version.commit_sha,
            "symbols": [
                {
                    "name": symbol.name,
                    "qualified_name": symbol.qualified_name,
                    "kind": symbol.kind,
                    "signature": symbol.signature,
                    "path": file.path,
                    "start_line": symbol.start_line,
                    "end_line": symbol.end_line,
                }
                for symbol, file in rows
            ],
        }


def _get_symbol_definition(arguments: SymbolInput, context: ToolContext) -> dict[str, Any]:
    from sqlalchemy import or_, select

    from tracegate.studio.models import IndexedFile, IndexedSymbol

    with _session_factory(context)() as session:
        version = _index_version(session, context.repository_id)
        statement = (
            select(IndexedSymbol, IndexedFile)
            .join(IndexedFile, IndexedFile.id == IndexedSymbol.indexed_file_id)
            .where(
                IndexedFile.index_version_id == version.id,
                or_(
                    IndexedSymbol.qualified_name == arguments.symbol,
                    IndexedSymbol.name == arguments.symbol,
                ),
            )
        )
        if arguments.path:
            statement = statement.where(IndexedFile.path == arguments.path)
        rows = session.execute(statement.limit(arguments.limit)).all()
        return {
            "index_version": version.id,
            "commit_sha": version.commit_sha,
            "definitions": [
                {
                    "path": file.path,
                    "name": symbol.name,
                    "qualified_name": symbol.qualified_name,
                    "kind": symbol.kind,
                    "signature": symbol.signature,
                    "start_line": symbol.start_line,
                    "end_line": symbol.end_line,
                }
                for symbol, file in rows
            ],
        }


def _get_symbol_references(arguments: SymbolInput, context: ToolContext) -> dict[str, Any]:
    from sqlalchemy import select

    from tracegate.studio.models import IndexedFile

    with _session_factory(context)() as session:
        version = _index_version(session, context.repository_id)
        statement = select(IndexedFile).where(IndexedFile.index_version_id == version.id)
        if arguments.path:
            statement = statement.where(IndexedFile.path == arguments.path)
        matches: list[dict[str, Any]] = []
        for file in session.scalars(statement):
            for reference in file.references_json:
                target = str(reference.get("target", ""))
                if target == arguments.symbol or target.rsplit(".", 1)[-1] == arguments.symbol:
                    matches.append({"path": file.path, **reference})
                    if len(matches) >= arguments.limit:
                        break
            if len(matches) >= arguments.limit:
                break
        return {
            "index_version": version.id,
            "commit_sha": version.commit_sha,
            "references": matches,
        }


def _get_dependency_neighbors(arguments: DependencyInput, context: ToolContext) -> dict[str, Any]:
    from tracegate.studio.index_store import RepositoryIndexError, load_repository_map

    with _session_factory(context)() as session:
        try:
            repository_map = load_repository_map(session, context.repository_id)
        except RepositoryIndexError as exc:
            raise ToolExecutionError("repository_not_indexed", str(exc)) from exc
    node_by_id = {node.id: node for node in repository_map.nodes}
    if arguments.node_id not in node_by_id:
        raise ToolExecutionError("graph_node_not_found", "Graph node was not found in the current index")
    adjacency: dict[str, list[tuple[str, str, bool]]] = {}
    for edge in repository_map.edges:
        adjacency.setdefault(edge.source, []).append((edge.target, edge.kind, edge.confirmed))
        adjacency.setdefault(edge.target, []).append((edge.source, edge.kind, edge.confirmed))
    depth_by_id = {arguments.node_id: 0}
    frontier = {arguments.node_id}
    relationships: list[dict[str, Any]] = []
    for depth in range(1, arguments.depth + 1):
        following: set[str] = set()
        for source in frontier:
            for target, kind, confirmed in adjacency.get(source, []):
                relationships.append(
                    {"source": source, "target": target, "kind": kind, "confirmed": confirmed}
                )
                if target not in depth_by_id:
                    depth_by_id[target] = depth
                    following.add(target)
                if len(depth_by_id) >= arguments.limit:
                    break
        frontier = following
        if len(depth_by_id) >= arguments.limit:
            break
    return {
        "index_version": repository_map.index_version,
        "commit_sha": repository_map.commit_sha,
        "nodes": [
            {**node_by_id[node_id].__dict__, "depth": depth}
            for node_id, depth in depth_by_id.items()
        ],
        "edges": relationships[: arguments.limit * 4],
        "truncated": len(depth_by_id) >= arguments.limit,
    }


def _get_repository_map(arguments: RepositoryMapInput, context: ToolContext) -> dict[str, Any]:
    from tracegate.studio.index_store import RepositoryIndexError, load_repository_map

    with _session_factory(context)() as session:
        try:
            repository_map = load_repository_map(session, context.repository_id)
        except RepositoryIndexError as exc:
            raise ToolExecutionError("repository_not_indexed", str(exc)) from exc
    nodes = list(repository_map.nodes[: arguments.limit])
    node_ids = {node.id for node in nodes}
    edges = [
        edge for edge in repository_map.edges if edge.source in node_ids and edge.target in node_ids
    ]
    return {
        "index_version": repository_map.index_version,
        "commit_sha": repository_map.commit_sha,
        "nodes": [node.__dict__ for node in nodes],
        "edges": [edge.__dict__ for edge in edges],
        "truncated": len(repository_map.nodes) > arguments.limit,
    }


def _pull_request_context(context: ToolContext):  # type: ignore[no-untyped-def]
    from tracegate.studio.models import PullRequest, Repository

    if context.pull_request_id is None:
        raise ToolExecutionError("pull_request_context_missing", "This tool requires a Pull Request context")
    with _session_factory(context)() as session:
        pull_request = session.get(PullRequest, context.pull_request_id)
        if pull_request is None or pull_request.repository_id != context.repository_id:
            raise ToolExecutionError("pull_request_not_found", "Pull Request is not in this repository context")
        repository = session.get(Repository, context.repository_id)
        if repository is None:
            raise ToolExecutionError("repository_not_found", "Repository context no longer exists")
        return {
            "id": pull_request.id,
            "number": pull_request.number,
            "title": pull_request.title,
            "state": pull_request.state,
            "url": pull_request.url,
            "author": pull_request.author,
            "base_sha": pull_request.base_sha,
            "head_sha": pull_request.head_sha,
            "draft": pull_request.draft,
            "additions": pull_request.additions,
            "deletions": pull_request.deletions,
            "changed_files": pull_request.changed_files,
            "analysis_status": pull_request.analysis_status,
            "owner": repository.owner,
            "repository": repository.name,
        }


def _get_pr_metadata(_arguments: BaseModel, context: ToolContext) -> dict[str, Any]:
    return _pull_request_context(context)


async def _github_resource(context: ToolContext, resource: str) -> list[dict[str, Any]]:
    from tracegate.github import GitHubAPIError, GitHubProvider

    metadata = _pull_request_context(context)
    provider = GitHubProvider(context.github_token)
    try:
        if resource == "files":
            return await provider.get_pull_request_files(
                metadata["owner"], metadata["repository"], metadata["number"]
            )
        if resource == "commits":
            return await provider.get_pull_request_commits(
                metadata["owner"], metadata["repository"], metadata["number"]
            )
        if resource == "comments":
            review = await provider.get_review_comments(
                metadata["owner"], metadata["repository"], metadata["number"]
            )
            issue = await provider.get_issue_comments(
                metadata["owner"], metadata["repository"], metadata["number"]
            )
            return [
                *({**item, "tracegate_comment_kind": "review"} for item in review),
                *({**item, "tracegate_comment_kind": "issue"} for item in issue),
            ]
        if resource == "checks":
            if not metadata["head_sha"]:
                raise ToolExecutionError("pull_request_head_missing", "Pull Request has no Head SHA")
            return await provider.get_check_runs(
                metadata["owner"], metadata["repository"], metadata["head_sha"]
            )
        raise ToolExecutionError("invalid_resource", "Unsupported GitHub resource")
    except GitHubAPIError as exc:
        raise ToolExecutionError("github_request_failed", str(exc)) from exc
    finally:
        await provider.close()


def _get_pr_files(_arguments: BaseModel, context: ToolContext) -> dict[str, Any]:
    return {"files": asyncio.run(_github_resource(context, "files"))}


def _get_pr_commits(_arguments: BaseModel, context: ToolContext) -> dict[str, Any]:
    return {"commits": asyncio.run(_github_resource(context, "commits"))}


def _get_pr_comments(_arguments: BaseModel, context: ToolContext) -> dict[str, Any]:
    return {"comments": asyncio.run(_github_resource(context, "comments"))}


def _get_check_runs(_arguments: BaseModel, context: ToolContext) -> dict[str, Any]:
    return {"check_runs": asyncio.run(_github_resource(context, "checks"))}


_COMMAND_ALLOWLIST = {
    ("python", "-m", "pytest"),
    ("python3", "-m", "pytest"),
    ("pytest",),
    ("pnpm", "test"),
    ("pnpm", "lint"),
    ("pnpm", "typecheck"),
    ("cargo", "test"),
    ("cargo", "check"),
}


def _run_command(arguments: RunCommandInput, context: ToolContext) -> dict[str, Any]:
    argv = tuple(arguments.argv)
    allowed = any(argv[: len(prefix)] == prefix for prefix in _COMMAND_ALLOWLIST)
    unsafe_argument = any(
        "\x00" in item
        or item.startswith(("/", "\\"))
        or ".." in Path(item.replace("=", "/")).parts
        for item in argv[1:]
    )
    if not allowed or unsafe_argument or any(
        item.startswith("-") and item in {"--delete", "--force"} for item in argv
    ):
        raise ToolExecutionError("command_forbidden", "Command is not in the restricted allowlist")
    environment = {name: os.environ[name] for name in ("PATH", "HOME", "LANG", "LC_ALL", "TMP", "TEMP") if name in os.environ}
    process = subprocess.run(
        list(argv),
        cwd=context.boundary.root,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=arguments.timeout_seconds,
        env=environment,
    )
    return {
        "return_code": process.returncode,
        "stdout": process.stdout[:512_000],
        "stderr": process.stderr[:512_000],
    }


def _run_tests(arguments: RunTestsInput, context: ToolContext) -> dict[str, Any]:
    commands = {
        "python": ["python", "-m", "pytest"],
        "frontend": ["pnpm", "test"],
        "rust": ["cargo", "test"],
    }
    return _run_command(
        RunCommandInput(
            argv=commands[arguments.target],
            timeout_seconds=arguments.timeout_seconds,
        ),
        context,
    )


def _apply_patch(arguments: ApplyPatchInput, context: ToolContext) -> dict[str, Any]:
    if not context.write_enabled:
        raise ToolExecutionError("write_mode_disabled", "Patch application is disabled for this run")
    if (
        context.patch_confirmation_id is None
        or arguments.confirmation_id != context.patch_confirmation_id
    ):
        raise ToolExecutionError(
            "write_confirmation_required",
            "Patch application requires the exact confirmation identifier shown to the user",
        )
    changed_paths: set[str] = set()
    for line in arguments.patch.splitlines():
        if not line.startswith(("+++ ", "--- ")):
            continue
        raw_path = line[4:].split("\t", 1)[0]
        if raw_path == "/dev/null":
            continue
        if raw_path.startswith(("a/", "b/")):
            raw_path = raw_path[2:]
        if raw_path.startswith('"') or "\x00" in raw_path:
            raise ToolExecutionError("patch_path_invalid", "Quoted or NUL patch paths are not supported")
        try:
            context.boundary.resolve(raw_path, allow_missing=True)
        except RepositoryPathError as exc:
            raise ToolExecutionError("patch_path_forbidden", str(exc)) from exc
        changed_paths.add(raw_path)
    if not changed_paths:
        raise ToolExecutionError("patch_invalid", "Patch does not contain a bounded file header")

    environment = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "LANG", "LC_ALL", "TMP", "TEMP")
        if name in os.environ
    }
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"})
    commands = (
        ["git", "apply", "--check", "--whitespace=nowarn", "-"],
        ["git", "apply", "--whitespace=nowarn", "-"],
    )
    for command in commands:
        process = subprocess.run(
            command,
            cwd=context.boundary.root,
            input=arguments.patch,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            env=environment,
            check=False,
        )
        if process.returncode != 0:
            raise ToolExecutionError(
                "patch_check_failed" if "--check" in command else "patch_apply_failed",
                process.stderr[:4000] or "git apply rejected the patch",
            )
    diff = GitProvider(context.boundary).diff().stdout
    return {
        "applied": True,
        "changed_paths": sorted(changed_paths),
        "git_diff": diff,
        "committed": False,
        "pushed": False,
    }


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def create_read_only_registry(disabled_names: set[str] | None = None) -> ToolRegistry:
    registry = ToolRegistry(disabled_names)
    registry.register(
        name="list_directory",
        description="List bounded entries below the enrolled repository root.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=ListDirectoryInput,
        handler=_list_directory,
    )
    registry.register(
        name="read_file",
        description="Read a bounded UTF-8 line range from an enrolled repository file.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=ReadFileInput,
        handler=_read_file,
    )
    registry.register(
        name="search_code",
        description="Run a literal ripgrep search without leaving the enrolled repository.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=SearchCodeInput,
        handler=_search_code,
    )
    registry.register(
        name="search_symbol",
        description="Search symbols in the current persisted index version.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=SearchSymbolInput,
        handler=_search_symbol,
    )
    registry.register(
        name="get_symbol_definition",
        description="Resolve an exact symbol definition from the current persisted index.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=SymbolInput,
        handler=_get_symbol_definition,
    )
    registry.register(
        name="get_symbol_references",
        description="Read parser-recorded references to a symbol from the current index.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=SymbolInput,
        handler=_get_symbol_references,
    )
    registry.register(
        name="get_dependency_neighbors",
        description="Traverse one or two hops of confirmed static repository graph relationships.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=DependencyInput,
        handler=_get_dependency_neighbors,
    )
    registry.register(
        name="get_repository_map",
        description="Read a bounded view of the persisted commit-bound Repository Map.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=RepositoryMapInput,
        handler=_get_repository_map,
    )
    registry.register(
        name="get_git_status",
        description="Read repository status and current branch.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=EmptyInput,
        handler=_git_status,
    )
    registry.register(
        name="get_git_diff",
        description="Read a bounded Git diff for the worktree or a revision range.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=GitDiffInput,
        handler=_git_diff,
    )
    registry.register(
        name="get_git_log",
        description="Read bounded structured Git commit metadata.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=GitLogInput,
        handler=_git_log,
    )
    registry.register(
        name="get_pr_metadata",
        description="Read the persisted Pull Request snapshot bound to the current run.",
        permission=PermissionLevel.REPOSITORY_READ,
        input_model=EmptyInput,
        handler=_get_pr_metadata,
    )
    registry.register(
        name="get_pr_files",
        description="Read changed-file metadata from the GitHub Pull Request API.",
        permission=PermissionLevel.NETWORK,
        input_model=EmptyInput,
        handler=_get_pr_files,
        timeout_seconds=30,
        max_output_bytes=8 * 1024 * 1024,
    )
    registry.register(
        name="get_pr_commits",
        description="Read commit metadata from the GitHub Pull Request API.",
        permission=PermissionLevel.NETWORK,
        input_model=EmptyInput,
        handler=_get_pr_commits,
        timeout_seconds=30,
        max_output_bytes=8 * 1024 * 1024,
    )
    registry.register(
        name="get_pr_comments",
        description="Read review and issue comments from the GitHub Pull Request API.",
        permission=PermissionLevel.NETWORK,
        input_model=EmptyInput,
        handler=_get_pr_comments,
        timeout_seconds=45,
        max_output_bytes=8 * 1024 * 1024,
    )
    registry.register(
        name="get_check_runs",
        description="Read GitHub Check Runs for the Pull Request Head SHA.",
        permission=PermissionLevel.NETWORK,
        input_model=EmptyInput,
        handler=_get_check_runs,
        timeout_seconds=30,
        max_output_bytes=8 * 1024 * 1024,
    )
    registry.register(
        name="run_tests",
        description="Run the repository Python, frontend, or Rust test command through the allowlist.",
        permission=PermissionLevel.COMMAND_RESTRICTED,
        input_model=RunTestsInput,
        handler=_run_tests,
        timeout_seconds=305,
        max_output_bytes=1_100_000,
    )
    registry.register(
        name="run_command",
        description="Run an argument-vector command from a small test/check allowlist.",
        permission=PermissionLevel.COMMAND_RESTRICTED,
        input_model=RunCommandInput,
        handler=_run_command,
        timeout_seconds=305,
        max_output_bytes=1_100_000,
    )
    registry.register(
        name="apply_patch",
        description="Apply a shown unified diff only after explicit write mode and confirmation; never commit or push.",
        permission=PermissionLevel.WRITE_CONFIRMATION,
        input_model=ApplyPatchInput,
        handler=_apply_patch,
        timeout_seconds=35,
        max_output_bytes=2 * 1024 * 1024,
    )
    return registry
