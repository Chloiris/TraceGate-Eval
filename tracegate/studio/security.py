from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import StudioAPIError


bearer_scheme = HTTPBearer(auto_error=False)


def require_local_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise StudioAPIError(401, "unauthorized", "A local bearer token is required.")
    expected = request.app.state.settings.local_api_token.get_secret_value()
    if not secrets.compare_digest(credentials.credentials, expected):
        raise StudioAPIError(401, "unauthorized", "The local bearer token is invalid.")
