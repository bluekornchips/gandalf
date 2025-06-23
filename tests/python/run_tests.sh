#!/bin/bash

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Change to gandalf root directory
cd "$GANDALF_ROOT"

# Export GANDALF_ROOT for the tests to use
export GANDALF_ROOT

# Activate virtual environment if it exists
if [[ -f ".venv/bin/activate" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check for pytest
if ! command -v pytest &>/dev/null; then
    echo "Installing pytest..."
    pip install pytest
fi

# Run Python tests, excluding deprecated files
echo "Running Python tests (excluding deprecated files)..."
echo "GANDALF_ROOT: $GANDALF_ROOT"
python3 -m pytest tests/python/ -v --ignore=tests/python/test_server_core_deprecated.py

echo "All Python tests completed successfully!" 