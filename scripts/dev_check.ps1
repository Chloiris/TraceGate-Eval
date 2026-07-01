$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Command
    )

    & $Command[0] @($Command[1..($Command.Length - 1)])
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $($Command -join ' ')"
    }
}

Write-Host "[TraceGate] compile check"
Invoke-CheckedCommand @("python", "-m", "compileall", ".")

Write-Host "[TraceGate] tests"
Invoke-CheckedCommand @("pytest", "-q")

Write-Host "[TraceGate] CLI help if available"
$helpPath = Join-Path $env:TEMP "tracegate_cli_help.txt"
python -m tracegate --help *> $helpPath
$hasHelp = $LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $helpPath) -and ((Get-Item -LiteralPath $helpPath).Length -gt 0)
if (-not $hasHelp) {
    python -m tracegate.cli --help *> $helpPath
    $hasHelp = $LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $helpPath) -and ((Get-Item -LiteralPath $helpPath).Length -gt 0)
}

if ($hasHelp) {
    Get-Content -LiteralPath $helpPath
} else {
    Write-Host "TraceGate CLI help not available yet; this may be implemented on Mac development phase."
}

Write-Host "[TraceGate] done"
