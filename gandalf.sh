#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GANDALF_ROOT="$SCRIPT_DIR"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export MCP_DEBUG="${MCP_DEBUG:-true}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SERVER_DIR="$GANDALF_ROOT/server"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"
TESTS_DIR="$GANDALF_ROOT/tests"

show_usage() {
    cat <<EOF
Gandalf CLI

USAGE:
    gandalf.sh <command> [options]

COMMANDS:
    conv <subcommand>           Conversation management
    setup [options]             Setup MCP server requirements
    install [repo] [options]    Install MCP server to repository/directory
    reset [options]             Reset MCP configuration (does not clear conversations)
    run [options]               Run MCP server directly (debugging)
    test [test-name]            Run tests
    lembas [repo] [-f|--force]  Run lembas: test -> reset -> install -> test
    help                        Show this help message

EOF
}

COMMAND="${1:-help}"

if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is required but not found in PATH" >&2
    exit 1
fi

case "$COMMAND" in
"conv") shift 1 && "$SCRIPTS_DIR/conversations.sh" "$@" ;;
"setup") shift 1 && "$SCRIPTS_DIR/setup.sh" "$@" ;;
"install") shift 1 && "$SCRIPTS_DIR/install.sh" "$@" ;;
"reset") shift 1 && "$SCRIPTS_DIR/reset.sh" "$@" ;;
"run") shift 1 && python3 "$SERVER_DIR/main.py" "$@" ;;
"test") shift 1 && "$TESTS_DIR/test-suite.sh" "$@" ;;
"lembas") shift 1 && "$SCRIPTS_DIR/lembas.sh" "$@" ;;
"help" | "-h" | "--help") show_usage ;;
*)
    echo -e "\nError: Unknown command: $COMMAND\n" >&2
    show_usage
    exit 1
    ;;
esac
