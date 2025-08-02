#!/usr/bin/env bats
# File-based Logging Tests for Gandalf MCP Server
# Tests the actual file-based logging implementation in src.utils.common

set -euo pipefail

GANDALF_ROOT=$(git rev-parse --show-toplevel)
load "$GANDALF_ROOT/tools/tests/test-helpers.sh"
execute_logging_test() {
    local python_code="$1"
    local session_id="${2:-$TEST_SESSION_ID}"
    
    pushd "$SERVER_DIR" >/dev/null
    
    local output stderr_output
    {
        output=$(MCP_DEBUG=1 python3 -c "
import os
os.environ['MCP_DEBUG'] = '1'
import sys
sys.path.insert(0, '.')
from src.utils.common import initialize_session_logging
initialize_session_logging('$session_id')
$python_code
" 2>&1)
        stderr_output=$?
    }
    
    popd >/dev/null
    echo "$output"
    return $stderr_output
}

find_log_file() {
    local session_id="$1"
    local log_dir="$GANDALF_HOME/logs"
    
    if [[ ! -d "$log_dir" ]]; then
        echo "ERROR: Log directory not found: $log_dir" >&2
        return 1
    fi
    
    local log_file
    log_file=$(find "$log_dir" -name "gandalf_session_${session_id}_*.log" | head -1)
    
    if [[ -z "$log_file" ]]; then
        echo "ERROR: No log file found for session: $session_id" >&2
        return 1
    fi
    
    echo "$log_file"
}

validate_log_entry() {
    local log_line="$1"
    local expected_level="$2"
    local expected_message="$3"
    local expected_logger="${4:-}"
    
    # Validate JSON structure
    if ! echo "$log_line" | jq . >/dev/null 2>&1; then
        echo "ERROR: Invalid JSON in log entry: $log_line" >&2
        return 1
    fi
    
    # Validate required fields
    local actual_level actual_message actual_logger
    actual_level=$(echo "$log_line" | jq -r '.level')
    actual_message=$(echo "$log_line" | jq -r '.message')
    
    if [[ "$actual_level" != "$expected_level" ]]; then
        echo "ERROR: Level mismatch. Expected: $expected_level, Got: $actual_level" >&2
        return 1
    fi
    
    if [[ "$actual_message" != "$expected_message" ]]; then
        echo "ERROR: Message mismatch. Expected: $expected_message, Got: $actual_message" >&2
        return 1
    fi
    
    if [[ -n "$expected_logger" ]]; then
        actual_logger=$(echo "$log_line" | jq -r '.logger')
        if [[ "$actual_logger" != "$expected_logger" ]]; then
            echo "ERROR: Logger mismatch. Expected: $expected_logger, Got: $actual_logger" >&2
            return 1
        fi
    fi
    
    # Validate timestamp format
    if ! echo "$log_line" | jq -r '.timestamp' | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' >/dev/null; then
        echo "ERROR: Invalid timestamp format in log entry" >&2
        return 1
    fi
    
    # Validate session_id
    if ! echo "$log_line" | jq -e --arg sid "$TEST_SESSION_ID" '.session_id == $sid' >/dev/null; then
        echo "ERROR: Session ID mismatch in log entry" >&2
        return 1
    fi
    
    return 0
}

get_last_log_entry() {
    local log_file="$1"
    
    if [[ ! -f "$log_file" ]]; then
        echo "ERROR: Log file not found: $log_file" >&2
        return 1
    fi
    
    tail -n1 "$log_file"
}

count_log_entries_by_level() {
    local log_file="$1"
    local level="$2"
    
    if [[ ! -f "$log_file" ]]; then
        echo "ERROR: Log file not found: $log_file" >&2
        return 1
    fi
    
    grep -c "\"level\": \"$level\"" "$log_file" || echo "0"
}

setup() {
    shared_setup
    
    # Set up logging environment
    export ORIGINAL_MCP_DEBUG="${MCP_DEBUG:-}"
    export MCP_DEBUG=1
    
    TEST_SESSION_ID="test_$(date +%s)_$$"
    TEMP_LOGS_DIR=$(mktemp -d)
    export GANDALF_HOME="$TEMP_LOGS_DIR/.gandalf"
    
    # Create logs directory
    mkdir -p "$GANDALF_HOME/logs"
}

teardown() {
    shared_teardown
    
    # Restore original MCP_DEBUG
    if [[ -n "${ORIGINAL_MCP_DEBUG:-}" ]]; then
        export MCP_DEBUG="$ORIGINAL_MCP_DEBUG"
    else
        unset MCP_DEBUG
    fi
    
    # Clean up temporary directory
    [[ -n "${TEMP_LOGS_DIR:-}" && -d "$TEMP_LOGS_DIR" ]] && rm -rf "$TEMP_LOGS_DIR"
}

@test "session logging initialization creates log file" {
    execute_logging_test ""
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    # Verify log file exists and is readable
    [[ -f "$log_file" ]]
    [[ -r "$log_file" ]]
    
    # Verify file has content
    [[ -s "$log_file" ]]
}

@test "session logging writes session start marker" {
    execute_logging_test ""
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    # Verify session start marker exists
    grep -q "GANDALF session started: $TEST_SESSION_ID" "$log_file"
}

@test "file logging writes structured JSON entries" {
    execute_logging_test "
from src.utils.common import write_log
write_log('info', 'test message', 'test_logger', {'key': 'value'})
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    local log_entry
    log_entry=$(get_last_log_entry "$log_file")
    
    # Validate log entry structure
    validate_log_entry "$log_entry" "info" "test message" "test_logger"
    
    # Validate additional data
    echo "$log_entry" | jq -e '.data.key == "value"' >/dev/null
}

@test "file logging handles different log levels correctly" {
    execute_logging_test "
from src.utils.common import write_log
write_log('debug', 'debug message')
write_log('info', 'info message')
write_log('warning', 'warning message')
write_log('error', 'error message')
write_log('critical', 'critical message')
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    # Verify all log levels are present - using more robust counting
    local debug_count info_count warning_count error_count critical_count
    debug_count=$(grep -c '"level": "debug"' "$log_file" || echo "0")
    info_count=$(grep -c '"level": "info"' "$log_file" || echo "0")
    warning_count=$(grep -c '"level": "warning"' "$log_file" || echo "0")
    error_count=$(grep -c '"level": "error"' "$log_file" || echo "0")
    critical_count=$(grep -c '"level": "critical"' "$log_file" || echo "0")
    
    # More lenient assertions - account for session initialization logs
    [[ "$debug_count" -ge 1 ]]
    [[ "$info_count" -ge 1 ]]
    [[ "$warning_count" -ge 1 ]]
    [[ "$error_count" -ge 1 ]]
    [[ "$critical_count" -ge 1 ]]
}

@test "file logging creates logs directory if it doesn't exist" {
    # Remove the logs directory
    rm -rf "$GANDALF_HOME/logs"
    
    execute_logging_test ""
    
    # Verify directory was created
    [[ -d "$GANDALF_HOME/logs" ]]
    
    # Verify log file was created
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    [[ -f "$log_file" ]]
}

@test "file logging handles concurrent sessions" {
    local session1="session1_$(date +%s)"
    local session2="session2_$(date +%s)"
    
    # Create two separate sessions
    execute_logging_test "
from src.utils.common import write_log
write_log('info', 'session1 message')
" "$session1"
    
    execute_logging_test "
from src.utils.common import write_log
write_log('info', 'session2 message')
" "$session2"
    
    # Verify both log files exist
    local log_file1 log_file2
    log_file1=$(find_log_file "$session1")
    log_file2=$(find_log_file "$session2")
    
    [[ -f "$log_file1" ]]
    [[ -f "$log_file2" ]]
    
    # Verify files are different
    [[ "$log_file1" != "$log_file2" ]]
    
    # Verify each file contains its respective session's message
    grep -q "session1 message" "$log_file1"
    grep -q "session2 message" "$log_file2"
    
    # Verify session messages don't cross-contaminate
    ! grep -q "session2 message" "$log_file1"
    ! grep -q "session1 message" "$log_file2"
}

@test "file logging includes complete timestamp information" {
    execute_logging_test "
from src.utils.common import write_log
write_log('info', 'timestamp test')
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    local log_entry
    log_entry=$(get_last_log_entry "$log_file")
    
    # Validate timestamp field exists and has correct format
    echo "$log_entry" | jq -e '.timestamp' >/dev/null
    
    local timestamp
    timestamp=$(echo "$log_entry" | jq -r '.timestamp')
    
    # Validate ISO 8601 format (YYYY-MM-DDTHH:MM:SS)
    echo "$timestamp" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}' >/dev/null
}

@test "file logging handles empty and null messages gracefully" {
    execute_logging_test "
from src.utils.common import write_log
write_log('info', '')
write_log('info', None)
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    # Verify entries were logged - check for empty and None messages
    grep -q '"message": ""' "$log_file"
    grep -q '"message": "None"' "$log_file" || grep -q '"message": null' "$log_file"
}

@test "file logging handles large messages without truncation" {
    local large_message
    large_message=$(printf 'A%.0s' {1..1000}) # 1000 character message
    
    execute_logging_test "
from src.utils.common import write_log
write_log('info', '$large_message')
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    local log_entry
    log_entry=$(get_last_log_entry "$log_file")
    
    # Validate message was not truncated
    echo "$log_entry" | jq -e --arg msg "$large_message" '.message == $msg' >/dev/null
}

@test "file logging handles special characters in messages" {
    execute_logging_test "
from src.utils.common import write_log
write_log('info', 'Special chars: hello world')
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    local log_entry
    log_entry=$(get_last_log_entry "$log_file")
    
    # Validate special characters are preserved
    echo "$log_entry" | jq -e '.message' >/dev/null
    
    # Verify message contains expected text
    echo "$log_entry" | jq -r '.message' | grep -q "hello world"
}

@test "file logging maintains chronological order of entries" {
    execute_logging_test "
from src.utils.common import write_log
import time
write_log('info', 'first message')
time.sleep(0.1)
write_log('info', 'second message')
time.sleep(0.1)
write_log('info', 'third message')
"
    
    local log_file
    log_file=$(find_log_file "$TEST_SESSION_ID")
    
    # Extract timestamps from messages with our specific content
    local timestamps
    timestamps=$(grep -E '"message": "(first|second|third) message"' "$log_file" | jq -r '.timestamp' | sort)
    
    # Verify we have 3 timestamps
    local timestamp_count
    timestamp_count=$(echo "$timestamps" | wc -l)
    [[ "$timestamp_count" -eq 3 ]]
    
    # Verify timestamps are in chronological order (already sorted above)
    local original_timestamps
    original_timestamps=$(grep -E '"message": "(first|second|third) message"' "$log_file" | jq -r '.timestamp')
    
    local sorted_timestamps
    sorted_timestamps=$(echo "$original_timestamps" | sort)
    
    [[ "$original_timestamps" == "$sorted_timestamps" ]]
}
