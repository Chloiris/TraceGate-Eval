from __future__ import annotations

import os
import secrets
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, SecretStr, field_validator

from .errors import StudioAPIError
from .security import bearer_scheme


RuntimeCredentialKind = Literal["github", "model", "relay"]

_ENVIRONMENT_NAMES: dict[RuntimeCredentialKind, tuple[str, ...]] = {
    "github": ("GITHUB_TOKEN", "GH_TOKEN"),
    "model": ("TRACEGATE_LLM_API_KEY", "DEEPSEEK_API_KEY"),
    "relay": ("TRACEGATE_RELAY_DEVICE_TOKEN",),
}


class RuntimeCredentialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret: SecretStr

    @field_validator("secret")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if not 20 <= len(raw) <= 8192 or any(character.isspace() for character in raw):
            raise ValueError("credential must contain between 20 and 8192 non-whitespace characters")
        return value


class RuntimeCredentialStatus(BaseModel):
    kind: RuntimeCredentialKind
    configured: bool


def require_credential_control_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    configured = request.app.state.settings.credential_control_token
    if credentials is None or credentials.scheme.lower() != "bearer" or configured is None:
        raise StudioAPIError(401, "unauthorized", "A desktop credential-control token is required.")
    if not secrets.compare_digest(credentials.credentials, configured.get_secret_value()):
        raise StudioAPIError(401, "unauthorized", "The desktop credential-control token is invalid.")


router = APIRouter(
    prefix="/internal/v1",
    dependencies=[Depends(require_credential_control_token)],
)


def _apply_runtime_credential(
    request: Request,
    kind: RuntimeCredentialKind,
    secret: SecretStr | None,
) -> RuntimeCredentialStatus:
    names = _ENVIRONMENT_NAMES[kind]
    if secret is None:
        for name in names:
            os.environ.pop(name, None)
        configured = False
    else:
        os.environ[names[0]] = secret.get_secret_value()
        for alias in names[1:]:
            os.environ.pop(alias, None)
        configured = True

    settings = request.app.state.settings
    updates: dict[str, bool] = {}
    if kind == "github":
        updates["github_token_configured"] = configured
        request.app.state.repository_monitor.wake()
    elif kind == "model":
        updates["model_api_key_configured"] = configured
    else:
        request.app.state.relay_monitor.wake()
    if updates:
        request.app.state.settings = settings.model_copy(update=updates)

    return RuntimeCredentialStatus(kind=kind, configured=configured)


@router.put("/credentials/{kind}", response_model=RuntimeCredentialStatus)
def update_runtime_credential(
    kind: RuntimeCredentialKind,
    payload: RuntimeCredentialUpdate,
    request: Request,
) -> RuntimeCredentialStatus:
    return _apply_runtime_credential(request, kind, payload.secret)


@router.delete("/credentials/{kind}", response_model=RuntimeCredentialStatus)
def delete_runtime_credential(
    kind: RuntimeCredentialKind,
    request: Request,
) -> RuntimeCredentialStatus:
    return _apply_runtime_credential(request, kind, None)
