#!/usr/bin/env bats
# Project Operation Tests for Gandalf MCP Server
# Tests project information, git integration, and statistics

set -euo pipefail

load "$GANDALF_ROOT/tools/tests/test-helpers.sh"

create_git_project() {
    local project_path="${1:-$TEST_PROJECT_DIR}"
    local project_name="${2:-there_and_back_again}"
    local user_email="${3:-bilbo@baggins.shire}"
    local user_name="${4:-Bilbo Baggins}"

    if [[ "$project_path" != "$TEST_PROJECT_DIR" ]]; then
        mkdir -p "$project_path"
        cd "$project_path"
        git init >/dev/null 2>&1
        git config user.email "$user_email"
        git config user.name "$user_name"
    fi

    cat <<'EOF' > README.md
# There and Back Again, a Hobbits Projec
A tale of adventure and discovery in the world of Middle-earth.
EOF

    cat <<'EOF' > main.py
#!/usr/bin/env python3
print("I'm going on an adventure!")
print("Adventure awaits beyond the Shire")
EOF

    cat <<'EOF' > package.json
{
    "name": "an-adventure",
    "version": "1.0.0",
    "description": "A hobbit's journey",
    "main": "main.py",
    "scripts": {
        "start": "python3 main.py"
    }
}
EOF

    git add . >/dev/null 2>&1
    git commit -m "Initial commit: There and Back Again" >/dev/null 2>&1

    # Create additional commit for git history
    cat <<'EOF' >> main.py
print("The road goes ever on and on")
EOF
    git add main.py >/dev/null 2>&1
    git commit -m "Add hobbit wisdom" >/dev/null 2>&1
}


validate_project_info_json() {
    local content="$1"
    local test_name="${2:-unknown test}"

    if ! echo "$content" | jq . >/dev/null 2>&1; then
        echo "ERROR: $test_name - Invalid JSON content: $content" >&2
        return 1
    fi

    # Validate required fields
    if ! echo "$content" | jq -e '.project_name' >/dev/null 2>&1; then
        echo "ERROR: $test_name - Missing project_name field" >&2
        return 1
    fi

    if ! echo "$content" | jq -e '.project_root' >/dev/null 2>&1; then
        echo "ERROR: $test_name - Missing project_root field" >&2
        return 1
    fi

    if ! echo "$content" | jq -e '.timestamp' >/dev/null 2>&1; then
        echo "ERROR: $test_name - Missing timestamp field" >&2
        return 1
    fi

    return 0
}




create_custom_project() {
    local project_dir="$1"
    local readme_content="${2:-# Custom Project}"

    mkdir -p "$project_dir"
    cd "$project_dir"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "$readme_content" > README.md
    git add . >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_git_project
}

teardown() {
    shared_teardown
}

@test "get_project_info returns valid project data with all required fields" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Validate basic fields
    local project_name project_root timestamp
    project_name=$(echo "$content" | jq -r '.project_name')
    project_root=$(echo "$content" | jq -r '.project_root')
    timestamp=$(echo "$content" | jq -r '.timestamp')

    [[ "$project_name" == "there_and_back_again" ]]
    [[ -n "$project_root" ]] && [[ "$project_root" != "null" ]]
    [[ "$timestamp" =~ ^[0-9]+\.?[0-9]*$ ]]
}

@test "get_project_info includes file statistics when requested" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "file statistics test"

    # Validate file statistics presence
    echo "$content" | jq -e '.file_stats' >/dev/null
    echo "$content" | jq -e '.file_stats.total_files' >/dev/null

    local file_coun
    file_count=$(echo "$content" | jq -r '.file_stats.total_files')
    [[ "$file_count" -gt 0 ]]
}

@test "get_project_info excludes file statistics when disabled" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": false}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "file statistics disabled test"

    # Should not include file stats when disabled
    ! echo "$content" | jq -e '.file_stats' >/dev/null 2>&1
}

@test "get_project_info includes comprehensive git information" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "git information test"

    # Validate git information structure
    echo "$content" | jq -e '.git' >/dev/null
    echo "$content" | jq -e '.git.is_git_repo' >/dev/null

    local is_git_repo current_branch repo_roo
    is_git_repo=$(echo "$content" | jq -r '.git.is_git_repo')
    [[ "$is_git_repo" == "true" ]]

    # Check for git branch information
    if echo "$content" | jq -e '.git.current_branch' >/dev/null 2>&1; then
        current_branch=$(echo "$content" | jq -r '.git.current_branch')
        [[ -n "$current_branch" ]] && [[ "$current_branch" != "null" ]]
    fi

    # Check for repository roo
    if echo "$content" | jq -e '.git.repo_root' >/dev/null 2>&1; then
        repo_root=$(echo "$content" | jq -r '.git.repo_root')
        [[ -n "$repo_root" ]] && [[ "$repo_root" != "null" ]]
    fi
}

@test "get_project_info handles non-git directories gracefully" {
    local non_git_project="$TEST_HOME/non-git-project"
    mkdir -p "$non_git_project"
    echo "# Non-git project" > "$non_git_project/README.md"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$non_git_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "non-git directory test"

    # Should still return project info for non-git directories
    local project_name is_git_repo
    project_name=$(echo "$content" | jq -r '.project_name')
    [[ "$project_name" == "non-git-project" ]]

    # Git info should indicate it's not a git repo
    echo "$content" | jq -e '.git' >/dev/null
    is_git_repo=$(echo "$content" | jq -r '.git.is_git_repo')
    [[ "$is_git_repo" == "false" ]]
}

@test "get_project_info handles empty directories gracefully" {
    local empty_project="$TEST_HOME/empty-project"
    mkdir -p "$empty_project"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$empty_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "empty directory test"

    # Should return basic project info for empty directories
    local project_name valid_path
    project_name=$(echo "$content" | jq -r '.project_name')
    [[ "$project_name" == "empty-project" ]]

    # Should indicate valid path
    valid_path=$(echo "$content" | jq -r '.valid_path')
    [[ "$valid_path" == "true" ]]
}

@test "get_project_info handles deeply nested directory structures" {
    local deep_project="$TEST_HOME/deep/nested/structure/project"
    create_custom_project "$deep_project" "# Deep nested project"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$deep_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "deep nested directory test"

    local project_name project_roo
    project_name=$(echo "$content" | jq -r '.project_name')
    project_root=$(echo "$content" | jq -r '.project_root')

    [[ "$project_name" == "project" ]]
    [[ "$project_root" == *"/deep/nested/structure/project"* ]]
}

@test "get_project_info handles special characters in project names" {
    local special_project="$TEST_HOME/test-project_with.special-chars"
    create_custom_project "$special_project" "# Special chars project"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$special_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "special characters test"

    local project_name sanitized
    project_name=$(echo "$content" | jq -r '.project_name')
    sanitized=$(echo "$content" | jq -r '.sanitized')

    # Should handle special characters appropriately
    [[ -n "$project_name" ]] && [[ "$project_name" != "null" ]]
    [[ "$sanitized" == "true" ]] || [[ "$sanitized" == "false" ]]
}

@test "get_project_info provides consistent results across multiple calls" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local first_response="$output"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    local second_response="$output"

    local first_content second_conten
    first_content=$(echo "$first_response" | jq -r '.result.content[0].text')
    second_content=$(echo "$second_response" | jq -r '.result.content[0].text')

    validate_project_info_json "$first_content" "consistency test (first call)"
    validate_project_info_json "$second_content" "consistency test (second call)"

    # Core fields should be consisten
    local first_name second_name first_root second_roo
    first_name=$(echo "$first_content" | jq -r '.project_name')
    second_name=$(echo "$second_content" | jq -r '.project_name')
    first_root=$(echo "$first_content" | jq -r '.project_root')
    second_root=$(echo "$second_content" | jq -r '.project_root')

    [[ "$first_name" == "$second_name" ]]
    [[ "$first_root" == "$second_root" ]]
}

@test "get_project_info includes processing time and performance metrics" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "performance metrics test"

    # Should include processing time
    echo "$content" | jq -e '.processing_time' >/dev/null

    local processing_time
    processing_time=$(echo "$content" | jq -r '.processing_time')
    [[ "$processing_time" =~ ^[0-9]+\.?[0-9]*$ ]]

    # Processing time should be reasonable (less than 5 seconds)
    # Use awk instead of bc for better compatibility
    [[ $(echo "$processing_time 5.0" | awk '{print ($1 < $2)}') -eq 1 ]]
}

@test "get_project_info handles project name sanitization correctly" {
    local unsafe_project="$TEST_HOME/project with spaces & symbols!"
    mkdir -p "$unsafe_project"
    echo "# Unsafe project name" > "$unsafe_project/README.md"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$unsafe_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local conten
    content=$(echo "$output" | jq -r '.result.content[0].text')

    validate_project_info_json "$content" "project name sanitization test"

    # Should sanitize project name and provide transparency
    local project_name sanitized raw_name
    project_name=$(echo "$content" | jq -r '.project_name')
    sanitized=$(echo "$content" | jq -r '.sanitized')

    [[ -n "$project_name" ]] && [[ "$project_name" != "null" ]]
    [[ "$sanitized" == "true" ]] || [[ "$sanitized" == "false" ]]

    # If sanitized, should include raw name
    if [[ "$sanitized" == "true" ]]; then
        echo "$content" | jq -e '.raw_project_name' >/dev/null
        raw_name=$(echo "$content" | jq -r '.raw_project_name')
        [[ "$raw_name" == "project with spaces & symbols!" ]]
    fi
}

@test "get_project_info error handling for invalid parameters" {
    # Test invalid include_stats parameter
    local response
    response=$(execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": "invalid"}}')

    # Should return error response
    echo "$response" | jq -e '.result.content[0].text' >/dev/null &&
    echo "$response" | jq -r '.result.content[0].text' | grep -q "error\|Error" ||
    echo "$response" | jq -e '.error' >/dev/null
}

@test "get_project_info validates project root accessibility" {
    local nonexistent_project="/nonexistent/path/to/project"

    # Use jq to build proper JSON params
    local params
    params=$(jq -nc '{"name": "get_project_info", "arguments": {}}')

    local response
    response=$(execute_rpc "tools/call" "$params" "$nonexistent_project")

    # Should handle nonexistent project gracefully - either error or valid_path=false
    if echo "$response" | jq -e '.result' >/dev/null 2>&1; then
        # If it returns a result, it should indicate invalid path
        local conten
        content=$(echo "$response" | jq -r '.result.content[0].text')

        # Only check valid_path if content is valid JSON
        if echo "$content" | jq . >/dev/null 2>&1; then
            local valid_path
            valid_path=$(echo "$content" | jq -r '.valid_path')
            [[ "$valid_path" == "false" ]] || [[ "$valid_path" == "null" ]]
        else
            # Content should contain error message
            echo "$content" | grep -q -i "error"
        fi
    else
        # Should return error response
        echo "$response" | jq -e '.error' >/dev/null
    fi
}
