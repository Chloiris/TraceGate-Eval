from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence

import uvicorn

from .app import create_app
from .config import StudioConfigurationError, StudioSettings
from .parent_watchdog import start_parent_watchdog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TraceGate Studio local Python sidecar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the authenticated local API sidecar.")
    serve.add_argument("--host", help="Loopback host; must be 127.0.0.1.")
    serve.add_argument("--port", type=int, help="Local API port selected by the desktop host.")
    serve.add_argument("--log-level", choices=["critical", "error", "warning", "info"], default="info")

    health = subparsers.add_parser("health", help="Check the authenticated local health endpoint.")
    health.add_argument("--host", help="Loopback host; defaults to TRACEGATE_HOST.")
    health.add_argument("--port", type=int, help="Local API port; defaults to TRACEGATE_PORT.")
    health.add_argument("--timeout", type=float, default=5.0)
    return parser


def _overrides(args: argparse.Namespace) -> dict[str, object]:
    values: dict[str, object] = {}
    if args.host is not None:
        values["host"] = args.host
    if args.port is not None:
        values["port"] = args.port
    return values


def _health(args: argparse.Namespace) -> int:
    token = os.environ.get("TRACEGATE_LOCAL_API_TOKEN")
    if not token:
        print("TRACEGATE_LOCAL_API_TOKEN is required for the health check", file=sys.stderr)
        return 2
    host = args.host or os.environ.get("TRACEGATE_HOST", "127.0.0.1")
    if host != "127.0.0.1":
        print("TraceGate Studio health checks only support 127.0.0.1", file=sys.stderr)
        return 2
    try:
        port = int(args.port or os.environ.get("TRACEGATE_PORT", "8765"))
    except ValueError:
        print("TRACEGATE_PORT must be an integer", file=sys.stderr)
        return 2
    request = urllib.request.Request(
        f"http://{host}:{port}/api/v1/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"TraceGate Studio health check failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    if response.status != 200 or payload.get("status") != "ok":
        print("TraceGate Studio health check returned an unhealthy response", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return 0


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "health":
        return _health(args)
    try:
        settings = StudioSettings.from_env(**_overrides(args))
    except StudioConfigurationError as exc:
        print(f"TraceGate Studio configuration error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "event": "tracegate_studio_sidecar_starting",
                "host": settings.host,
                "port": settings.port,
                "authentication": "bearer",
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    start_parent_watchdog()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=args.log_level,
        access_log=False,
        proxy_headers=False,
        server_header=False,
        workers=1,
    )
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
