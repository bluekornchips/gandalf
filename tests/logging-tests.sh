#!/usr/bin/env bats

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
SERVER_DIR="$GANDALF_ROOT/server"

setup() {
    export ORIGINAL_MCP_DEBUG="$MCP_DEBUG"
}

teardown() {
    if [[ -n "$ORIGINAL_MCP_DEBUG" ]]; then
        export MCP_DEBUG="$ORIGINAL_MCP_DEBUG"
    else
        unset MCP_DEBUG
    fi
}

@test "Server uses MCP logging format, should pass" {
    output=$(echo '{"method": "initialize", "id": 1}' |
        python3 "$SERVER_DIR/main.py" --project-root /tmp 2>/dev/null)
    if [[ -n "$output" ]]; then
        echo "$output" | jq -r 'select(.method == "notifications/message") | .params.level' | grep -q 'info'
        return 0
    fi
    return 1
}

@test "MCP logging notification structure, should pass" {
    output=$(echo '{"method": "initialize", "id": 1}' |
        python3 "$SERVER_DIR/main.py" --project-root /tmp 2>/dev/null)
    if [[ -n "$output" ]]; then
        echo "$output" | jq -r 'select(.method == "notifications/message") | .params.level' | grep -q 'info'
        return 0
    fi
    return 1
}

@test "Log an MCP message with log level [error], should pass" {
    cd "$SERVER_DIR"
    output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.utils import log_error
log_error(Exception('test'), 'test context')
" 2>/dev/null)

    if [[ -n "$output" ]]; then
        echo "$output" | jq -e '.method == "notifications/message" and .params.level == "error"'
        return 0
    fi
    return 1
}

@test "Debug logging enabled, should show debug message, should pass" {
    cd "$SERVER_DIR"
    export MCP_DEBUG=1
    output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.utils import debug_log
debug_log('test debug message')
" 2>/dev/null)

    if [[ -n "$output" ]]; then
        echo "$output" | jq -e '.method == "notifications/message" and .params.level == "debug"'
        return 0
    fi
    return 1
}

@test "Server separates responses from logs, showing 1 response and 1 log, should pass" {
    output=$(echo '{"method": "initialize", "id": 1}' |
        python3 "$SERVER_DIR/main.py" --project-root /tmp 2>/dev/null)

    response_count=$(echo "$output" | jq -s 'map(select(.id == 1)) | length')
    log_count=$(echo "$output" | jq -s 'map(select(.method == "notifications/message")) | length')

    if [[ "$response_count" -ge 1 && "$log_count" -ge 1 ]]; then
        return 0
    fi
    return 1
}

@test "Debug logging disabled, should pass" {
    cd "$SERVER_DIR"
    export MCP_DEBUG=0
    output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.utils import debug_log
debug_log('test debug message')
" 2>/dev/null)

    [[ -z "$output" ]] && return 0
    return 1
}

@test "Invalid log level handling, should catch safely, should pass" {
    cd "$SERVER_DIR"
    output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.utils import send_log_notification
send_log_notification('invalid_level', 'test message')
" 2>/dev/null)

    if [[ -n "$output" ]]; then
        echo "$output" | jq -e '.method == "notifications/message" and .params.level == "invalid_level"'
        return 0
    fi
    return 1
}

@test "Logging with malformed data, should catch safely, should pass" {
    cd "$SERVER_DIR"
    output=$(python3 -c "
import sys
sys.path.insert(0, '.')
from src.utils import send_log_notification
send_log_notification('info', 'test message', data=None)
" 2>/dev/null)

    if [[ -n "$output" ]]; then
        echo "$output" | jq -e '.method == "notifications/message" and .params.message == "test message"'
        return 0
    fi
    return 1
}
