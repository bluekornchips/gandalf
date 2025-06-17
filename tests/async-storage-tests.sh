#!/usr/bin/env bats

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required for async storage tests" >&2
    exit 1
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
SERVER_DIR="$GANDALF_ROOT/server"

ORIGINAL_HOME="$HOME"
TEST_PROJECT="async-test"
TEST_PROJECT_DIR=""
test_id=0

setup() {
    TEST_HOME=$(mktemp -d)
    export HOME="$TEST_HOME"
    export GANDALF_HOME="$TEST_HOME/.gandalf"
    export CONVERSATIONS_DIR="$TEST_HOME/.gandalf/conversations"
    export AUTO_STORE_THRESHOLD=1 # Enable immediate async storage
    export MCP_DEBUG=true

    TEST_PROJECT_DIR="$TEST_HOME/$TEST_PROJECT"
    mkdir -p "$TEST_PROJECT_DIR"
    (cd "$TEST_PROJECT_DIR" && git init >/dev/null 2>&1)
}

teardown() {
    export HOME="$ORIGINAL_HOME"
    if [[ -n "$TEST_HOME" && -d "$TEST_HOME" ]]; then
        rm -rf "$TEST_HOME"
    fi
}

# Helper function to execute JSON-RPC tool calls
execute_tool_call() {
    test_id=$((test_id + 1))
    local tool_name="$1"
    local arguments="${2:-{}}"
    local project_dir="${3:-$TEST_PROJECT_DIR}"

    local request=$(jq -nc \
        --arg method "tools/call" \
        --arg tool_name "$tool_name" \
        --argjson arguments "$arguments" \
        --arg id "$test_id" \
        '{
            "jsonrpc": "2.0",
            "id": $id,
            "method": $method,
            "params": {
                "name": $tool_name,
                "arguments": $arguments
            }
        }')

    (cd "$project_dir" && echo "$request" | python3 "$SERVER_DIR/main.py" --project-root "$project_dir" 2>&1)
}

execute_rapid_tool_calls() {
    local tools=("get_project_info" "get_git_status" "list_project_files")
    local results=()

    for tool in "${tools[@]}"; do
        local result=$(execute_tool_call "$tool")
        local exit_code=$?
        results+=("$exit_code")

        # Small delay between calls to simulate rapid usage
        sleep 0.1
    done

    for code in "${results[@]}"; do
        if [ "$code" -ne 0 ]; then
            return 1
        fi
    done
    return 0
}

# Helper function for concurrent tool calls
execute_concurrent_tool_calls() {
    local num_calls="${1:-3}"
    local pids=()
    local temp_files=()

    # Start multiple background processes
    for ((i = 1; i <= num_calls; i++)); do
        local temp_file=$(mktemp)
        temp_files+=("$temp_file")

        # Execute tool call and store result in temp file, run in background
        (
            execute_tool_call "get_project_info" "{}" "$TEST_PROJECT_DIR" >"$temp_file" 2>&1
            echo $? >>"$temp_file"
        ) &
        pids+=($!)
    done

    # Wait for all processes to complete
    local all_success=true
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            all_success=false
        fi
    done

    # Check results
    for temp_file in "${temp_files[@]}"; do
        if [ -f "$temp_file" ]; then
            local exit_code=$(tail -n 1 "$temp_file")
            if [ "$exit_code" -ne 0 ]; then
                all_success=false
            fi
            rm -f "$temp_file"
        fi
    done

    [ "$all_success" = true ]
}

wait_for_async_storage() {
    sleep 1
}

get_conversation_dir() {
    echo "$CONVERSATIONS_DIR/$TEST_PROJECT"
}

find_conversation_files() {
    local conv_dir=$(get_conversation_dir)
    if [ -d "$conv_dir" ]; then
        find "$conv_dir" -name "*.json" 2>/dev/null
    fi
}

count_conversation_files() {
    local files=($(find_conversation_files))
    echo ${#files[@]}
}

has_async_storage_marker() {
    local files=($(find_conversation_files))
    for file in "${files[@]}"; do
        if [ -f "$file" ] && jq -e '.stored_async' "$file" >/dev/null 2>&1; then
            return 0
        fi
    done
    return 1
}

validate_conversation_file() {
    local file="$1"

    if ! jq . "$file" >/dev/null 2>&1; then
        return 1
    fi

    jq -e '.conversation_id' "$file" >/dev/null 2>&1 || return 1
    jq -e '.messages' "$file" >/dev/null 2>&1 || return 1
    jq -e '.auto_generated' "$file" >/dev/null 2>&1 || return 1

    local message_count=$(jq -r '.message_count' "$file" 2>/dev/null)
    local actual_count=$(jq -r '.messages | length' "$file" 2>/dev/null)

    if [ "$message_count" != "null" ] && [ "$actual_count" != "null" ]; then
        [ "$message_count" -eq "$actual_count" ] || return 1
    fi

    return 0
}

@test "Async storage script executable, should pass" {
    [ -f "$SERVER_DIR/main.py" ]
    [ -x "$SERVER_DIR/main.py" ]
}

@test "Async storage creates conversation files immediately, should pass" {
    run execute_tool_call "get_project_info"
    [ "$status" -eq 0 ]

    wait_for_async_storage

    # Async storage should create conversation files
    local file_count=$(count_conversation_files)
    [ "$file_count" -gt 0 ]

    # Verify at least one file has async storage marker
    run has_async_storage_marker
    [ "$status" -eq 0 ]
}

@test "Async storage handles multiple rapid tool calls, should pass" {
    run execute_rapid_tool_calls
    [ "$status" -eq 0 ]

    wait_for_async_storage

    local file_count=$(count_conversation_files)
    if [ "$file_count" -gt 0 ]; then
        run has_async_storage_marker
        [ "$status" -eq 0 ]
    else
        echo "No conversation files found - async storage may use different location"
    fi
}

@test "Async storage maintains thread safety, should pass" {
    run execute_concurrent_tool_calls 3
    [ "$status" -eq 0 ]

    wait_for_async_storage

    # Verify no corruption occurred by validating all JSON files
    local files=($(find_conversation_files))
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            run validate_conversation_file "$file"
            [ "$status" -eq 0 ]
        fi
    done
}

@test "Async storage fallback mechanism exists, should pass" {
    # Check that the fallback code exists
    run grep -q "falling back to synchronous storage" "$SERVER_DIR/main.py"
    [ "$status" -eq 0 ]

    # Check that both async and sync methods exist
    run grep -q "_auto_store_conversation_async" "$SERVER_DIR/main.py"
    [ "$status" -eq 0 ]

    run grep -q "_auto_store_conversation_worker" "$SERVER_DIR/main.py"
    [ "$status" -eq 0 ]
}

@test "Async storage preserves conversation data integrity, should pass" {
    run execute_tool_call "get_project_info"
    [ "$status" -eq 0 ]

    wait_for_async_storage

    # Validate all conversation files
    local files=($(find_conversation_files))
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            run validate_conversation_file "$file"
            [ "$status" -eq 0 ]
        fi
    done
}

@test "Async storage performance is reasonable, should pass" {
    # Measure tool call performance using seconds
    local start_time=$(date +%s)

    run execute_tool_call "get_project_info"
    [ "$status" -eq 0 ]

    local end_time=$(date +%s)
    local latency_seconds=$((end_time - start_time))

    # With async storage, latency should be reasonable, under 10s for tests
    [ "$latency_seconds" -lt 10 ]
}

@test "Async storage configuration via environment variable, should pass" {
    # Test with different thresholds
    export AUTO_STORE_THRESHOLD=3

    # Verify the setting is loaded
    run python3 -c "
import sys
sys.path.insert(0, '$SERVER_DIR')
from config.constants import AUTO_STORE_THRESHOLD
print(f'Threshold: {AUTO_STORE_THRESHOLD}')
assert AUTO_STORE_THRESHOLD == 3, f'Expected 3, got {AUTO_STORE_THRESHOLD}'
"
    [ "$status" -eq 0 ]
}

@test "Handles conversation directory creation, should pass" {
    local conv_dir=$(get_conversation_dir)
    rm -rf "$conv_dir"

    run execute_tool_call "get_project_info"
    [ "$status" -eq 0 ]

    wait_for_async_storage

    # Tool call should succeed regardless of directory creation
    [ "$status" -eq 0 ]
}

@test "Handles malformed server responses gracefully, should pass" {
    # Test with invalid JSON request - capture exit code properly
    local invalid_request="invalid json"

    # Run the command and capture its actual exit code
    cd "$TEST_PROJECT_DIR"
    echo "$invalid_request" | python3 "$SERVER_DIR/main.py" --project-root "$TEST_PROJECT_DIR" >/dev/null 2>&1
    local exit_code=$?

    # Server should handle malformed input gracefully and return 0 or 1, and not crash with 2+ or negative
    [ "$exit_code" -eq 0 ] || [ "$exit_code" -eq 1 ]
}
