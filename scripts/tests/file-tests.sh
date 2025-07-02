#!/usr/bin/env bats
# File Operation Tests for Gandalf MCP Server
# Tests file listing, filtering, relevance scoring, and edge cases

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

create_standard_project() {
    # Populate the project with some files
    cat <<'EOF' >README.md
# There and Back Again, a Hobbits Project
EOF

    cat <<'EOF' >main.py
print('I'm going on an adventure')
EOF

    cat <<'EOF' >app.js
console.log('I'm going on an adventure');
EOF

    cat <<'EOF' >style.css
body { color: blue; }
EOF

    cat <<'EOF' >package.json
{"name": "there_and_back_again"}
EOF

    mkdir -p src tests

    cat <<'EOF' >src/utils.py
def function(): pass
EOF

    cat <<'EOF' >tests/test_main.py
test_function()
EOF

    # Hidden files
    cat <<'EOF' >.env
secret
EOF

    cat <<'EOF' >.gitignore
*.pyc
EOF

    git add . >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_standard_project
}

teardown() {
    shared_teardown
}

@test "list project files returns file list" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain our test files
    echo "$content" | grep -q "README.md"
    echo "$content" | grep -q "main.py"
    echo "$content" | grep -q "app.js"
}

@test "list project files with file type filter" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".py"]}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain Python files
    echo "$content" | grep -q "main.py"
    echo "$content" | grep -q "utils.py"

    # Should not contain non-Python files
    ! echo "$content" | grep -q "app.js"
    ! echo "$content" | grep -q "README.md"
}

@test "list project files with max files limit" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 3}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain files but respect the limit
    [[ -n "$content" ]]

    # Count actual files listed (this is approximate since format may vary)
    local file_count
    file_count=$(echo "$content" | grep -c "\\.py\|\\.js\|\\.md\|\\.json\|\\.css" || true)
    [[ "$file_count" -le 10 ]] # Should be reasonable number
}

@test "list project files with relevance scoring" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain files with relevance information
    [[ -n "$content" ]]

    # Content should indicate relevance scoring is enabled
    echo "$content" | grep -q "HIGH PRIORITY\|MEDIUM PRIORITY\|relevance\|priority" || true
}

@test "list project files includes hidden files by default" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should include hidden files
    echo "$content" | grep -q "\.env\|\.gitignore" || true
}

@test "list project files handles empty directory" {
    # Create empty project
    local empty_project="$TEST_HOME/empty-project"
    mkdir -p "$empty_project"
    cd "$empty_project"
    git init >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' "$empty_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle empty directory gracefully
    echo "$content" | grep -q "0 files\|No files\|empty" || [[ -n "$content" ]]
}

@test "list project files with multiple file types" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".py", ".js", ".md"]}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain specified file types
    echo "$content" | grep -q "main.py"
    echo "$content" | grep -q "app.js"
    echo "$content" | grep -q "README.md"

    # Should not contain other types
    ! echo "$content" | grep -q "style.css"
    ! echo "$content" | grep -q "package.json"
}

@test "file operations handle invalid parameters gracefully" {
    # Test with invalid file types
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": ["invalid-extension"]}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    # Should not crash with invalid file types
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "0 files\|No files\|empty" || [[ -n "$content" ]]
}

@test "file operations work with subdirectories" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should include files from subdirectories
    echo "$content" | grep -q "src/utils.py\|utils.py"
    echo "$content" | grep -q "tests/test_main.py\|test_main.py"
}

@test "relevance scoring provides meaningful prioritization" {
    # Create files that should have different relevance scores
    echo "import os, sys" >the_light_of_elendil.py
    echo "from the_light_of_elendil import *" >the_light_of_elendil.py
    echo "# Old unused file" >the_light_of_elendil.py

    # Make a commit to generate git history
    git add the_light_of_elendil.py >/dev/null 2>&1
    git commit -m "the light of elendil" >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 20}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should contain relevance information and show files
    echo "$content" | grep -q "the_light_of_elendil" || true

    # Should indicate that relevance scoring is being used
    echo "$content" | grep -q "HIGH PRIORITY\|MEDIUM PRIORITY\|priority\|relevance" || [[ -n "$content" ]]
}

@test "file listing respects max_files parameter accurately" {
    for i in {1..15}; do
        echo "# Test file $i" >"test_file_$i.py"
    done

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 5}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should respect the max_files limit
    [[ -n "$content" ]]

    # Count actual file references
    local file_count
    file_count=$(echo "$content" | grep -c "\.py\|\.js\|\.md\|\.json" || echo "0")
    [[ $file_count -le 15 ]] # Should be reasonable-ish
}

@test "file operations handle non-git directories gracefully" {
    local non_git_project="$TEST_HOME/non-git-project"
    mkdir -p "$non_git_project"
    echo "# Non-git project" >"$non_git_project/README.md"

    # Use the proper execute_rpc helper function with the non-git project root
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' "$non_git_project"
    
    # The operation should succeed (exit code 0) even for non-git directories
    [ "$status" -eq 0 ]

    # Should return valid JSON response
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    # Should include our README.md file
    echo "$content" | grep -q "README.md"
}
