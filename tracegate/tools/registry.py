from __future__ import annotations

import asyncio
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tracegate.repository import RepositoryBoundary, RepositoryPathError
from tracegate.vcs import GitCommandError, GitProvider


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


@dataclass(frozen=True)
class ToolContext:
    repository_id: str
    boundary: RepositoryBoundary
    caller_agent: str
    cancellation_event: asyncio.Event | None = None


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

    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name=self.name,
            description=self.description,
            permission=self.permission,
            timeout_seconds=self.timeout_seconds,
            max_output_bytes=self.max_output_bytes,
            input_schema=self.input_model.model_json_schema(),
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, _RegisteredTool[Any]] = {}
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
        return [self._tools[name].descriptor() for name in sorted(self._tools)]

    async def execute(self, name: str, payload: dict[str, Any], context: ToolContext) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError("tool_not_found", f"Tool {name} is not registered")
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


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def create_read_only_registry() -> ToolRegistry:
    registry = ToolRegistry()
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
        name="run_command",
        description="Run an argument-vector command from a small test/check allowlist.",
        permission=PermissionLevel.COMMAND_RESTRICTED,
        input_model=RunCommandInput,
        handler=_run_command,
        timeout_seconds=305,
        max_output_bytes=1_100_000,
    )
    return registry
