#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "TraceGate Studio macOS packaging requires a macOS arm64 host." >&2
  exit 1
fi

app_path="apps/desktop/src-tauri/target/release/bundle/macos/TraceGate Studio.app"
sidecar_path="apps/desktop/src-tauri/binaries/tracegate-backend-aarch64-apple-darwin"
artifact_dir="artifacts/macos"
archive="$artifact_dir/TraceGate-Studio-macos-arm64.zip"

if [[ ! -d "$app_path" || ! -x "$sidecar_path" ]]; then
  echo "Build the native application and Sidecar before packaging." >&2
  exit 66
fi

mkdir -p "$artifact_dir"
rm -f "$archive"
ditto -c -k --sequesterRsrc --keepParent "$app_path" "$archive"
(
  cd "$artifact_dir"
  shasum -a 256 "$(basename "$archive")" > SHA256SUMS.txt
)
echo "$archive"
cat "$artifact_dir/SHA256SUMS.txt"
