#!/bin/bash
# Test Helper Functions for Gandalf MCP Server Test Suite
# Shared utilities for consistent testing across all test categories

set -euo pipefail

readonly DEFAULT_PROJECT_NAME="there_and_back_again"
readonly DEFAULT_USER_EMAIL="bilbo@baggins.shire"
readonly DEFAULT_USER_NAME="Bilbo Baggins"
readonly TEST_ID_COUNTER_START=0
readonly MCP_DEBUG_DEFAULT="false"

# Global test counter
TEST_ID_COUNTER=${TEST_ID_COUNTER_START}

setup_gandalf_paths() {
    local current_dir
    current_dir="$(pwd -P)"
    local search_dir="$current_dir"

    if [[ -n "${BASH_SOURCE[1]:-}" ]]; then
        search_dir="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd -P)"
    fi

    while [[ "$search_dir" != "/" ]]; do
        if [[ -d "$search_dir/server/src" && -f "$search_dir/server/src/main.py" ]]; then
            if [[ -z "${GANDALF_ROOT:-}" ]]; then
                export GANDALF_ROOT="$search_dir"
            fi
            if [[ -z "${SERVER_DIR:-}" ]]; then
                export SERVER_DIR="$GANDALF_ROOT/server/src"
            fi
            if [[ -z "${TESTS_DIR:-}" ]]; then
                export TESTS_DIR="$GANDALF_ROOT/scripts/tests"
            fi
            if [[ -z "${SCRIPTS_DIR:-}" ]]; then
                export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
            fi
            export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    echo "Warning: Could not auto-detect GANDALF_ROOT, using fallback" >&2
    if [[ -z "${GANDALF_ROOT:-}" ]]; then
        export GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd -P)"
    fi
    if [[ -z "${SERVER_DIR:-}" ]]; then
        export SERVER_DIR="$GANDALF_ROOT/server/src"
    fi
    if [[ -z "${TESTS_DIR:-}" ]]; then
        export TESTS_DIR="$GANDALF_ROOT/scripts/tests"
    fi
    if [[ -z "${SCRIPTS_DIR:-}" ]]; then
        export SCRIPTS_DIR="$GANDALF_ROOT/scripts"
    fi
    export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
}

setup_gandalf_paths

check_test_dependencies() {
    if ! command -v bats &>/dev/null; then
        echo "ERROR: BATS (Bash Automated Testing System) is required for shell tests" >&2
        echo "Install BATS with: brew install bats-core" >&2
        return 1
    fi

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

    local python_cmd
    python_cmd=$(get_python_executable)
    if ! "$python_cmd" -c "import yaml" &>/dev/null; then
        echo "ERROR: PyYAML is required. Install with: pip install PyYAML" >&2
        return 1
    fi

    return 0
}

get_python_executable() {
    local venv_dir="$GANDALF_ROOT/.venv"
    if [[ -d "$venv_dir" && -f "$venv_dir/bin/python3" ]]; then
        echo "$venv_dir/bin/python3"
    else
        echo "python3"
    fi
}

execute_server() {
    local args="$*"
    local python_cmd
    python_cmd=$(get_python_executable)
    bash -c "cd '$GANDALF_ROOT/server' && PYTHONPATH=. $python_cmd src/main.py $args"
}

export MCP_DEBUG="${MCP_DEBUG:-$MCP_DEBUG_DEFAULT}"

generate_test_id() {
    TEST_ID_COUNTER=$((TEST_ID_COUNTER + 1))
    echo "$TEST_ID_COUNTER"
}

execute_rpc() {
    local method="$1"
    local params="$2"
    local project_root="${3:-${TEST_PROJECT_DIR:-$PWD}}"

    export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

    [[ -z "$params" ]] && params="{}"

    if ! echo "$params" | jq . >/dev/null 2>&1; then
        echo "ERROR: Invalid JSON params: $params" >&2
        return 1
    fi

    local test_id
    test_id=$(generate_test_id)

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

    local temp_stdout temp_stderr
    temp_stdout=$(mktemp)
    temp_stderr=$(mktemp)

    local python_cmd exit_code
    python_cmd=$(get_python_executable)
    echo "$request" | (
        cd "$GANDALF_ROOT/server"
        PYTHONPATH=. "$python_cmd" src/main.py --project-root "$project_root"
    ) >"$temp_stdout" 2>"$temp_stderr"
    exit_code=$?

    local full_output
    full_output=$(cat "$temp_stdout")

    rm -f "$temp_stdout" "$temp_stderr"

    if [[ $exit_code -ne 0 ]]; then
        return 1
    fi

    local temp_file response
    temp_file=$(mktemp)
    echo "$full_output" >"$temp_file"

    response=""
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            if echo "$line" | jq -e '.id != null' >/dev/null 2>&1; then
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

create_test_conversation_args() {
    local conversation_id="$1"
    local messages="$2"
    local title="${3:-Test Conversation}"
    local additional_tags="${4:-}"

    local tags='["test"]'
    if [[ -n "$additional_tags" ]]; then
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

check_timeout_with_warning() {
    local duration="$1"
    local threshold="$2"
    local operation_name="$3"

    if [[ $duration -gt $threshold ]]; then
        echo "WARNING: $operation_name took ${duration}s (threshold: ${threshold}s)" >&2
        echo "This may indicate performance issues but is not a test failure" >&2
    fi
    return 0
}

shared_setup() {
    local project_name="$DEFAULT_PROJECT_NAME"
    local user_email="$DEFAULT_USER_EMAIL"
    local user_name="$DEFAULT_USER_NAME"

    TEST_HOME=$(mktemp -d -t gandalf_test.XXXXXX)
    export ORIGINAL_HOME="$HOME"
    export HOME="$TEST_HOME"

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

    [[ -n "${TEST_HOME:-}" && -d "$TEST_HOME" ]] && rm -rf "$TEST_HOME"
}

create_minimal_project() {
    echo "# There and Back Again, a Hobbits Project" >README.md
    git add . >/dev/null 2>&1
    git commit -m "I'm going on an adventure!" >/dev/null 2>&1
}

export GANDALF_TEST_MODE="true"
export MCP_DEBUG="${MCP_DEBUG:-$MCP_DEBUG_DEFAULT}"
export SERVER_DIR="$GANDALF_ROOT/server/src"
export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
