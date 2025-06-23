#!/usr/bin/env bats
# Integration Tests for Gandalf MCP Server
# End-to-end workflows and multi-tool scenarios

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

create_integration_test_structure() {
    mkdir -p src tests docs
    echo "# There and Back Again, a Hobbits Project" >README.md
    echo "print('I'm going on an adventure')" >src/main.py
    echo "def helper(): pass" >src/helper.py
    echo "test_main()" >tests/test_main.py
    echo "# For Frodo" >docs/api.md
    echo '{"name": "integration-test", "version": "1.0.0"}' >package.json
    echo "*.pyc" >.gitignore

    git add . >/dev/null 2>&1
    git commit -m "Initial project setup" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_integration_test_structure
}

teardown() {
    shared_teardown
}

@test "full workflow: initialize, list tools, get project info, list files" {
    TEST_ID=0

    # Initialize server
    run execute_rpc "initialize" '{}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result.protocolVersion' >/dev/null

    # List available tools
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result.tools | length > 0' >/dev/null

    # Get project information
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local project_info
    project_info=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$project_info" | jq -e '.project_name == "there_and_back_again"' >/dev/null

    # List project files
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local files_content
    files_content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$files_content" | grep -q "README.md"
    echo "$files_content" | grep -q "src/main.py"
}

@test "file operations with different project structures" {
    # Test with Python-focused filter
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".py"]}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local py_content
    py_content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$py_content" | grep -q "main.py"
    echo "$py_content" | grep -q "helper.py"
    ! echo "$py_content" | grep -q "package.json"

    # Test with documentation filter
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".md"]}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local md_content
    md_content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$md_content" | grep -q "README.md"
    echo "$md_content" | grep -q "api.md"
    ! echo "$md_content" | grep -q "main.py"
}

@test "project info integration with file operations" {
    # Get project info with stats
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local project_info
    project_info=$(echo "$output" | jq -r '.result.content[0].text')

    # Extract file count from project info
    local file_count
    file_count=$(echo "$project_info" | jq -r '.file_stats.total_files')
    [[ "$file_count" -gt 0 ]]

    # List files and verify count is reasonable
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local files_content
    files_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain the main files we created
    echo "$files_content" | grep -q "README.md"
    echo "$files_content" | grep -q "package.json"
    echo "$files_content" | grep -q "src/"
    echo "$files_content" | grep -q "tests/"
}

@test "error handling across different tools" {
    # Test invalid tool call
    run execute_rpc "tools/call" '{"name": "nonexistent_tool", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    # Check for error in result field (server returns errors this way)
    echo "$output" | jq -e '.result.error' >/dev/null
}

@test "multiple project switching works correctly" {
    # Create second project
    local project2="$TEST_HOME/project2"
    mkdir -p "$project2"
    cd "$project2"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Project 2" >README.md
    echo "console.log('project2');" >app.js
    git add . >/dev/null 2>&1
    git commit -m "Project 2 setup" >/dev/null 2>&1

    # Get info for project 1 (change back to original directory first)
    cd "$TEST_PROJECT_DIR"
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local project1_info
    project1_info=$(echo "$output" | jq -r '.result.content[0].text')
    local project1_name
    project1_name=$(echo "$project1_info" | jq -r '.project_name')
    [[ "$project1_name" == "there_and_back_again" ]]

    # Get info for project 2 (change to project2 directory)
    cd "$project2"
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$project2"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local project2_info
    project2_info=$(echo "$output" | jq -r '.result.content[0].text')
    local project2_name
    project2_name=$(echo "$project2_info" | jq -r '.project_name')
    [[ "$project2_name" == "project2" ]]

    # Verify files are different (from project2 directory)
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' "$project2"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local project2_files
    project2_files=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$project2_files" | grep -q "app.js"
    ! echo "$project2_files" | grep -q "src/main.py"
}

@test "cursor integration workflow" {
    # Test cursor chat extraction functionality
    run execute_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"summary": true}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local cursor_content
    cursor_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return summary data structure
    echo "$cursor_content" | jq -e '.workspaces' >/dev/null
    echo "$cursor_content" | jq -e '.total_conversations' >/dev/null

    # Test listing cursor workspaces
    run execute_rpc "tools/call" '{"name": "list_cursor_workspaces", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local workspaces_content
    workspaces_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return workspace information
    [[ -n "$workspaces_content" ]]
}
