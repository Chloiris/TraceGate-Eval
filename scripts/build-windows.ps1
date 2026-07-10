$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -notin @("AMD64", "x86_64")) {
    throw "TraceGate Studio Windows builds require a Windows x86_64 host."
}

pnpm --filter @tracegate/web build

if (Test-Path "build\sidecar") { Remove-Item "build\sidecar" -Recurse -Force }
uv run --extra packaging pyinstaller `
    --noconfirm `
    --clean `
    --distpath "build\sidecar\dist" `
    --workpath "build\sidecar\work" `
    "packaging\tracegate-backend.spec"

$Sidecar = Join-Path $RootDir "build\sidecar\dist\tracegate-backend.exe"
if (-not (Test-Path -LiteralPath $Sidecar -PathType Leaf)) {
    throw "PyInstaller did not produce $Sidecar"
}

$Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
$Listener.Start()
$Port = ([System.Net.IPEndPoint]$Listener.LocalEndpoint).Port
$Listener.Stop()
$RandomBytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
$env:TRACEGATE_HOST = "127.0.0.1"
$env:TRACEGATE_PORT = "$Port"
$env:TRACEGATE_LOCAL_API_TOKEN = [Convert]::ToBase64String($RandomBytes)
$HealthRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("tracegate-sidecar-" + [guid]::NewGuid())
$env:TRACEGATE_DATA_DIR = Join-Path $HealthRoot "data"
New-Item -ItemType Directory -Path $HealthRoot | Out-Null

$SidecarProcess = $null
try {
    $SidecarProcess = Start-Process -FilePath $Sidecar -ArgumentList @("serve") -PassThru -NoNewWindow `
        -RedirectStandardOutput (Join-Path $HealthRoot "stdout.log") `
        -RedirectStandardError (Join-Path $HealthRoot "stderr.log")
    $Healthy = $false
    foreach ($Attempt in 1..120) {
        uv run tracegate-studio health --timeout 1 *> $null
        if ($LASTEXITCODE -eq 0) {
            $Healthy = $true
            break
        }
        if ($SidecarProcess.HasExited) { break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $Healthy) {
        Get-Content (Join-Path $HealthRoot "stderr.log") -ErrorAction SilentlyContinue
        throw "Packaged Sidecar failed its authenticated health check."
    }
} finally {
    if ($SidecarProcess -and -not $SidecarProcess.HasExited) {
        Stop-Process -Id $SidecarProcess.Id -ErrorAction SilentlyContinue
        $SidecarProcess.WaitForExit(5000) | Out-Null
    }
    Remove-Item -LiteralPath $HealthRoot -Recurse -Force -ErrorAction SilentlyContinue
}

& "apps\desktop\scripts\stage-sidecar.ps1" -SourceBinary $Sidecar
pnpm --filter @tracegate/desktop build
