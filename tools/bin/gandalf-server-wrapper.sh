#!/usr/bin/env bash
# Gandalf MCP Server Wrapper
# Provides environment isolation and IDE integration for consolidated installations

set -euo pipefail

readonly SERVER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_DIR="$SERVER_DIR/.venv"
readonly PYTHON_BIN="$VENV_DIR/bin/python3"

# Activate virtual environment
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    source "$VENV_DIR/bin/activate"
fi

# Set Python path for module resolution
export PYTHONPATH="$SERVER_DIR:${PYTHONPATH:-}"

# Set version from local VERSION file if available
if [[ -f "$SERVER_DIR/VERSION" ]]; then
    export GANDALF_SERVER_VERSION="$(cat "$SERVER_DIR/VERSION")"
fi

# Read default project root from config file
readonly CONFIG_FILE="$SERVER_DIR/.gandalf-config"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Handle run command
if [[ "${1:-}" == "run" ]]; then
    shift
    project_root_arg="${DEFAULT_PROJECT_ROOT:-$(pwd)}"
    debug_mode="false"
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
        --project-root)
            project_root_arg="$2"
            shift 2
            ;;
        --debug)
            debug_mode="true"
            export MCP_DEBUG="true"
            shift
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            exit 1
            ;;
        esac
    done
    
    cd "$SERVER_DIR"
    exec "$PYTHON_BIN" -m src.main --project-root "$project_root_arg"
else
    # Pass through other commands
    cd "$SERVER_DIR"
    exec "$PYTHON_BIN" -m src.main "$@"
fi 