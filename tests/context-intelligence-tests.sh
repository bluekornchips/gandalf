#!/usr/bin/env bats

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required for context intelligence tests" >&2
    exit 1
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
test_id=0

execute_rpc() {
    test_id=$((test_id + 1))
    local method="$1"
    local params="$2"
    local project_root="${3:-$TEST_REPO}"

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

    # Disable dynamic project detection for context intelligence tests
    export GANDALF_DISABLE_DYNAMIC_DETECTION=true
    # Disable conversation storage during tests
    export GANDALF_TEST_MODE=true
    echo "$request" | "$GANDALF_ROOT/gandalf.sh" run --project-root "$project_root" 2>/dev/null
    local exit_code=$?

    return $exit_code
}

setup() {
    TEMP_DIR=$(mktemp -d)
    TEST_REPO="$TEMP_DIR/test-repo"
    mkdir -p "$TEST_REPO"

    pushd "$TEST_REPO" >/dev/null

    git init >/dev/null 2>&1
    git config user.email "frodo@bagend.shire"
    git config user.name "Frodo Baggins"

    # High priority file, python
    mkdir -p src
    echo 'def main(): print("Oh, Sam.")' >src/main.py
    echo 'class RingOfPower: pass' >src/models.py

    # Medium priority file, JavaScript
    mkdir -p components
    cat <<EOF >components/app.js
function createApp() {
    console.log("They're taking the hobbits to Isengard!")
    return {}
}
EOF

    echo '# Project Documentation' >README.md
    echo '# API Documentation' >docs.md
    echo '{"name": "the-fellowship"}' >package.json
    echo 'debug = true' >config.toml

    # Large file, should get lower priority
    head -c 100000 /dev/zero >large_file.bin

    # Hidden files, should be excluded by default
    echo 'secret' >.env

    # Test directory structure, should be included
    mkdir -p tests
    echo 'test("basic", () => expect(true).toBe(true))' >tests/basic.test.js

    # Old file, mimic old modification time
    echo 'old content' >old_file.txt

    # Add and commit some files to mimic git activity, should be included
    git add src/ README.md package.json >/dev/null 2>&1
    git commit -m "Initial commit" >/dev/null 2>&1

    # Simulate recent activity on specific files, should be included
    echo '# Updated documentation' >>README.md
    git add README.md >/dev/null 2>&1
    git commit -m "Update README" >/dev/null 2>&1

    popd >/dev/null
}

@test "Context intelligence can be enabled/disabled, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "HIGH PRIORITY FILES:"
    echo "$output" | grep -q "TOP FILES BY RELEVANCE:"
    echo "$output" | grep -q "SUMMARY:.*total files"

    # Test with intelligence disabled
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": false, "max_files": 5}}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Found [0-9]* files:"
    # Should not have context intelligence formatting
    ! echo "$output" | grep -q "HIGH PRIORITY FILES"
    ! echo "$output" | grep -q "TOP FILES BY RELEVANCE"
}

@test "File type prioritization works, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # Verify Python files (.py) appear in high priority section (they should score higher)
    echo "$output" | grep -q "HIGH PRIORITY FILES:"
    echo "$output" | grep -A10 "HIGH PRIORITY FILES:" | grep -q "\.py"

    # Verify JavaScript and markdown files (.js and .md) are still included
    echo "$output" | grep -q "\.js"
    echo "$output" | grep -q "\.md"
}

@test "Hidden files are excluded, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # Should not include .env file in any section
    ! echo "$output" | grep -q "\.env"
}

@test "Hidden files can be included if requested, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "include_hidden": true}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q "HIGH PRIORITY FILES:\|TOP FILES BY RELEVANCE:"
    # Should include .env file
    echo "$output" | grep -q "\.env"
}

@test "File type filtering works, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "file_types": [".py"]}}'
    [ "$status" -eq 0 ]

    # .py only files
    echo "$output" | grep -q "main\.py"
    echo "$output" | grep -q "models\.py"
    ! echo "$output" | grep -q "app\.js"
    ! echo "$output" | grep -q "README\.md"
}

@test "Summary statistics are accurate, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # Verify specific summary format and content
    echo "$output" | grep -q "SUMMARY: [0-9]* total files"
    echo "$output" | grep -q "High priority: [0-9]*"
    echo "$output" | grep -q "Medium priority: [0-9]*"
    echo "$output" | grep -q "Low priority: [0-9]*"

    # We should verify total, but that is a more sophisticated check I will do later
    echo "$output" | grep -q "SUMMARY:"
}

@test "Large files get lower priority, should pass" {
    # This is testing whether we crash or not basically
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # Should have context intelligence format
    echo "$output" | grep -q "HIGH PRIORITY FILES:"
    echo "$output" | grep -q "TOP FILES BY RELEVANCE:"

    echo "$output" | grep -q "large_file\.bin"
}

@test "Git activity affects file scoring, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # README.md was committed recently in setup, so should appear in results
    echo "$output" | grep -q "README\.md"
    echo "$output" | grep -q "HIGH PRIORITY FILES:"
}

@test "Max files limit is respected with scoring, should pass" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 3}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q "HIGH PRIORITY FILES:"
    echo "$output" | grep -q "TOP FILES BY RELEVANCE:"

    # Should show exactly 3 files in summary
    echo "$output" | grep -q "SUMMARY: 3 total files"

    # Count the actual files listed (should be 3 or fewer)
    file_count=$(echo "$output" | grep -E "  [a-zA-Z0-9_/.-]+\.(py|js|md|bin|toml|json)" | wc -l | tr -d ' ')
    [ "$file_count" -le 6 ] # The files appear in both sections, so max 6 lines
}

@test "Context intelligence handles empty project, should exit okay and pass" {
    EMPTY_REPO="$TEMP_DIR/empty-repo"
    mkdir -p "$EMPTY_REPO"
    cd "$EMPTY_REPO" && git init >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}' "$EMPTY_REPO"
    [ "$status" -eq 0 ]

    # Should handle empty project without errors - may show 0 or empty results but as long theres not exit code 1 we are good
    echo "$output" | grep -q "SUMMARY: 0 total files\|Found 0 files\|HIGH PRIORITY FILES:"
}

@test "Tool definition includes relevance scoring parameter, should pass" {
    run execute_rpc "tools/list" "{}"
    [ "$status" -eq 0 ]

    # Should include the specific parameter name and description
    echo "$output" | grep -q "use_relevance_scoring"
    echo "$output" | grep -q "Enable intelligent file prioritization\|prioritization\|scoring"
}

@test "Performance: relevance scoring vs basic mode, should pass" {
    # Test that both relevance scoring and basic modes work correctly

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": false}}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Found [0-9]* files:"
    # Should NOT have context intelligence formatting
    ! echo "$output" | grep -q "HIGH PRIORITY FILES"
    ! echo "$output" | grep -q "TOP FILES BY RELEVANCE"

    # Test relevance scoring mode - should use context intelligence format
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "HIGH PRIORITY FILES:"
    echo "$output" | grep -q "TOP FILES BY RELEVANCE:"
    echo "$output" | grep -q "SUMMARY: [0-9]* total files"
    ! echo "$output" | grep -q "Found [0-9]* files:"
}

@test "Fallback mode, intelligence disabled via config, should pass" {
    # Basic mode should still work when intelligence is disabled
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": false}}'
    [ "$status" -eq 0 ]

    echo "$output" | grep -q "Found [0-9]* files:"
    ! echo "$output" | grep -q "HIGH PRIORITY"
    ! echo "$output" | grep -q "TOP FILES BY RELEVANCE"
    ! echo "$output" | grep -q "SUMMARY:"
}

@test "Environment variable configuration overrides work, should pass" {
    ENABLE_CONTEXT_INTELLIGENCE=true WEIGHT_FILE_TYPE_PRIORITY=0.1 run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # Should still use context intelligence format (since ENABLE_CONTEXT_INTELLIGENCE=true)
    echo "$output" | grep -q "HIGH PRIORITY FILES:"
    echo "$output" | grep -q "TOP FILES BY RELEVANCE:"
    echo "$output" | grep -q "SUMMARY: [0-9]* total files"
}

@test "Context intelligence can be disabled via environment, should pass" {
    # Test that context intelligence can be disabled via environment variable
    ENABLE_CONTEXT_INTELLIGENCE=false run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}'
    [ "$status" -eq 0 ]

    # Should fall back to basic mode even when use_relevance_scoring=true
    echo "$output" | grep -q "Found [0-9]* files:"
    ! echo "$output" | grep -q "HIGH PRIORITY FILES"
    ! echo "$output" | grep -q "TOP FILES BY RELEVANCE"
}
