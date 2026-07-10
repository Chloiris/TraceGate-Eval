from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ComponentState = Literal["ready", "not_configured", "error", "unavailable"]
OnboardingStep = Literal[
    "welcome",
    "appearance",
    "github",
    "model",
    "repository",
    "background",
    "complete",
]


class ComponentStatus(BaseModel):
    state: ComponentState
    configured: bool
    message: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["tracegate-studio"] = "tracegate-studio"
    version: str
    api_version: Literal["v1"] = "v1"
    database: ComponentStatus


class SystemComponents(BaseModel):
    api: ComponentStatus
    database: ComponentStatus
    github: ComponentStatus
    model: ComponentStatus
    eval: ComponentStatus


class SystemStatusResponse(BaseModel):
    status: Literal["ready", "degraded", "error"]
    components: SystemComponents
    checked_at: datetime


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    theme: Literal["system", "light", "dark"]
    language: Literal["zh-CN", "en-US"]
    background_monitoring: bool
    launch_at_startup: bool
    model_provider: str | None
    model_base_url: str | None
    model_name: str | None
    updated_at: datetime


class SettingsUpdate(BaseModel):
    theme: Literal["system", "light", "dark"] | None = None
    language: Literal["zh-CN", "en-US"] | None = None
    background_monitoring: bool | None = None
    launch_at_startup: bool | None = None
    model_provider: str | None = Field(default=None, max_length=64)
    model_base_url: str | None = Field(default=None, max_length=2048)
    model_name: str | None = Field(default=None, max_length=255)

    @field_validator("model_provider", "model_name")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("model_base_url")
    @classmethod
    def validate_model_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().rstrip("/")
        if not normalized:
            return None
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("model_base_url must be an absolute HTTP(S) URL")
        return normalized

    @model_validator(mode="after")
    def require_update(self) -> "SettingsUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one settings field is required")
        for name in ("theme", "language", "background_monitoring", "launch_at_startup"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class OnboardingResponse(BaseModel):
    completed: bool
    current_step: OnboardingStep
    github: ComponentStatus
    model: ComponentStatus
    repository_added: bool
    background_monitoring: bool
    launch_at_startup: bool
    completed_at: datetime | None
    updated_at: datetime


class OnboardingUpdate(BaseModel):
    completed: bool | None = None
    current_step: OnboardingStep | None = None
    background_monitoring: bool | None = None
    launch_at_startup: bool | None = None

    @model_validator(mode="after")
    def require_update(self) -> "OnboardingUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one onboarding field is required")
        for name in (
            "completed",
            "current_step",
            "background_monitoring",
            "launch_at_startup",
        ):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


REPOSITORY_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RepositoryCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=201)
    clone_url: str | None = Field(default=None, max_length=2048)
    local_path: str | None = Field(default=None, max_length=2048)
    default_branch: str | None = Field(default=None, max_length=255)
    monitoring_enabled: bool = False

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if not REPOSITORY_NAME_RE.fullmatch(normalized):
            raise ValueError("full_name must use the GitHub owner/name format")
        return normalized

    @field_validator("clone_url")
    @classmethod
    def validate_clone_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme != "https" or parsed.hostname != "github.com":
            raise ValueError("clone_url must be an HTTPS github.com URL")
        return normalized

    @field_validator("local_path", "default_branch")
    @classmethod
    def normalize_optional_value(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RepositoryUpdate(BaseModel):
    local_path: str | None = Field(default=None, max_length=2048)
    default_branch: str | None = Field(default=None, max_length=255)
    monitoring_enabled: bool | None = None

    @model_validator(mode="after")
    def require_update(self) -> "RepositoryUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one repository field is required")
        return self


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner: str
    name: str
    full_name: str
    clone_url: str | None
    local_path: str | None
    default_branch: str | None
    monitoring_enabled: bool
    connection_status: Literal["not_connected", "pending", "ready", "error"]
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]
    total: int
    limit: int
    offset: int


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
