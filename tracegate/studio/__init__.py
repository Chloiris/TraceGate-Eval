"""TraceGate Studio local API and persistence foundation.

Imports stay lazy so indexing, retrieval, and agent modules can depend on the
Studio persistence models without initializing the FastAPI routing graph.
"""

from typing import Any

__all__ = [
    "StudioConfigurationError",
    "StudioSettings",
    "create_app",
    "create_app_from_env",
]


def __getattr__(name: str) -> Any:
    if name in {"create_app", "create_app_from_env"}:
        from .app import create_app, create_app_from_env

        return {"create_app": create_app, "create_app_from_env": create_app_from_env}[name]
    if name in {"StudioConfigurationError", "StudioSettings"}:
        from .config import StudioConfigurationError, StudioSettings

        return {
            "StudioConfigurationError": StudioConfigurationError,
            "StudioSettings": StudioSettings,
        }[name]
    raise AttributeError(name)
