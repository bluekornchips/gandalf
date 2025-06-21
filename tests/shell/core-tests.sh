#!/usr/bin/env bats
# Core MCP Server Functionality Tests
# Basic server operations and MCP protocol compliance

set -eo pipefail

load 'fixtures/helpers/test-helpers'

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "server starts without errors" {
    local python_exec
    python_exec=$(get_python_executable)
    run "$python_exec" "$SERVER_DIR/main.py" --help
    [ "$status" -eq 0 ]
}

@test "server handles initialization request" {
    run execute_rpc "initialize" '{}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result.protocolVersion' >/dev/null
    echo "$output" | jq -e '.result.serverInfo' >/dev/null
}

@test "server lists available tools" {
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result.tools | length > 0' >/dev/null

    local tools
    tools=$(echo "$output" | jq -r '.result.tools[].name')
    echo "$tools" | grep -q "list_project_files"
    echo "$tools" | grep -q "get_project_info"
    echo "$tools" | grep -q "query_cursor_conversations"
    echo "$tools" | grep -q "list_cursor_workspaces"
}

@test "server handles invalid method gracefully" {
    run execute_rpc "invalid_method" '{}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.error.code == -32601' >/dev/null
}

@test "server handles malformed JSON" {
    local malformed_json='{"invalid": json}'
    local python_exec
    python_exec=$(get_python_executable)

    run bash -c "echo '$malformed_json' | '$python_exec' '$SERVER_DIR/main.py' --project-root '$TEST_PROJECT_DIR' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Server returns multiple JSON objects: notifications + error response
    # Find the one with the error code; it should be the last one
    echo "$output" | while IFS= read -r line; do
        if [[ -n "$line" ]] && echo "$line" | jq -e '.error.code == -32700' >/dev/null 2>&1; then
            exit 0
        fi
    done

}

@test "server handles empty input gracefully" {
    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "echo '' | '$python_exec' '$SERVER_DIR/main.py' --project-root '$TEST_PROJECT_DIR' 2>/dev/null"
    [ "$status" -eq 0 ]
}

@test "project info tool returns valid data" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.project_name' >/dev/null
    echo "$content" | jq -e '.project_root' >/dev/null
}

@test "list files tool works with basic parameters" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "README.md"
}

@test "cursor extraction tools are available" {
    run execute_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"summary": true}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    # Should return summary data even if no conversations exist
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.workspaces' >/dev/null
    echo "$content" | jq -e '.total_conversations' >/dev/null
}

@test "server handles multiple sequential requests" {
    # Test that server can handle multiple requests in sequence
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]
    local first_id=$(echo "$output" | jq -r '.id')
    validate_jsonrpc_response "$output" "$first_id"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    local second_id=$(echo "$output" | jq -r '.id')
    validate_jsonrpc_response "$output" "$second_id"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    local third_id=$(echo "$output" | jq -r '.id')
    validate_jsonrpc_response "$output" "$third_id"
}

@test "server handles invalid tool calls gracefully" {
    run execute_rpc "tools/call" '{"name": "nonexistent_tool", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result.error' >/dev/null
}

@test "server respects project root parameter" {
    local other_project="$TEST_HOME/other-project"
    mkdir -p "$other_project"
    cd "$other_project"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Other Project" >OTHER.md
    git add . >/dev/null 2>&1
    git commit -m "Other project" >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' "$other_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "OTHER.md"
    ! echo "$content" | grep -q "README.md"
}
