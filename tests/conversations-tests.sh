#!/usr/bin/env bats

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required for conversation tests" >&2
    exit 1
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
CONV_SCRIPT="$GANDALF_ROOT/scripts/conversations.sh"

ORIGINAL_HOME="$HOME"
TEST_PROJECT="mordor"
TEST_PROJECT_DIR=""

execute_conv() {
    if [[ $# -gt 1 ]] && ([[ "$1" =~ ^\[.*\]$ ]] || [[ "$1" == "invalid json" ]]); then
        local stdin_input="$1"
        shift
        (cd "$TEST_PROJECT_DIR" && echo "$stdin_input" | "$CONV_SCRIPT" "$@")
    else
        (cd "$TEST_PROJECT_DIR" && "$CONV_SCRIPT" "$@")
    fi
}

create_test_message() {
    local content="${1:-Test message}"
    local timestamp="${2:-2024-01-01T10:00:00Z}"
    jq -nc \
        --arg content "$content" \
        --arg timestamp "$timestamp" \
        '[{
            "role": "user",
            "content": $content,
            "timestamp": $timestamp
        }]'
}

create_test_conversation_messages() {
    local title="$1"
    local user_timestamp="${2:-2024-01-01T10:00:00.000Z}"
    local assistant_timestamp="${3:-2024-01-01T10:00:30.000Z}"

    jq -nc \
        --arg title "$title" \
        --arg user_timestamp "$user_timestamp" \
        --arg assistant_timestamp "$assistant_timestamp" \
        '[
            {
                "role": "user",
                "content": ("Hello, I have the one ring - " + $title),
                "timestamp": $user_timestamp
            },
            {
                "role": "assistant",
                "content": ("Hello! I hope you are not Sauron - " + $title + "."),
                "timestamp": $assistant_timestamp
            }
        ]'
}

extract_conv_id() {
    echo "$1" | grep "Full ID:" | cut -d' ' -f3
}

get_conv_file_path() {
    echo "$CONVERSATIONS_DIR/$TEST_PROJECT/$1.json"
}

setup() {
    TEST_HOME=$(mktemp -d) # Make a new temp dir for each test
    export HOME="$TEST_HOME"
    export CONVERSATIONS_DIR="$TEST_HOME/.gandalf/conversations"

    TEST_PROJECT_DIR="$TEST_HOME/$TEST_PROJECT"
    mkdir -p "$TEST_PROJECT_DIR"

    (cd "$TEST_PROJECT_DIR" && git init >/dev/null 2>&1)
}

teardown() {
    export HOME="$ORIGINAL_HOME"
    if [[ -n "$TEST_HOME" && -d "$TEST_HOME" ]]; then
        rm -rf "$TEST_HOME"
    fi
}

create_test_conversation() {
    local conv_title="$1"
    local conv_tags="$2"

    local test_messages=$(create_test_conversation_messages "$conv_title")

    local output=$(echo "$test_messages" | execute_conv store "temp-id" -t "$conv_title" -g "$conv_tags" 2>&1)
    extract_conv_id "$output"
}

@test "conv.sh script executable, should pass" {
    [ -f "$CONV_SCRIPT" ]
    [ -x "$CONV_SCRIPT" ]
}

@test "help command, should pass" {
    run execute_conv -h
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage:"
}

@test "No arguments, shows help and should fail" {
    run execute_conv
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Usage:"
}

@test "Invalid command, should fail" {
    run execute_conv invalid-command
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown command"
}

@test "Store without ID, should fail" {
    run execute_conv store
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Conversation ID required"
}

@test "Show without ID, should fail" {
    run execute_conv show
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Conversation ID required"
}

@test "Store with invalid JSON, should fail" {
    run execute_conv "invalid json" store "test-invalid"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Invalid JSON"
}

@test "Store conversation via stdin, should pass" {
    test_messages=$(create_test_message "Test message")

    run execute_conv "$test_messages" store "temp-id" -t "Test Conversation" -g "test,demo"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Stored conversation:"
    echo "$output" | grep -q "Full ID:"
}

@test "Conv creates correct file structure, should pass" {
    test_messages=$(create_test_message)
    output=$(execute_conv "$test_messages" store "temp-id" -t "Test Conversation" -g "test,demo" 2>&1)
    conv_id=$(extract_conv_id "$output")

    conv_file=$(get_conv_file_path "$conv_id")
    [ -f "$conv_file" ]

    run jq -e '.conversation_id' "$conv_file"
    [ "$status" -eq 0 ]

    run jq -e '.messages' "$conv_file"
    [ "$status" -eq 0 ]

    run jq -e '.title' "$conv_file"
    [ "$status" -eq 0 ]

    run jq -e '.tags' "$conv_file"
    [ "$status" -eq 0 ]
}

@test "Conv stores correct metadata, should pass" {
    test_messages=$(create_test_message "Metadata test")
    output=$(execute_conv "$test_messages" store "temp-id" -t "Metadata Test" -g "meta,test" 2>&1)
    conv_id=$(extract_conv_id "$output")

    conv_file=$(get_conv_file_path "$conv_id")

    run jq -r '.conversation_id' "$conv_file"
    [ "$output" = "$conv_id" ]

    run jq -r '.title' "$conv_file"
    [ "$output" = "Metadata Test" ]

    run jq -r '.tags[0]' "$conv_file"
    [ "$output" = "meta" ]
}

@test "List with no conversations, should pass" {
    run execute_conv list
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "No conversations found"
}

@test "List shows stored conversations, should pass" {
    conv_id1=$(create_test_conversation "First Test" "test")
    conv_id2=$(create_test_conversation "Second Test" "test")

    run execute_conv list
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "${conv_id1:0:9}" # Get the first 9 chars of the conv_id
    echo "$output" | grep -q "${conv_id2:0:9}"
}

@test "List json format, should pass" {
    conv_id=$(create_test_conversation "JSON Test" "json")

    run execute_conv list -f json
    [ "$status" -eq 0 ]

    run bash -c "execute_conv list -f json | jq ."
    [ "$status" -eq 0 ]
}

@test "Show existing conversation, should pass" {
    conv_id=$(create_test_conversation "Show Test" "show")

    run execute_conv show "$conv_id"
    [ "$status" -eq 0 ]
    # Text format checks
    echo "$output" | grep -q "# Conversation: $conv_id"
    echo "$output" | grep -q "Title: Show Test"
    echo "$output" | grep -q "## Messages"
}

@test "Show existing conversation JSON format, should pass" {
    conv_id=$(create_test_conversation "JSON Show Test" "json,show")

    run execute_conv show "$conv_id" -f json
    [ "$status" -eq 0 ]
    # JSON format validation
    run bash -c "execute_conv show '$conv_id' -f json | jq ."
    [ "$status" -eq 0 ]
    # Check specific JSON fields
    conv_data=$(execute_conv show "$conv_id" -f json)
    echo "$conv_data" | jq -e ".conversation_id == \"$conv_id\""
    echo "$conv_data" | jq -e ".title == \"JSON Show Test\""
}

@test "Show with short ID pattern matching, should pass" {
    conv_id=$(create_test_conversation "Pattern Test" "pattern")
    short_id="${conv_id:0:8}"

    run execute_conv show "$short_id"
    [ "$status" -eq 0 ]
    # Text format checks
    echo "$output" | grep -q "# Conversation: $conv_id"
    echo "$output" | grep -q "Title: Pattern Test"
}

@test "Stats with conversations, should pass" {
    conv_id1=$(create_test_conversation "Stats Test 1" "stats")
    conv_id2=$(create_test_conversation "Stats Test 2" "stats")

    run execute_conv stats
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Total Conversations:"
    echo "$output" | grep -q "Total Messages:"
    echo "$output" | grep -q "Storage Location:"
}

@test "Stats with no conversations, should pass" {
    run execute_conv stats
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "No conversations found"
}

@test "Cleanup removes old conversations, should pass" {
    conv_id=$(create_test_conversation "Old Conversation" "old")

    old_file=$(get_conv_file_path "$conv_id")
    echo "Debug: Old file path: $old_file" >&2
    
    # Should handle both Linux and mac date commands
    old_timestamp=$(date -u -d "31 days ago" +%Y-%m-%dT%H:%M:%S.%3NZ 2>/dev/null || date -u -v-31d +%Y-%m-%dT%H:%M:%S.%3NZ)
    echo "Debug: Old timestamp: $old_timestamp" >&2

    temp_file=$(mktemp)
    echo "Debug: Temp file: $temp_file" >&2
    
    jq --arg timestamp "$old_timestamp" \
        '.created_at = $timestamp' \
        "$old_file" >"$temp_file" && mv "$temp_file" "$old_file"
    
    echo "Debug: File contents after update:" >&2
    cat "$old_file" >&2
    
    echo "Debug: Running cleanup command..." >&2
    run execute_conv cleanup 30
    echo "Debug: Cleanup status: $status" >&2
    echo "Debug: Cleanup output: $output" >&2
    
    [ "$status" -eq 0 ]
    [ ! -f "$old_file" ]
}

@test "Cleanup with invalid days, should fail" {
    run execute_conv cleanup invalid-days
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Days must be a positive number"
}

@test "Handles special characters in ID, should pass" {
    test_messages=$(create_test_message "Special test")
    output=$(execute_conv "$test_messages" store "temp-id" -t "Special Test" 2>&1)
    conv_id=$(extract_conv_id "$output")

    conv_file=$(get_conv_file_path "$conv_id")
    [ -f "$conv_file" ]
}

@test "Handles malformed JSON files gracefully, should pass" {
    mkdir -p "$CONVERSATIONS_DIR/$TEST_PROJECT"
    echo "invalid json" >"$CONVERSATIONS_DIR/$TEST_PROJECT/malformed.json"

    run execute_conv list
    [ "$status" -eq 0 ]
}

@test "Handles empty project directory, should pass" {
    rm -rf "$CONVERSATIONS_DIR/$TEST_PROJECT"

    run execute_conv list
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "No conversations found"
}

@test "Called from gandalf.sh, conv integration, should pass" {
    run "$GANDALF_ROOT/gandalf.sh" conv -h
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage:"
}

@test "Handles hash-based IDs properly, should pass" {
    test_messages=$(create_test_message "Hash test")
    output=$(execute_conv "$test_messages" store "temp-id" -t "Hash Test" 2>&1)
    conv_id=$(extract_conv_id "$output")

    [ ${#conv_id} -eq 16 ]

    conv_file=$(get_conv_file_path "$conv_id")
    [ -f "$conv_file" ]
}

@test "Show non-existent conversation, should fail" {
    run execute_conv show nonexistent-pattern-xyz
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Conversation not found"
}

@test "Show displays full content from metadata when available, should pass" {
    test_messages=$(jq -nc '[{
        "role": "user",
        "content": "Called tool: test_tool",
        "timestamp": "2024-01-01T10:00:00Z"
    }, {
        "role": "assistant",
        "content": "Truncated response",
        "timestamp": "2024-01-01T10:01:00Z",
        "metadata": {
            "tool_name": "test_tool",
            "full_result": {
                "content": [{
                    "type": "text",
                    "text": "Full detailed response with all information"
                }]
            }
        }
    }]')

    conv_id=$(echo "$test_messages" | execute_conv store "temp-id" -t "Full Content Test" | grep "Full ID:" | cut -d' ' -f3)

    run execute_conv show "$conv_id"
    [ "$status" -eq 0 ]

    # Should show the full content from metadata, not the truncated version
    echo "$output" | grep -q "Full detailed response with all information"
    ! echo "$output" | grep -q "Truncated response"
}

@test "Auto-capture functionality, should pass" {
    test_messages=$(create_test_message "Auto test")

    run execute_conv "$test_messages" auto -t "Auto Test" -g "auto,test"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Auto-captured conversation successfully"
    echo "$output" | grep -q "View with:"
}

@test "gandalf.sh, conv updated store integration, should pass" {
    test_messages=$(jq -nc '{
        "role": "user",
        "content": "Gandalf integration test",
        "timestamp": "2024-01-01T10:00:00Z"
    } | [.]')

    run bash -c "echo '$test_messages' | '$GANDALF_ROOT/gandalf.sh' conv store 'temp-id' -t 'Gandalf Integration'"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Stored conversation:"
    echo "$output" | grep -q "Full ID:"
}

@test "gandalf.sh, conv updated list integration, should pass" {
    test_messages=$(jq -nc '{
        "role": "user",
        "content": "Gandalf list test",
        "timestamp": "2024-01-01T10:00:00Z"
    } | [.]')

    run bash -c "echo '$test_messages' | '$GANDALF_ROOT/gandalf.sh' conv store 'temp-id' -t 'Gandalf List Test'"
    [ "$status" -eq 0 ]

    run "$GANDALF_ROOT/gandalf.sh" conv list
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Gandalf List Test"
}

@test "Shows warning when jq is missing, should pass" {
    conv_id=$(create_test_conversation "Basic Fallback Test" "basic")

    temp_script=$(mktemp)
    cat >"$temp_script" <<'EOF'
#!/bin/bash
jq() { 
    echo "command not found: jq" >&2
    return 127
}
export -f jq
EOF

    run bash -c "source '$temp_script' && cd '$TEST_PROJECT_DIR' && '$CONV_SCRIPT' show '$conv_id'"

    [ "$status" -eq 0 ]

    echo "$output" | grep -q "=== Conversation File Contents ==="
    echo "$output" | grep -q "Note: Install jq for formatted output"

}

@test "Pattern matching with middle of hash, should pass" {
    conv_id=$(create_test_conversation "Middle Pattern Test" "middle")
    prefix_pattern="${conv_id:0:8}"

    run execute_conv show "$prefix_pattern"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "# Conversation: $conv_id"
    echo "$output" | grep -q "Title: Middle Pattern Test"
}
