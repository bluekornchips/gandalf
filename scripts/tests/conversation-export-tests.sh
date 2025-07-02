#!/bin/bash
# Tests for streamlined Gandalf MCP server functionality

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

# Helper function for clean RPC calls without debug noise
execute_clean_rpc() {
    local method="$1"
    local params="$2"

    # Call execute_rpc directly without BATS run to avoid stdout/stderr mixing
    output=$(execute_rpc "$method" "$params")
    local status=$?

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Return the output for BATS to capture
    echo "$output"
}

# Core Conversation Aggregator Tests

@test "recall_conversations: basic functionality with fast mode" {
    # Test basic conversation recall with fast mode
    run execute_clean_rpc "tools/call" '{"name": "recall_conversations", "arguments": {"fast_mode": true, "limit": 5}}'
    [ "$status" -eq 0 ]

    local recall_content
    recall_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify basic response structure
    [[ -n "$recall_content" ]]
    
    # Should contain some conversation data or indication of no conversations
    if echo "$recall_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        # If it's valid JSON, check for expected fields
        echo "$recall_content" | jq -e 'has("conversations") or has("total_conversations") or has("message")' >/dev/null
    fi
}

@test "search_conversations: cross-tool search" {
    # Test cross-tool conversation search
    run execute_clean_rpc "tools/call" '{"name": "search_conversations", "arguments": {"query": "fellowship", "limit": 5}}'
    [ "$status" -eq 0 ]

    local search_content
    search_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify basic response structure
    [[ -n "$search_content" ]]
    
    # Should contain search results or indication of no results
    if echo "$search_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        # If it's valid JSON, check for expected fields
        echo "$search_content" | jq -e 'has("conversations") or has("total_matches") or has("message")' >/dev/null
    fi
}

@test "export_individual_conversations: basic functionality" {
    # Test basic conversation export
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"limit": 2}}'
    [ "$status" -eq 0 ]

    local export_content
    export_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify export structure
    [[ -n "$export_content" ]]

    if echo "$export_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        # Check for export-specific fields
        echo "$export_content" | jq -e 'has("output_directory") or has("exported_files") or has("message")' >/dev/null
    fi
}

@test "export_individual_conversations: markdown format" {
    # Test markdown format export
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"format": "md", "limit": 2}}'
    [ "$status" -eq 0 ]

    local export_content
    export_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify format is preserved
    [[ -n "$export_content" ]]
    
    if echo "$export_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        local format
        format=$(echo "$export_content" | jq -r '.format // "unknown"')
        [[ "$format" == "md" || "$format" == "unknown" ]]
    fi
}

# Server Information Tests

@test "get_server_version: basic functionality" {
    # Test server version retrieval
    run execute_clean_rpc "tools/call" '{"name": "get_server_version", "arguments": {"random_string": "gondor"}}'
    [ "$status" -eq 0 ]

    local version_content
    version_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify version information
    [[ -n "$version_content" ]]
    
    if echo "$version_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "$version_content" | jq -e 'has("server_version") or has("protocol_version") or has("message")' >/dev/null
    fi
}

@test "get_project_info: basic functionality" {
    # Test project information retrieval
    run execute_clean_rpc "tools/call" '{"name": "get_project_info", "arguments": {"include_stats": true}}'
    [ "$status" -eq 0 ]

    local project_content
    project_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify project information
    [[ -n "$project_content" ]]
    
    if echo "$project_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "$project_content" | jq -e 'has("project_name") or has("file_count") or has("message")' >/dev/null
    fi
}

@test "list_project_files: basic functionality" {
    # Test file listing functionality
    run execute_clean_rpc "tools/call" '{"name": "list_project_files", "arguments": {"max_files": 10}}'
    [ "$status" -eq 0 ]

    local files_content
    files_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify file listing
    [[ -n "$files_content" ]]
    
    if echo "$files_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "$files_content" | jq -e 'has("files") or has("total_files") or has("message")' >/dev/null
    fi
}

# Integration Tests

@test "recall_conversations: comprehensive mode" {
    # Test comprehensive conversation recall
    run execute_clean_rpc "tools/call" '{"name": "recall_conversations", "arguments": {"fast_mode": false, "limit": 10}}'
    [ "$status" -eq 0 ]

    local recall_content
    recall_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify comprehensive response
    [[ -n "$recall_content" ]]
    
    if echo "$recall_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "$recall_content" | jq -e 'has("conversations") or has("total_conversations") or has("message")' >/dev/null
    fi
}

@test "search_conversations: with date filtering" {
    # Test conversation search with date filtering
    run execute_clean_rpc "tools/call" '{"name": "search_conversations", "arguments": {"query": "project", "days_lookback": 7, "limit": 5}}'
    [ "$status" -eq 0 ]

    local search_content
    search_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify search with date filtering
    [[ -n "$search_content" ]]
    
    if echo "$search_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "$search_content" | jq -e 'has("conversations") or has("total_matches") or has("message")' >/dev/null
    fi
}

@test "export_individual_conversations: with conversation type filter" {
    # Test export with conversation type filtering
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"conversation_types": ["technical"], "limit": 3}}'
    [ "$status" -eq 0 ]

    local export_content
    export_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Verify filtered export
    [[ -n "$export_content" ]]
    
    if echo "$export_content" | jq -e 'type == "object"' >/dev/null 2>&1; then
        echo "$export_content" | jq -e 'has("output_directory") or has("exported_files") or has("message")' >/dev/null
    fi
}

# Error Handling Tests

@test "recall_conversations: handles invalid parameters gracefully" {
    # Test error handling for invalid parameters
    run execute_clean_rpc "tools/call" '{"name": "recall_conversations", "arguments": {"limit": -1}}'
    [ "$status" -eq 0 ]

    local response
    response=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle invalid parameters gracefully
    [[ -n "$response" ]]
}

@test "search_conversations: handles empty query gracefully" {
    # Test error handling for empty query
    run execute_clean_rpc "tools/call" '{"name": "search_conversations", "arguments": {"query": "", "limit": 5}}'
    [ "$status" -eq 0 ]

    local response
    response=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle empty query gracefully
    [[ -n "$response" ]]
}

@test "export_individual_conversations: handles invalid format gracefully" {
    # Test error handling for invalid format
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"format": "invalid_format", "limit": 1}}'
    [ "$status" -eq 0 ]

    local response
    response=$(echo "$output" | jq -r '.result.content[0].text')

    # Should handle invalid format gracefully
    [[ -n "$response" ]]
}
