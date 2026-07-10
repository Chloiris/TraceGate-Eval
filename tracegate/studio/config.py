from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from tracegate import __version__
from tracegate.config import PROJECT_ROOT


DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:1420",
    "http://localhost:1420",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
)


class StudioConfigurationError(ValueError):
    """Raised when the local Studio service cannot start safely."""


def default_data_dir() -> Path:
    configured = os.environ.get("TRACEGATE_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return root / "TraceGate Studio"
    if os.uname().sysname == "Darwin":
        return Path.home() / "Library" / "Application Support" / "TraceGate Studio"
    root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return root / "tracegate-studio"


def sqlite_database_url(data_dir: Path) -> str:
    database_path = (data_dir / "tracegate-studio.db").expanduser().resolve()
    return f"sqlite+pysqlite:///{database_path.as_posix()}"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise StudioConfigurationError(f"{name} must be a boolean value")


class StudioSettings(BaseModel):
    """Validated process settings; secret values are never serialized by API schemas."""

    model_config = ConfigDict(frozen=True)

    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1, le=65535)
    local_api_token: SecretStr
    database_url: str
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
    auto_migrate: bool = True
    eval_root: Path = PROJECT_ROOT
    github_token_configured: bool = False
    model_api_key_configured: bool = False
    version: str = __version__

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("TraceGate Studio must bind to 127.0.0.1")
        return value

    @field_validator("local_api_token")
    @classmethod
    def validate_token(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("TRACEGATE_LOCAL_API_TOKEN must contain at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("database_url must not be empty")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        unique: list[str] = []
        for value in values:
            if value == "*":
                raise ValueError("wildcard CORS origins are forbidden")
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https", "tauri"} or not parsed.netloc:
                raise ValueError(f"invalid CORS origin: {value}")
            normalized = value.rstrip("/")
            if normalized not in unique:
                unique.append(normalized)
        return tuple(unique)

    @classmethod
    def from_env(cls, **overrides: Any) -> "StudioSettings":
        token = os.environ.get("TRACEGATE_LOCAL_API_TOKEN")
        if not token:
            raise StudioConfigurationError(
                "TRACEGATE_LOCAL_API_TOKEN is required; the desktop host must provide a 256-bit local token"
            )
        data_dir = default_data_dir()
        raw_origins = os.environ.get("TRACEGATE_CORS_ORIGINS")
        origins = (
            tuple(item.strip() for item in raw_origins.split(",") if item.strip())
            if raw_origins is not None
            else DEFAULT_CORS_ORIGINS
        )
        values: dict[str, Any] = {
            "host": os.environ.get("TRACEGATE_HOST", "127.0.0.1"),
            "port": int(os.environ.get("TRACEGATE_PORT", "8765")),
            "local_api_token": SecretStr(token),
            "database_url": os.environ.get("TRACEGATE_DATABASE_URL") or sqlite_database_url(data_dir),
            "cors_origins": origins,
            "auto_migrate": _env_bool("TRACEGATE_AUTO_MIGRATE", True),
            "eval_root": PROJECT_ROOT,
            "github_token_configured": bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
            "model_api_key_configured": bool(
                os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("TRACEGATE_LLM_API_KEY")
            ),
        }
        values.update(overrides)
        try:
            return cls.model_validate(values)
        except (TypeError, ValueError) as exc:
            raise StudioConfigurationError(str(exc)) from exc
