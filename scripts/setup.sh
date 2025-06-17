#!/bin/bash
set -eo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"
SERVER_DIR="$GANDALF_ROOT/server"

usage() {
    cat <<EOF
Usage: ./setup.sh [OPTIONS]

Verify MCP server requirements (one-time setup).

Options:
    -f, --force     Force verification
    -h, --help      Show this help

Examples:
    ./setup.sh      # Standard verification
    ./setup.sh -f   # Force re-verification

EOF
}

FORCE=${FORCE:-false}

while [[ $# -gt 0 ]]; do
    case $1 in
    -f | --force) FORCE=true ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "Error: Unknown option $1"
        usage
        exit 1
        ;;
    esac
done

echo "Setting up MCP server..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "Error: Python 3.10+ is required"
    python3 --version
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo "Error: Git is required but not found"
    exit 1
fi

if [[ ! -d "$SERVER_DIR" ]]; then
    echo "Error: Server directory not found: $SERVER_DIR"
    exit 1
fi

SERVER_SCRIPT="$SERVER_DIR/main.py"
if [[ ! -f "$SERVER_SCRIPT" ]]; then
    echo "Error: MCP server script not found: $SERVER_SCRIPT"
    exit 1
fi

# No checks, always chmod
chmod +x "$GANDALF_ROOT/gandalf.sh" "$SCRIPT_DIR"/* "$SERVER_SCRIPT" 2>/dev/null || true

echo "Testing MCP server..."
if ! python3 "$SERVER_SCRIPT" --help >/dev/null 2>&1; then
    echo "Error: MCP server test failed"
    exit 1
fi

cat <<EOF
MCP Server Setup Complete!

Requirements verified:
- Python 3.10+: $(python3 --version)
- Git: $(git --version | head -1)
- Server: $SERVER_SCRIPT

Configuration:
- AI Model Weights: gandalf/weights.yaml
- System Constants: server/config/constants.py

Next Steps:
    1. Run: gandalf.sh install
    2. Restart Cursor
    3. Test with: gandalf.sh test

Optional: Add gandalf.sh to your PATH for global access:
    echo 'export PATH="$GANDALF_ROOT:\$PATH"' >> ~/.bashrc
    source ~/.bashrc
EOF
