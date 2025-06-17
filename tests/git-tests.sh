#!/usr/bin/env bats

# Git tests.
# At the moment these are only testing git diffs, the rest of the git tools we use like history and status aren't
# something we need extensive testing for. Even diff isn't incredibly important but I like it for sanity checking.

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
test_id=0

# Helper function to execute JSON-RPC requests
execute_rpc() {
    test_id=$((test_id + 1))
    local method="$1"
    local params="$2"
    local project_root="${3:-$GANDALF_ROOT}"

    local request
    if [[ "$params" == "invalid_json" ]]; then
        request="invalid json"
    else
        request=$(jq -nc \
            --arg method "$method" \
            --argjson params "$params" \
            --arg id "$test_id" \
            '{
                "id": $id,
                "method": $method,
                "params": $params
            }')
    fi

    export GANDALF_TEST_MODE=true
    echo "$request" | "$GANDALF_ROOT/gandalf.sh" run --project-root "$project_root" 2>/dev/null
    local exit_code=$?

    return $exit_code
}

@test "Git diff tool available, should pass" {
    run execute_rpc "tools/list" "{}"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"name": "get_git_diff"'
}

@test "Git diff HEAD commit, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"commit_hash": "HEAD"}}'
    [ "$status" -eq 0 ]

    # Should contain result with content
    echo "$output" | grep -q '"result"'
    echo "$output" | grep -q '"content"'
}

@test "Git diff specific file, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"commit_hash": "HEAD", "file_path": "gandalf/gandalf.sh"}}'
    [ "$status" -eq 0 ]

    # Should contain result, mention 'HEAD' specifically, and 'gandalf.sh'
    echo "$output" | grep -q '"result"'
    echo "$output" | grep -q 'commit_hash.*HEAD'
    echo "$output" | grep -q 'file_path.*gandalf'
}

@test "Git diff staged changes, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"staged": true}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q '"result"'
    echo "$output" | grep -q 'staged.*true'
}

@test "Git diff invalid commit hash, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"commit_hash": "nonexistent123"}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q '"result"'
}

@test "Git diff with timeout, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"commit_hash": "HEAD", "timeout": 5}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q '"result"'
}

@test "Git diff with invalid timeout parameter, should fail" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"commit_hash": "HEAD", "timeout": -1}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q '"error"\|"result"'
}

@test "Git diff with malformed arguments, should fail" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"invalid_field": "value"}}'
    [ "$status" -eq 0 ]

    # Should handle missing required fields gracefully.
    echo "$output" | grep -q '"result"'
}

@test "Git diff non-existent file, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_diff", "arguments": {"commit_hash": "HEAD", "file_path": "non-existent-file.txt"}}'

    # Empty diff is still a valid response
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"result"'
}

@test "Git status tool, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_status", "arguments": {}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q '"result"'
    echo "$output" | grep -q '"content"'
}

@test "Git commit history tool, should pass" {
    run execute_rpc "tools/call" '{"name": "get_git_commit_history", "arguments": {"limit": 5}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q '"result"'
    echo "$output" | grep -q '"content"'
}
