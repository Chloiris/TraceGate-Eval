from __future__ import annotations

import subprocess
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
        "search_symbol",
        "get_symbol_definition",
        "get_symbol_references",
        "get_dependency_neighbors",
        "get_repository_map",
        "get_pr_metadata",
        "get_pr_files",
        "get_pr_commits",
        "get_pr_comments",
        "get_check_runs",
        "run_tests",
        "apply_patch",
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


@pytest.mark.asyncio
async def test_apply_patch_is_disabled_until_exact_user_confirmation(
    tool_context: ToolContext,
) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tool_context.boundary.root, check=True)
    subprocess.run(["git", "config", "user.email", "tracegate@example.invalid"], cwd=tool_context.boundary.root, check=True)
    subprocess.run(["git", "config", "user.name", "TraceGate Test"], cwd=tool_context.boundary.root, check=True)
    subprocess.run(["git", "add", "."], cwd=tool_context.boundary.root, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tool_context.boundary.root, check=True)
    patch = """--- a/src/main.py
+++ b/src/main.py
@@ -1,2 +1,2 @@
 def alpha():
-    return 'needle'
+    return 'changed'
"""
    registry = create_read_only_registry()
    with pytest.raises(ToolExecutionError) as disabled:
        await registry.execute(
            "apply_patch",
            {"patch": patch, "confirmation_id": "confirmation-123456"},
            tool_context,
        )
    assert disabled.value.code == "write_mode_disabled"

    write_context = ToolContext(
        tool_context.repository_id,
        tool_context.boundary,
        tool_context.caller_agent,
        write_enabled=True,
        patch_confirmation_id="confirmation-123456",
    )
    with pytest.raises(ToolExecutionError) as unconfirmed:
        await registry.execute(
            "apply_patch",
            {"patch": patch, "confirmation_id": "wrong-confirmation"},
            write_context,
        )
    assert unconfirmed.value.code == "write_confirmation_required"

    result = await registry.execute(
        "apply_patch",
        {"patch": patch, "confirmation_id": "confirmation-123456"},
        write_context,
    )
    assert result["applied"] is True
    assert result["committed"] is False
    assert result["pushed"] is False
    assert "return 'changed'" in (tool_context.boundary.root / "src" / "main.py").read_text()
