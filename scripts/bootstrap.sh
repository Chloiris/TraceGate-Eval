#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

for command_name in uv pnpm cargo; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Missing required command: $command_name" >&2
    exit 1
  fi
done

uv sync --extra dev
pnpm install --frozen-lockfile
cargo fetch --manifest-path apps/desktop/src-tauri/Cargo.toml

echo "TraceGate Studio dependencies are ready."
