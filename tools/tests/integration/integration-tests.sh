#!/usr/bin/env bats
# Integration Tests for Gandalf MCP Server
# End-to-end workflows and multi-tool scenarios

set -euo pipefail

GANDALF_ROOT=$(git rev-parse --show-toplevel)
load "$GANDALF_ROOT/tools/tests/test-helpers.sh"

execute_tool_call() {
    local tool_name="$1"
    local arguments="$2"
    local project_dir="${3:-}"
    
    local rpc_call="{\"name\": \"$tool_name\", \"arguments\": $arguments}"
    
    if [[ -n "$project_dir" ]]; then
        execute_rpc "tools/call" "$rpc_call" "$project_dir"
    else
        execute_rpc "tools/call" "$rpc_call"
    fi
}


validate_tool_response() {
    local output="$1"
    local expected_pattern="${2:-}"
    
    validate_jsonrpc_response "$output"
    
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    if [[ -z "$content" ]]; then
        echo "ERROR: Empty content in tool response" >&2
        return 1
    fi
    
    if [[ -n "$expected_pattern" ]]; then
        if ! echo "$content" | grep -q "$expected_pattern"; then
            echo "ERROR: Expected pattern '$expected_pattern' not found in: $content" >&2
            return 1
        fi
    fi
    
    echo "$content"
}


validate_json_field() {
    local content="$1"
    local field_path="$2"
    local expected_value="${3:-}"
    
    if [[ -n "$expected_value" ]]; then
        if ! echo "$content" | jq -e "$field_path == \"$expected_value\"" >/dev/null 2>&1; then
            echo "ERROR: Expected $field_path to be '$expected_value' but got: $(echo "$content" | jq -r "$field_path")" >&2
            return 1
        fi
    else
        if ! echo "$content" | jq -e "$field_path" >/dev/null 2>&1; then
            echo "ERROR: Expected field $field_path not found in: $content" >&2
            return 1
        fi
    fi
}


validate_file_in_listing() {
    local content="$1"
    local file_pattern="$2"
    
    if ! echo "$content" | grep -q "$file_pattern"; then
        echo "ERROR: Expected file '$file_pattern' not found in listing: $content" >&2
        return 1
    fi
}


validate_file_not_in_listing() {
    local content="$1"
    local file_pattern="$2"
    
    if echo "$content" | grep -q "$file_pattern"; then
        echo "ERROR: Unexpected file '$file_pattern' found in listing: $content" >&2
        return 1
    fi
}


create_secondary_project() {
    local project_name="$1"
    local project_dir="$TEST_HOME/$project_name"
    
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    
    echo "# $project_name" >README.md
    echo "console.log('$project_name');" >app.js
    
    git add . >/dev/null 2>&1
    git commit -m "$project_name setup" >/dev/null 2>&1
    
    echo "$project_dir"
}


validate_workflow_step() {
    local step_name="$1"
    local status="$2"
    local output="$3"
    
    if [[ "$status" -ne 0 ]]; then
        echo "ERROR: $step_name failed with status $status" >&2
        return 1
    fi
    
    validate_jsonrpc_response "$output"
    echo "✓ $step_name completed successfully"
}


validate_conversation_response() {
    local output="$1"
    local tool_name="$2"
    
    validate_jsonrpc_response "$output"
    
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    if [[ -z "$content" ]]; then
        echo "ERROR: Empty content from $tool_name" >&2
        return 1
    fi
    
    echo "✓ $tool_name returned valid content"
    echo "$content"
}

create_integration_test_structure() {
    mkdir -p src tests docs
    
    cat <<'EOF' >README.md
# There and Back Again, a Hobbits Project
EOF
    
    cat <<'EOF' >src/main.py
print('I'm going on an adventure')
EOF
    
    cat <<'EOF' >src/helper.py
def helper(): pass
EOF
    
    cat <<'EOF' >tests/test_main.py
test_main()
EOF
    
    cat <<'EOF' >docs/api.md
# For Frodo
EOF
    
    cat <<'EOF' >package.json
{"name": "integration-test", "version": "1.0.0"}
EOF
    
    cat <<'EOF' >.gitignore
*.pyc
EOF
    
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
    
    run execute_rpc "initialize" '{}'
    validate_workflow_step "Initialize server" "$status" "$output"
    validate_json_field "$output" '.result.protocolVersion'
    
    run execute_rpc "tools/list" '{}'
    validate_workflow_step "List tools" "$status" "$output"
    validate_json_field "$output" '.result.tools | length > 0'
    
    run execute_tool_call "get_project_info" '{}'
    validate_workflow_step "Get project info" "$status" "$output"
    local project_info
    project_info=$(validate_tool_response "$output")
    validate_json_field "$project_info" '.project_name' "there_and_back_again"
    
    run execute_tool_call "list_project_files" '{}'
    validate_workflow_step "List project files" "$status" "$output"
    local files_content
    files_content=$(validate_tool_response "$output")
    validate_file_in_listing "$files_content" "README.md"
    validate_file_in_listing "$files_content" "src/main.py"
}

@test "file operations with different project structures" {
    run execute_tool_call "list_project_files" '{"file_types": [".py"]}'
    [ "$status" -eq 0 ]
    local py_content
    py_content=$(validate_tool_response "$output")
    validate_file_in_listing "$py_content" "main.py"
    validate_file_in_listing "$py_content" "helper.py"
    validate_file_not_in_listing "$py_content" "package.json"
    
    run execute_tool_call "list_project_files" '{"file_types": [".md"]}'
    [ "$status" -eq 0 ]
    local md_content
    md_content=$(validate_tool_response "$output")
    validate_file_in_listing "$md_content" "README.md"
    validate_file_in_listing "$md_content" "api.md"
    validate_file_not_in_listing "$md_content" "main.py"
}

@test "project info integration with file operations" {
    run execute_tool_call "get_project_info" '{"include_stats": true}'
    [ "$status" -eq 0 ]
    local project_info
    project_info=$(validate_tool_response "$output")
    
    local file_count
    file_count=$(echo "$project_info" | jq -r '.file_stats.total_files')
    
    if [[ "$file_count" -le 0 ]]; then
        echo "ERROR: Expected positive file count but got: $file_count" >&2
        false
    fi
    
    run execute_tool_call "list_project_files" '{}'
    [ "$status" -eq 0 ]
    local files_content
    files_content=$(validate_tool_response "$output")
    
    local expected_files=("README.md" "package.json" "src/" "tests/")
    for file in "${expected_files[@]}"; do
        validate_file_in_listing "$files_content" "$file"
    done
}

@test "error handling across different tools" {
    run execute_tool_call "nonexistent_tool" '{}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    
    if ! echo "$output" | jq -e '.result.error' >/dev/null 2>&1; then
        echo "ERROR: Expected error field for nonexistent tool" >&2
        false
    fi
    
    echo "✓ Error handling works correctly for invalid tools"
}

@test "multiple project switching works correctly" {
    local project2_dir
    project2_dir=$(create_secondary_project "project2")
    
    cd "$TEST_PROJECT_DIR"
    run execute_tool_call "get_project_info" '{}'
    [ "$status" -eq 0 ]
    local project1_info
    project1_info=$(validate_tool_response "$output")
    validate_json_field "$project1_info" '.project_name' "there_and_back_again"
    
    run execute_tool_call "get_project_info" '{}' "$project2_dir"
    [ "$status" -eq 0 ]
    local project2_info
    project2_info=$(validate_tool_response "$output")
    validate_json_field "$project2_info" '.project_name' "project2"
    
    run execute_tool_call "list_project_files" '{}' "$project2_dir"
    [ "$status" -eq 0 ]
    local project2_files
    project2_files=$(validate_tool_response "$output")
    validate_file_in_listing "$project2_files" "app.js"
    validate_file_not_in_listing "$project2_files" "src/main.py"
    
    echo "✓ Multiple projects handled correctly"
}

@test "conversation aggregation integration workflow" {
    local conversation_tools=("recall_conversations" "search_conversations" "export_individual_conversations")
    local arguments=('{"fast_mode": true, "limit": 5}' '{"query": "project", "limit": 5}' '{"limit": 2}')
    
    for i in "${!conversation_tools[@]}"; do
        local tool="${conversation_tools[i]}"
        local args="${arguments[i]}"
        
        run execute_tool_call "$tool" "$args"
        [ "$status" -eq 0 ]
        validate_conversation_response "$output" "$tool"
    done
    
    echo "✓ All conversation tools working correctly"
}
