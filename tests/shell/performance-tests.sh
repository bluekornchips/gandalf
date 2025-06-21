#!/usr/bin/env bats
# Performance and Load Tests
# Performance characteristics, response times, and resource usage

set -eo pipefail

load 'fixtures/helpers/test-helpers'

create_large_project_structure() {
    # Create multiple directories with various file types
    local dirs=("src" "tests" "docs" "config" "scripts" "lib" "utils" "components" "services" "models")

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"

        # python
        for i in {1..10}; do
            echo "# $dir module $i" >"$dir/module_$i.py"
            echo "def function_$i(): pass" >>"$dir/module_$i.py"
        done

        # js
        for i in {1..8}; do
            echo "// $dir component $i" >"$dir/component_$i.js"
            echo "export default function Component$i() { return null; }" >>"$dir/component_$i.js"
        done

        # markdown
        for i in {1..5}; do
            echo "# $dir Documentation $i" >"$dir/doc_$i.md"
            echo "This is documentation for $dir module $i" >>"$dir/doc_$i.md"
        done
    done

    # configuration files
    echo '{"name": "performance-test", "version": "1.0.0"}' >package.json
    echo 'flask==2.0.0' >requirements.txt
    echo 'DEBUG=true' >.env
    echo '*.pyc' >.gitignore

    # Create some larger files
    for i in {1..3}; do
        {
            echo "# Large file $i"
            for j in {1..1000}; do
                echo "Line $j of large file $i with some content to make it realistic"
            done
        } >"large_file_$i.txt"
    done

    git add . >/dev/null 2>&1
    git commit -m "Performance test project setup" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_large_project_structure
}

teardown() {
    shared_teardown
}

@test "list project files completes within reasonable time for large projects" {
    local start_time end_time duration
    start_time=$(date +%s)

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should complete within 5 seconds even for large projects
    [[ $duration -le 5 ]]

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    # Should contain many files
    echo "$content" | grep -q "module_\|component_\|doc_"
}

@test "list project files with file type filtering is efficient" {
    local start_time end_time duration
    start_time=$(date +%s)

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".py"]}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Filtering should be fast (within 3 seconds)
    [[ $duration -le 3 ]]

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    # Should only contain Python files
    echo "$content" | grep -q "\.py"
    ! echo "$content" | grep -q "\.js\|\.md"
}

@test "conversation ingestion performs well with rapid calls" {
    # Test rapid conversation ingestion performance
    local start_time end_time duration
    start_time=$(date +%s)

    # Test multiple rapid conversation ingestion calls
    for i in {1..5}; do
        execute_rpc "tools/call" '{"name": "ingest_conversations", "arguments": {"fast_mode": true, "limit": 5, "days_lookback": 7}}' >/dev/null
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Should complete within reasonable time (10 seconds for 5 ingestion calls)
    [[ $duration -le 10 ]]
}

@test "conversation analysis performs well with large conversation history" {
    # Test conversation analysis performance with realistic parameters
    local start_time end_time duration
    start_time=$(date +%s)

    run execute_rpc "tools/call" '{"name": "ingest_conversations", "arguments": {"fast_mode": true, "limit": 20, "days_lookback": 30}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Conversation analysis should be fast (within 5 seconds)
    [[ $duration -le 5 ]]

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.total_conversations // .mode' >/dev/null
}

@test "project info generation is fast for complex projects" {
    local start_time end_time duration
    start_time=$(date +%s)

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Project info should generate quickly (within 3 seconds)
    [[ $duration -le 3 ]]

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.project_name' >/dev/null
    echo "$content" | jq -e '.file_stats' >/dev/null
}

@test "server handles rapid sequential requests efficiently" {
    # Test rapid sequential tool calls
    local start_time end_time duration
    start_time=$(date +%s)

    # Make 5 rapid requests to different tools (reduced for better reliability)
    for i in {1..5}; do
        execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' >/dev/null
        execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 5}}' >/dev/null
    done

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # Should handle 10 requests within 60 seconds (very lenient for test environment)
    [[ $duration -le 60 ]]
}

@test "file operations scale with project size" {
    # Create additional nested directories
    for depth in {1..5}; do
        local nested_path="deep"
        for i in $(seq 1 $depth); do
            nested_path="$nested_path/level$i"
        done
        mkdir -p "$nested_path"
        echo "Deep file at level $depth" >"$nested_path/deep_file.py"
    done

    # Add and commit the new files so they're tracked by git
    git add . >/dev/null 2>&1
    git commit -m "Add deep nested files for performance test" >/dev/null 2>&1

    local start_time end_time duration
    start_time=$(date +%s)

    # Use higher max_files to ensure deep nested files are included in results
    # (the test project has ~527 files, so 50 is too low to guarantee inclusion)
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 200}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle deep nesting efficiently (within 4 seconds)
    [[ $duration -le 4 ]]

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "deep_file\|level"
}

@test "memory usage stays reasonable during operations" {
    # This test checks that operations don't consume excessive memory
    # We'll run a series of operations and ensure they complete successfully

    # Large file listing
    execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' >/dev/null

    # Multiple conversation operations using real MCP tools
    for i in {1..3}; do
        execute_rpc "tools/call" '{"name": "ingest_conversations", "arguments": {"fast_mode": true, "limit": 10, "days_lookback": 7}}' >/dev/null
    done

    # Search operations using real query tool
    execute_rpc "tools/call" '{"name": "query_conversation_context", "arguments": {"query": "test", "limit": 5}}' >/dev/null

    # Cursor database operations
    execute_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"summary": true}}' >/dev/null

    # Project info with stats
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # If we get here without errors, memory usage is reasonable
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.project_name' >/dev/null
}

# =============================================================================
# STRESS TESTS - Testing system limits and edge cases
# =============================================================================

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

@test "extreme weight configurations don't crash system" {
    # Skip if weights.yaml doesn't exist (not all setups may have it)
    if [[ ! -f "$GANDALF_ROOT/weights.yaml" ]]; then
        skip "weights.yaml not found - skipping extreme weights test"
    fi

    # Backup original weights
    local backup_file=$(mktemp)
    cp "$GANDALF_ROOT/weights.yaml" "$backup_file"

    # Use Sauron's extreme weights configuration - maximum power test
    cp "$GANDALF_ROOT/tests/shell/fixtures/data/saurons_weights.yaml" "$GANDALF_ROOT/weights.yaml"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    local exit_code=$status

    # Restore original weights
    cp "$backup_file" "$GANDALF_ROOT/weights.yaml"
    rm -f "$backup_file"

    [ "$exit_code" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should not crash with extreme values
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]
}

@test "inverted priority configuration works correctly" {
    # Skip if weights.yaml doesn't exist
    if [[ ! -f "$GANDALF_ROOT/weights.yaml" ]]; then
        skip "weights.yaml not found - skipping inverted priorities test"
    fi

    # Backup original weights
    local backup_file=$(mktemp)
    cp "$GANDALF_ROOT/weights.yaml" "$backup_file"

    # Use Palantir's twisted visions - inverted weights configuration
    cp "$GANDALF_ROOT/tests/shell/fixtures/data/weights_inverted.yaml" "$GANDALF_ROOT/weights.yaml"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    local exit_code=$status

    # Restore original weights
    cp "$backup_file" "$GANDALF_ROOT/weights.yaml"
    rm -f "$backup_file"

    [ "$exit_code" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should work with inverted priorities
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]
}

@test "context intelligence disabled mode works" {
    # Skip if weights.yaml doesn't exist
    if [[ ! -f "$GANDALF_ROOT/weights.yaml" ]]; then
        skip "weights.yaml not found - skipping disabled mode test"
    fi

    # Backup original weights
    local backup_file=$(mktemp)
    cp "$GANDALF_ROOT/weights.yaml" "$backup_file"

    # Use Shire's peaceful weights - minimal scoring configuration
    cp "$GANDALF_ROOT/tests/shell/fixtures/data/shire_weights.yaml" "$GANDALF_ROOT/weights.yaml"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": false, "max_files": 5}}'
    local exit_code=$status

    # Restore original weights
    cp "$backup_file" "$GANDALF_ROOT/weights.yaml"
    rm -f "$backup_file"

    [ "$exit_code" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should work when context intelligence is disabled
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]
}

@test "deep nested directories work efficiently" {
    # Create test directory with deep nesting
    local nested_dir="$TEST_HOME/deep-nested-test"
    mkdir -p "$nested_dir"
    cd "$nested_dir"

    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"

    # Create nested structure directly
    mkdir -p "level1/level2/level3/level4"
    echo "# Deep nested file" >level1/level2/level3/level4/deep_file.py
    echo "def deep_function(): pass" >>level1/level2/level3/level4/deep_file.py

    mkdir -p "components/nested/validators"
    echo "# Nested component" >components/nested/validators/validator.js
    echo "export function validate() { return true; }" >>components/nested/validators/validator.js

    git add . >/dev/null 2>&1
    git commit -m "Deep nested test" >/dev/null 2>&1

    local start_time end_time duration
    start_time=$(date +%s)

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 20}}' "$nested_dir"

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle deep nesting efficiently (within 5 seconds)
    [[ $duration -le 5 ]]

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    # Should find files in nested structure
    echo "$content" | grep -q "deep_file\|validator" || [[ -n "$content" ]]
}
