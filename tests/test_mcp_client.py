from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tracegate.mcp import MCPClient, MCPClientError, MCPServerConfig
from tracegate.repository import RepositoryBoundary


def test_stdio_mcp_client_negotiates_filters_and_calls_allowlisted_tool(tmp_path: Path) -> None:
    server = Path(__file__).parent / "fixtures" / "mcp_stdio_server.py"
    config = MCPServerConfig(
        name="test-server",
        command=sys.executable,
        arguments=[str(server)],
        timeout_seconds=5,
    )
    client = MCPClient(
        config,
        RepositoryBoundary(tmp_path),
        allowed_executables={sys.executable},
        allowed_tool_names={"echo"},
    )
    try:
        initialized = client.connect()
        assert initialized["protocolVersion"] == "2025-11-25"
        assert [tool["name"] for tool in client.list_tools()] == ["echo"]
        result = client.call_tool("echo", {"path": "src/main.py"})
        assert result["structuredContent"] == {"path": "src/main.py"}
        with pytest.raises(MCPClientError) as forbidden:
            client.call_tool("hidden", {})
        assert forbidden.value.code == "tool_forbidden"
    finally:
        client.close()
    assert client.connected is False


def test_stdio_mcp_client_rejects_non_allowlisted_executable(tmp_path: Path) -> None:
    config = MCPServerConfig(name="forbidden", command=sys.executable)
    with pytest.raises(MCPClientError) as caught:
        MCPClient(
            config,
            RepositoryBoundary(tmp_path),
            allowed_executables={"/definitely/not/python"},
        )
    assert caught.value.code == "executable_forbidden"
