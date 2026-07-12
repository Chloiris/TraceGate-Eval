$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if (-not $env:TRACEGATE_HOST) { $env:TRACEGATE_HOST = "127.0.0.1" }
if (-not $env:TRACEGATE_PORT) { $env:TRACEGATE_PORT = "8765" }
if (-not $env:TRACEGATE_DATA_DIR) { $env:TRACEGATE_DATA_DIR = Join-Path $RootDir ".tracegate-dev" }
if (-not $env:TRACEGATE_LOCAL_API_TOKEN) {
    $RandomBytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    $env:TRACEGATE_LOCAL_API_TOKEN = [Convert]::ToBase64String($RandomBytes)
}
$env:TRACEGATE_DEV_API_TARGET = "http://$($env:TRACEGATE_HOST):$($env:TRACEGATE_PORT)"
$env:VITE_TRACEGATE_API_BASE_URL = "/api/v1"
$env:VITE_TRACEGATE_API_TOKEN = $env:TRACEGATE_LOCAL_API_TOKEN

$Backend = $null
try {
    $Backend = Start-Process -FilePath "uv" -ArgumentList @("run", "tracegate-studio", "serve") -NoNewWindow -PassThru
    pnpm dev
} finally {
    if ($Backend -and -not $Backend.HasExited) {
        Stop-Process -Id $Backend.Id -ErrorAction SilentlyContinue
        $Backend.WaitForExit(5000) | Out-Null
    }
}
