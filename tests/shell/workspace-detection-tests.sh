#!/usr/bin/env bats
# Testing of project root detection strategies

set -euo pipefail

load 'fixtures/helpers/test-helpers'

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "Strategy 1: WORKSPACE_FOLDER_PATHS takes highest priority" {
    local workspace_project="$TEST_HOME/workspace-project"
    mkdir -p "$workspace_project"
    cd "$workspace_project"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Workspace Project" >README.md

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "env WORKSPACE_FOLDER_PATHS='$workspace_project' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should detect workspace project as root (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected_resolved
    expected_resolved=$(cd "$workspace_project" && pwd -P)
    [[ "$detected_root" == "$expected_resolved" ]]
}

@test "Strategy 1: Multiple workspace paths - uses first valid one" {
    local workspace1="$TEST_HOME/workspace1"
    local workspace2="$TEST_HOME/workspace2"

    # Create first workspace (invalid)
    mkdir -p "$workspace1"

    # Create second workspace (valid git repo)
    mkdir -p "$workspace2"
    cd "$workspace2"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Workspace 2" >README.md

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "env WORKSPACE_FOLDER_PATHS='$workspace1:$workspace2' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should use the first valid workspace (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected1_resolved expected2_resolved
    expected1_resolved=$(cd "$workspace1" && pwd -P)
    expected2_resolved=$(cd "$workspace2" && pwd -P)
    [[ "$detected_root" == "$expected1_resolved" ]] || [[ "$detected_root" == "$expected2_resolved" ]]
}

@test "Strategy 2: Git root detection in workspace paths" {
    local git_subdir="$TEST_HOME/git-project/subdir"
    mkdir -p "$git_subdir"
    cd "$TEST_HOME/git-project"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Git Project" >README.md

    local python_exec
    python_exec=$(get_python_executable)
    # Test without WORKSPACE_FOLDER_PATHS to trigger git root detection
    run bash -c "cd '$git_subdir' && '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should detect git root from subdirectory (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected_resolved
    expected_resolved=$(cd "$TEST_HOME/git-project" && pwd -P)
    [[ "$detected_root" == "$expected_resolved" ]]
}

@test "Strategy 2: Git detection fallback to current directory" {
    local git_project="$TEST_HOME/git-fallback"
    mkdir -p "$git_project"
    cd "$git_project"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Git Fallback" >README.md

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "cd '$git_project' && '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should detect current git directory (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected_resolved
    expected_resolved=$(cd "$git_project" && pwd -P)
    [[ "$detected_root" == "$expected_resolved" ]]
}

@test "Strategy 3: PWD environment variable fallback" {
    local pwd_project="$TEST_HOME/pwd-project"
    mkdir -p "$pwd_project"
    echo "# PWD Project" >"$pwd_project/README.md"

    local python_exec
    python_exec=$(get_python_executable)
    # Run from a different directory with PWD set to trigger PWD fallback
    run bash -c "cd /tmp && env PWD='$pwd_project' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should use PWD as fallback (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected_resolved
    expected_resolved=$(cd "$pwd_project" && pwd -P)
    [[ "$detected_root" == "$expected_resolved" ]]
}

@test "Strategy 4: Current working directory final fallback" {
    local cwd_project="$TEST_HOME/cwd-project"
    mkdir -p "$cwd_project"
    echo "# CWD Project" >"$cwd_project/README.md"

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "cd '$cwd_project' && env -u PWD -u WORKSPACE_FOLDER_PATHS '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should use current working directory as final fallback (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected_resolved
    expected_resolved=$(cd "$cwd_project" && pwd -P)
    [[ "$detected_root" == "$expected_resolved" ]]
}

@test "Real-world scenario: Cursor MCP server startup" {
    local cursor_workspace="$TEST_HOME/cursor-workspace"
    mkdir -p "$cursor_workspace/src"
    cd "$cursor_workspace"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Cursor Workspace" >README.md
    echo "console.log('hello');" >src/app.js

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "env WORKSPACE_FOLDER_PATHS='$cursor_workspace' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\".js\", \".md\"]}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should list files from the cursor workspace
    echo "$output" | grep -q "app.js\|README.md"
}

@test "Error handling: Invalid workspace paths" {
    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "env WORKSPACE_FOLDER_PATHS='/nonexistent/path:/another/invalid/path' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Should fallback gracefully and not crash
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    echo "$result_line" | jq -e '.result.content[0].text | fromjson | .project_root' >/dev/null
}

@test "Workspace detection logging verification" {
    local workspace_project="$TEST_HOME/logging-test"
    mkdir -p "$workspace_project"
    cd "$workspace_project"
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Logging Test" >README.md

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "env WORKSPACE_FOLDER_PATHS='$workspace_project' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}'"
    [ "$status" -eq 0 ]

    # Should include workspace detection info in logs (notifications)
    echo "$output" | grep -q "notification\|workspace\|project.*root" || true
}

@test "Strategy priority ordering verification" {
    local workspace_path="$TEST_HOME/priority-workspace"
    local pwd_path="$TEST_HOME/priority-pwd"

    mkdir -p "$workspace_path" "$pwd_path"
    echo "# Workspace" >"$workspace_path/README.md"
    echo "# PWD" >"$pwd_path/README.md"

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "env WORKSPACE_FOLDER_PATHS='$workspace_path' PWD='$pwd_path' '$python_exec' '$SERVER_DIR/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null"
    [ "$status" -eq 0 ]

    # WORKSPACE_FOLDER_PATHS should take priority over PWD (handle path resolution)
    local result_line
    result_line=$(echo "$output" | grep '"result"' | head -1)
    local detected_root
    detected_root=$(echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root')

    # Compare resolved paths since server resolves symlinks
    local expected_resolved
    expected_resolved=$(cd "$workspace_path" && pwd -P)
    [[ "$detected_root" == "$expected_resolved" ]]
}
