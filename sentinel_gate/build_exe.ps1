# Build script for Windows (PowerShell) - Unified SentinelGate UI & CLI

# 1. Ensure absolute path using the script's own location
$SourcePath = $PSScriptRoot
if (-not $SourcePath) { $SourcePath = Get-Location }

Write-Host "--- SentinelGate Build System v3.5 ---" -ForegroundColor Cyan
Write-Host "Source: $SourcePath"

# 2. Check/Create Virtual Environment
if (-not (Test-Path "$SourcePath\.venv")) {
    Write-Host "Step 0/3: Creating Virtual Environment (.venv)..." -ForegroundColor Yellow
    python -m venv "$SourcePath\.venv"
}

# 3. Activate Virtual Environment
Write-Host "Step 1/3: Activating environment and installing dependencies..." -ForegroundColor Cyan
& "$SourcePath\.venv\Scripts\Activate.ps1"

# Standardize on relative path to requirements since we're in the source root
python -m pip install --upgrade pip
pip install -r "$SourcePath\requirements.txt"
pip install pyinstaller

# 3. Build the executable
Write-Host "Step 2/3: Starting PyInstaller build..." -ForegroundColor Cyan
Write-Host "Note: This can take 5-15 minutes due to heavy dependencies (Streamlit, Evidently)." -ForegroundColor Gray
cd "$SourcePath"

# We use the .spec file for advanced bundling (includes app.py)
Write-Host ">>> Phase: Analyzing scripts and collecting imports..." -ForegroundColor Yellow
pyinstaller --clean sentinel_gate.spec

# 4. Cleanup and Finish
Write-Host "Step 3/3: Finalizing and checking output..." -ForegroundColor Cyan
# Go back to the original directory (where the script started)
cd "$SourcePath/.."

# Check for the executable inside the onedir folder
$ExePath = "$SourcePath/dist/sentinel_gate/sentinel_gate.exe"
if (Test-Path $ExePath) {
    Write-Host "SUCCESS! Deployment complete." -ForegroundColor Green
    Write-Host "Executable ready at: $ExePath" -ForegroundColor Green
    Write-Host "Usage from project root: ./sentinel_gate/dist/sentinel_gate/sentinel_gate.exe --studio" -ForegroundColor Yellow
} else {
    Write-Host "FAILED: Executable not found in sentinel_gate/dist/sentinel_gate/. Check logs above." -ForegroundColor Red
}
