#!/usr/bin/env bats
# Conversation Export Tests for Gandalf MCP Server
# Tests for exporting Cursor IDE conversations via MCP tools

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

setup() {
    shared_setup
    create_minimal_project

    # Create export test directory for isolated testing
    EXPORT_TEST_DIR="$TEST_PROJECT_DIR/exports"
    mkdir -p "$EXPORT_TEST_DIR"

    # Keep test mode enabled to prevent actual file creation
    export ORIGINAL_TEST_MODE="$GANDALF_TEST_MODE"
}

teardown() {
    # Restore original test mode
    export GANDALF_TEST_MODE="$ORIGINAL_TEST_MODE"

    cd "$TEST_PROJECT_DIR" || cd /tmp
    if [[ -n "$EXPORT_TEST_DIR" && -d "$EXPORT_TEST_DIR" ]]; then
        rm -rf "$EXPORT_TEST_DIR"
    fi

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

@test "query_cursor_conversations: basic functionality with JSON format" {
    # Test basic conversation querying with explicit JSON format
    run execute_clean_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"format": "json"}}'
    [ "$status" -eq 0 ]

    local cursor_content
    cursor_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return valid conversation data structure
    echo "$cursor_content" | jq -e '.workspaces' >/dev/null
    echo "$cursor_content" | jq -e '.query_timestamp' >/dev/null
}

@test "query_cursor_conversations: summary mode" {
    # Test summary mode for quick overview
    run execute_clean_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"summary": true}}'
    [ "$status" -eq 0 ]

    local summary_content
    summary_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return summary statistics
    echo "$summary_content" | jq -e '.workspaces' >/dev/null
    echo "$summary_content" | jq -e '.total_conversations' >/dev/null
    echo "$summary_content" | jq -e '.total_prompts' >/dev/null
    echo "$summary_content" | jq -e '.total_generations' >/dev/null
    echo "$summary_content" | jq -e '.query_timestamp' >/dev/null

    # Verify numeric values are reasonable
    local total_conversations
    total_conversations=$(echo "$summary_content" | jq -r '.total_conversations')
    [[ "$total_conversations" =~ ^[0-9]+$ ]]
}

@test "query_cursor_conversations: different formats" {
    run execute_clean_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"format": "json"}}'
    [ "$status" -eq 0 ]

    local json_content
    json_content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$json_content" | jq -e '.workspaces' >/dev/null

    # Test Markdown format
    run execute_clean_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"format": "markdown"}}'
    [ "$status" -eq 0 ]

    local markdown_content
    markdown_content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$markdown_content" | grep -q "# Cursor Conversations"

    # Test Cursor format (default)
    run execute_clean_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"format": "cursor"}}'
    [ "$status" -eq 0 ]

    local cursor_content
    cursor_content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$cursor_content" | grep -q "# Cursor Chat History"
}

@test "list_cursor_workspaces: basic functionality" {
    run execute_clean_rpc "tools/call" '{"name": "list_cursor_workspaces", "arguments": {"random_string": "shire"}}'
    [ "$status" -eq 0 ]

    local workspaces_content
    workspaces_content=$(echo "$output" | jq -r '.result.content[0].text')

    [[ -n "$workspaces_content" ]]

    if echo "$workspaces_content" | jq -e 'type == "object" and has("workspaces") and (.workspaces | length > 0)' >/dev/null 2>&1; then
        echo "$workspaces_content" | jq -e '.workspaces[0].workspace_hash' >/dev/null
        echo "$workspaces_content" | jq -e '.workspaces[0].database_path' >/dev/null
    fi
}

@test "ingest_conversations: fast mode" {
    run execute_clean_rpc "tools/call" '{"name": "ingest_conversations", "arguments": {"fast_mode": true, "limit": 5}}'
    [ "$status" -eq 0 ]

    local ingest_content
    ingest_content=$(echo "$output" | jq -r '.result.content[0].text')

    echo "$ingest_content" | jq -e '.mode' >/dev/null
    echo "$ingest_content" | jq -e '.total_conversations' >/dev/null
    echo "$ingest_content" | jq -e '.parameters' >/dev/null

    local mode
    mode=$(echo "$ingest_content" | jq -r '.mode')
    [[ "$mode" == "ultra_fast_extraction" || "$mode" == "cached_results" ]]
}

@test "query_conversation_context: basic search" {
    # Test conversation context searching for rings of power related discussions
    run execute_clean_rpc "tools/call" '{"name": "query_conversation_context", "arguments": {"query": "rings of power", "limit": 5}}'
    [ "$status" -eq 0 ]

    local search_content
    search_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return search results structure
    echo "$search_content" | jq -e '.query' >/dev/null
    echo "$search_content" | jq -e '.total_matches' >/dev/null
    echo "$search_content" | jq -e '.processed_conversations' >/dev/null
    echo "$search_content" | jq -e '.conversations' >/dev/null

    # Verify query was preserved
    local query
    query=$(echo "$search_content" | jq -r '.query')
    [[ "$query" == "rings of power" ]]
}

@test "conversation export workflow: fellowship integration" {
    run execute_clean_rpc "tools/call" '{"name": "query_cursor_conversations", "arguments": {"summary": true}}'
    [ "$status" -eq 0 ]

    local summary_result
    summary_result=$(echo "$output" | jq -r '.result.content[0].text')
    local conversation_count
    conversation_count=$(echo "$summary_result" | jq -r '.total_conversations')

    run execute_clean_rpc "tools/call" '{"name": "list_cursor_workspaces", "arguments": {"random_string": "middle_earth"}}'
    [ "$status" -eq 0 ]

    local workspaces_result
    workspaces_result=$(echo "$output" | jq -r '.result.content[0].text')

    [[ "$conversation_count" =~ ^[0-9]+$ ]]
    [[ -n "$workspaces_result" ]]
}

@test "export_individual_conversations: basic functionality" {
    # Test basic individual conversation export
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"format": "json", "limit": 3}}'
    [ "$status" -eq 0 ]

    local export_content
    export_content=$(echo "$output" | jq -r '.result.content[0].text')

    echo "$export_content" | grep -q "exported_count"
    [[ -n "$export_content" ]]
}

@test "export_individual_conversations: markdown format" {
    # Test markdown format export
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"format": "md", "limit": 2}}'
    [ "$status" -eq 0 ]

    local export_content
    export_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should indicate markdown export
    echo "$export_content" | grep -q "exported_count"
}

@test "export_individual_conversations: with conversation filter" {
    # Test export with conversation name filter
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"format": "json", "conversation_filter": "test", "limit": 5}}'
    [ "$status" -eq 0 ]

    local export_content
    export_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should complete without error, may have 0 matches
    [[ -n "$export_content" ]]
}

@test "export_individual_conversations: invalid format error" {
    # Test invalid format parameter
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"format": "invalid_format"}}'
    [ "$status" -eq 0 ]

    local error_content
    error_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return error about invalid format
    echo "$error_content" | grep -q "Invalid format"
}

@test "export_individual_conversations: limit validation" {
    # Test limit parameter validation
    run execute_clean_rpc "tools/call" '{"name": "export_individual_conversations", "arguments": {"limit": 150}}'
    [ "$status" -eq 0 ]

    local error_content
    error_content=$(echo "$output" | jq -r '.result.content[0].text')

    # Should return error about invalid limit
    echo "$error_content" | grep -q "Limit must be an integer between 1 and 100"
}
