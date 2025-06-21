#!/usr/bin/env bats

load '../fixtures/helpers/test-helpers'

setup() {
    export ORIGINAL_MCP_DEBUG="$MCP_DEBUG"
    export MCP_DEBUG=1

    TEST_SESSION_ID="test_$(date +%s)"
    TEMP_LOGS_DIR=$(mktemp -d)
    export GANDALF_HOME="$TEMP_LOGS_DIR/.gandalf"
}

teardown() {
    rm -rf "$TEMP_LOGS_DIR"
}

# Helper function to execute Python code with file logging
execute_file_logging_test() {
    local python_code="$1"

    pushd "$SERVER_DIR" >/dev/null
    MCP_DEBUG=1 python3 -c "
import os
os.environ['MCP_DEBUG'] = '1'
import sys
sys.path.insert(0, '.')
from src.utils.common import initialize_session_logging
initialize_session_logging('$TEST_SESSION_ID')
$python_code
" 2>/dev/null
    popd >/dev/null
}

@test "Session logging initialization creates log file, should pass" {
    execute_file_logging_test ""

    # Check that log file was created
    log_file=$(find "$GANDALF_HOME/logs" -name "gandalf_session_${TEST_SESSION_ID}_*.log" 2>/dev/null | head -n1)
    [[ -f "$log_file" ]]
}

@test "Session logging writes session start marker, should pass" {
    execute_file_logging_test ""

    log_file=$(find "$GANDALF_HOME/logs" -name "gandalf_session_${TEST_SESSION_ID}_*.log" 2>/dev/null | head -n1)
    [[ -f "$log_file" ]]

    # Check that session start is logged
    grep -q "GANDALF session started: $TEST_SESSION_ID" "$log_file"
}

@test "File logging writes structured JSON entries, should pass" {
    execute_file_logging_test "
from src.utils.common import write_log
write_log('info', 'test message', 'test_logger', {'key': 'value'})
"

    log_file=$(find "$GANDALF_HOME/logs" -name "gandalf_session_${TEST_SESSION_ID}_*.log" 2>/dev/null | head -n1)
    [[ -f "$log_file" ]]

    # Check that the log entry is valid JSON and contains expected fields
    tail -n1 "$log_file" | jq -e '.level == "info"'
    tail -n1 "$log_file" | jq -e '.message == "test message"'
    tail -n1 "$log_file" | jq -e '.logger == "test_logger"'
    tail -n1 "$log_file" | jq -e '.data.key == "value"'
    tail -n1 "$log_file" | jq -e '.session_id == "'$TEST_SESSION_ID'"'
}

@test "File logging handles different log levels, should pass" {
    execute_file_logging_test "
from src.utils.common import write_log
write_log('debug', 'debug message')
write_log('info', 'info message')
write_log('error', 'error message')
"

    log_file=$(find "$GANDALF_HOME/logs" -name "gandalf_session_${TEST_SESSION_ID}_*.log" 2>/dev/null | head -n1)
    [[ -f "$log_file" ]]

    # Check that all log levels are present, accounting for JSON formatting with spaces
    grep -q '"level": "debug"' "$log_file"
    grep -q '"level": "info"' "$log_file"
    grep -q '"level": "error"' "$log_file"
}

@test "File logging creates logs directory if it doesn't exist, should pass" {
    # Remove the logs directory
    rm -rf "$GANDALF_HOME/logs"

    execute_file_logging_test ""

    # Check that directory was created
    [[ -d "$GANDALF_HOME/logs" ]]
}

@test "File logging handles missing log file gracefully, should pass" {
    execute_file_logging_test "
from src.utils.common import write_log
# Try to write to log after initialization
write_log('info', 'test message')
"

    # Should not crash - test passes if we get here
    return 0
}

@test "File logging includes timestamps, should pass" {
    execute_file_logging_test "
from src.utils.common import write_log
write_log('info', 'timestamp test')
"

    log_file=$(find "$GANDALF_HOME/logs" -name "gandalf_session_${TEST_SESSION_ID}_*.log" 2>/dev/null | head -n1)
    [[ -f "$log_file" ]]

    # Check that timestamp field exists and is valid ISO format
    tail -n1 "$log_file" | jq -e '.timestamp'
    tail -n1 "$log_file" | jq -r '.timestamp' | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
}
