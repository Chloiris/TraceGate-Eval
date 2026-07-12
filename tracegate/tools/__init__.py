"""Typed, observable tools for TraceGate Studio agents."""

from .registry import (
    PermissionLevel,
    ToolContext,
    ToolDescriptor,
    ToolExecutionError,
    ToolRegistry,
    create_read_only_registry,
)

__all__ = [
    "PermissionLevel",
    "ToolContext",
    "ToolDescriptor",
    "ToolExecutionError",
    "ToolRegistry",
    "create_read_only_registry",
]
