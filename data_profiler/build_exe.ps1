# Build script for Windows (PowerShell)

# 1. Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt
pip install pyinstaller

# 2. Build the executable
Write-Host "Building executable with PyInstaller..." -ForegroundColor Cyan
# --onefile: Single executable
# --name: Executable name
# --hidden-import: Ensure dynamic/indirect dependencies are included
# --clean: Clean cache before build
pyinstaller `
    --onefile `
    --name data-profiler `
    --hidden-import google.cloud.bigquery `
    --hidden-import ydata_profiling `
    --hidden-import mcp `
    --hidden-import pydantic `
    --hidden-import matplotlib.backends.backend_svg `
    --hidden-import matplotlib.backends.backend_pdf `
    --hidden-import matplotlib.backends.backend_agg `
    --collect-all ydata_profiling `
    --collect-all matplotlib `
    --clean `
    ..\main.py

Write-Host "Build complete! Check the dist/ folder for data-profiler.exe" -ForegroundColor Green
