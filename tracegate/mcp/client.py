from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from tracegate.repository import RepositoryBoundary


PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {"2025-11-25", "2025-06-18", "2025-03-26"}
_ENV_ALLOWLIST = ("HOME", "LANG", "LC_ALL", "PATH", "SYSTEMROOT", "TMP", "TEMP")


class MCPClientError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    command: str = Field(min_length=1, max_length=2048)
    arguments: list[str] = Field(default_factory=list, max_length=32)
    environment: dict[str, SecretStr] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=20.0, ge=1.0, le=120.0)
    max_message_bytes: int = Field(default=2 * 1024 * 1024, ge=1024, le=8 * 1024 * 1024)


class MCPClient:
    """Sequential, newline-delimited MCP stdio client with deny-by-default tools."""

    def __init__(
        self,
        config: MCPServerConfig,
        boundary: RepositoryBoundary,
        *,
        allowed_executables: set[str],
        allowed_tool_names: set[str] | None = None,
    ) -> None:
        executable = str(Path(config.command).expanduser().resolve())
        normalized_allowed = {str(Path(item).expanduser().resolve()) for item in allowed_executables}
        if executable not in normalized_allowed:
            raise MCPClientError("executable_forbidden", "MCP server executable is not allowlisted")
        if any("\x00" in item for item in config.arguments):
            raise MCPClientError("invalid_arguments", "MCP server arguments contain NUL")
        self.config = config
        self.boundary = boundary
        self.executable = executable
        self.allowed_tool_names = frozenset(allowed_tool_names or set())
        self._process: subprocess.Popen[str] | None = None
        self._messages: queue.Queue[dict[str, Any] | MCPClientError] = queue.Queue()
        self._request_id = 0
        self._lock = threading.Lock()
        self._protocol_version: str | None = None

    @property
    def connected(self) -> bool:
        return self._process is not None and self._process.poll() is None and self._protocol_version is not None

    def connect(self) -> dict[str, Any]:
        if self._process is not None:
            raise MCPClientError("already_started", "MCP client process has already been started")
        environment = {name: os.environ[name] for name in _ENV_ALLOWLIST if name in os.environ}
        environment.update(
            {name: value.get_secret_value() for name, value in self.config.environment.items()}
        )
        try:
            self._process = subprocess.Popen(
                [self.executable, *self.config.arguments],
                cwd=self.boundary.root,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="strict",
                shell=False,
                bufsize=1,
            )
        except OSError as exc:
            raise MCPClientError("spawn_failed", f"MCP server could not start: {type(exc).__name__}") from exc
        threading.Thread(target=self._read_messages, name=f"mcp-{self.config.name}-stdout", daemon=True).start()
        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "tracegate-studio",
                    "title": "TraceGate Studio",
                    "version": "0.1.0",
                },
            },
        )
        version = result.get("protocolVersion")
        if version not in SUPPORTED_PROTOCOL_VERSIONS:
            self.close()
            raise MCPClientError("unsupported_protocol", "MCP server negotiated an unsupported version")
        self._protocol_version = str(version)
        self._notify("notifications/initialized", {})
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        self._require_connected()
        result = self._request("tools/list", {})
        tools = result.get("tools")
        if not isinstance(tools, list) or not all(isinstance(item, dict) for item in tools):
            raise MCPClientError("invalid_response", "MCP tools/list response is invalid")
        bounded = []
        for item in tools:
            name = item.get("name")
            if isinstance(name, str) and name in self.allowed_tool_names:
                bounded.append(item)
        return bounded

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._require_connected()
        if name not in self.allowed_tool_names:
            raise MCPClientError("tool_forbidden", "MCP tool is not allowlisted")
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        content = result.get("content")
        if not isinstance(content, list):
            raise MCPClientError("invalid_response", "MCP tools/call response has no content list")
        if result.get("isError") is True:
            raise MCPClientError("tool_error", "MCP server reported a tool execution error")
        return result

    def close(self) -> None:
        process = self._process
        self._process = None
        self._protocol_version = None
        if process is None:
            return
        if process.stdin:
            process.stdin.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    def __enter__(self) -> "MCPClient":
        self.connect()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_connected(self) -> None:
        if not self.connected:
            raise MCPClientError("not_connected", "MCP client has not completed initialization")

    def _read_messages(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            for line in process.stdout:
                if len(line.encode("utf-8")) > self.config.max_message_bytes:
                    self._messages.put(MCPClientError("message_too_large", "MCP message exceeded its limit"))
                    return
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    self._messages.put(MCPClientError("invalid_json", "MCP server emitted invalid JSON"))
                    return
                if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
                    self._messages.put(MCPClientError("invalid_message", "MCP server emitted an invalid message"))
                    return
                self._messages.put(payload)
        except (OSError, UnicodeError):
            self._messages.put(MCPClientError("transport_closed", "MCP stdio transport closed unexpectedly"))

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._request_id += 1
            request_id = self._request_id
            self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            while True:
                try:
                    message = self._messages.get(timeout=self.config.timeout_seconds)
                except queue.Empty as exc:
                    raise MCPClientError("timeout", f"MCP request {method} timed out") from exc
                if isinstance(message, MCPClientError):
                    raise message
                if message.get("id") != request_id:
                    if "method" in message and "id" not in message:
                        continue
                    raise MCPClientError("unexpected_message", "MCP response ID did not match the request")
                if "error" in message:
                    error = message["error"]
                    code = error.get("code") if isinstance(error, dict) else "unknown"
                    raise MCPClientError("protocol_error", f"MCP server returned JSON-RPC error {code}")
                result = message.get("result")
                if not isinstance(result, dict):
                    raise MCPClientError("invalid_response", "MCP response result is not an object")
                return result

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def _write(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise MCPClientError("transport_closed", "MCP stdio transport is unavailable")
        encoded = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > self.config.max_message_bytes:
            raise MCPClientError("message_too_large", "MCP request exceeded its limit")
        try:
            process.stdin.write(encoded + "\n")
            process.stdin.flush()
        except OSError as exc:
            raise MCPClientError("transport_closed", "MCP request could not be written") from exc
