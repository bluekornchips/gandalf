#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$SCRIPT_DIR"

export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export MCP_DEBUG="${MCP_DEBUG:-true}"
export GANDALF_SERVER_VERSION="${GANDALF_SERVER_VERSION:-2.0.1}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
SERVER_DIR="$GANDALF_ROOT/server/src"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"
TESTS_DIR="$GANDALF_ROOT"

show_usage() {
    cat <<EOF
$MCP_SERVER_NAME CLI

USAGE:
    gandalf.sh <command> [options]

COMMANDS:
    deps [--install]            Check system dependencies
    conv <subcommand>           Conversation management
    install [options]           Install global MCP server for all agentic tools
    uninstall [options]         Uninstall MCP server and remove configurations
    run [options]               Run MCP server directly (debugging)
    test [test-name] [options]  Run tests (defaults to all tests: shell + python)
    lembas [options]            Run lembas: test -> reset -> install -> test
    help                        Show this help message

LEMBAS OPTIONS:
    -f, --force                 Force installation even if server exists
    -s, --short                 Run in short mode (fast tests only)
    --core                      Run core tests only (excludes performance and python tests)

UNINSTALL OPTIONS:
    -f, --force                 Skip confirmation prompts
    --dry-run                   Show what would be removed without removing
    --keep-cache                Keep cache files
    --backup-dir <path>         Custom backup directory

EXAMPLES:
    gandalf.sh deps                             # Check all dependencies
    gandalf.sh deps --install                   # Check and offer to install missing deps
    gandalf.sh install                          # Install globally for all agentic tools
    gandalf.sh install -r                       # Reset existing server and install fresh
    gandalf.sh uninstall                        # Interactive uninstall with prompts
    gandalf.sh uninstall -f                     # Force uninstall without prompts
    gandalf.sh uninstall --dry-run              # Show what would be removed
    gandalf.sh test                             # Run all tests (shell + python)
    gandalf.sh test --shell                     # Run shell tests only
    gandalf.sh test --python                    # Run Python tests only
    gandalf.sh test core                        # Run core tests only
    gandalf.sh lembas                           # Full test cycle with all tests
    gandalf.sh lembas --core                    # Full test cycle with core tests only

NOTES:
    - 'deps' verifies Python, Git, and other system requirements
    - 'install' includes dependency verification, configures global MCP server, and tests connectivity
    - 'install -r' combines reset and install for a fresh global setup
    - 'install' updates agentic tool configs globally and works for all agentic tools (Cursor, Claude Code, Windsurf)
    - 'uninstall' removes all global configurations but preserves conversation history
    - 'test' runs all tests by default; use --shell or --python for specific types
    - 'lembas' runs all tests by default; use --core for faster core-only tests
    - Gandalf works globally across all projects once installed

EOF
}

check_dependencies() {
    echo "Checking system dependencies..."

    local install_missing=false
    if [[ "${1:-}" == "--install" ]]; then
        install_missing=true
    fi

    local failed=false

    # Check Python 3.10+
    if ! command -v python3 &>/dev/null; then
        echo "ERROR: Python 3 not found"
        failed=true
    else
        local python_version
        python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        if printf '%s\n' "3.10" "$python_version" | sort -V | head -n1 | grep -q "^3.10$"; then
            echo "Python $python_version found"
        else
            echo "ERROR: Python $python_version found, but 3.10+ required"
            failed=true
        fi
    fi

    # Check pip3.10
    if command -v pip3.10 &>/dev/null; then
        echo "pip3.10 found"
    else
        echo "ERROR: pip3.10 not found"
        failed=true
    fi

    # Check Git
    if command -v git &>/dev/null; then
        echo "Git found: $(git --version | head -1)"
    else
        echo "ERROR: Git not found"
        failed=true
    fi

    # Check optional tools
    if command -v jq &>/dev/null; then
        echo "jq found (optional)"
    else
        echo "WARNING: jq not found (optional, but recommended)"
    fi

    if command -v bats &>/dev/null; then
        echo "BATS found (for testing)"
    else
        echo "WARNING: BATS not found (needed for shell tests)"
    fi

    # Check project structure
    local required_dirs=("server" "scripts")
    local required_files=("server/src/main.py" "gandalf.sh")

    for dir in "${required_dirs[@]}"; do
        if [[ -d "$GANDALF_ROOT/$dir" ]]; then
            echo "Directory: $dir/"
        else
            echo "ERROR: Missing directory: $dir/"
            failed=true
        fi
    done

    for file in "${required_files[@]}"; do
        if [[ -f "$GANDALF_ROOT/$file" ]]; then
            echo "File: $file"
        else
            echo "ERROR: Missing file: $file"
            failed=true
        fi
    done

    if [[ "$failed" == "true" ]]; then
        echo ""
        echo "FAILED: Some dependencies are missing"
        echo ""
        if [[ "$install_missing" == "true" ]]; then
            cat <<EOF
Suggestions for installation:
- For complete development environment: ../../scripts/setup.sh
- For Python: brew install python3 (macOS) or apt install python3 (Linux)
- For pip3.10: python3 -m ensurepip --upgrade
- For Git: brew install git (macOS) or apt install git (Linux)
- For jq: brew install jq
- For BATS: brew install bats-core
EOF
        else
            echo "Run 'gandalf.sh deps --install' for installation suggestions"
        fi
        return 1
    else
        echo ""
        echo "SUCCESS: All required dependencies satisfied"
        return 0
    fi
}

COMMAND="${1:-help}"

case "$COMMAND" in
"deps") shift 1 && check_dependencies "$@" ;;
"conv") shift 1 && "$SCRIPTS_DIR/conversations.sh" "$@" ;;
"install") shift 1 && "$SCRIPTS_DIR/install.sh" "$@" ;;
"uninstall") shift 1 && "$SCRIPTS_DIR/uninstall.sh" "$@" ;;
"run")
    shift 1
    # Activate virtual environment if it exists
    if [[ -f "$GANDALF_ROOT/.venv/bin/activate" ]]; then
        source "$GANDALF_ROOT/.venv/bin/activate"
    fi
    python3 "$SERVER_DIR/main.py" "$@"
    ;;
"test")
    shift 1
    if [[ $# -eq 0 ]]; then
        bash "$SCRIPTS_DIR/test-suite.sh"
    else
        bash "$SCRIPTS_DIR/test-suite.sh" "$@"
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
