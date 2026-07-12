$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

uv run pytest -q
pnpm lint
pnpm typecheck
pnpm test
cargo fmt --manifest-path apps/desktop/src-tauri/Cargo.toml --all -- --check
cargo clippy --manifest-path apps/desktop/src-tauri/Cargo.toml --all-targets --all-features -- -D warnings
cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml
