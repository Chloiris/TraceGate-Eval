from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import router
from .config import StudioSettings
from .database import StudioDatabase
from .errors import StudioAPIError
from .migration_runner import require_current_revision, upgrade_database


SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; base-uri 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def create_app(settings: StudioSettings) -> FastAPI:
    database = StudioDatabase(settings.database_url)
    logger = logging.getLogger("tracegate.studio.api")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            if settings.auto_migrate:
                upgrade_database(settings.database_url)
            require_current_revision(database.engine, settings.database_url)
            database.check_connection()
            logger.info("api_ready database_migrated=true")
            yield
        finally:
            database.dispose()
            logger.info("api_stopped database_disposed=true")

    app = FastAPI(
        title="TraceGate Studio API",
        version=settings.version,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    @app.exception_handler(StudioAPIError)
    async def studio_api_error(_request: Request, exc: StudioAPIError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        message = errors[0].get("msg", "Request validation failed.") if errors else "Request validation failed."
        return _error_response(422, "validation_error", str(message))

    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return _error_response(
            503,
            "database_error",
            "The local database operation failed; no cached replacement result was returned.",
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _error_response(404, "not_found", "The requested API endpoint was not found.")
        return _error_response(exc.status_code, "http_error", str(exc.detail))

    app.include_router(router)
    return app


def create_app_from_env() -> FastAPI:
    return create_app(StudioSettings.from_env())
