#!/usr/bin/env bats
# Core MCP Server Functionality Tests
# Basic server operations and MCP protocol compliance

set -euo pipefail

load '../../lib/test-helpers.sh'

execute_server_command() {
    local command="$1"
    local project_root="${2:-$TEST_PROJECT_DIR}"
    
    run bash -c "cd '$GANDALF_ROOT/server' && PYTHONPATH=. python3 src/main.py $command --project-root '$project_root'"
}

validate_tool_listing() {
    local output="$1"
    local expected_tools=("list_project_files" "get_project_info" "recall_conversations" "get_server_version" "export_individual_conversations")
    
    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result.tools | length > 0' >/dev/null
    
    local tools
    tools=$(echo "$output" | jq -r '.result.tools[].name')
    
    for tool in "${expected_tools[@]}"; do
        if ! echo "$tools" | grep -q "$tool"; then
            echo "ERROR: Expected tool '$tool' not found in tool listing" >&2
            return 1
        fi
    done
    
    return 0
}

validate_project_info_response() {
    local output="$1"
    
    validate_jsonrpc_response "$output"
    
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    if ! echo "$content" | jq -e '.project_name' >/dev/null; then
        echo "ERROR: Missing project_name in project info response" >&2
        return 1
    fi
    
    if ! echo "$content" | jq -e '.project_root' >/dev/null; then
        echo "ERROR: Missing project_root in project info response" >&2
        return 1
    fi
    
    return 0
}

validate_file_listing_response() {
    local output="$1"
    local expected_file="${2:-README.md}"
    
    validate_jsonrpc_response "$output"
    
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    if ! echo "$content" | grep -q "$expected_file"; then
        echo "ERROR: Expected file '$expected_file' not found in file listing" >&2
        return 1
    fi
    
    return 0
}

create_test_project() {
    local project_dir="$1"
    local project_name="${2:-rivendell-project}"
    local user_email="${3:-elrond@rivendell.middleearth}"
    local user_name="${4:-Elrond Half-elven}"
    local readme_file="${5:-RIVENDELL.md}"
    local readme_content="${6:-# Rivendell Project}"
    
    mkdir -p "$project_dir"
    cd "$project_dir"
    git init >/dev/null 2>&1
    git config user.email "$user_email"
    git config user.name "$user_name"
    echo "$readme_content" >"$readme_file"
    git add . >/dev/null 2>&1
    git commit -m "Council of Elrond" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "server starts without crashing and shows help" {
    execute_server_command "--help"
    [ "$status" -eq 0 ]
    
    # Validate help output contains expected information
    if ! echo "$output" | grep -q "usage\|help\|Usage\|Help"; then
        if ! echo "$output" | grep -q "Gandalf"; then
            echo "ERROR: Help output doesn't contain expected usage information" >&2
            return 1
        fi
    fi
}

@test "server handles initialization request correctly" {
    run execute_rpc "initialize" '{}'
    [ "$status" -eq 0 ]
    
    validate_jsonrpc_response "$output"
    
    # Validate initialization response structure
    echo "$output" | jq -e '.result.protocolVersion' >/dev/null
    echo "$output" | jq -e '.result.serverInfo' >/dev/null
    
    # Validate protocol version format
    local protocol_version
    protocol_version=$(echo "$output" | jq -r '.result.protocolVersion')
    echo "$protocol_version" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' >/dev/null
}

@test "server lists available tools with complete information" {
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]
    
    validate_tool_listing "$output"
    
    # Validate tool definitions have required fields
    local tools_json
    tools_json=$(echo "$output" | jq -r '.result.tools')
    
    echo "$tools_json" | jq -e '.[].name' >/dev/null
    echo "$tools_json" | jq -e '.[].description' >/dev/null
    echo "$tools_json" | jq -e '.[].inputSchema' >/dev/null
}

@test "server handles invalid method gracefully" {
    run execute_rpc "invalid_method" '{}'
    [ "$status" -eq 0 ]
    
    validate_jsonrpc_response "$output"
    
    # Validate error response structure
    echo "$output" | jq -e '.error.code == -32601' >/dev/null
    echo "$output" | jq -e '.error.message' >/dev/null
}

@test "server handles malformed JSON gracefully" {
    local malformed_json='{"jsonrpc": "2.0", "method": "tools/call", "id": 1'
    
    run bash -c "cd '$GANDALF_ROOT/server' && echo '$malformed_json' | PYTHONPATH=. python3 src/main.py --project-root '$TEST_PROJECT_DIR' 2>/dev/null"
    [ "$status" -eq 0 ]
    
    # Server should return a JSON-RPC parse error response
    echo "$output" | jq -e '.error.code == -32700' >/dev/null
    echo "$output" | jq -e '.error.message' >/dev/null
}

@test "server handles empty input gracefully" {
    run bash -c "cd '$GANDALF_ROOT/server' && echo '' | PYTHONPATH=. python3 src/main.py --project-root '$TEST_PROJECT_DIR' 2>/dev/null"
    [ "$status" -eq 0 ]
    
    # Server should handle empty input gracefully, no output expected
    [ -z "$output" ]
}

@test "project info tool returns valid data structure" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    
    validate_project_info_response "$output"
    
    # Validate additional fields
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.timestamp' >/dev/null
    
    # Validate project name matches expected value
    local project_name
    project_name=$(echo "$content" | jq -r '.project_name')
    [[ "$project_name" == "there_and_back_again" ]]
}

@test "list files tool works with basic parameters" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    
    validate_file_listing_response "$output"
    
    # Validate content is not empty
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]
}

@test "conversation aggregation tools are available and functional" {
    run execute_rpc "tools/call" '{"name": "recall_conversations", "arguments": {"fast_mode": true, "limit": 5}}'
    [ "$status" -eq 0 ]
    
    validate_jsonrpc_response "$output"
    
    # Validate response has content
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]
    
    # Validate content is valid JSON or text
    if echo "$content" | jq . >/dev/null 2>&1; then
        # If it's JSON, validate basic structure
        echo "$content" | jq -e 'type' >/dev/null
    fi
}

@test "server handles multiple sequential requests correctly" {
    # First request: tools/list
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]
    local first_id
    first_id=$(echo "$output" | jq -r '.id')
    validate_jsonrpc_response "$output" "$first_id"
    
    # Small delay to ensure different timestamps
    sleep 0.1
    
    # Second request: get_project_info
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    local second_id
    second_id=$(echo "$output" | jq -r '.id')
    validate_jsonrpc_response "$output" "$second_id"
    validate_project_info_response "$output"
    
    # Small delay to ensure different timestamps
    sleep 0.1
    
    # Third request: list_project_files
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    local third_id
    third_id=$(echo "$output" | jq -r '.id')
    validate_jsonrpc_response "$output" "$third_id"
    validate_file_listing_response "$output"
    
    # Validate all requests executed successfully (IDs may not be unique due to timing)
    [[ -n "$first_id" ]]
    [[ -n "$second_id" ]]
    [[ -n "$third_id" ]]
}

@test "server handles invalid tool calls gracefully" {
    run execute_rpc "tools/call" '{"name": "nonexistent_tool", "arguments": {}}'
    [ "$status" -eq 0 ]
    
    validate_jsonrpc_response "$output"
    
    # Validate error response structure
    echo "$output" | jq -e '.result.error' >/dev/null
    
    # Validate error contains meaningful information
    local error_message
    error_message=$(echo "$output" | jq -r '.result.error')
    [[ -n "$error_message" ]]
}

@test "server respects project root parameter correctly" {
    local other_project="$TEST_HOME/rivendell-project"
    create_test_project "$other_project"
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' "$other_project"
    [ "$status" -eq 0 ]
    
    validate_file_listing_response "$output" "RIVENDELL.md"
    
    # Validate it doesn't contain files from the original project
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    ! echo "$content" | grep -q "README.md"
}

@test "conversation tools are automatically detected and functional" {
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]
    
    validate_tool_listing "$output"
    
    # Validate specific conversation tools
    local tools
    tools=$(echo "$output" | jq -r '.result.tools[].name')
    
    echo "$tools" | grep -q "recall_conversations"
    echo "$tools" | grep -q "export_individual_conversations"
}

@test "server handles concurrent requests appropriately" {
    # Test that server can handle multiple requests in sequence without issues
    local request_count=5
    
    for i in $(seq 1 $request_count); do
        run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
        [ "$status" -eq 0 ]
        validate_project_info_response "$output"
    done
}

@test "server validates tool parameters correctly" {
    # Test with invalid parameters
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"invalid_param": true}}'
    [ "$status" -eq 0 ]
    
    validate_jsonrpc_response "$output"
    
    # Should either succeed (ignoring invalid params) or return error
    if echo "$output" | jq -e '.result.error' >/dev/null 2>&1; then
        # If error, validate it's meaningful
        local error_message
        error_message=$(echo "$output" | jq -r '.result.error')
        [[ -n "$error_message" ]]
    else
        # If success, validate response structure
        validate_project_info_response "$output"
    fi
}

@test "server maintains consistent response format" {
    # Test different tools maintain consistent response format
    local tools=("get_project_info" "list_project_files")
    
    for tool in "${tools[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"$tool\", \"arguments\": {}}"
        [ "$status" -eq 0 ]
        
        validate_jsonrpc_response "$output"
        
        # Validate response has content array
        echo "$output" | jq -e '.result.content' >/dev/null
        echo "$output" | jq -e '.result.content[0].text' >/dev/null
    done
}
