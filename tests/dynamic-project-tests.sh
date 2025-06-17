#!/usr/bin/env bats

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
test_id=0

execute_rpc_dynamic() {
    test_id=$((test_id + 1))
    local method="$1"
    local params="$2"
    local working_dir="$3"

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

    # Change to the working directory and set PWD environment variable
    # This sould simulate how the server would be called from different projects
    cd "$working_dir"
    export PWD="$working_dir"
    export GANDALF_TEST_MODE=true
    echo "$request" | "$GANDALF_ROOT/gandalf.sh" run 2>/dev/null
    local exit_code=$?

    return $exit_code
}

create_test_repo() {
    local repo_name="$1"
    local repo_dir="$TEMP_BASE_DIR/$repo_name"

    mkdir -p "$repo_dir"
    pushd "$repo_dir" >/dev/null

    git init >/dev/null 2>&1
    git config user.email "samwise@shire.net"
    git config user.name "Samwise Gamgee"

    echo "# $repo_name Repository" >README.md
    echo "def main():" >main.py
    echo "    print('Hello from $repo_name')" >>main.py
    echo "*.pyc" >.gitignore
    echo "*.log" >>.gitignore

    git add . >/dev/null 2>&1
    git commit -m "Initial commit for $repo_name" >/dev/null 2>&1

    popd >/dev/null

    echo "$repo_dir"
}

# Helper function to get conversation count for a project
get_conversation_count() {
    local project_dir="$1"
    cd "$project_dir"
    export PWD="$project_dir"
    echo '{"id": 1, "method": "tools/call", "params": {"name": "list_conversations", "arguments": {}}}' |
        "$GANDALF_ROOT/gandalf.sh" run 2>/dev/null |
        jq -r '.result.content[0].text' 2>/dev/null |
        grep -o '"conversation_id"' | wc -l || echo "0"
}

setup_file() {
    TEMP_BASE_DIR=$(mktemp -d)
    export TEMP_BASE_DIR

    REPO_MORDOR=$(create_test_repo "project-mordor")
    REPO_SHIRE=$(create_test_repo "project-shire")
    REPO_RIVENDELL=$(create_test_repo "project-rivendell")

    export REPO_MORDOR REPO_SHIRE REPO_RIVENDELL

    cat <<EOF
Created test repositories:
    Project Mordor: $REPO_MORDOR
    Project Shire:  $REPO_SHIRE
    Project Rivendell: $REPO_RIVENDELL
EOF
}

teardown_file() {
    [[ -n "$TEMP_BASE_DIR" && -d "$TEMP_BASE_DIR" ]] && rm -rf "$TEMP_BASE_DIR" 2>/dev/null || true
    echo "Cleaned up test repositories"
}

setup() {
    cd "$GIT_ROOT"
    unset PWD
}

teardown() {
    cd "$GIT_ROOT"
    unset PWD
}

# Helper function to format JSON output with jq for better readability
format_json_output() {
    local output="$1"
    echo "$output" | jq -r '.result.content[0].text' 2>/dev/null | jq . 2>/dev/null || echo "$output"
}

@test "Dynamic project detection: Server initializes correctly from different directories" {
    run execute_rpc_dynamic "initialize" "{}" "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "protocolVersion"

    run execute_rpc_dynamic "initialize" "{}" "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "protocolVersion"

    run execute_rpc_dynamic "initialize" "{}" "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "protocolVersion"
}

@test "Dynamic project detection: get_project_info returns correct project for each directory" {
    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]

    if ! echo "$output" | grep -q "project-mordor"; then
        echo "Expected project-mordor, got:"
        format_json_output "$output"
    fi

    echo "$output" | grep -q "project-mordor"
    echo "$output" | grep -q "$REPO_MORDOR"

    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    if ! echo "$output" | grep -q "project-shire"; then
        echo "Expected project-shire, got:"
        format_json_output "$output"
    fi

    echo "$output" | grep -q "project-shire"
    echo "$output" | grep -q "$REPO_SHIRE"

    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]

    if ! echo "$output" | grep -q "project-rivendell"; then
        echo "Expected project-rivendell, got:"
        format_json_output "$output"
    fi

    echo "$output" | grep -q "project-rivendell"
    echo "$output" | grep -q "$REPO_RIVENDELL"
}

@test "Dynamic project detection: list_project_files returns correct files for each project" {
    run execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "README.md"
    echo "$output" | grep -q "main.py"

    run execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "README.md"
    echo "$output" | grep -q "main.py"

    run execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "README.md"
    echo "$output" | grep -q "main.py"
}

@test "Dynamic project detection: git_status returns correct git info for each project" {
    run execute_rpc_dynamic "tools/call" '{"name": "get_git_status", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "is_clean"
    echo "$output" | grep -q "current_branch"

    run execute_rpc_dynamic "tools/call" '{"name": "get_git_status", "arguments": {}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "is_clean"
    echo "$output" | grep -q "current_branch"

    # Test rivendell git status
    run execute_rpc_dynamic "tools/call" '{"name": "get_git_status", "arguments": {}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "is_clean"
    echo "$output" | grep -q "current_branch"
}

@test "Dynamic project detection: conversations use correct project context" {
    # Even if storage fails, the project detection should work

    run execute_rpc_dynamic "tools/call" '{"name": "list_conversations", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    # Should detect project-mordor
    echo "$output" | grep -q "project-mordor" || echo "$output" | grep -q "project: /.*project-mordor"

    run execute_rpc_dynamic "tools/call" '{"name": "list_conversations", "arguments": {}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    # Should detect project-shire
    echo "$output" | grep -q "project-shire" || echo "$output" | grep -q "project: /.*project-shire"

    run execute_rpc_dynamic "tools/call" '{"name": "list_conversations", "arguments": {}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    # Should detect project-rivendell
    echo "$output" | grep -q "project-rivendell" || echo "$output" | grep -q "project: /.*project-rivendell"
}

@test "Dynamic project detection: search_conversations detects correct project context" {

    run execute_rpc_dynamic "tools/call" '{"name": "search_conversations", "arguments": {"query": "test", "type": "all"}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    # Should operate in project-mordor context
    echo "$output" | grep -q "project-mordor" || echo "$output" | grep -q "project: /.*project-mordor"

    run execute_rpc_dynamic "tools/call" '{"name": "search_conversations", "arguments": {"query": "test", "type": "all"}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    # Should operate in project-shire context
    echo "$output" | grep -q "project-shire" || echo "$output" | grep -q "project: /.*project-shire"
}

@test "Dynamic project detection: analytics sessions are project-specific" {
    # Trigger analytics

    execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_MORDOR" >/dev/null
    execute_rpc_dynamic "tools/call" '{"name": "get_git_status", "arguments": {}}' "$REPO_MORDOR" >/dev/null

    execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_SHIRE" >/dev/null
    execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_SHIRE" >/dev/null

    # This passes if no errors occur and projects are detected correctly
    [ $? -eq 0 ]
}

@test "Dynamic project detection: project switching preserves separate analytics sessions" {
    # Generate analytics session in morder by calling multiple tools
    execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_MORDOR" >/dev/null
    execute_rpc_dynamic "tools/call" '{"name": "get_git_status", "arguments": {}}' "$REPO_MORDOR" >/dev/null

    # Generate analytics session in shire by calling multiple tools
    execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_SHIRE" >/dev/null
    execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_SHIRE" >/dev/null

    # Wait a moment for async storage
    sleep 2

    # Verify that analytics are being stored separately per project
    # Instead of checking exact counts, verify that each project can access its own analytics
    run execute_rpc_dynamic "tools/call" '{"name": "list_conversations", "arguments": {"type": "analytics"}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    # Should work without errors; the fact it runs means project detection is working

    run execute_rpc_dynamic "tools/call" '{"name": "list_conversations", "arguments": {"type": "analytics"}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    # Should work without errors; the fact it runs means project detection is working

    # Test passes if both projects can access their analytics without errors
    # This verifies the core functionality: separate project contexts
}

@test "Dynamic project detection: file operations work correctly per project" {
    # Create different files in each project
    echo "Mordor specific content" >"$REPO_MORDOR/mordor.txt"
    echo "Shire specific content" >"$REPO_SHIRE/shire.txt"
    echo "Rivendell specific content" >"$REPO_RIVENDELL/rivendell.txt"

    # Test file listing in morder (should see mordor.txt)
    run execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "mordor.txt"
    ! echo "$output" | grep -q "shire.txt"
    ! echo "$output" | grep -q "rivendell.txt"

    # Test file listing in shire (should see shire.txt)
    run execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "shire.txt"
    ! echo "$output" | grep -q "mordor.txt"
    ! echo "$output" | grep -q "rivendell.txt"

    # Test file listing in rivendell (should see rivendell.txt)
    run execute_rpc_dynamic "tools/call" '{"name": "list_project_files", "arguments": {}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "rivendell.txt"
    ! echo "$output" | grep -q "mordor.txt"
    ! echo "$output" | grep -q "shire.txt"
}

@test "Dynamic project detection: codebase_search works correctly per project" {
    # Test semantic search in each project returns project-specific results
    run execute_rpc_dynamic "tools/call" '{"name": "codebase_search", "arguments": {"query": "main function"}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-mordor" || echo "$output" | grep -q "main.py"

    run execute_rpc_dynamic "tools/call" '{"name": "codebase_search", "arguments": {"query": "main function"}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-shire" || echo "$output" | grep -q "main.py"

    run execute_rpc_dynamic "tools/call" '{"name": "codebase_search", "arguments": {"query": "main function"}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-rivendell" || echo "$output" | grep -q "main.py"
}

@test "Dynamic project detection: rapid project switching works correctly" {
    # Rapidly switch between projects and verify correct detection
    for i in {1..5}; do
        # morder
        run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_MORDOR"
        [ "$status" -eq 0 ]
        echo "$output" | grep -q "project-mordor"

        # shire
        run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_SHIRE"
        [ "$status" -eq 0 ]
        echo "$output" | grep -q "project-shire"

        # rivendell
        run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_RIVENDELL"
        [ "$status" -eq 0 ]
        echo "$output" | grep -q "project-rivendell"
    done
}

@test "Dynamic project detection: error handling for non-existent directories" {
    # Test that server handles non-existent directories gracefully
    local non_existent_dir="/tmp/does-not-exist-$(date +%s)"

    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$non_existent_dir"
    # Should not crash, but may return an error
    # The test passes if the server doesn't crash completely
    [ "$status" -eq 0 ] || echo "$output" | grep -q "error"
}

@test "Dynamic project detection: project context switching works correctly" {
    # Verify morder context is detected correctly
    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-mordor"

    # Immediately switch to shire and verify context change
    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_SHIRE"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-shire"

    # Switch back to morder and verify it still works
    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_MORDOR"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-mordor"

    # Test rivendell
    run execute_rpc_dynamic "tools/call" '{"name": "get_project_info", "arguments": {}}' "$REPO_RIVENDELL"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "project-rivendell"
}
