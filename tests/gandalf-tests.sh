#!/usr/bin/env bats

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
PROJECT_ROOT="$GANDALF_ROOT"

test_id=0

# Helper function to execute JSON-RPC requests
execute_rpc() {
    test_id=$((test_id + 1))
    local method="$1"
    local params="$2"
    local project_root="${3:-$TEST_REPO}"

    local request
    if [[ "$params" == "invalid_json" ]]; then
        request="invalid json"
    else
        request=$(jq -nc \
            --arg method "$method" \
            --argjson params "$params" \
            --arg id "$test_id" \
            '{
                "id": $id,
                "method": $method,
                "params": $params
            }')
    fi

    export GANDALF_TEST_MODE=true
    echo "$request" | "$GANDALF_ROOT/gandalf.sh" run --project-root "$project_root" 2>/dev/null
    local exit_code=$?

    return $exit_code
}

# CONSOLIDATED: Requirements validation (was 3 separate tests)
@test "system requirements met (python3.10+, git, basic tools)" {
    command -v python3
    python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
    command -v git
}

# CONSOLIDATED: All scripts and files exist and are executable (was 5 separate tests)
@test "all gandalf scripts and files exist and are executable" {
    # Core scripts
    [ -f "$GANDALF_ROOT/gandalf.sh" ] && [ -x "$GANDALF_ROOT/gandalf.sh" ]
    [ -f "$GANDALF_ROOT/scripts/setup.sh" ] && [ -x "$GANDALF_ROOT/scripts/setup.sh" ]
    [ -f "$GANDALF_ROOT/scripts/install.sh" ] && [ -x "$GANDALF_ROOT/scripts/install.sh" ]
    [ -f "$GANDALF_ROOT/scripts/reset.sh" ] && [ -x "$GANDALF_ROOT/scripts/reset.sh" ]
    
    # Server files
    [ -d "$GANDALF_ROOT/server" ]
    [ -f "$GANDALF_ROOT/server/main.py" ] && [ -x "$GANDALF_ROOT/server/main.py" ]
}

# CONSOLIDATED: Core help commands (was 7 separate tests, now 3 essential ones)
@test "main help commands work" {
    run python3 "$GANDALF_ROOT/server/main.py" --help
    [ "$status" -eq 0 ] && echo "$output" | grep -q "Gandalf"
    
    run "$GANDALF_ROOT/gandalf.sh" help
    [ "$status" -eq 0 ] && echo "$output" | grep -q "Gandalf"
    
    run "$GANDALF_ROOT/gandalf.sh"
    [ "$status" -eq 0 ] && echo "$output" | grep -q "USAGE:"
}

@test "subcommand help works" {
    run "$GANDALF_ROOT/gandalf.sh" setup --help
    [ "$status" -eq 0 ] && echo "$output" | grep -q "Verify MCP server requirements"
    
    run "$GANDALF_ROOT/gandalf.sh" install --help
    [ "$status" -eq 0 ] && echo "$output" | grep -q "Configure MCP server"
}

@test "error handling works" {
    run python3 "$GANDALF_ROOT/server/main.py" --invalid-argument
    [ "$status" -eq 2 ]
    
    run "$GANDALF_ROOT/gandalf.sh" invalid-command
    [ "$status" -eq 1 ] && echo "$output" | grep -q "Unknown command"
}

# Core MCP Protocol Tests
@test "mcp protocol initialization works" {
    run execute_rpc "initialize" "{}"
    [ "$status" -eq 0 ] && echo "$output" | grep -q "protocolVersion"
}

@test "mcp tools list works" {
    run execute_rpc "tools/list" "{}"
    [ "$status" -eq 0 ] && echo "$output" | grep -q "tools"
}

@test "mcp invalid method fails gracefully" {
    run execute_rpc "invalid_method" "{}"
    [ "$status" -eq 0 ] && echo "$output" | grep -q "Method not found"
}

# Essential Tool Tests
@test "list project files tool works" {
    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ] && echo "$output" | grep -q "content"
}

@test "get project info tool works" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ] && echo "$output" | grep -q "content"
}

@test "get git status tool works" {
    run execute_rpc "tools/call" '{"name": "get_git_status", "arguments": {}}'
    [ "$status" -eq 0 ] && echo "$output" | grep -q "content"
}

@test "invalid tool call fails gracefully" {
    run execute_rpc "tools/call" '{"name": "non_existent_tool", "arguments": {}}'
    [ "$status" -eq 0 ] && echo "$output" | grep -q "Unknown tool"
}

# Performance Test
@test "server startup performance under 1 second" {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        start_time=$(python3 -c "import time; print(int(time.time() * 1000))")
        execute_rpc "initialize" "{}" >/dev/null 2>&1
        end_time=$(python3 -c "import time; print(int(time.time() * 1000))")
        startup_time=$((end_time - start_time))
    elif [[ "$OSTYPE" == "linux"* ]]; then
        start_time=$(date +%s%N)
        execute_rpc "initialize" "{}" >/dev/null 2>&1
        end_time=$(date +%s%N)
        startup_time=$(((end_time - start_time) / 1000000))
    else
        skip "Unsupported OS"
    fi

    # Should start in less than 1 second
    [ $startup_time -lt 1000 ]
} 