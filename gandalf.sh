#!/bin/bash
# Gandalf MCP Server - Main Entry Point
# This script provides the primary interface for managing the Gandalf MCP server

set -euo pipefail

readonly SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
readonly GANDALF_ROOT="$(dirname "$SCRIPT_PATH")"
readonly SCRIPTS_DIR="$GANDALF_ROOT/scripts"
readonly SERVER_DIR="$GANDALF_ROOT/server"
readonly PYTHON_MIN_MAJOR=3
readonly PYTHON_MIN_MINOR=10

export PYTHONPATH="$SERVER_DIR:${PYTHONPATH:-}"
export GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"

# Logging functions
print_header() {
    local message="$1"
    cat <<EOF

==========================================
$message
==========================================
EOF
}

print_info() {
    local message="$1"
    echo "[INFO] $message"
}

print_error() {
    local message="$1"
    echo "[ERROR] $message" >&2
}

show_help() {
    cat <<EOF
Gandalf MCP Server - AI conversation history analysis and intelligent project context

Usage: $0 COMMAND [OPTIONS]

Commands:
    run                 Start the MCP server
    install             Install MCP server globally for all supported tools
    uninstall           Remove MCP server configurations
    test                Run test suites (shell, python, or specific test categories)
    lembas              Run comprehensive test suite and validation
    status              Show server status and configuration
    help                Show this help message

Options:
    --help, -h          Show help for specific command
    --debug             Enable debug mode with verbose output
    --project-root DIR  Set project root directory (for run command)

Examples:
    $0 install                    # Install for all detected tools
    $0 run --project-root /path   # Start server for specific project
    $0 test --all                 # Run all tests
    $0 test core                  # Run core tests only
    $0 lembas                     # Run full test suite
    $0 status                     # Check installation status

For more information, see: $GANDALF_ROOT/README.md

EOF
}

check_dependencies() {
    echo "Checking system dependencies..."

    local install_missing=false
    if [[ "${1:-}" == "--install" ]]; then
        install_missing=true
    fi

    local failed=false

    if ! command -v python3 &>/dev/null; then
        echo "ERROR: Python 3 not found"
        failed=true
    else
        local python_version
        python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        if printf '%s\n' "${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}" "$python_version" | sort -V | head -n1 | grep -q "^${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}$"; then
            echo "Python $python_version found"
        else
            echo "ERROR: Python $python_version found, but ${PYTHON_MIN_MAJOR}.${PYTHON_MIN_MINOR}+ required"
            failed=true
        fi
    fi

    if command -v pip3.10 &>/dev/null; then
        echo "pip3.10 found"
    else
        echo "ERROR: pip3.10 not found"
        failed=true
    fi

    if command -v git &>/dev/null; then
        echo "Git found: $(git --version | head -1)"
    else
        echo "ERROR: Git not found"
        failed=true
    fi

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

    local -a required_dirs=("server" "scripts")
    local -a required_files=("server/src/main.py" "gandalf.sh")

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
        echo "Dependency check failed. Please install missing dependencies."
        echo "For development setup, run: ../../scripts/setup.sh"
        return 1
    fi

    echo "All dependencies satisfied"
    return 0
}

run_server() {
    local project_root="${1:-$PWD}"
    local debug_mode="${2:-false}"

    if [[ "$debug_mode" == "true" ]]; then
        export MCP_DEBUG="true"
    fi

    # Activate virtual environment if it exists (check server-level venv first)
    if [[ -f "$SERVER_DIR/venv/bin/activate" ]]; then
        source "$SERVER_DIR/venv/bin/activate"
    elif [[ -f "$GANDALF_ROOT/.venv/bin/activate" ]]; then
        source "$GANDALF_ROOT/.venv/bin/activate"
    fi

    cd "$SERVER_DIR"
    exec python3 -m src.main --project-root "$project_root"
}

install_server() {
    echo "Installing Gandalf MCP Server..."
    exec "$SCRIPTS_DIR/install.sh" "$@"
}

uninstall_server() {
    echo "Uninstalling Gandalf MCP Server..."
    exec "$SCRIPTS_DIR/uninstall.sh" "$@"
}

run_lembas() {
    echo "Running Lembas - Comprehensive Test Suite..."
    exec "$SCRIPTS_DIR/lembas.sh" "$@"
}

run_tests() {
    echo "Running Test Suite..."
    exec "$SCRIPTS_DIR/test-suite.sh" "$@"
}

show_status() {
    cat <<EOF

Gandalf MCP Server Status
=========================
Root: $GANDALF_ROOT
Home: $GANDALF_HOME
Python Path: $PYTHONPATH

EOF

    if check_dependencies >/dev/null 2>&1; then
        echo "Dependencies: ✓ All satisfied"
    else
        echo "Dependencies: ✗ Issues found"
        echo "Run '$0 help' for dependency information"
    fi

    echo ""
    echo "Configuration files:"

    local -a config_files=(
        "$HOME/.cursor/mcp.json"
        "$HOME/.claude/mcp.json"
        "$HOME/.codeium/windsurf/mcp_config.json"
    )

    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            echo "  ✓ $config_file"
        else
            echo "  ✗ $config_file"
        fi
    done
}

main() {
    local command="${1:-help}"
    local debug_mode="false"
    local project_root=""

    case "$command" in
    run)
        shift
        while [[ $# -gt 0 ]]; do
            case "$1" in
            --debug)
                debug_mode="true"
                shift
                ;;
            --project-root)
                project_root="$2"
                shift 2
                ;;
            --help | -h)
                echo "Usage: $0 run [--debug] [--project-root DIR]"
                echo "Start the Gandalf MCP server"
                exit 0
                ;;
            *)
                echo "Error: Unknown option for run command: $1" >&2
                exit 1
                ;;
            esac
        done
        run_server "${project_root:-$PWD}" "$debug_mode"
        ;;
    install)
        shift
        install_server "$@"
        ;;
    uninstall)
        shift
        uninstall_server "$@"
        ;;
    test)
        shift
        run_tests "$@"
        ;;
    lembas)
        shift
        run_lembas "$@"
        ;;
    status)
        show_status
        ;;
    help | --help | -h)
        show_help
        ;;
    *)
        echo "Error: Unknown command: $command" >&2
        echo "Run '$0 help' for usage information" >&2
        exit 1
        ;;
    esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
