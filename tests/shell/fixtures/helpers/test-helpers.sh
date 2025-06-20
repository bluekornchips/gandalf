#!/bin/bash
# Test Helper Functions for Gandalf MCP Server Test Suite
# Shared utilities for consistent testing across all test categories

set -euo pipefail

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
SERVER_DIR="$GANDALF_ROOT/server"
TEST_ID_COUNTER=0
export GANDALF_TEST_MODE="false"  # Disable debug output by default
export MCP_DEBUG="false"

# Helper function to get the correct Python executable
get_python_executable() {
    echo "python3"
}

# Generate unique test ID for each request
generate_test_id() {
    TEST_ID_COUNTER=$((TEST_ID_COUNTER + 1))
    echo "$TEST_ID_COUNTER"
}

execute_rpc() {
    local method="$1"
    local params="$2"
    local project_root="${3:-$PWD}"

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

    # Execute and filter to get only the response with matching ID
    local python_exec
    python_exec=$(get_python_executable)

    # Debug output in test mode
    if [[ "${GANDALF_TEST_MODE:-}" == "true" ]]; then
        echo "DEBUG: Request: $request" >&2
        echo "DEBUG: Python exec: $python_exec" >&2
        echo "DEBUG: Project root: $project_root" >&2
        echo "DEBUG: PYTHONPATH: $PYTHONPATH" >&2
        echo "DEBUG: Server path: $SERVER_DIR/main.py" >&2
    fi

    # Separate stdout and stderr - only capture stdout for JSON responses
    local temp_stdout=$(mktemp)
    local temp_stderr=$(mktemp)
    
    echo "$request" | "$python_exec" "$SERVER_DIR/main.py" --project-root "$project_root" >"$temp_stdout" 2>"$temp_stderr"
    local exit_code=$?
    
    local full_output
    full_output=$(cat "$temp_stdout")
    local error_output
    error_output=$(cat "$temp_stderr")
    
    # Debug output in test mode
    if [[ "${GANDALF_TEST_MODE:-}" == "true" ]]; then
        echo "DEBUG: Exit code: $exit_code" >&2
        echo "DEBUG: Full output length: ${#full_output}" >&2
        echo "DEBUG: Error output length: ${#error_output}" >&2
        if [[ -n "$error_output" ]]; then
            echo "DEBUG: Error output (first 300 chars): ${error_output:0:300}" >&2
        fi
        echo "DEBUG: Full output (first 300 chars): ${full_output:0:300}" >&2
    fi
    
    # Clean up temp files
    rm -f "$temp_stdout" "$temp_stderr"
    
    # If there was an error, return empty response
    if [[ $exit_code -ne 0 ]]; then
        if [[ "${GANDALF_TEST_MODE:-}" == "true" ]]; then
            echo "DEBUG: Server exited with code $exit_code" >&2
        fi
        return 1
    fi

    # Extract only the response with the matching ID (not notifications)
    # Use a temporary file to avoid subshell issues
    local temp_file=$(mktemp)
    echo "$full_output" >"$temp_file"

    local response=""
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            # Check if this line has our ID as either string or number
            if echo "$line" | jq -e --arg id "$test_id" '.id != null and (.id == $id or .id == ($id | tonumber))' >/dev/null 2>&1; then
                response="$line"
                break
            fi
        fi
    done <"$temp_file"

    rm -f "$temp_file"
    
    # Debug output in test mode
    if [[ "${GANDALF_TEST_MODE:-}" == "true" ]]; then
        echo "DEBUG: Final response length: ${#response}" >&2
        echo "DEBUG: Final response: $response" >&2
    fi
    
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

shared_setup() {
    local project_name="there_and_back_again"
    local user_email="bilbo@baggins.shire"
    local user_name="Bilbo Baggins"

    TEST_HOME=$(mktemp -d)
    export ORIGINAL_HOME="$HOME"
    export HOME="$TEST_HOME"

    # Ensure conversation storage is isolated to test environment
    export GANDALF_HOME="$TEST_HOME/.gandalf"
    export CONVERSATIONS_DIR="$TEST_HOME/.gandalf/conversations"
    mkdir -p "$CONVERSATIONS_DIR"

    TEST_PROJECT_DIR="$TEST_HOME/$project_name"
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
