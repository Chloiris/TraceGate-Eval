#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export TRACEGATE_HOST="${TRACEGATE_HOST:-127.0.0.1}"
export TRACEGATE_PORT="${TRACEGATE_PORT:-8765}"
export TRACEGATE_DATA_DIR="${TRACEGATE_DATA_DIR:-$ROOT_DIR/.tracegate-dev}"
export TRACEGATE_LOCAL_API_TOKEN="${TRACEGATE_LOCAL_API_TOKEN:-$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')}"
export TRACEGATE_DEV_API_TARGET="http://${TRACEGATE_HOST}:${TRACEGATE_PORT}"
export VITE_TRACEGATE_API_BASE_URL="/api/v1"
export VITE_TRACEGATE_API_TOKEN="$TRACEGATE_LOCAL_API_TOKEN"

backend_pid=""
cleanup() {
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
    wait "$backend_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

uv run tracegate-studio serve &
backend_pid=$!
pnpm dev
