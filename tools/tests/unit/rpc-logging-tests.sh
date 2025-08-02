#!/usr/bin/env bats
# File-based Logging Tests for Gandalf MCP Server
# Tests the actual file-based logging implementation in src.utils.common

set -euo pipefail

GANDALF_ROOT=$(git rev-parse --show-toplevel)
load "$GANDALF_ROOT/tools/tests/test-helpers.sh"
execute_logging_test() {
    local python_code="$1"
    local session_id="${2:-test_session_$(date +%s)}"
    
    pushd "$GANDALF_ROOT/server" >/dev/null
    
    local output stderr_output
    {
        output=$(python3 -c "
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
    local log_dir="$TEST_HOME/.gandalf/logs"
    
    if [[ ! -d "$log_dir" ]]; then
        echo "ERROR: Log directory not found: $log_dir" >&2
        return 1
    fi
    
    local log_file
    log_file=$(find "$log_dir" -name "*session_${session_id}_*.log" | head -1)
    
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
    
    if ! echo "$log_line" | jq . >/dev/null 2>&1; then
        echo "ERROR: Invalid JSON in log entry: $log_line" >&2
        return 1
    fi
    
    local actual_level actual_message
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
    
    return 0
}

setup() {
    shared_setup
    create_minimal_project
    
    export GANDALF_HOME="$TEST_HOME/.gandalf"
    mkdir -p "$GANDALF_HOME/logs"
}

teardown() {
    shared_teardown
}

@test "Session logging initialization creates log directory and file" {
    local session_id="init_test_$(date +%s)"
    
    execute_logging_test "" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    [[ -f "$log_file" ]] && [[ -r "$log_file" ]]
    
    grep -q "GANDALF session started: $session_id" "$log_file"
}

@test "log_info creates properly formatted log entries" {
    local session_id="info_test_$(date +%s)"
    local test_message="This is a test info message"
    
    execute_logging_test "
from src.utils.common import log_info
log_info('$test_message')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    local info_line
    info_line=$(grep '"level": "info"' "$log_file" | grep "$test_message")
    
    validate_log_entry "$info_line" "info" "$test_message"
}

@test "log_error creates properly formatted error entries" {
    local session_id="error_test_$(date +%s)"
    local error_message="Test error message"
    local context="test context"
    
    execute_logging_test "
from src.utils.common import log_error
log_error(Exception('$error_message'), '$context')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    # Find the error log entry
    local error_line
    error_line=$(grep '"level": "error"' "$log_file")
    
    # Verify error message contains both context and error
    echo "$error_line" | jq -r '.message' | grep -q "$context.*$error_message"
}

@test "log_debug creates debug level entries" {
    local session_id="debug_test_$(date +%s)"
    local debug_message="Debug information"
    
    execute_logging_test "
from src.utils.common import log_debug
log_debug('$debug_message')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    local debug_line
    debug_line=$(grep '"level": "debug"' "$log_file")
    
    validate_log_entry "$debug_line" "debug" "$debug_message"
}

@test "log_critical creates critical level entries" {
    local session_id="critical_test_$(date +%s)"
    local critical_message="Critical system error"
    
    execute_logging_test "
from src.utils.common import log_critical
log_critical('$critical_message')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    local critical_line
    critical_line=$(grep '"level": "critical"' "$log_file")
    
    validate_log_entry "$critical_line" "critical" "$critical_message"
}

@test "write_log supports additional logger and data fields" {
    local session_id="write_test_$(date +%s)"
    local test_message="Test message with extra data"
    local logger_name="test_logger"
    
    execute_logging_test "
from src.utils.common import write_log
write_log('info', '$test_message', logger='$logger_name', data={'key': 'value', 'number': 42})
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    local log_line
    log_line=$(grep "$test_message" "$log_file")
    
    # Verify logger field
    local actual_logger
    actual_logger=$(echo "$log_line" | jq -r '.logger')
    [[ "$actual_logger" == "$logger_name" ]]
    
    # Verify data field
    local key_value number_value
    key_value=$(echo "$log_line" | jq -r '.data.key')
    number_value=$(echo "$log_line" | jq -r '.data.number')
    [[ "$key_value" == "value" ]] && [[ "$number_value" == "42" ]]
}

@test "All log entries contain required fields" {
    local session_id="fields_test_$(date +%s)"
    
    execute_logging_test "
from src.utils.common import log_info
log_info('Field validation test')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    local log_line
    log_line=$(grep "Field validation test" "$log_file")
    
    # Verify all required fields exist
    echo "$log_line" | jq -e '.timestamp' >/dev/null
    echo "$log_line" | jq -e '.level' >/dev/null
    echo "$log_line" | jq -e '.message' >/dev/null
    echo "$log_line" | jq -e '.session_id' >/dev/null
    
    # Verify timestamp is valid ISO format
    local timestamp
    timestamp=$(echo "$log_line" | jq -r '.timestamp')
    
    # Use Python to validate ISO timestamp (cross-platform compatible)
    python3 -c "
import sys
from datetime import datetime
try:
    datetime.fromisoformat('$timestamp'.replace('Z', '+00:00'))
    sys.exit(0)
except ValueError:
    sys.exit(1)
" >/dev/null 2>&1
}

@test "Logging gracefully handles file system errors" {
    local session_id="error_handling_test_$(date +%s)"
    
    # Test that write_log handles errors gracefully by testing with None log file path
    local output
    output=$(pushd "$GANDALF_ROOT/server" >/dev/null && \
        python3 -c "
import sys
sys.path.insert(0, '.')
from src.utils.common import write_log, log_info
# Test that write_log handles missing log file path gracefully
try:
    # This should not crash even though no session is initialized
    write_log('info', 'Test message without initialization')
    log_info('This should also not crash')
    print('SUCCESS: No crash occurred')
except Exception as e:
    print(f'ERROR: Unexpected exception: {e}')
" 2>&1 && popd >/dev/null)
    
    # Test should not crash - look for success message
    echo "$output" | grep -q "SUCCESS: No crash occurred" || {
        echo "ERROR: Expected 'SUCCESS: No crash occurred' but got: $output" >&2
        return 1
    }
}

@test "Multiple log calls create separate entries" {
    local session_id="multiple_test_$(date +%s)"
    
    execute_logging_test "
from src.utils.common import log_info, log_error, log_debug
log_info('First message')
log_error(Exception('Test error'), 'error context')
log_debug('Debug message')
log_info('Second message')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    # Count different log levels (excluding session start marker)
    local info_count error_count debug_count
    info_count=$(grep -c '"level": "info"' "$log_file")
    error_count=$(grep -c '"level": "error"' "$log_file")
    debug_count=$(grep -c '"level": "debug"' "$log_file")
    
    # Should have: 1 session start + 2 info messages = 3 info entries
    [[ "$info_count" -eq 3 ]] && [[ "$error_count" -eq 1 ]] && [[ "$debug_count" -eq 1 ]]
}

@test "Session ID consistency across log entries" {
    local session_id="consistency_test_$(date +%s)"
    
    execute_logging_test "
from src.utils.common import log_info, log_error, log_debug
log_info('Message 1')
log_error(Exception('Error'), 'context')
log_debug('Debug')
" "$session_id"
    
    local log_file
    log_file=$(find_log_file "$session_id")
    
    # Extract all session IDs from the log file
    local session_ids
    session_ids=$(jq -r '.session_id' "$log_file" | sort -u)
    
    # Should have exactly one unique session ID
    local unique_count
    unique_count=$(echo "$session_ids" | wc -l)
    [[ "$unique_count" -eq 1 ]] && [[ "$session_ids" == "$session_id" ]]
}
