$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

foreach ($CommandName in @("uv", "pnpm", "cargo")) {
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $CommandName"
    }
}

uv sync --extra dev
pnpm install --frozen-lockfile
cargo fetch --manifest-path apps/desktop/src-tauri/Cargo.toml

Write-Host "TraceGate Studio dependencies are ready."
