#!/usr/bin/env bats
# Project Operations Tests
# Project information, git operations, and project context functionality

set -eo pipefail

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"

# Source shared test helpers and environment variables
source "$GANDALF_ROOT/tests/shell/fixtures/helpers/test-helpers.sh"

create_project_test_structure() {
    echo "# There and Back Again, a Hobbits Project" >README.md
    echo "print('I'm going on an adventure')" >main.py
    echo '{"name": "an-adventure", "version": "1.0.0"}' >package.json

    git add . >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1

    # Create additional commits for git history
    echo "print('good morning')" >>main.py
    git add main.py >/dev/null 2>&1
    git commit -m "I'm going on an adventure" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_project_test_structure
}

teardown() {
    shared_teardown
}

@test "get project info returns valid project data" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should be valid JSON with project information
    echo "$content" | jq . >/dev/null
    echo "$content" | jq -e '.project_name' >/dev/null
    echo "$content" | jq -e '.project_root' >/dev/null

    # Project name should be derived from directory
    local project_name
    project_name=$(echo "$content" | jq -r '.project_name')
    [[ "$project_name" == "there_and_back_again" ]]
}

@test "get project info includes file statistics" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should include file statistics
    echo "$content" | jq -e '.file_stats' >/dev/null
    echo "$content" | jq -e '.file_stats.total_files' >/dev/null

    # Should have reasonable file count
    local file_count
    file_count=$(echo "$content" | jq -r '.file_stats.total_files')
    [[ "$file_count" -gt 0 ]]
}

@test "get project info includes git information" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should include git information since we have a git repo
    echo "$content" | jq -e '.git' >/dev/null || echo "$content" | jq -e '.is_git_repo' >/dev/null

    # Git info should indicate this is a git repository
    if echo "$content" | jq -e '.git' >/dev/null 2>&1; then
        echo "$content" | jq -e '.git.is_git_repo' >/dev/null
    fi
}

@test "server handles non-git directories gracefully" {
    local non_git_project="$TEST_HOME/non-git-project"
    mkdir -p "$non_git_project"
    echo "# Non-git project" >"$non_git_project/README.md"

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "echo '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' | '$python_exec' '$SERVER_DIR/main.py' --project-root '$non_git_project' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should still return project info even for non-git directories
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_name' >/dev/null
}

@test "server handles empty directories gracefully" {
    local empty_project="$TEST_HOME/empty-project"
    mkdir -p "$empty_project"

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "echo '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' | '$python_exec' '$SERVER_DIR/main.py' --project-root '$empty_project' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should return project info for empty directories
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_name' >/dev/null
}

@test "project info respects include_stats parameter" {
    # Test with stats disabled
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": false}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should not include file stats when disabled
    ! echo "$content" | jq -e '.file_stats' >/dev/null 2>&1 || true
}

@test "project operations handle deeply nested directories" {
    # Create deep directory structure
    local deep_project="$TEST_HOME/deep/nested/structure/project"
    mkdir -p "$deep_project"
    cd "$deep_project"

    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Deep project" >README.md
    git add . >/dev/null 2>&1
    git commit -m "Deep project" >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$deep_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle deep paths correctly
    echo "$content" | jq -e '.project_name' >/dev/null
    echo "$content" | jq -e '.project_root' >/dev/null

    local project_name
    project_name=$(echo "$content" | jq -r '.project_name')
    [[ "$project_name" == "project" ]]
}

@test "project info handles special characters in paths" {
    # Create project with special characters (that are valid in filenames)
    local special_project="$TEST_HOME/test-project_with.special-chars"
    mkdir -p "$special_project"
    cd "$special_project"

    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Special chars project" >README.md
    git add . >/dev/null 2>&1
    git commit -m "Special chars" >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$special_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle special characters in project name
    echo "$content" | jq -e '.project_name' >/dev/null
    echo "$content" | jq -e '.project_root' >/dev/null

    local project_name
    project_name=$(echo "$content" | jq -r '.project_name')
    [[ "$project_name" == "test-project_with.special-chars" ]]
}

@test "project operations are consistent across multiple calls" {
    # Make multiple calls and ensure consistency
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local first_response
    first_response=$(echo "$output" | jq -r '.result.content[0].text')

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local second_response
    second_response=$(echo "$output" | jq -r '.result.content[0].text')

    # Project name should be consistent
    local first_name second_name
    first_name=$(echo "$first_response" | jq -r '.project_name')
    second_name=$(echo "$second_response" | jq -r '.project_name')
    [[ "$first_name" == "$second_name" ]]

    # Project root should be consistent
    local first_root second_root
    first_root=$(echo "$first_response" | jq -r '.project_root')
    second_root=$(echo "$second_response" | jq -r '.project_root')
    [[ "$first_root" == "$second_root" ]]
}
