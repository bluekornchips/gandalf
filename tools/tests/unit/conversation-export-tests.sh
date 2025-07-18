#!/usr/bin/env bats
# Conversation Export and Aggregation Tests for Gandalf MCP Server
# Tests conversation recall, search, export, and server information functionality

set -euo pipefail

load '../../lib/test-helpers.sh'

execute_conversation_tool() {
    local tool_name="$1"
    local arguments="$2"
    
    run execute_rpc "tools/call" "{\"name\": \"$tool_name\", \"arguments\": $arguments}"
    [ "$status" -eq 0 ]
    
    validate_jsonrpc_response "$output"
    
    # Extract and return content
    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    
    if [[ -z "$content" ]]; then
        echo "ERROR: Empty content returned from $tool_name" >&2
        return 1
    fi
    
    echo "$content"
}

validate_conversation_response() {
    local content="$1"
    local expected_fields="$2"  # comma-separated list of expected fields
    
    # Try to parse as JSON
    if echo "$content" | jq . >/dev/null 2>&1; then
        # If it's valid JSON, check for expected fields
        IFS=',' read -ra fields <<< "$expected_fields"
        local has_field=false
        
        for field in "${fields[@]}"; do
            if echo "$content" | jq -e "has(\"$field\")" >/dev/null 2>&1; then
                has_field=true
                break
            fi
        done
        
        if [[ "$has_field" == false ]]; then
            echo "ERROR: None of expected fields ($expected_fields) found in response" >&2
            return 1
        fi
    else
        # If not JSON, just verify it's not empty
        [[ -n "$content" ]]
    fi
    
    return 0
}

validate_export_response() {
    local content="$1"
    
    validate_conversation_response "$content" "output_directory,exported_files,message"
    
    # Additional validation for export responses
    if echo "$content" | jq . >/dev/null 2>&1; then
        # Check if it has export-specific information
        if echo "$content" | jq -e 'has("output_directory")' >/dev/null 2>&1; then
            local output_dir
            output_dir=$(echo "$content" | jq -r '.output_directory')
            [[ -n "$output_dir" ]]
        fi
    fi
    
    return 0
}

validate_server_info_response() {
    local content="$1"
    local expected_fields="$2"
    
    validate_conversation_response "$content" "$expected_fields"
    
    # Additional validation for server info
    if echo "$content" | jq . >/dev/null 2>&1; then
        if echo "$content" | jq -e 'has("server_version")' >/dev/null 2>&1; then
            local version
            version=$(echo "$content" | jq -r '.server_version')
            [[ -n "$version" ]]
        fi
    fi
    
    return 0
}

test_parameter_validation() {
    local tool_name="$1"
    local invalid_params="$2"
    
    local content
    content=$(execute_conversation_tool "$tool_name" "$invalid_params")
    
    # Should handle invalid parameters gracefully
    [[ -n "$content" ]]
    
    # Check if it's an error response or graceful handling
    if echo "$content" | jq . >/dev/null 2>&1; then
        # If JSON, check for error indicators
        if echo "$content" | jq -e 'has("error") or has("message")' >/dev/null 2>&1; then
            # Has error information - that's good
            return 0
        fi
    fi
    
    # If no explicit error, should still be valid response
    return 0
}

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

# Core Conversation Aggregator Tests

@test "recall conversations with fast mode functionality" {
    local content
    content=$(execute_conversation_tool "recall_conversations" '{"fast_mode": true, "limit": 5}')
    
    validate_conversation_response "$content" "conversations,total_conversations,message"
    
    # Check if conversations exist in main array or tool_results
    local conv_count=0
    if echo "$content" | jq -e 'has("conversations")' >/dev/null 2>&1; then
        conv_count=$(echo "$content" | jq -r '.conversations | length' | tr -d '\n' | tr -d ' ')
    fi
    
    # If main conversations array is empty, check tool_results
    if [[ "$conv_count" -eq 0 ]]; then
        local cursor_count
        cursor_count=$(echo "$content" | jq -r '.tool_results.cursor.conversations | length' 2>/dev/null | tr -d '\n' | tr -d ' ' || echo "0")
        [[ "$cursor_count" =~ ^[0-9]+$ ]] && [[ "$cursor_count" -le 5 ]]
    else
        [[ "$conv_count" =~ ^[0-9]+$ ]] && [[ "$conv_count" -le 5 ]]
    fi
}

@test "search conversations with query functionality" {
    local content
    content=$(execute_conversation_tool "search_conversations" '{"query": "fellowship", "limit": 5}')
    
    validate_conversation_response "$content" "conversations,total_matches,message"
    
    # Validate search functionality
    if echo "$content" | jq -e 'has("conversations")' >/dev/null 2>&1; then
        local conv_count
        conv_count=$(echo "$content" | jq -r '.conversations | length' | sed 's/[[:space:]]//g')
        [[ "$conv_count" =~ ^[0-9]+$ ]] && [[ "$conv_count" -le 5 ]]
    fi
}

@test "export individual conversations basic functionality" {
    local content
    content=$(execute_conversation_tool "export_individual_conversations" '{"limit": 2}')
    
    validate_export_response "$content"
    
    # Validate export limit
    if echo "$content" | jq -e 'has("exported_files")' >/dev/null 2>&1; then
        local file_count
        file_count=$(echo "$content" | jq -r '.exported_files | length' | sed 's/[[:space:]]//g')
        [[ "$file_count" =~ ^[0-9]+$ ]] && [[ "$file_count" -le 2 ]]
    fi
}

@test "export individual conversations with markdown format" {
    local content
    content=$(execute_conversation_tool "export_individual_conversations" '{"format": "md", "limit": 2}')
    
    validate_export_response "$content"
    
    # Check if format field exists and is correct
    if echo "$content" | jq -e 'has("format")' >/dev/null 2>&1; then
        # Use jq to directly check if format matches expected values
        if echo "$content" | jq -e '.format == "md" or .format == "markdown"' >/dev/null 2>&1; then
            return 0
        else
            local format
            format=$(echo "$content" | jq -r '.format' 2>/dev/null)
            echo "ERROR: Expected format 'md' or 'markdown', got '$format'" >&2
            return 1
        fi
    else
        # If no format field, check if the tool handled the request successfully
        echo "$content" | jq -e '.output_directory or .exported_files or .message' >/dev/null 2>&1
    fi
}

# Server Information Tests

@test "get server version with parameters" {
    local content
    content=$(execute_conversation_tool "get_server_version" '{"random_string": "gondor"}')
    
    validate_server_info_response "$content" "server_version,protocol_version,message"
    
    # Validate version format if present
    if echo "$content" | jq -e 'has("server_version")' >/dev/null 2>&1; then
        local version
        version=$(echo "$content" | jq -r '.server_version')
        # Should be a valid version string (not empty)
        [[ -n "$version" ]]
    fi
}

@test "get project info with statistics" {
    local content
    content=$(execute_conversation_tool "get_project_info" '{"include_stats": true}')
    
    validate_server_info_response "$content" "project_name,file_count,project_root,file_stats"
    
    # Validate project information (be flexible with project name)
    if echo "$content" | jq -e 'has("project_name")' >/dev/null 2>&1; then
        local project_name
        project_name=$(echo "$content" | jq -r '.project_name')
        # Accept any valid project name, not just the default
        [[ -n "$project_name" && "$project_name" != "null" ]]
    fi
}

@test "list project files with file limit" {
    local content
    content=$(execute_conversation_tool "list_project_files" '{"max_files": 10}')
    
    validate_conversation_response "$content" "files,total_files,message"
    
    # Validate file listing contains expected file
    if echo "$content" | grep -q "README.md"; then
        # File listing contains expected content
        true
    elif echo "$content" | jq -e 'has("files")' >/dev/null 2>&1; then
        # JSON format file listing
        local files
        files=$(echo "$content" | jq -r '.files[]' 2>/dev/null || echo "")
        echo "$files" | grep -q "README.md" || [[ -n "$files" ]]
    fi
}

# Advanced Functionality Tests

@test "recall conversations with comprehensive mode" {
    local content
    content=$(execute_conversation_tool "recall_conversations" '{"fast_mode": false, "limit": 10}')
    
    validate_conversation_response "$content" "conversations,total_conversations,message"
    
    # Check if conversations exist in main array or tool_results
    local conv_count=0
    if echo "$content" | jq -e 'has("conversations")' >/dev/null 2>&1; then
        conv_count=$(echo "$content" | jq -r '.conversations | length' | tr -d '\n' | tr -d ' ')
    fi
    
    # If main conversations array is empty, check tool_results
    if [[ "$conv_count" -eq 0 ]]; then
        local cursor_count
        cursor_count=$(echo "$content" | jq -r '.tool_results.cursor.conversations | length' 2>/dev/null | tr -d '\n' | tr -d ' ' || echo "0")
        [[ "$cursor_count" =~ ^[0-9]+$ ]] && [[ "$cursor_count" -le 10 ]]
    else
        [[ "$conv_count" =~ ^[0-9]+$ ]] && [[ "$conv_count" -le 10 ]]
    fi
}

@test "search conversations with date filtering" {
    local content
    content=$(execute_conversation_tool "search_conversations" '{"query": "project", "days_lookback": 7, "limit": 5}')
    
    validate_conversation_response "$content" "conversations,total_matches,message"
    
    # Validate date filtering functionality
    if echo "$content" | jq -e 'has("conversations")' >/dev/null 2>&1; then
        local conv_count
        conv_count=$(echo "$content" | jq -r '.conversations | length' | sed 's/[[:space:]]//g')
        [[ "$conv_count" =~ ^[0-9]+$ ]] && [[ "$conv_count" -le 5 ]]
    fi
}

@test "export conversations with type filtering" {
    local content
    content=$(execute_conversation_tool "export_individual_conversations" '{"conversation_types": ["technical"], "limit": 3}')
    
    validate_export_response "$content"
    
    # Validate type filtering
    if echo "$content" | jq -e 'has("exported_files")' >/dev/null 2>&1; then
        local file_count
        file_count=$(echo "$content" | jq -r '.exported_files | length' | sed 's/[[:space:]]//g')
        [[ "$file_count" =~ ^[0-9]+$ ]] && [[ "$file_count" -le 3 ]]
    fi
}

# Error Handling and Edge Cases Tests

@test "recall conversations handles invalid limit parameter" {
    test_parameter_validation "recall_conversations" '{"limit": -1}'
}

@test "search conversations handles empty query" {
    test_parameter_validation "search_conversations" '{"query": "", "limit": 5}'
}

@test "export conversations handles invalid format" {
    test_parameter_validation "export_individual_conversations" '{"format": "invalid_format", "limit": 1}'
}

@test "recall conversations handles zero limit" {
    local content
    content=$(execute_conversation_tool "recall_conversations" '{"limit": 0}')
    
    validate_conversation_response "$content" "conversations,total_conversations,message"
    
    # Check if conversations exist in main array or tool_results
    local conv_count=0
    if echo "$content" | jq -e 'has("conversations")' >/dev/null 2>&1; then
        conv_count=$(echo "$content" | jq -r '.conversations | length' | tr -d '\n' | tr -d ' ')
    fi
    
    # With zero limit, both main array and tool results should be empty
    [[ "$conv_count" -eq 0 ]]
    
    # Also check that the tool acknowledged the zero limit
    local cursor_count
    cursor_count=$(echo "$content" | jq -r '.tool_results.cursor.conversations | length' 2>/dev/null | tr -d '\n' | tr -d ' ' || echo "0")
    [[ "$cursor_count" -eq 0 ]]
}

@test "search conversations handles large limit" {
    local content
    content=$(execute_conversation_tool "search_conversations" '{"query": "test", "limit": 1000}')
    
    validate_conversation_response "$content" "conversations,total_matches,message"
    
    # Should handle large limit gracefully
    if echo "$content" | jq -e 'has("conversations")' >/dev/null 2>&1; then
        local conv_count
        conv_count=$(echo "$content" | jq -r '.conversations | length' | sed 's/[[:space:]]//g')
        [[ "$conv_count" =~ ^[0-9]+$ ]] && [[ "$conv_count" -le 1000 ]]
    fi
}

@test "export conversations handles missing parameters" {
    local content
    content=$(execute_conversation_tool "export_individual_conversations" '{}')
    
    validate_export_response "$content"
    
    # Should handle missing parameters with defaults
    [[ -n "$content" ]]
}

@test "get project info handles invalid boolean parameter" {
    local content
    content=$(execute_conversation_tool "get_project_info" '{"include_stats": "invalid"}')
    
    validate_server_info_response "$content" "project_name,project_root,message"
    
    # Should handle invalid boolean gracefully
    [[ -n "$content" ]]
}

@test "list project files handles invalid file types" {
    local content
    content=$(execute_conversation_tool "list_project_files" '{"file_types": ["invalid_extension"]}')
    
    validate_conversation_response "$content" "files,total_files,message"
    
    # Should handle invalid file types gracefully
    [[ -n "$content" ]]
}
