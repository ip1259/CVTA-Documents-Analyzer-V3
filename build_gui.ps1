$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot
$env:UV_CACHE_DIR = Join-Path $ProjectRoot ".uv-cache"

uv run pyinstaller `
    --noconfirm `
    --clean `
    "CVTA-Documents-Analyzer-GUI.spec"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE."
}

Write-Host ""
Write-Host "GUI build completed:"
Write-Host "  dist\CVTA-Documents-Analyzer\CVTA-Documents-Analyzer.exe"
