#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This script only builds the macOS arm64 Sidecar." >&2
  exit 1
fi

rm -rf build/sidecar
uv run --extra packaging pyinstaller \
  --noconfirm \
  --clean \
  --distpath build/sidecar/dist \
  --workpath build/sidecar/work \
  packaging/tracegate-backend.spec

sidecar="$ROOT_DIR/build/sidecar/dist/tracegate-backend"
if [[ ! -x "$sidecar" ]]; then
  echo "PyInstaller did not produce $sidecar" >&2
  exit 1
fi

health_root="$(mktemp -d)"
health_pid=""
cleanup() {
  if [[ -n "$health_pid" ]] && kill -0 "$health_pid" 2>/dev/null; then
    kill "$health_pid" 2>/dev/null || true
    wait "$health_pid" 2>/dev/null || true
  fi
  rm -rf "$health_root"
}
trap cleanup EXIT INT TERM

export TRACEGATE_HOST=127.0.0.1
export TRACEGATE_PORT="$(uv run python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
export TRACEGATE_LOCAL_API_TOKEN="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export TRACEGATE_DATA_DIR="$health_root/data"

"$sidecar" serve >"$health_root/sidecar.log" 2>&1 &
health_pid=$!

healthy=false
for _ in {1..120}; do
  if uv run tracegate-studio health --timeout 1 >/dev/null 2>&1; then
    healthy=true
    break
  fi
  if ! kill -0 "$health_pid" 2>/dev/null; then
    break
  fi
  sleep 0.25
done

if [[ "$healthy" != true ]]; then
  echo "Packaged Sidecar failed its authenticated health check." >&2
  sed -n '1,160p' "$health_root/sidecar.log" >&2
  exit 1
fi

kill "$health_pid"
wait "$health_pid" 2>/dev/null || true
health_pid=""
apps/desktop/scripts/stage-sidecar.sh "$sidecar"
echo "$sidecar"
