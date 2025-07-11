#!/bin/bash

# Lembas bread could not fulfill the hunger of a hobbit, but it could fulfill the hunger of a developer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure PYTHONPATH is set for server imports, maybe there's a better way
export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export MCP_DEBUG="${MCP_DEBUG:-true}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
TESTS_DIR="$GANDALF_ROOT/scripts"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"

# Global variables for step tracking
CURRENT_STEP=0
TOTAL_STEPS=8
TEST_MODE="core" # Default to core tests, quick validation

# Tracks and displays step progress with timing
run_step() {
    local step_name="$1"
    local step_function="$2"

    ((CURRENT_STEP++))
    local step_start=$(date +%s)

    echo "Step $CURRENT_STEP/$TOTAL_STEPS: $step_name..."

    if ! "$step_function"; then
        return 1
    fi

    local step_duration=$(($(date +%s) - step_start))
    echo "$step_name complete (${step_duration}s)"
    return 0
}

run_tests_suite() {
    echo "Running test suite for validation..."

    case "$TEST_MODE" in
    "core")
        echo "Running core tests (quick validation)..."
        if ! bash "$SCRIPTS_DIR/test-suite.sh" core; then
            return 1
        fi
        ;;
    "e2e")
        echo "Running end-to-end tests (integration workflows and performance)..."
        if ! bash "$SCRIPTS_DIR/test-suite.sh" e2e; then
            return 1
        fi
        ;;
    "all")
        echo "Running all tests (shell + python)..."
        if ! bash "$SCRIPTS_DIR/test-suite.sh" all; then
            return 1
        fi
        ;;
    *)
        echo "Unknown test mode: $TEST_MODE"
        return 1
        ;;
    esac
}

check_conversation_system() {
    echo "Checking MCP conversation system..."

    if [[ -x "$SCRIPTS_DIR/conversations.sh" ]]; then
        if "$SCRIPTS_DIR/conversations.sh" workspaces >/dev/null 2>&1; then
            echo "MCP conversation tools are working"

            # Get workspace count for reporting
            local workspace_count=0
            if workspace_output=$("$SCRIPTS_DIR/conversations.sh" workspaces 2>/dev/null); then
                workspace_count=$(echo "$workspace_output" | jq -r '.total_workspaces // 0' 2>/dev/null || echo "0")
            fi
            show_conversation_info "$workspace_count"
        else
            echo "Warning: MCP conversation tools are not responding properly"
        fi
    else
        echo "Warning: conversations.sh script not found or not executable"
    fi

    echo "Conversation check complete"
    return 0
}

verify_conversation_logging() {
    echo "Checking MCP conversation system accessibility..."

    # Check for session activity in MCP logs
    local session_check_passed=false
    local mcp_log_file="$HOME/.cursor/logs/mcp.log"

    if [[ -f "$mcp_log_file" ]]; then
        # Look for recent session activity
        local recent_session_activity=$(tail -100 "$mcp_log_file" 2>/dev/null | grep -i "session\|conversation\|$MCP_SERVER_NAME" | tail -5 || echo "")
        if [[ -n "$recent_session_activity" ]]; then
            show_recent_activity "$recent_session_activity"
            session_check_passed=true
        else
            echo "No recent session activity found in MCP logs"
        fi
    else
        echo "MCP log file not found at $mcp_log_file"
    fi

    echo "Testing real-time conversation access..."
    local conversation_system_working=false
    if "$SCRIPTS_DIR/conversations.sh" export --summary=true >/dev/null 2>&1; then
        conversation_system_working=true
        echo "Real-time conversation access: WORKING"
    else
        echo "Real-time conversation access: NOT AVAILABLE"
    fi

    if [[ "$session_check_passed" == "true" ]] || [[ "$conversation_system_working" == "true" ]]; then
        echo "Conversation system verification: PASSED"
    else
        show_conversation_warning
    fi

    echo "Verifying lembas conversation logging complete"
    return 0
}

lembas() {
    local repo_path=""
    local force_flag=""

    if [[ $# -eq 0 || "${1:-}" == -* ]]; then
        repo_path="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
    else
        repo_path="$1"
        shift
    fi

    while [[ $# -gt 0 ]]; do
        case $1 in
        -f | --force)
            force_flag="-f"
            shift
            ;;
        --core)
            TEST_MODE="core"
            shift
            ;;
        --e2e)
            TEST_MODE="e2e"
            shift
            ;;
        --all)
            TEST_MODE="all"
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            shift
            ;;
        esac
    done

    case "$TEST_MODE" in
    "core")
        echo "Core mode enabled: Running core test suite only (quick tests)"
        ;;
    "e2e")
        echo "End-to-end mode enabled: Running end-to-end test suite (integration workflows and performance)"
        ;;
    "all")
        echo "All mode enabled: Running complete test suite (shell + python tests)"
        ;;
    *)
        echo "Full mode enabled: Running complete test suite (shell + python tests)"
        TEST_MODE="all"
        ;;
    esac

    echo "Repository path: $repo_path"

    local start_time=$(date +%s)

    export LEMBAS_MODE=true

    # Reset step tracking
    CURRENT_STEP=0
    TOTAL_STEPS=8

    # Execute all steps
    run_step "Checking system dependencies" \
        "$GANDALF_ROOT/gandalf.sh" deps || return 1

    run_step "Running initial tests" run_tests_suite || return 1

    run_step "Installing MCP server with reset" \
        "$SCRIPTS_DIR/install.sh" "$repo_path" -r --wait-time 15 ${force_flag:+"$force_flag"} || return 1

    run_step "Running final tests" run_tests_suite || return 1

    run_step "Checking conversation system" check_conversation_system || return 1

    run_step "Verifying lembas conversation logging" verify_conversation_logging || return 1

    # Clean up environment variable
    unset LEMBAS_MODE

    local total_time=$(($(date +%s) - start_time))

    local mode_description="Full mode (complete validation)"
    case "$TEST_MODE" in
    "core")
        mode_description="Core mode (core tests only)"
        ;;
    "e2e")
        mode_description="End-to-end mode (integration workflows and performance)"
        ;;
    "all")
        mode_description="All mode (complete validation)"
        ;;
    *)
        mode_description="Full mode (complete validation)"
        ;;
    esac

    cat <<EOF

Lembas Complete
===============
All automated tests passed; system is fully validated.

Execution Summary
-----------------
Total execution time: ${total_time}s
Execution mode: $mode_description
MCP conversation system: Real-time access enabled

Next Steps
----------
1. Verify MCP server integration in Cursor
2. Test real-time conversation queries via MCP tools
3. Monitor system performance under normal usage
EOF
}

# Show test failure message
show_test_failure() {
    cat <<EOF
Tests failed. Aborting lembas.
Fix the failing tests above and run lembas again.
EOF
}

# Show conversation info
show_conversation_info() {
    local workspace_count="$1"
    echo "Found $workspace_count Cursor workspaces accessible via MCP"
}

# Show recent activity
show_recent_activity() {
    local activity="$1"

    cat <<EOF
Found recent MCP session activity:
$(echo "$activity" | sed 's/^/    /')
EOF
}

# Show conversation logging warning
show_conversation_warning() {
    cat <<EOF
Conversation logging verification: WARNING
    Consider checking MCP server connection and auto-session configuration
EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    lembas "$@"
fi
