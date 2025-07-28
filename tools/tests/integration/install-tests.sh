#!/usr/bin/env bats
# Install Script Tests
# Tests for gandalf MCP server installation functionality

set -euo pipefail

load "$GANDALF_ROOT/tools/tests/test-helpers.sh"

create_tool_directories() {
    mkdir -p "$TEST_HOME/.cursor/rules"
    mkdir -p "$TEST_HOME/.claude"
    mkdir -p "$TEST_HOME/.windsurf"
    mkdir -p "$TEST_HOME/.gandalf"
    mkdir -p "$TEST_HOME/.gandalf/cache"
    mkdir -p "$TEST_HOME/.gandalf/exports"
    mkdir -p "$TEST_HOME/.gandalf/backups"
    mkdir -p "$TEST_HOME/.gandalf/config"
}

execute_install_command() {
    local args="$1"
    local spec_override="${2:-$TEST_SPEC_DIR}"

    HOME="$TEST_HOME" \
    GANDALF_HOME="$TEST_HOME/.gandalf" \
    GANDALF_SPEC_OVERRIDE="$spec_override" \
    "$GANDALF_ROOT/tools/bin/install" $args
}

validate_backup_created() {
    local backup_pattern="$1"
    local expected_content="$2"

    # Check for MCP config backups in .gandalf/backups directory
    local backup_files=("$TEST_HOME/.gandalf/backups/"${backup_pattern}*)
    [[ -f "${backup_files[0]}" ]] || return 1

    if [[ -n "$expected_content" ]]; then
        grep -q "$expected_content" "${backup_files[0]}" || return 1
    fi
}

validate_backup_count() {
    local backup_pattern="$1"
    local max_count="$2"

    local backup_files=("$TEST_HOME/.gandalf/backups/"${backup_pattern}*)
    local count=0

    for file in "${backup_files[@]}"; do
        [[ -f "$file" ]] && ((count++))
    done

    [[ "$count" -le "$max_count" ]] || return 1
}

validate_directory_structure() {
    # Check gandalf infrastructure directories (created by install script)
    [[ -d "$TEST_HOME/.gandalf" ]] || { echo "Missing: $TEST_HOME/.gandalf"; return 1; }
    [[ -d "$TEST_HOME/.gandalf/cache" ]] || { echo "Missing: $TEST_HOME/.gandalf/cache"; return 1; }
    [[ -d "$TEST_HOME/.gandalf/exports" ]] || { echo "Missing: $TEST_HOME/.gandalf/exports"; return 1; }
    [[ -d "$TEST_HOME/.gandalf/backups" ]] || { echo "Missing: $TEST_HOME/.gandalf/backups"; return 1; }
    [[ -d "$TEST_HOME/.gandalf/config" ]] || { echo "Missing: $TEST_HOME/.gandalf/config"; return 1; }
    [[ -d "$TEST_HOME/.gandalf/logs" ]] || { echo "Missing: $TEST_HOME/.gandalf/logs"; return 1; }
    
    # Check that tool directories are created by create-rules (called from install)
    [[ -d "$TEST_HOME/.cursor/rules" ]] || { echo "Missing: $TEST_HOME/.cursor/rules"; return 1; }
    [[ -d "$TEST_HOME/.claude" ]] || { echo "Missing: $TEST_HOME/.claude"; return 1; }
    [[ -d "$TEST_HOME/.windsurf" ]] || { echo "Missing: $TEST_HOME/.windsurf"; return 1; }
}

validate_installation_state() {
    local state_file="$TEST_HOME/.gandalf/installation-state"
    [[ -f "$state_file" ]] || return 1
    grep -q "GANDALF_ROOT=" "$state_file" || return 1
    grep -q "INSTALLATION_DATE=" "$state_file" || return 1
    grep -q "DETECTED_TOOL=" "$state_file" || return 1
}

validate_success_messages() {
    local output="$1"

    echo "$output" | grep -q "Installing for Cursor IDE" || return 1
    echo "$output" | grep -q "Installing for Claude Code" || return 1
    echo "$output" | grep -q "Installing for Windsurf IDE" || return 1
    echo "$output" | grep -q "Installation Summary" || return 1
}

setup() {
    shared_setup
    create_minimal_project

    TEST_SPEC_DIR="$TEST_HOME/spec"
    mkdir -p "$TEST_SPEC_DIR/rules"

    # Create spec files needed by create-rules script
    cat > "$TEST_SPEC_DIR/rules/core.md" << 'EOF'
---
description: Test Gandalf Rules Core
---
# Test Gandalf Rules for Install Test
Test core rules content for installation testing.
EOF

    cat > "$TEST_SPEC_DIR/rules/troubleshooting.md" << 'EOF'
---
description: Test troubleshooting rules
---
# Test Troubleshooting Rules
Test troubleshooting content for installation testing.
EOF

    export ORIGINAL_GANDALF_SPEC="$GANDALF_ROOT/spec"
}

teardown() {
    [[ -n "$TEST_SPEC_DIR" && -d "$TEST_SPEC_DIR" ]] && rm -rf "$TEST_SPEC_DIR"
    shared_teardown
}

# Basic functionality tests
@test "install script shows help message" {
    run execute_install_command "--help"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Configure global MCP server for Cursor, Claude Code, and Windsurf"
    echo "$output" | grep -q "\-\-force.*Force setup"
    echo "$output" | grep -q "\-\-tool.*Force specific agentic tool"
}

@test "install script handles invalid arguments" {
    run execute_install_command "--invalid-option"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
}

@test "install creates proper directory structure" {
    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_directory_structure
}

@test "install updates installation state with multi-tool results" {
    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_installation_state
}

@test "install reports success for multi-tool configuration" {
    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_success_messages "$output"
    echo "$output" | grep -q "Global MCP Configuration Complete"
    echo "$output" | grep -q "Primary tool:"
    echo "$output" | grep -q "Installation Type: Global"
}

@test "backup system creates organized backups" {
    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"existing": {}}}' > "$TEST_HOME/.cursor/mcp.json"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_backup_created "cursor-mcp.json.backup" ""
}

@test "backup cleanup removes old backups" {
    mkdir -p "$TEST_HOME/.gandalf/backups"

    for i in {1..7}; do
        echo '{}' > "$TEST_HOME/.gandalf/backups/cursor-mcp.json.backup.2024010${i}_120000"
    done

    local initial_count
    initial_count=$(find "$TEST_HOME/.gandalf/backups" -name "cursor-mcp.json.backup.*" | wc -l)
    [ "$initial_count" -eq 7 ]

    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"test": {}}}' > "$TEST_HOME/.cursor/mcp.json"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    # Should have 5 or fewer backups after cleanup
    local final_count
    final_count=$(find "$TEST_HOME/.gandalf/backups" -name "cursor-mcp.json.backup.*" | wc -l)
    [ "$final_count" -le 5 ]
}

@test "force flag clears cache directory" {
    create_tool_directories
    
    # Create some cache files
    echo "cache_file_1" > "$TEST_HOME/.gandalf/cache/test_cache_1.txt"
    echo "cache_file_2" > "$TEST_HOME/.gandalf/cache/test_cache_2.json" 
    mkdir -p "$TEST_HOME/.gandalf/cache/subdir"
    echo "nested_cache" > "$TEST_HOME/.gandalf/cache/subdir/nested.txt"
    
    # Verify cache files exist
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_1.txt" ]
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_2.json" ]
    [ -f "$TEST_HOME/.gandalf/cache/subdir/nested.txt" ]
    
    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]
    
    # Verify cache was cleared
    [ ! -f "$TEST_HOME/.gandalf/cache/test_cache_1.txt" ]
    [ ! -f "$TEST_HOME/.gandalf/cache/test_cache_2.json" ]
    [ ! -f "$TEST_HOME/.gandalf/cache/subdir/nested.txt" ]
    
    # Verify cache directory still exists but is empty
    [ -d "$TEST_HOME/.gandalf/cache" ]
    [ $(find "$TEST_HOME/.gandalf/cache" -type f | wc -l) -eq 0 ]
}

@test "install without force flag does not clear cache" {
    create_tool_directories
    
    # Create some cache files
    echo "cache_file_1" > "$TEST_HOME/.gandalf/cache/test_cache_1.txt"
    echo "cache_file_2" > "$TEST_HOME/.gandalf/cache/test_cache_2.json" 
    
    # Verify cache files exist
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_1.txt" ]
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_2.json" ]
    
    run execute_install_command "--skip-test"
    [ "$status" -eq 0 ]
    
    # Verify cache was NOT cleared
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_1.txt" ]
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_2.json" ]
}

@test "install handles missing create-rules script gracefully" {
    # Temporarily rename the create-rules script
    local create_rules_script="$GANDALF_ROOT/tools/bin/create-rules"
    local backup_script="$GANDALF_ROOT/tools/bin/create-rules.backup"
    
    mv "$create_rules_script" "$backup_script" 2>/dev/null || true

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]
    
    echo "$output" | grep -q "create-rules script not found"
    echo "$output" | grep -q "Skipping rules file creation"

    # Restore the script
    mv "$backup_script" "$create_rules_script" 2>/dev/null || true
}
