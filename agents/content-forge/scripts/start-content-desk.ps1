# Matrixly Content Desk — PowerShell launcher (non-technical friendly)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host ""
Write-Host "  Matrixly Content Desk — guided setup" -ForegroundColor Cyan
Write-Host "  Only business details and optional secrets are requested." -ForegroundColor Gray
Write-Host ""

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "  Python not found. Install 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  Enable 'Add python.exe to PATH', then re-run this script." -ForegroundColor Red
    exit 1
}

& python scripts\bootstrap.py @args
exit $LASTEXITCODE
