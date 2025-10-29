#!/bin/bash

set -e

# Always run from this script's directory
cd "$(cd "$(dirname "$0")" && pwd)"

VENV_DIR=".venv_failure"

echo "=========================================="
echo "Failure Mode Analysis - Local Setup"
echo "=========================================="

# Check Python venv availability
if ! python3 -c "import venv" &> /dev/null; then
    echo "Error: Python venv module is not available."
    echo "On Debian/Ubuntu systems, install it with:"
    echo "  sudo apt update && sudo apt install python3-venv"
    exit 1
fi

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
echo "Activated $VENV_DIR"

# Upgrade pip and install local dependencies (isolated from project root)
python -m pip install --upgrade pip
pip install "openai>=2.6.0,<3" python-dotenv

echo ""
echo "Done. To activate this environment later, run:"
echo "source $(pwd)/$VENV_DIR/bin/activate"
echo ""
echo "Note: The analyzer loads OPENAI_API_KEY from ../../.env (relative to this folder)"
echo "      Ensure ../../.env exists and contains OPENAI_API_KEY=..."
