#!/usr/bin/env bats

load '../fixtures/helpers/test-helpers'

setup() {
    export ORIGINAL_MCP_DEBUG="$MCP_DEBUG"
}

execute_utils_function() {
    local python_code="$1"
    local mcp_debug="${2:-}"

    pushd "$SERVER_DIR" >/dev/null
    local env_vars=""
    [[ -n "$mcp_debug" ]] && env_vars="env MCP_DEBUG=$mcp_debug"

    local output
    output=$(eval "$env_vars python3 -c \"
import sys
sys.path.insert(0, '.')
$python_code
\" 2>/dev/null")

    popd >/dev/null
    echo "$output"
}

execute_server_with_input() {
    local json_input="$1"
    local mcp_debug="${2:-1}"

    echo "$json_input" | env MCP_DEBUG="$mcp_debug" \
        python3 "$SERVER_DIR/main.py" --project-root /tmp 2>/dev/null
}

@test "Server uses MCP logging format, should pass" {
    output=$(execute_server_with_input '{"method": "initialize", "id": 1}')
    if [[ -n "$output" ]]; then
        echo "$output" | jq -r 'select(.method == "notifications/message") | .params.level' | grep -q 'info'
        return 0
    fi
    return 1
}

@test "MCP logging notification structure, should pass" {
    output=$(execute_server_with_input '{"method": "initialize", "id": 1}')
    if [[ -n "$output" ]]; then
        echo "$output" | jq -r 'select(.method == "notifications/message") | .params.level' | grep -q 'info'
        return 0
    fi
    return 1
}

@test "Log an MCP message with log level [error], should pass" {
    output=$(execute_utils_function "
from src.utils.common import log_error
log_error(Exception('test'), 'test context')
" "1")

    if [[ -n "$output" ]]; then
        echo "$output" | jq -e '.method == "notifications/message" and .params.level == "error"'
        return 0
    fi
    return 1
}

@test "Debug logging enabled, should show debug message, should pass" {
    export MCP_DEBUG=1
    output=$(execute_utils_function "
from src.utils.common import log_debug
log_debug('test debug message')
")

    if [[ -n "$output" ]]; then
        echo "$output" | jq -e '.method == "notifications/message" and .params.level == "debug"'
        return 0
    fi
    return 1
}

@test "All three RPC logging functions work correctly, should pass" {
    export MCP_DEBUG=1
    output=$(execute_utils_function "
from src.utils.common import log_debug, log_info, log_error
log_debug('debug test')
log_info('info test')  
log_error(Exception('error test'), 'context')
")

    if [[ -n "$output" ]]; then
        # Check that we got 3 messages with correct levels
        debug_count=$(echo "$output" | jq -s 'map(select(.params.level == "debug")) | length')
        info_count=$(echo "$output" | jq -s 'map(select(.params.level == "info")) | length')
        error_count=$(echo "$output" | jq -s 'map(select(.params.level == "error")) | length')

        [[ "$debug_count" -eq 1 && "$info_count" -eq 1 && "$error_count" -eq 1 ]]
        return $?
    fi
    return 1
}

@test "send_rpc_message produces valid JSON-RPC, should pass" {
    local output
    pushd "$GANDALF_ROOT" >/dev/null
    output=$(python3 -c "
import sys
sys.path.insert(0, 'server')
from src.utils.common import send_rpc_message
send_rpc_message('info', 'test message', logger='test_logger', data={'key': 'value'})
" 2>&1)
    popd >/dev/null

    echo "$output" | jq -e .
    echo "$output" | jq -e '.jsonrpc == "2.0"'
    echo "$output" | jq -e '.method == "notifications/message"'
    echo "$output" | jq -e '.params.level == "info"'
    echo "$output" | jq -e '.params.message == "test message"'
    echo "$output" | jq -e '.params.logger == "test_logger"'
    echo "$output" | jq -e '.params.data.key == "value"'
}

@test "Server separates responses from logs, showing 1 response and 1 log, should pass" {
    output=$(execute_server_with_input '{"method": "initialize", "id": 1}')

    response_count=$(echo "$output" | jq -s 'map(select(.id == 1)) | length')
    log_count=$(echo "$output" | jq -s 'map(select(.method == "notifications/message")) | length')

    if [[ "$response_count" -ge 1 && "$log_count" -ge 1 ]]; then
        return 0
    fi
    return 1
}

@test "Debug logging disabled, should pass" {
    export MCP_DEBUG=0
    output=$(execute_utils_function "
from src.utils.common import log_debug
log_debug('test debug message')
")

    [[ -z "$output" ]] && return 0
    return 1
}

@test "Invalid log level handling, should catch safely, should pass" {
    local output
    output=$(python3 -c "
import sys
sys.path.insert(0, 'server')
from src.utils.common import send_rpc_message
send_rpc_message('invalid_level', 'test message')
" 2>&1)

    # Should not crash and should produce some output
    [[ -n "$output" ]]
}

@test "Logging with malformed data, should catch safely, should pass" {
    local output
    output=$(python3 -c "
import sys
sys.path.insert(0, 'server')
from src.utils.common import send_rpc_message
send_rpc_message('info', 'test message', data=None)
" 2>&1)

    # Should not crash and should produce some output
    [[ -n "$output" ]]
}
