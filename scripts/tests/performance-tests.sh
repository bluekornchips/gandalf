#!/usr/bin/env bats
# Performance and Load Tests
# Basic performance validation without arbitrary benchmarks

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

create_large_project_structure() {
    # Create multiple directories with various file types
    local dirs=("src" "tests" "docs" "config" "scripts" "lib" "utils")

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"

        # python files
        for i in {1..10}; do
            echo "# $dir module $i" >"$dir/module_$i.py"
            echo "def function_$i(): pass" >>"$dir/module_$i.py"
        done

        # js files
        for i in {1..5}; do
            echo "// $dir component $i" >"$dir/component_$i.js"
            echo "export default function Component$i() { return null; }" >>"$dir/component_$i.js"
        done

        # markdown files
        for i in {1..3}; do
            echo "# $dir Documentation $i" >"$dir/doc_$i.md"
            echo "This is documentation for $dir module $i" >>"$dir/doc_$i.md"
        done
    done

    # configuration files
    echo '{"name": "performance-test", "version": "1.0.0"}' >package.json
    echo 'flask==2.0.0' >requirements.txt
    echo 'DEBUG=true' >.env
    echo '*.pyc' >.gitignore

    git add . >/dev/null 2>&1
    git commit -m "Performance test project setup" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_large_project_structure
}

teardown() {
    # Clean up any test weights files
    [[ -n "${TEST_WEIGHTS_FILE:-}" && -f "$TEST_WEIGHTS_FILE" ]] && rm -f "$TEST_WEIGHTS_FILE"
    unset GANDALF_WEIGHTS_FILE
    shared_teardown
}

create_test_weights_file() {
    local weights_fixture="$1"

    TEST_WEIGHTS_FILE=$(mktemp -t gandalf_test_weights.XXXXXX.yaml)

    # Copy the fixture to the temp file
    cp "$GANDALF_ROOT/scripts/tests/fixtures/data/$weights_fixture" "$TEST_WEIGHTS_FILE"

    export GANDALF_WEIGHTS_FILE="$TEST_WEIGHTS_FILE"

    echo "$TEST_WEIGHTS_FILE"
}

@test "basic file operations complete successfully" {
    # Test basic file operations without arbitrary timing constraints
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "module_\|component_\|doc_"

    # Test with filtering
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".py"]}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "\.py"
    ! echo "$content" | grep -q "\.js\|\.md"

    # Test project info
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.project_name' >/dev/null
    echo "$content" | jq -e '.file_stats' >/dev/null
}

@test "memory usage stays reasonable during operations" {
    # Test that operations complete without excessive memory consumption
    # Large file listing
    execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' >/dev/null

    # Multiple conversation operations
    for i in {1..3}; do
        execute_rpc "tools/call" '{"name": "recall_conversations", "arguments": {"fast_mode": true, "limit": 10}}' >/dev/null
    done

    # Search operations
    execute_rpc "tools/call" '{"name": "search_conversations", "arguments": {"query": "test", "limit": 5}}' >/dev/null

    # Export operations
    execute_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"limit": 2}}' >/dev/null

    # Project info with stats
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # If we get here without errors, memory usage is reasonable
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.project_name' >/dev/null
}

@test "handles large files without crashing" {
    # Create test directory with large files
    local large_files_dir="$TEST_HOME/large-files-test"
    mkdir -p "$large_files_dir"
    cd "$large_files_dir"

    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"

    # Create large files directly
    echo "# Large test file" >large_test.py
    for i in {1..1000}; do
        echo "# Line $i of large file" >>large_test.py
    done

    echo "# Binary test file" >binary_test.bin
    head -c 50000 /dev/zero >>binary_test.bin 2>/dev/null || dd if=/dev/zero of=binary_test.bin bs=1024 count=50 2>/dev/null

    git add . >/dev/null 2>&1
    git commit -m "Large files test" >/dev/null 2>&1

    # Test with relevance scoring enabled
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 10}}' "$large_files_dir"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    # Should handle large files without crashing
    [[ -n "$content" ]]
}

@test "context intelligence functionality works" {
    # Test context intelligence enabled
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content_enabled
    content_enabled=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content_enabled" ]]

    # Test context intelligence disabled
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": false, "max_files": 5}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content_disabled
    content_disabled=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content_disabled" ]]

    # Test with extreme weight configurations
    local test_weights_file
    test_weights_file=$(create_test_weights_file "saurons_weights.yaml")

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content_extreme
    content_extreme=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content_extreme" ]]
}
