#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$SCRIPT_DIR"

export PYTHONPATH="$GANDALF_ROOT:${PYTHONPATH:-}"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export MCP_DEBUG="${MCP_DEBUG:-true}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
SERVER_DIR="$GANDALF_ROOT/src"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"
TESTS_DIR="$GANDALF_ROOT/tests"

show_usage() {
    cat <<EOF
$MCP_SERVER_NAME CLI

USAGE:
    gandalf.sh <command> [options]

COMMANDS:
    deps [options]              Check system dependencies
    conv <subcommand>           Conversation management
    install [repo] [options]    Install MCP server to repository/directory
    analyze_messages [options]  Analyze comprehensive message logs
    run [options]               Run MCP server directly (debugging)
    test [test-name] [options]  Run tests (defaults to all tests: shell + python)
    lembas [repo] [-f|--force]  Run lembas: test -> reset -> install -> test
    help                        Show this help message

EXAMPLES:
    gandalf.sh deps                             # Check all dependencies
    gandalf.sh deps --install                   # Check and offer to install missing deps
    gandalf.sh install                          # Install to current repo
    gandalf.sh install -r                       # Reset existing server and install fresh
    gandalf.sh test                             # Run all tests (shell + python)
    gandalf.sh test --shell                     # Run shell tests only
    gandalf.sh test --python                    # Run Python tests only
    gandalf.sh test core                        # Run core tests only
    gandalf.sh lembas /path/to/repo             # Full test cycle

NOTES:
    - 'deps' verifies Python, Git, BATS, and other system requirements
    - 'install' verifies requirements, configures MCP server, and tests connectivity
    - 'install -r' combines reset and install for a fresh setup
    - 'install' updates Cursor's config but doesn't restart the server
    - 'test' runs all tests by default; use --shell or --python for specific types
    - Set MCP Logs level to DEBUG/INFO in Cursor for detailed visibility

EOF
}

COMMAND="${1:-help}"

if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is required but not found in PATH" >&2
    exit 1
fi

case "$COMMAND" in
"deps") shift 1 && "$SCRIPTS_DIR/check-dependencies.sh" "$@" ;;
"conv") shift 1 && "$SCRIPTS_DIR/conversations.sh" "$@" ;;
"install") shift 1 && "$SCRIPTS_DIR/install.sh" "$@" ;;
"analyze_messages") shift 1 && "$SCRIPTS_DIR/analyze_messages.sh" "$@" ;;
"run")
    shift 1
    python3 "$SERVER_DIR/main.py" "$@"
    ;;
"test")
    shift 1
    if [[ $# -eq 0 ]]; then
        bash "$TESTS_DIR/test-suite.sh"
    else
        bash "$TESTS_DIR/test-suite.sh" "$@"
    fi
    ;;
"lembas") shift 1 && "$SCRIPTS_DIR/lembas.sh" "$@" ;;
"help" | "-h" | "--help") show_usage ;;
*)
    echo -e "\nError: Unknown command: $COMMAND\n" >&2
    show_usage
    exit 1
    ;;
esac
