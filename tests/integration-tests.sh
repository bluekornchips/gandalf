#!/usr/bin/env bats

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
TEST_SERVER_NAME="gandalf-test-repo"
test_id=0

# Helper function to execute JSON-RPC requests
execute_rpc() {
    test_id=$((test_id + 1))
    local method="$1"
    local params="$2"
    local project_root="${3:-$GANDALF_ROOT}"

    local request
    request=$(jq -nc \
        --arg method "$method" \
        --argjson params "$params" \
        --arg id "$test_id" \
        '{
            "id": $id,
            "method": $method,
            "params": $params
        }')

    export GANDALF_TEST_MODE=true
    echo "$request" | "$GANDALF_ROOT/gandalf.sh" run --project-root "$project_root" 2>/dev/null
    local exit_code=$?

    return $exit_code
}

# Ref: https://bats-core.readthedocs.io/en/stable/tutorial.html#avoiding-costly-repeated-setups
setup_file() {
    "$GANDALF_ROOT/gandalf.sh" reset "$TEST_SERVER_NAME" >/dev/null 2>&1 || true
}

teardown_file() {
    "$GANDALF_ROOT/gandalf.sh" reset "$TEST_SERVER_NAME" >/dev/null 2>&1 || true
    echo "Cleaned up test server: $TEST_SERVER_NAME"
}

setup() {
    TEMP_DIR=$(mktemp -d)
    TEST_REPO="$TEMP_DIR/test-repo"
    mkdir -p "$TEST_REPO"

    pushd "$TEST_REPO" >/dev/null

    git init >/dev/null 2>&1
    git config user.email "strider@rivendell.lotr"
    git config user.name "Aragorn"
    echo 'def main(): pass' >main.py
    echo '*.pyc' >.gitignore
    git add . >/dev/null 2>&1
    git commit -m "For Frodo" >/dev/null 2>&1

    popd >/dev/null
}

teardown() {
    [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]] && rm -rf "$TEMP_DIR" 2>/dev/null || true
}

@test "Setup works, should pass" {
    run "$GANDALF_ROOT/gandalf.sh" setup
    [ "$status" -eq 0 ]
}

@test "Install with non-existent repository fails, should fail" {
    run "$GANDALF_ROOT/gandalf.sh" install "/non/existent/repo"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "does not exist"
}

@test "Install with test repository, should pass" {
    run "$GANDALF_ROOT/gandalf.sh" install "$TEST_REPO"
    [ "$status" -eq 0 ]
}

@test "Server initialization with the test repo, should pass" {
    run execute_rpc "initialize" "{}"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "protocolVersion"
    echo "$output" | grep -q "serverInfo"
}

@test "List files tool with test repo, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "main.py"
}

@test "Project info tool with test repo, should pass" {
    run execute_rpc "tools/call" '{"name": "get_project_info"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "result"
}

@test "Git status tool with test repo, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_status"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "result"
}

@test "Server with invalid project root warns but continues, should pass" {
    run execute_rpc "initialize" "{}" "/non/existent/path"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Warning: Project root does not exist yet"
}

@test "Server with malformed JSON request, should pass" {
    export GANDALF_TEST_MODE=true
    run bash -c 'echo "{\"id\": 1, \"method\": \"initialize\", \"params\": invalid_json}" | "'$GANDALF_ROOT'/gandalf.sh" run 2>/dev/null'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "error"
}

@test "Tool call with invalid tool name fails, should fail" {
    run execute_rpc "tools/call" '{"name": "invalid_tool_name"}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"error"'
}
