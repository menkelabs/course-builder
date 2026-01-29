#!/bin/bash
# Phase 1 Setup Script
# Sets up the virtual environment and installs Phase 1
# Run from project root: bash phase1/setup_venv.sh

set -e

# Get the project root directory (parent of phase1/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"

echo "=========================================="
echo "Phase 1 Setup Script"
echo "=========================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo "Virtual env:  $VENV_PATH"
echo ""

# Check if .venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install Phase 1 in editable mode
echo ""
echo "Installing Phase 1..."
cd "$SCRIPT_DIR"
pip install -e .

echo ""
echo "=========================================="
echo "✓ Phase 1 setup complete!"
echo "=========================================="
echo ""
echo "You can now use Phase 1 commands:"
echo ""
echo "  # Activate the virtual environment first:"
echo "  source $VENV_PATH/bin/activate"
echo ""
echo "  # Then run Phase 1 commands:"
echo "  python -m phase1.cli --help"
echo "  python -m phase1.cli interactive-select --course-name MyCourse -o workspace/"
echo ""
echo "Or install phase1 as a command:"
echo "  pip install -e phase1/"
echo "  phase1 --help"
