from __future__ import annotations

from pathlib import Path

import pytest

from tracegate.repository import RepositoryBoundary
from tracegate.tools import ToolContext, ToolExecutionError, create_read_only_registry


@pytest.fixture
def tool_context(tmp_path: Path) -> ToolContext:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def alpha():\n    return 'needle'\n", encoding="utf-8")
    return ToolContext("repository-1", RepositoryBoundary(tmp_path), "Repository Retriever")


@pytest.mark.asyncio
async def test_registry_descriptors_have_schema_permission_timeout_and_limits() -> None:
    descriptors = create_read_only_registry().descriptors()
    assert {item.name for item in descriptors} >= {
        "list_directory",
        "read_file",
        "search_code",
        "get_git_diff",
        "run_command",
    }
    assert all(item.input_schema["type"] == "object" for item in descriptors)
    assert all(item.timeout_seconds > 0 and item.max_output_bytes > 0 for item in descriptors)


@pytest.mark.asyncio
async def test_read_and_search_tools_use_real_repository_content(tool_context: ToolContext) -> None:
    registry = create_read_only_registry()
    read = await registry.execute("read_file", {"path": "src/main.py"}, tool_context)
    search = await registry.execute("search_code", {"query": "needle"}, tool_context)
    assert "def alpha" in read["content"]
    assert search["matches"][0]["path"] == "src/main.py"
    assert registry.invocations[-1].succeeded is True


@pytest.mark.asyncio
async def test_registry_rejects_invalid_paths_and_commands(tool_context: ToolContext) -> None:
    registry = create_read_only_registry()
    with pytest.raises(ToolExecutionError, match="forbidden"):
        await registry.execute("read_file", {"path": "../secret"}, tool_context)
    with pytest.raises(ToolExecutionError) as caught:
        await registry.execute("run_command", {"argv": ["rm", "-rf", "."]}, tool_context)
    assert caught.value.code == "command_forbidden"
    assert registry.invocations[-1].succeeded is False


@pytest.mark.asyncio
async def test_registry_honors_pre_execution_cancellation(tool_context: ToolContext) -> None:
    import asyncio

    event = asyncio.Event()
    event.set()
    cancelled = ToolContext(
        tool_context.repository_id,
        tool_context.boundary,
        tool_context.caller_agent,
        event,
    )
    with pytest.raises(ToolExecutionError) as caught:
        await create_read_only_registry().execute("list_directory", {}, cancelled)
    assert caught.value.code == "cancelled"
