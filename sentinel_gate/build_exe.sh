#!/bin/bash
# Build script for Linux - Unified SentinelGate UI & CLI

# 1. Ensure we are in the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "--- SentinelGate Build System v3.5 (Linux) ---"
echo "Source: $SCRIPT_DIR"

# 2. Check/Create Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Step 0/3: Creating Virtual Environment (.venv)..."
    python3 -m venv .venv
fi

# 3. Activate Virtual Environment
echo "Step 1/3: Activating environment and installing dependencies..."
source .venv/bin/activate

# 4. Check dependencies
python3 -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

# 3. Build the executable
echo "Step 2/3: Building standalone binary..."
# We use the .spec file for advanced bundling (includes app.py)
pyinstaller --clean sentinel_gate.spec

# 4. Cleanup and Finish
echo "Step 3/3: Finalizing..."
if [ -f "dist/sentinel_gate" ]; then
    echo -e "\033[0;32mSUCCESS! Executable ready at: dist/sentinel_gate\033[0m"
    echo "Usage: ./dist/sentinel_gate --help"
    echo "Usage: ./dist/sentinel_gate --studio"
else
    echo -e "\033[0;31mFAILED: Executable not found. Check logs above.\033[0m"
fi
