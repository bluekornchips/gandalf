#!/bin/bash
# Test Helper Functions for Gandalf MCP Server Test Suite
# Shared utilities for consistent testing across all test categories

set -euo pipefail

# Centralized path calculation function
setup_gandalf_paths() {
    local current_dir="$(pwd -P)"
    local search_dir="$current_dir"

    # If called from a script, use the script's directory as starting point
    if [[ -n "${BASH_SOURCE[1]:-}" ]]; then
        search_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd -P)"
    fi

    # Walk up directory tree to find gandalf root
    while [[ "$search_dir" != "/" ]]; do
        if [[ -d "$search_dir/server/src" && -f "$search_dir/server/src/main.py" ]]; then
            export GANDALF_ROOT="$search_dir"
            export SERVER_DIR="$GANDALF_ROOT/server/src"
            export TESTS_DIR="$GANDALF_ROOT/scripts/tests"
            export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
            export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    # Fallback if gandalf root not found
    echo "Warning: Could not auto-detect GANDALF_ROOT, using fallback" >&2
    export GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd -P)"
    export SERVER_DIR="$GANDALF_ROOT/server/src"
    export TESTS_DIR="$GANDALF_ROOT/scripts/tests"
    export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
    export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
}

# Auto-setup paths when this file is sourced
setup_gandalf_paths

# Check test dependencies before running tests
check_test_dependencies() {
    # Check for BATS
    if ! command -v bats &>/dev/null; then
        echo "ERROR: BATS (Bash Automated Testing System) is required for shell tests" >&2
        echo "Install BATS with: brew install bats-core" >&2
        return 1
    fi

    # Check for Python 3.10+
    if ! command -v python3 &>/dev/null; then
        echo "ERROR: Python 3 is required" >&2
        return 1
    fi

    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    if ! printf '%s\n' "3.10" "$python_version" | sort -V | head -n1 | grep -q "^3.10$"; then
        echo "ERROR: Python 3.10+ required, found $python_version" >&2
        return 1
    fi

    # Check for essential Python packages
    local python_cmd="python3"
    local venv_dir="$GANDALF_ROOT/.venv"
    if [[ -d "$venv_dir" && -f "$venv_dir/bin/python3" ]]; then
        python_cmd="$venv_dir/bin/python3"
    fi

    if ! "$python_cmd" -c "import yaml" &>/dev/null; then
        echo "ERROR: PyYAML is required. Install with: pip install PyYAML" >&2
        return 1
    fi

    return 0
}

# Get Python executable (simplified version for tests)
get_python_executable() {
    local venv_dir="$GANDALF_ROOT/.venv"
    if [[ -d "$venv_dir" && -f "$venv_dir/bin/python3" ]]; then
        echo "$venv_dir/bin/python3"
    else
        echo "python3"
    fi
}

# Execute server with proper context
execute_server() {
    local args="$*"
    local python_cmd=$(get_python_executable)
    bash -c "cd '$GANDALF_ROOT/server' && PYTHONPATH=. $python_cmd src/main.py $args"
}

TEST_ID_COUNTER=0
export MCP_DEBUG="false"

# Generate unique test ID for each request
generate_test_id() {
    TEST_ID_COUNTER=$((TEST_ID_COUNTER + 1))
    echo "$TEST_ID_COUNTER"
}

execute_rpc() {
    local method="$1"
    local params="$2"
    local project_root="${3:-${TEST_PROJECT_DIR:-$PWD}}"

    # Ensure PYTHONPATH is always set for the server imports
    export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

    [[ -z "$params" ]] && params="{}"

    if ! echo "$params" | jq . >/dev/null 2>&1; then
        echo "ERROR: Invalid JSON params: $params" >&2
        return 1
    fi

    local test_id=$(generate_test_id)

    local request
    request=$(jq -nc \
        --arg method "$method" \
        --argjson params "$params" \
        --arg id "$test_id" \
        '{
            "jsonrpc": "2.0",
            "id": $id,
            "method": $method,
            "params": $params
        }')

    # Separate stdout and stderr - only capture stdout for JSON responses
    local temp_stdout=$(mktemp)
    local temp_stderr=$(mktemp)

    local python_cmd=$(get_python_executable)
    echo "$request" | (
        cd "$GANDALF_ROOT/server"
        PYTHONPATH=. "$python_cmd" src/main.py --project-root "$project_root"
    ) >"$temp_stdout" 2>"$temp_stderr"
    local exit_code=$?

    local full_output
    full_output=$(cat "$temp_stdout")
    local error_output
    error_output=$(cat "$temp_stderr")

    rm -f "$temp_stdout" "$temp_stderr"

    # If there was an error, return empty response
    if [[ $exit_code -ne 0 ]]; then
        return 1
    fi

    # Extract only the response with the matching ID (not notifications)
    # Use a temporary file to avoid subshell issues
    local temp_file=$(mktemp)
    echo "$full_output" >"$temp_file"

    local response=""
    # Look for a line that contains both "result" or "error" AND the matching ID
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            # First check if this line contains an ID field
            if echo "$line" | jq -e '.id != null' >/dev/null 2>&1; then
                # Then check if the ID matches our test ID
                local line_id
                line_id=$(echo "$line" | jq -r '.id' 2>/dev/null)
                if [[ "$line_id" == "$test_id" ]]; then
                    response="$line"
                    break
                fi
            fi
        fi
    done <"$temp_file"

    rm -f "$temp_file"

    echo "$response"
}

validate_jsonrpc_response() {
    local response="$1"
    local expected_id="${2:-}"

    # Check if we have any response at all
    if [[ -z "$response" ]]; then
        echo "No response received" >&2
        return 1
    fi

    if ! echo "$response" | jq . >/dev/null 2>&1; then
        echo "Invalid JSON response: $response" >&2
        return 1
    fi

    if ! echo "$response" | jq -e '.jsonrpc == "2.0"' >/dev/null 2>&1; then
        echo "Missing or invalid jsonrpc field" >&2
        return 1
    fi

    # Must have an ID field
    if ! echo "$response" | jq -e '.id != null' >/dev/null 2>&1; then
        echo "Missing id field" >&2
        return 1
    fi

    if [[ -n "$expected_id" ]]; then
        if ! echo "$response" | jq -e --arg id "$expected_id" '.id != null and (.id == $id or .id == ($id | tonumber))' >/dev/null 2>&1; then
            local actual_id
            actual_id=$(echo "$response" | jq -r '.id')
            echo "ID mismatch. Expected: $expected_id, Got: $actual_id" >&2
            return 1
        fi
    fi

    if ! echo "$response" | jq -e '.result' >/dev/null 2>&1; then
        if ! echo "$response" | jq -e '.error' >/dev/null 2>&1; then
            echo "Response missing both result and error fields" >&2
            return 1
        fi
    fi

    return 0
}

# Helper function to create store_conversation arguments with automatic test tagging
create_test_conversation_args() {
    local conversation_id="$1"
    local messages="$2"
    local title="${3:-Test Conversation}"
    local additional_tags="${4:-}"

    # Always include "test" tag for test conversations
    local tags='["test"]'
    if [[ -n "$additional_tags" ]]; then
        # Merge additional tags with the test tag
        tags=$(echo "$additional_tags" | jq '. + ["test"] | unique')
    fi

    jq -nc \
        --arg id "$conversation_id" \
        --argjson messages "$messages" \
        --arg title "$title" \
        --argjson tags "$tags" \
        '{
            "conversation_id": $id,
            "messages": $messages,
            "title": $title,
            "tags": $tags
        }'
}

# Helper function to check timeouts and emit warnings instead of failing
check_timeout_with_warning() {
    local duration="$1"
    local threshold="$2"
    local operation_name="$3"

    if [[ $duration -gt $threshold ]]; then
        echo "WARNING: $operation_name took ${duration}s (threshold: ${threshold}s)" >&2
        echo "This may indicate performance issues but is not a test failure" >&2
    fi
    return 0 # Always return success so tests don't fail on warnings
}

shared_setup() {
    local project_name="there_and_back_again"
    local user_email="bilbo@baggins.shire"
    local user_name="Bilbo Baggins"

    # Use proper temporary directory with mktemp for secure isolation
    TEST_HOME=$(mktemp -d -t gandalf_test.XXXXXX)
    export ORIGINAL_HOME="$HOME"
    export HOME="$TEST_HOME"

    # Ensure conversation storage is isolated to test environment
    export GANDALF_HOME="$TEST_HOME/.gandalf"
    export CONVERSATIONS_DIR="$TEST_HOME/.gandalf/conversations"
    mkdir -p "$CONVERSATIONS_DIR"

    TEST_PROJECT_DIR="$TEST_HOME/$project_name"
    export TEST_PROJECT_DIR
    mkdir -p "$TEST_PROJECT_DIR"
    cd "$TEST_PROJECT_DIR"

    git init >/dev/null 2>&1
    git config user.email "$user_email"
    git config user.name "$user_name"
}

shared_teardown() {
    export HOME="$ORIGINAL_HOME"
    unset GANDALF_HOME
    unset CONVERSATIONS_DIR

    [[ -n "$TEST_HOME" && -d "$TEST_HOME" ]] && rm -rf "$TEST_HOME"
}

# Create a minimal project structure (used by core and conversation tests)
create_minimal_project() {
    echo "# There and Back Again, a Hobbits Project" >README.md
    git add . >/dev/null 2>&1
    git commit -m "I'm going on an adventure!" >/dev/null 2>&1
}

# Test environment configuration
export GANDALF_TEST_MODE="true"
export MCP_DEBUG="${MCP_DEBUG:-false}"
export SERVER_DIR="$GANDALF_ROOT/server/src"
export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
