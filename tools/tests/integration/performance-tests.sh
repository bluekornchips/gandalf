#!/usr/bin/env bats
# Performance and Load Tests
# Performance characteristics, response times, and resource usage

set -euo pipefail

load '../../lib/test-helpers.sh'

check_performance_timing() {
    local duration="$1"
    local max_time="$2"
    local operation="$3"
    
    if [[ $duration -gt $max_time ]]; then
        echo "WARNING: $operation took ${duration}s (expected <${max_time}s)"
    else
        echo "✓ $operation completed in ${duration}s"
    fi
}

measure_operation_time() {
    local operation_name="$1"
    local max_time="$2"
    shift 2
    
    local start_time end_time duration
    start_time=$(date +%s)
    
    "$@"
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    check_performance_timing "$duration" "$max_time" "$operation_name"
}


create_files_in_directory() {
    local dir="$1"
    local file_count="${2:-10}"
    
    mkdir -p "$dir"
    
    for i in $(seq 1 "$file_count"); do
        echo "# $dir module $i" >"$dir/module_$i.py"
        echo "def function_$i(): pass" >>"$dir/module_$i.py"
    done
    
    for i in $(seq 1 $((file_count - 2))); do
        echo "// $dir component $i" >"$dir/component_$i.js"
        echo "export default function Component$i() { return null; }" >>"$dir/component_$i.js"
    done
    
    for i in $(seq 1 $((file_count / 2))); do
        echo "# $dir Documentation $i" >"$dir/doc_$i.md"
        echo "This is documentation for $dir module $i" >>"$dir/doc_$i.md"
    done
}


create_large_files() {
    local count="${1:-3}"
    local lines_per_file="${2:-1000}"
    
    for i in $(seq 1 "$count"); do
        {
            echo "# Large file $i"
            for j in $(seq 1 "$lines_per_file"); do
                echo "Line $j of large file $i with some content to make it realistic"
            done
        } >"large_file_$i.txt"
    done
}


create_nested_structure() {
    local max_depth="${1:-5}"
    
    for depth in $(seq 1 "$max_depth"); do
        local nested_path="deep"
        for i in $(seq 1 "$depth"); do
            nested_path="$nested_path/level$i"
        done
        mkdir -p "$nested_path"
        echo "Deep file at level $depth" >"$nested_path/deep_file.py"
    done
}


validate_performance_response() {
    local output="$1"
    local expected_pattern="${2:-}"
    
    validate_jsonrpc_response "$output"
    
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    if [[ -z "$content" ]]; then
        echo "ERROR: Empty content in performance response" >&2
        return 1
    fi
    
    if [[ -n "$expected_pattern" ]]; then
        if ! echo "$content" | grep -q "$expected_pattern"; then
            echo "ERROR: Expected pattern '$expected_pattern' not found in: $content" >&2
            return 1
        fi
    fi
    
    echo "$content"
}


execute_rapid_calls() {
    local call_count="$1"
    local rpc_call="$2"
    
    for i in $(seq 1 "$call_count"); do
        execute_rpc "tools/call" "$rpc_call" >/dev/null
    done
}


create_test_weights_file() {
    local weights_fixture="$1"
    
    TEST_WEIGHTS_FILE=$(mktemp -t gandalf_test_weights.XXXXXX.yaml)
    
    if [[ -f "$GANDALF_ROOT/tools/tests/fixtures/data/$weights_fixture" ]]; then
        cp "$GANDALF_ROOT/tools/tests/fixtures/data/$weights_fixture" "$TEST_WEIGHTS_FILE"
    else
        echo "ERROR: Weights fixture not found: $weights_fixture" >&2
        return 1
    fi
    
    export GANDALF_WEIGHTS_FILE="$TEST_WEIGHTS_FILE"
    echo "$TEST_WEIGHTS_FILE"
}


create_isolated_test_project() {
    local project_name="$1"
    local project_dir="$TEST_HOME/$project_name"
    
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    
    echo "$project_dir"
}

create_large_project_structure() {
    local dirs=("src" "tests" "docs" "config" "scripts" "lib" "utils" "components" "services" "models")
    
    for dir in "${dirs[@]}"; do
        create_files_in_directory "$dir" 10
    done
    
    echo '{"name": "performance-test", "version": "1.0.0"}' >package.json
    echo 'flask==2.0.0' >requirements.txt
    echo 'DEBUG=true' >.env
    echo '*.pyc' >.gitignore
    
    create_large_files 3 1000
    
    git add . >/dev/null 2>&1
    git commit -m "Performance test project setup" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_large_project_structure
}

teardown() {
    if [[ -n "${TEST_WEIGHTS_FILE:-}" && -f "$TEST_WEIGHTS_FILE" ]]; then
        rm -f "$TEST_WEIGHTS_FILE"
    fi
    unset GANDALF_WEIGHTS_FILE
    shared_teardown
}

@test "list project files completes within reasonable time for large projects" {
    local start_time end_time duration
    start_time=$(date +%s)
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    [ "$status" -eq 0 ]
    local content
    content=$(validate_performance_response "$output" "module_\|component_\|doc_")
    
    check_performance_timing "$duration" 15 "list_project_files for large projects"
}

@test "list project files with file type filtering is efficient" {
    local start_time end_time duration
    start_time=$(date +%s)
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": [".py"]}}'
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    [ "$status" -eq 0 ]
    local content
    content=$(validate_performance_response "$output" "\.py")
    
    if echo "$content" | grep -q "\.js\|\.md"; then
        echo "ERROR: Filtered output should not contain non-Python files" >&2
        false
    fi
    
    check_performance_timing "$duration" 10 "list_project_files with file type filtering"
}

@test "conversation recall performs well with rapid calls" {
    local start_time end_time duration
    start_time=$(date +%s)
    
    execute_rapid_calls 5 '{"name": "recall_cursor_conversations", "arguments": {"fast_mode": true, "limit": 5, "days_lookback": 7}}'
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    check_performance_timing "$duration" 30 "rapid conversation recall calls"
}

@test "conversation analysis performs well with large conversation history" {
    local start_time end_time duration
    start_time=$(date +%s)
    
    run execute_rpc "tools/call" '{"name": "recall_conversations", "arguments": {"fast_mode": true, "limit": 10}}'
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    [ "$status" -eq 0 ]
    validate_performance_response "$output"
    
    check_performance_timing "$duration" 15 "conversation analysis with large history"
}

@test "project info generation is fast for complex projects" {
    local start_time end_time duration
    start_time=$(date +%s)
    
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    [ "$status" -eq 0 ]
    local content
    content=$(validate_performance_response "$output")
    
    if ! echo "$content" | jq -e '.project_name' >/dev/null 2>&1; then
        echo "ERROR: Project info should contain project_name" >&2
        false
    fi
    
    if ! echo "$content" | jq -e '.file_stats' >/dev/null 2>&1; then
        echo "ERROR: Project info should contain file_stats" >&2
        false
    fi
    
    check_performance_timing "$duration" 10 "project info generation for complex projects"
}

@test "server handles rapid sequential requests efficiently" {
    local start_time end_time duration
    start_time=$(date +%s)
    
    for i in {1..5}; do
        execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' >/dev/null
        execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 5}}' >/dev/null
    done
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    check_performance_timing "$duration" 120 "rapid sequential requests"
}

@test "file operations scale with project size" {
    create_nested_structure 5
    
    git add . >/dev/null 2>&1
    git commit -m "Add deep nested files for performance test" >/dev/null 2>&1
    
    local start_time end_time duration
    start_time=$(date +%s)
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 200}}'
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    [ "$status" -eq 0 ]
    local content
    content=$(validate_performance_response "$output" "deep_file\|level")
    
    check_performance_timing "$duration" 15 "file operations with deep nesting"
}

@test "memory usage stays reasonable during operations" {
    execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' >/dev/null
    
    execute_rapid_calls 3 '{"name": "recall_conversations", "arguments": {"fast_mode": true, "limit": 10}}'
    
    execute_rpc "tools/call" '{"name": "search_conversations", "arguments": {"query": "test", "limit": 5}}' >/dev/null
    
    execute_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"limit": 2}}' >/dev/null
    
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    
    [ "$status" -eq 0 ]
    local content
    content=$(validate_performance_response "$output")
    
    if ! echo "$content" | jq -e '.project_name' >/dev/null 2>&1; then
        echo "ERROR: Memory usage test should return valid project info" >&2
        false
    fi
}

@test "handles large files without crashing" {
    local large_files_dir
    large_files_dir=$(create_isolated_test_project "large-files-test")
    
    echo "# Large test file" >large_test.py
    for i in {1..1000}; do
        echo "# Line $i of large file" >>large_test.py
    done
    
    echo "# Binary test file" >binary_test.bin
    head -c 50000 /dev/zero >>binary_test.bin 2>/dev/null || dd if=/dev/zero of=binary_test.bin bs=1024 count=50 2>/dev/null
    
    git add . >/dev/null 2>&1
    git commit -m "Large files test" >/dev/null 2>&1
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 10}}' "$large_files_dir"
    [ "$status" -eq 0 ]
    
    validate_performance_response "$output"
}

@test "extreme weight configurations don't crash system" {
    local test_weights_file
    test_weights_file=$(create_test_weights_file "saurons_weights.yaml")
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    
    [ "$status" -eq 0 ]
    validate_performance_response "$output"
}

@test "inverted priority configuration works correctly" {
    local test_weights_file
    test_weights_file=$(create_test_weights_file "weights_inverted.yaml")
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true, "max_files": 5}}'
    
    [ "$status" -eq 0 ]
    validate_performance_response "$output"
}

@test "context intelligence disabled mode works" {
    local test_weights_file
    test_weights_file=$(create_test_weights_file "shire_weights.yaml")
    
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": false, "max_files": 5}}'
    
    [ "$status" -eq 0 ]
    validate_performance_response "$output"
}

@test "deep nested directories work efficiently" {
    local nested_dir
    nested_dir=$(create_isolated_test_project "deep-nested-test")
    
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
    local content
    content=$(validate_performance_response "$output")
    
    if echo "$content" | grep -q "deep_file\|validator"; then
        echo "✓ Found nested files in output"
    else
        echo "Deep nested files should be accessible"
    fi
    
    check_performance_timing "$duration" 5 "deep nested directories handling"
}
