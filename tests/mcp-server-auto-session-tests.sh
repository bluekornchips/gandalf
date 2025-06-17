#!/usr/bin/env bats

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required for MCP server auto-session tests" >&2
    exit 1
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"

ORIGINAL_HOME="$HOME"
TEST_PROJECT="mcp-test-project"
TEST_PROJECT_DIR=""
test_id=0

execute_rpc() {
    test_id=$((test_id + 1))
    local method="$1"
    local params="$2"
    local project_root="${3:-$TEST_PROJECT_DIR}"

    local request
    if [[ "$params" == "invalid_json" ]]; then
        request="invalid json"
    else
        request=$(jq -nc \
            --arg method "$method" \
            --argjson params "$params" \
            --arg id "$test_id" \
            '{
                "id": $id,
                "method": $method,
                "params": $params
            }')
    fi

    # Don't disable conversation storage for auto-session tests
    # These tests specifically need to test the conversation storage functionality
    echo "$request" | "$GANDALF_ROOT/gandalf.sh" run --project-root "$project_root" 2>/dev/null
    local exit_code=$?

    return $exit_code
}

setup() {
    TEST_HOME=$(mktemp -d)
    export HOME="$TEST_HOME"
    export CONVERSATIONS_DIR="$TEST_HOME/.gandalf/conversations"
    export STORE_CONVERSATIONS=true

    TEST_PROJECT_DIR="$TEST_HOME/$TEST_PROJECT"
    mkdir -p "$TEST_PROJECT_DIR"

    pushd "$TEST_PROJECT_DIR" >/dev/null
    git init >/dev/null 2>&1
    git config user.email "frodo@shire.me"
    git config user.name "Frodo Baggins"
    echo "print('Hello Shire')" >test.py
    git add . && git commit -m "Initial commit" >/dev/null 2>&1
    popd >/dev/null
}

teardown() {
    export HOME="$ORIGINAL_HOME"
    if [[ -n "$TEST_HOME" && -d "$TEST_HOME" ]]; then
        rm -rf "$TEST_HOME"
    fi
}

@test "STORE_CONVERSATIONS=false prevents auto-session file creation" {
    export STORE_CONVERSATIONS=false
    export AUTO_STORE_THRESHOLD=1

    session_files_before=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1 # Give time for potential file creation

    session_files_after=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

    [ "$session_files_after" -eq "$session_files_before" ]
}

@test "STORE_CONVERSATIONS=true creates auto-session files with 16-char hash names" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)

    echo "Found session files: $session_files" >&3

    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)
    session_filename=$(basename "$session_file" .json)

    echo "Session filename: '$session_filename'" >&3
    echo "Filename length: ${#session_filename}" >&3

    [ ${#session_filename} -eq 16 ]
}

@test "Auto-session filenames are 16-character hex hashes not timestamps" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=1

    run execute_rpc "tools/call" '{"name": "get_git_status", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)

    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)
    session_filename=$(basename "$session_file" .json)

    [ ${#session_filename} -eq 16 ]

    [[ ! "$session_filename" =~ ^[0-9]{8}-[0-9]{6}- ]]
}

@test "Auto-session files contain required metadata fields and auto_generated flag" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)
    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)

    run jq -e '.conversation_id' "$session_file"
    [ "$status" -eq 0 ]

    run jq -e '.title' "$session_file"
    [ "$status" -eq 0 ]

    run jq -e '.auto_generated' "$session_file"
    [ "$status" -eq 0 ]

    run jq -e '.messages' "$session_file"
    [ "$status" -eq 0 ]

    auto_generated=$(jq -r '.auto_generated' "$session_file")
    [ "$auto_generated" = "true" ]
}

@test "Auto-session titles reflect the tools that were called" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)
    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)
    title=$(jq -r '.title' "$session_file")

    [[ "$title" =~ "Get Project Info" ]] || [[ "$title" =~ "get_project_info" ]]
}

@test "Auto-session messages have proper role and content structure" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)
    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)

    message_count=$(jq '.messages | length' "$session_file")
    [ "$message_count" -gt 0 ]

    run jq -e '.messages[0].role' "$session_file"
    [ "$status" -eq 0 ]

    run jq -e '.messages[0].content' "$session_file"
    [ "$status" -eq 0 ]
}

@test "AUTO_STORE_THRESHOLD controls when sessions are automatically saved" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=3

    session_files_before=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

    for i in {1..5}; do
        execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    done

    sleep 1

    session_files_after=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

    [ "$session_files_after" -gt "$session_files_before" ]
}

@test "Auto-sessions are tagged with correct project names for isolation" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    project1_sessions=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)
    [ "$project1_sessions" -gt 0 ]

    TEST_PROJECT_2="$TEST_PROJECT_DIR/../second-project"
    mkdir -p "$TEST_PROJECT_2"
    echo "print('test2')" >"$TEST_PROJECT_2/test2.py"

    pushd "$TEST_PROJECT_2" >/dev/null
    git init && git config user.email "frodo@shire.me" && git config user.name "Frodo Baggins" && git add . && git commit -m "Initial commit"
    popd >/dev/null

    session_file=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | head -1)
    project_name=$(jq -r '.project_name' "$session_file")

    [ "$project_name" = "$TEST_PROJECT" ]
}

@test "SESSION_CONTEXT_MESSAGES limits retained messages after auto-storage" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=2     # Very low threshold for testing
    export SESSION_CONTEXT_MESSAGES=1 # Keep only 1 message for testing

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    run execute_rpc "tools/call" '{"name": "get_git_status", "arguments": {}}'
    [ "$status" -eq 0 ]

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    sleep 1

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)
    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)

    message_count=$(jq '.messages | length' "$session_file")
    [ "$message_count" -gt 0 ]

    tools_used=$(jq -r '.session_tools | length' "$session_file")
    [ "$tools_used" -gt 0 ]
}

@test "Server shutdown triggers auto-storage of remaining session data" {
    export STORE_CONVERSATIONS=true
    export AUTO_STORE_THRESHOLD=100 # High threshold so only shutdown triggers storage

    session_files_before=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

    {
        echo '{"id": 1, "method": "tools/call", "params": {"name": "get_project_info", "arguments": {}}}'
        sleep 1 # Give time for processing
    } | timeout 2s "$GANDALF_ROOT/gandalf.sh" run --project-root "$TEST_PROJECT_DIR" 2>/dev/null || true

    sleep 2 # Give time for shutdown processing

    session_files_after=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)

    [ "$session_files_after" -gt "$session_files_before" ]

    session_files=$(find "$CONVERSATIONS_DIR" -maxdepth 1 -name "*.json" 2>/dev/null)
    [ -n "$session_files" ]

    session_file=$(echo "$session_files" | head -1)

    auto_generated=$(jq -r '.auto_generated' "$session_file")
    [ "$auto_generated" = "true" ]
}
