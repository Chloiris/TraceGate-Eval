#!/usr/bin/env bash
set -euo pipefail

if ! command -v sips >/dev/null 2>&1; then
  echo "sips is required to regenerate the committed icon assets on macOS" >&2
  exit 69
fi
if ! command -v iconutil >/dev/null 2>&1; then
  echo "iconutil is required to regenerate the committed macOS icon" >&2
  exit 69
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
icon_dir="$script_dir/../src-tauri/icons"
source_svg="$icon_dir/icon.svg"

sips -s format png -z 32 32 "$source_svg" --out "$icon_dir/32x32.png" >/dev/null
sips -s format png -z 128 128 "$source_svg" --out "$icon_dir/128x128.png" >/dev/null
sips -s format png -z 256 256 "$source_svg" --out "$icon_dir/128x128@2x.png" >/dev/null
sips -s format png -z 512 512 "$source_svg" --out "$icon_dir/icon.png" >/dev/null

temporary_directory=$(mktemp -d)
trap 'rm -rf "$temporary_directory"' EXIT
iconset="$temporary_directory/TraceGate.iconset"
mkdir -p "$iconset"
sips -s format png -z 16 16 "$source_svg" --out "$iconset/icon_16x16.png" >/dev/null
sips -s format png -z 32 32 "$source_svg" --out "$iconset/icon_16x16@2x.png" >/dev/null
sips -s format png -z 32 32 "$source_svg" --out "$iconset/icon_32x32.png" >/dev/null
sips -s format png -z 64 64 "$source_svg" --out "$iconset/icon_32x32@2x.png" >/dev/null
sips -s format png -z 128 128 "$source_svg" --out "$iconset/icon_128x128.png" >/dev/null
sips -s format png -z 256 256 "$source_svg" --out "$iconset/icon_128x128@2x.png" >/dev/null
sips -s format png -z 256 256 "$source_svg" --out "$iconset/icon_256x256.png" >/dev/null
sips -s format png -z 512 512 "$source_svg" --out "$iconset/icon_256x256@2x.png" >/dev/null
sips -s format png -z 512 512 "$source_svg" --out "$iconset/icon_512x512.png" >/dev/null
sips -s format png -z 1024 1024 "$source_svg" --out "$iconset/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$iconset" -o "$icon_dir/icon.icns"
sips -s format ico -z 256 256 "$icon_dir/icon.png" --out "$icon_dir/icon.ico" >/dev/null

echo "regenerated TraceGate Studio icon assets"
