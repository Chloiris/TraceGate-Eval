param(
  [Parameter(Mandatory = $true)]
  [string]$SourceBinary
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $SourceBinary -PathType Leaf)) {
  throw "SourceBinary must be a file."
}

$stream = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $SourceBinary))
try {
  if ($stream.Length -lt 2 -or $stream.ReadByte() -ne 0x4D -or $stream.ReadByte() -ne 0x5A) {
    throw "Refusing a Sidecar without a Windows PE MZ header."
  }
}
finally {
  $stream.Dispose()
}

$binaryDirectory = Join-Path $PSScriptRoot "..\src-tauri\binaries"
$destination = Join-Path $binaryDirectory "tracegate-backend-x86_64-pc-windows-msvc.exe"
Copy-Item -LiteralPath $SourceBinary -Destination $destination -Force
Write-Output "staged tracegate-backend-x86_64-pc-windows-msvc.exe"
