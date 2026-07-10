#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "TraceGate Studio macOS builds require a macOS arm64 host." >&2
  exit 1
fi

pnpm --filter @tracegate/web build
./scripts/build-sidecar.sh
pnpm --filter @tracegate/desktop build
