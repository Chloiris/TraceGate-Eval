#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/macos-arm64-pyinstaller-output" >&2
  exit 64
fi

source_binary=$1
if [[ ! -f "$source_binary" || ! -x "$source_binary" ]]; then
  echo "source must be an executable file" >&2
  exit 66
fi

description=$(file -b "$source_binary")
if [[ "$description" != *"Mach-O 64-bit executable arm64"* ]]; then
  echo "refusing non-macOS-arm64 Sidecar: $description" >&2
  exit 65
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
destination="$script_dir/../src-tauri/binaries/tracegate-backend-aarch64-apple-darwin"
install -m 0755 "$source_binary" "$destination"
echo "staged $(basename "$destination")"
