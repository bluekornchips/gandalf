#!/bin/bash
# Test Helper Functions for Gandalf MCP Server Test Suite
# Shared utilities for consistent testing across all test categories

set -euo pipefail

# Centralized path calculation function
# Usage: source this file and call `setup_gandalf_paths`
setup_gandalf_paths() {
    # Find the gandalf root by looking for the characteristic server directory
    local current_dir="$(pwd -P)"
    local search_dir="$current_dir"

    # If called from a script, use the script's directory as starting point
    if [[ -n "${BASH_SOURCE[1]:-}" ]]; then
        # Kind of hard to read for non shell lovers, so lets break it down:
        # "${BASH_SOURCE[1]}" - This is the path to the script that is sourcing this file
        # "$(dirname "${BASH_SOURCE[1]}")" - Adding in 'dirname' we get the directory of the script that is sourcing this file
        # "pwd -P" - Finds the pwd with the full path, no symlinks
        # Putting it all together, we get the path to the directory of the script that is sourcing this file
        search_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd -P)"
    fi

    # Try walking up the directory tree to find gandalf root, if we can't find it, we'll use the fallback
    while [[ "$search_dir" != "/" ]]; do
        if [[ -d "$search_dir/src" && -f "$search_dir/src/main.py" ]]; then
            export GANDALF_ROOT="$search_dir"
            export SERVER_DIR="$GANDALF_ROOT/src"
            export TESTS_DIR="$GANDALF_ROOT/tests/shell"
            export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
            export PYTHONPATH="$GANDALF_ROOT:${PYTHONPATH:-}"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    # if we can't find it assume we're in tests
    echo "Warning: Could not auto-detect GANDALF_ROOT, using fallback" >&2
    export GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd -P)"
    export SERVER_DIR="$GANDALF_ROOT/src"
    export TESTS_DIR="$GANDALF_ROOT/tests/shell"
    export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
    export PYTHONPATH="$GANDALF_ROOT:${PYTHONPATH:-}"
}

# Auto-setup paths when this file is sourced
setup_gandalf_paths

# Check test dependencies before running tests
check_test_dependencies() {
    local dependency_script="$GANDALF_ROOT/scripts/check-dependencies.sh"

    if [[ ! -f "$dependency_script" ]]; then
        echo "Warning: Dependency checker not found at $dependency_script" >&2
        return 0
    fi

    if ! "$dependency_script" --bats-only --quiet; then
        echo "ERROR: BATS (Bash Automated Testing System) is required for shell tests" >&2
        echo "Install BATS and run tests again" >&2
        return 1
    fi

    if ! "$dependency_script" --python-only --quiet; then
        echo "ERROR: Python requirements not satisfied" >&2
        echo "Run: $dependency_script --python-only for details" >&2
        return 1
    fi

    return 0
}

# Get Python executable (simplified version for tests)
get_python_executable() {
    echo "python3"
}

TEST_ID_COUNTER=0
export GANDALF_TEST_MODE="true"
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
    export PYTHONPATH="$GANDALF_ROOT:${PYTHONPATH:-}"

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

    echo "$request" | python3 "$SERVER_DIR/main.py" --project-root "$project_root" >"$temp_stdout" 2>"$temp_stderr"
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
