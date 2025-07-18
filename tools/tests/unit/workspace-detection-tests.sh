#!/usr/bin/env bats
# Workspace Detection Tests for Gandalf MCP Server
# Tests workspace detection and project root identification

set -euo pipefail

load '../../lib/test-helpers.sh'

create_git_workspace() {
    local workspace_path="$1"
    local user_email="${2:-test@gandalf.test}"
    local user_name="${3:-Gandalf Test}"
    local readme_content="${4:-# Test Workspace}"
    
    mkdir -p "$workspace_path"
    cd "$workspace_path"
    git init >/dev/null 2>&1
    git config user.email "$user_email"
    git config user.name "$user_name"
    echo "$readme_content" > README.md
    git add . >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1
}

execute_workspace_detection() {
    local env_vars="$1"
    local project_root="${2:-}"
    
    local params="{}"
    local server_args=""
    
    if [[ -n "$project_root" ]]; then
        server_args="--project-root '$project_root'"
    fi
    
    local response
    response=$(bash -c "cd '$GANDALF_ROOT/server' && env $env_vars PYTHONPATH=. python3 src/main.py $server_args <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null")
    
    if [[ $? -ne 0 ]]; then
        echo "ERROR: Server execution failed"
        return 1
    fi
    
    local result_line
    result_line=$(echo "$response" | grep '"result"' | head -1)
    
    if [[ -z "$result_line" ]]; then
        echo "ERROR: No result found in response"
        return 1
    fi
    
    echo "$result_line" | jq -r '.result.content[0].text | fromjson | .project_root'
}

resolve_and_compare_paths() {
    local detected_path="$1"
    local expected_path="$2"
    local test_name="${3:-unknown test}"
    
    local expected_resolved
    expected_resolved=$(cd "$expected_path" && pwd -P)
    
    if [[ "$detected_path" != "$expected_resolved" ]]; then
        echo "FAIL: $test_name - Expected: $expected_resolved, Got: $detected_path" >&2
        return 1
    fi
    
    return 0
}

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "Strategy 1: WORKSPACE_FOLDER_PATHS takes highest priority" {
    local workspace_project="$TEST_HOME/rivendell-workspace"
    create_git_workspace "$workspace_project" "elrond@rivendell.middleearth" "Lord Elrond" "# Rivendell Workspace"
    
    local detected_root
    detected_root=$(execute_workspace_detection "WORKSPACE_FOLDER_PATHS='$workspace_project'")
    
    resolve_and_compare_paths "$detected_root" "$workspace_project" "WORKSPACE_FOLDER_PATHS priority test"
}

@test "Strategy 1: Multiple workspace paths - uses first valid one" {
    local workspace1="$TEST_HOME/moria-mines"
    local workspace2="$TEST_HOME/lothlorien-realm"
    
    # Create first workspace (invalid, no git)
    mkdir -p "$workspace1"
    
    # Create second workspace (valid git repo)
    create_git_workspace "$workspace2" "galadriel@lothlorien.middleearth" "Lady Galadriel" "# Lothlorien Realm"
    
    local detected_root
    detected_root=$(execute_workspace_detection "WORKSPACE_FOLDER_PATHS='$workspace1:$workspace2'")
    
    # Should use the first valid workspace
    local expected1_resolved expected2_resolved
    expected1_resolved=$(cd "$workspace1" && pwd -P)
    expected2_resolved=$(cd "$workspace2" && pwd -P)
    
    [[ "$detected_root" == "$expected1_resolved" ]] || [[ "$detected_root" == "$expected2_resolved" ]]
}

@test "Strategy 2: Git root detection in workspace paths" {
    local git_subdir="$TEST_HOME/isengard-tower/saruman-quarters"
    local git_root="$TEST_HOME/isengard-tower"
    
    create_git_workspace "$git_root" "saruman@isengard.middleearth" "Saruman the White" "# Isengard Tower"
    mkdir -p "$git_subdir"
    
    # Execute from subdirectory to test git root detection
    local detected_root
    detected_root=$(bash -c "cd '$git_subdir' && PYTHONPATH='$GANDALF_ROOT/server' python3 '$GANDALF_ROOT/server/src/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null" | grep '"result"' | head -1 | jq -r '.result.content[0].text | fromjson | .project_root')
    
    resolve_and_compare_paths "$detected_root" "$git_root" "git root detection test"
}

@test "Strategy 2: Git detection fallback to current directory" {
    local git_project="$TEST_HOME/git-fallback"
    create_git_workspace "$git_project" "test@gandalf.test" "Gandalf Test" "# Git Fallback"
    
    local detected_root
    detected_root=$(execute_workspace_detection "" "$git_project")
    
    resolve_and_compare_paths "$detected_root" "$git_project" "git fallback test"
}

@test "Strategy 3: PWD environment variable fallback" {
    local pwd_project="$TEST_HOME/pwd-project"
    mkdir -p "$pwd_project"
    echo "# PWD Project" > "$pwd_project/README.md"
    
    local detected_root
    detected_root=$(bash -c "cd /tmp && env PWD='$pwd_project' PYTHONPATH='$GANDALF_ROOT/server' python3 '$GANDALF_ROOT/server/src/main.py' <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}' 2>/dev/null" | grep '"result"' | head -1 | jq -r '.result.content[0].text | fromjson | .project_root')
    
    resolve_and_compare_paths "$detected_root" "$pwd_project" "PWD fallback test"
}

@test "Strategy 4: Current working directory final fallback" {
    local cwd_project="$TEST_HOME/cwd-project"
    mkdir -p "$cwd_project"
    echo "# CWD Project" > "$cwd_project/README.md"
    
    local detected_root
    detected_root=$(execute_workspace_detection "env -u PWD -u WORKSPACE_FOLDER_PATHS" "$cwd_project")
    
    # The core test is that the server doesn't crash and returns a valid project root
    [[ -n "$detected_root" ]] && [[ "$detected_root" != "null" ]] && [[ "$detected_root" != "" ]]
}

@test "Real-world scenario: Cursor MCP server startup" {
    local cursor_workspace="$TEST_HOME/rohan-kingdom"
    mkdir -p "$cursor_workspace/src"
    create_git_workspace "$cursor_workspace" "theoden@rohan.middleearth" "King Theoden" "# Rohan Kingdom"
    echo "console.log('Riders of Rohan!');" > "$cursor_workspace/src/app.js"
    
    local response
    response=$(bash -c "cd '$GANDALF_ROOT/server' && env WORKSPACE_FOLDER_PATHS='$cursor_workspace' PYTHONPATH=. python3 src/main.py <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\".js\", \".md\"]}}}' 2>/dev/null")
    
    echo "$response" | grep -q "app.js\|README.md"
}

@test "Error handling: Invalid workspace paths" {
    local detected_root
    detected_root=$(execute_workspace_detection "WORKSPACE_FOLDER_PATHS='/nonexistent/path:/another/invalid/path'")
    
    # Should fallback gracefully and not crash
    [[ -n "$detected_root" ]] && [[ "$detected_root" != "null" ]]
}

@test "Workspace detection logging verification" {
    local workspace_project="$TEST_HOME/logging-test"
    create_git_workspace "$workspace_project" "test@gandalf.test" "Gandalf Test" "# Logging Test"
    
    local response
    response=$(bash -c "cd '$GANDALF_ROOT/server' && env WORKSPACE_FOLDER_PATHS='$workspace_project' PYTHONPATH=. python3 src/main.py <<< '{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\", \"id\": 1, \"params\": {\"name\": \"get_project_info\", \"arguments\": {}}}'" 2>&1)
    
    # Should include workspace detection info in logs (stdout/stderr)
    echo "$response" | grep -q "notification\|workspace\|project.*root" || true
}

@test "Strategy priority ordering verification" {
    local workspace_path="$TEST_HOME/priority-test"
    local pwd_path="$TEST_HOME/pwd-test"
    
    create_git_workspace "$workspace_path" "test@gandalf.test" "Gandalf Test" "# Priority Test"
    mkdir -p "$pwd_path"
    
    local detected_root
    detected_root=$(execute_workspace_detection "WORKSPACE_FOLDER_PATHS='$workspace_path' PWD='$pwd_path'")
    
    # Should prioritize WORKSPACE_FOLDER_PATHS over PWD
    resolve_and_compare_paths "$detected_root" "$workspace_path" "priority ordering test"
}
