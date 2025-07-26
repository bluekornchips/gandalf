#!/usr/bin/env bash

BATS_TEST_NAME_PREFIX="[setup]"
BATS_TEST_DESCRIPTION="Gandalf setup script tests"

# Test data files
TEST_DATA_DIR="$(dirname "$BATS_TEST_DIRNAME")/fixtures/data"
TEST_VERSION_FILE="$TEST_DATA_DIR/test_version.txt"

load_test_helpers() {
    local test_helpers_path="$BATS_TEST_DIRNAME/../tools/lib/test-helpers.sh"
    if [[ -f "$test_helpers_path" ]]; then
        source "$test_helpers_path"
    fi
}

setup_file() {
    load_test_helpers
    
    # Create test version file
    mkdir -p "$TEST_DATA_DIR"
    echo "2.5.0" > "$TEST_VERSION_FILE"
}

setup() {
    # Create temporary directory for tests
    export TEST_TEMP_DIR=$(mktemp -d)
    export GANDALF_HOME="$TEST_TEMP_DIR/.gandalf"
    
    # Mock GANDALF_ROOT
    export GANDALF_ROOT="$TEST_TEMP_DIR/gandalf"
    mkdir -p "$GANDALF_ROOT"
    
    # Create VERSION file
    echo "2.5.0" > "$GANDALF_ROOT/VERSION"
    
    # Source the setup script functions
    source "$BATS_TEST_DIRNAME/../../bin/setup"
}

teardown() {
    rm -rf "$TEST_TEMP_DIR"
}

teardown_file() {
    rm -f "$TEST_VERSION_FILE"
}

@test "get_version returns correct version from VERSION file" {
    result=$(_get_version)
    [[ "$result" == "2.5.0" ]]
}

@test "get_version returns default when VERSION file missing" {
    rm -f "$GANDALF_ROOT/VERSION"
    result=$(_get_version)
    [[ "$result" == "2.5.0" ]]
}

@test "create_gandalf_directory creates required directories" {
    create_gandalf_directory
    
    [[ -d "$GANDALF_HOME" ]]
    [[ -d "$GANDALF_HOME/cache" ]]
    [[ -d "$GANDALF_HOME/exports" ]]
    [[ -d "$GANDALF_HOME/backups" ]]
    [[ -d "$GANDALF_HOME/config" ]]
}

@test "create_gandalf_directory sets proper permissions" {
    create_gandalf_directory
    
    # Check directory permissions (755)
    local perms=$(stat -c '%a' "$GANDALF_HOME" 2>/dev/null || stat -f '%OLp' "$GANDALF_HOME")
    [[ "$perms" == "755" ]]
}

@test "ensure_gandalf_directory creates directory if missing" {
    [[ ! -d "$GANDALF_HOME" ]]
    
    ensure_gandalf_directory
    
    [[ -d "$GANDALF_HOME" ]]
    [[ -d "$GANDALF_HOME/cache" ]]
}

@test "ensure_gandalf_directory verifies existing directory" {
    mkdir -p "$GANDALF_HOME"
    
    run ensure_gandalf_directory
    
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "Verified.*directory structure"
}

@test "create_installation_state creates state file" {
    create_installation_state
    
    [[ -f "$GANDALF_HOME/installation-state" ]]
}

@test "create_installation_state includes correct values" {
    create_installation_state
    
    local state_file="$GANDALF_HOME/installation-state"
    
    grep -q "GANDALF_ROOT=\"$GANDALF_ROOT\"" "$state_file"
    grep -q "GANDALF_VERSION=\"2.5.0\"" "$state_file"
    grep -q "CURSOR_INSTALLED=false" "$state_file"
    grep -q "CLAUDE_CODE_INSTALLED=false" "$state_file"
}

@test "update_installation_state creates state file if missing" {
    CURSOR_SETUP_SUCCESS=true
    CLAUDE_CODE_SETUP_SUCCESS=false
    
    update_installation_state
    
    [[ -f "$GANDALF_HOME/installation-state" ]]
}

@test "update_installation_state updates values" {
    create_installation_state
    
    CURSOR_SETUP_SUCCESS=true
    CLAUDE_CODE_SETUP_SUCCESS=false
    
    update_installation_state
    
    local state_file="$GANDALF_HOME/installation-state"
    grep -q "CURSOR_INSTALLED=true" "$state_file"
    grep -q "CLAUDE_CODE_INSTALLED=false" "$state_file"
}

@test "load_installation_state loads variables" {
    create_installation_state
    
    # Clear variables
    unset GANDALF_ROOT GANDALF_VERSION CURSOR_INSTALLED CLAUDE_CODE_INSTALLED
    
    load_installation_state
    
    [[ "$GANDALF_ROOT" == "$TEST_TEMP_DIR/gandalf" ]]
    [[ "$GANDALF_VERSION" == "2.5.0" ]]
    [[ "$CURSOR_INSTALLED" == "false" ]]
    [[ "$CLAUDE_CODE_INSTALLED" == "false" ]]
}

@test "show_subdir_info shows correct info for existing directory" {
    mkdir -p "$GANDALF_HOME/cache"
    touch "$GANDALF_HOME/cache/test1.txt"
    touch "$GANDALF_HOME/cache/test2.txt"
    
    run show_subdir_info "cache" "$GANDALF_HOME"
    
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "cache/:"
    echo "$output" | grep -q "(2 files)"
}

@test "show_subdir_info shows not found for missing directory" {
    run show_subdir_info "missing" "$GANDALF_HOME"
    
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "missing/: Not found"
}

@test "detect_agentic_tool_availability detects cursor" {
    # Mock cursor config directory
    mkdir -p "$HOME/.cursor"
    
    detect_agentic_tool_availability
    
    [[ "$CURSOR_AVAILABLE" == "true" ]]
}

@test "detect_agentic_tool_availability detects claude code" {
    # Mock claude config directory
    mkdir -p "$HOME/.claude"
    
    detect_agentic_tool_availability
    
    [[ "$CLAUDE_CODE_AVAILABLE" == "true" ]]
}

@test "setup_cursor fails when cursor not available" {
    CURSOR_AVAILABLE=false
    
    run setup_cursor "test-server" "$GANDALF_ROOT"
    
    [[ "$status" -eq 1 ]]
    echo "$output" | grep -q "Skipping Cursor setup"
}

@test "setup_cursor creates config when cursor available" {
    CURSOR_AVAILABLE=true
    mkdir -p "$HOME/.cursor"
    
    # Mock jq command
    jq() {
        echo '{"mcpServers": {"test-server": {"command": "test", "args": ["run"]}}}'
    }
    export -f jq
    
    run setup_cursor "test-server" "$GANDALF_ROOT"
    
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "Cursor IDE setup completed"
}

@test "setup_claude_code fails when claude code not available" {
    CLAUDE_CODE_AVAILABLE=false
    
    run setup_claude_code "test-server" "$GANDALF_ROOT"
    
    [[ "$status" -eq 1 ]]
    echo "$output" | grep -q "Skipping Claude Code setup"
}

@test "setup_claude_code creates config when claude code available" {
    CLAUDE_CODE_AVAILABLE=true
    mkdir -p "$HOME/.claude"
    
    # Mock jq command
    jq() {
        echo '{"mcpServers": {"test-server": {"command": "test", "args": ["run"]}}}'
    }
    export -f jq
    
    run setup_claude_code "test-server" "$GANDALF_ROOT"
    
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "Claude Code setup completed"
}

@test "parse_args handles help option" {
    run parse_args --help
    
    [[ "$status" -eq 0 ]]
}

@test "parse_args handles info option" {
    run parse_args --info
    
    [[ "$status" -eq 0 ]]
}

@test "parse_args handles invalid option" {
    run parse_args --invalid
    
    [[ "$status" -eq 1 ]]
    echo "$output" | grep -q "Unknown option"
}

@test "parse_args validates directory option" {
    run parse_args --directory "/nonexistent/path"
    
    [[ "$status" -eq 1 ]]
    echo "$output" | grep -q "does not exist"
}

@test "main function executes without errors" {
    # Mock successful setup
    CURSOR_AVAILABLE=false
    CLAUDE_CODE_AVAILABLE=false
    
    run main
    
    [[ "$status" -eq 0 ]]
    echo "$output" | grep -q "Setup Summary"
} 