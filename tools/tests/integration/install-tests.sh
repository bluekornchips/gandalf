#!/usr/bin/env bats
# Install Script Tests
# Tests for gandalf install functionality and multi-tool rules creation

set -euo pipefail

load '../../lib/test-helpers.sh'


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

create_existing_rules_files() {
    local cursor_content="${1:-# Existing Cursor Rules}"
    local claude_content="${2:-{\"gandalfRules\": \"existing rules\"}}"
    local windsurf_content="${3:-# Existing Windsurf Rules}"

    create_tool_directories
    echo "$cursor_content" > "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    echo "$claude_content" > "$TEST_HOME/.claude/global_settings.json"
    echo "$windsurf_content" > "$TEST_HOME/.windsurf/global_rules.md"
}

validate_rules_file_exists() {
    local tool="$1"
    local expected_content="$2"

    case "$tool" in
        "cursor")
            [[ -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]] || return 1
            grep -q "$expected_content" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" || return 1
            ;;
        "claude")
            [[ -f "$TEST_HOME/.claude/global_settings.json" ]] || return 1
            grep -q "$expected_content" "$TEST_HOME/.claude/global_settings.json" || return 1
            ;;
        "windsurf")
            [[ -f "$TEST_HOME/.windsurf/global_rules.md" ]] || return 1
            grep -q "$expected_content" "$TEST_HOME/.windsurf/global_rules.md" || return 1
            ;;
        *)
            return 1
            ;;
    esac
}

validate_rules_file_absent() {
    local tool="$1"
    local content="$2"

    case "$tool" in
        "cursor")
            ! grep -q "$content" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" 2>/dev/null || return 1
            ;;
        "claude")
            ! grep -q "$content" "$TEST_HOME/.claude/global_settings.json" 2>/dev/null || return 1
            ;;
        "windsurf")
            ! grep -q "$content" "$TEST_HOME/.windsurf/global_rules.md" 2>/dev/null || return 1
            ;;
        *)
            return 1
            ;;
    esac
}

validate_claude_json_format() {
    local json_file="$TEST_HOME/.claude/global_settings.json"

    [[ -f "$json_file" ]] || return 1
    jq empty "$json_file" || return 1
    jq -e '.permissions' "$json_file" >/dev/null || return 1
    jq -e '.gandalfRules' "$json_file" >/dev/null || return 1
}

validate_claude_json_content() {
    local json_file="$TEST_HOME/.claude/global_settings.json"
    local expected_content="$1"

    validate_claude_json_format || return 1
    jq -r '.gandalfRules' "$json_file" | grep -q "$expected_content" || return 1
}

validate_backup_created() {
    local backup_pattern="$1"
    local expected_content="$2"

    # Check for Claude backups in .claude directory
    if [[ "$backup_pattern" == "global_settings.json.backup" ]]; then
        local backup_files=("$TEST_HOME/.claude/"${backup_pattern}*)
        [[ -f "${backup_files[0]}" ]] || return 1

        if [[ -n "$expected_content" ]]; then
            grep -q "$expected_content" "${backup_files[0]}" || return 1
        fi
    else
        # Check for other backups in .gandalf/backups directory
        local backup_files=("$TEST_HOME/.gandalf/backups/"${backup_pattern}*)
        [[ -f "${backup_files[0]}" ]] || return 1

        if [[ -n "$expected_content" ]]; then
            grep -q "$expected_content" "${backup_files[0]}" || return 1
        fi
    fi
}

validate_backup_count() {
    local backup_pattern="$1"
    local max_count="$2"

    # Check for Claude backups in .claude directory
    if [[ "$backup_pattern" == "global_settings.json.backup" ]]; then
        local backup_files=("$TEST_HOME/.claude/"${backup_pattern}*)
        local count=0

        for file in "${backup_files[@]}"; do
            [[ -f "$file" ]] && ((count++))
        done

        [[ "$count" -le "$max_count" ]] || return 1
    else
        # Check for other backups in .gandalf/backups directory
        local backup_files=("$TEST_HOME/.gandalf/backups/"${backup_pattern}*)
        local count=0

        for file in "${backup_files[@]}"; do
            [[ -f "$file" ]] && ((count++))
        done

        [[ "$count" -le "$max_count" ]] || return 1
    fi
}

validate_windsurf_truncation() {
    local windsurf_file="$TEST_HOME/.windsurf/global_rules.md"
    local max_chars="$1"

    [[ -f "$windsurf_file" ]] || return 1

    local char_coun
    char_count=$(wc -c < "$windsurf_file")

    [[ "$char_count" -le "$max_chars" ]] || return 1
    grep -q "Content truncated to fit Windsurf" "$windsurf_file" || return 1
}

validate_installation_state() {
    local state_file="$TEST_HOME/.gandalf/installation-state"

    [[ -f "$state_file" ]] || return 1
    grep -q "CURSOR_INSTALLED=" "$state_file" || return 1
    grep -q "CLAUDE_CODE_INSTALLED=" "$state_file" || return 1
    grep -q "WIND_SURF_INSTALLED=" "$state_file" || return 1
    grep -q "INSTALL_ALL_TOOLS=true" "$state_file" || return 1
}

validate_success_messages() {
    local output="$1"

    echo "$output" | grep -q "Installing for Cursor IDE" || return 1
    echo "$output" | grep -q "Installing for Claude Code" || return 1
    echo "$output" | grep -q "Installing for Windsurf IDE" || return 1
    echo "$output" | grep -q "Global Rules Files Created" || return 1
    echo "$output" | grep -q "Cursor:.*gandalf-rules.mdc" || return 1
    echo "$output" | grep -q "Claude Code:.*global_settings.json" || return 1
    echo "$output" | grep -q "Windsurf:.*global_rules.md" || return 1
}

validate_directory_structure() {
    [[ -d "$TEST_HOME/.cursor/rules" ]] || return 1
    [[ -d "$TEST_HOME/.claude" ]] || return 1
    [[ -d "$TEST_HOME/.windsurf" ]] || return 1
    [[ -d "$TEST_HOME/.gandalf" ]] || return 1
    [[ -d "$TEST_HOME/.gandalf/cache" ]] || return 1
    [[ -d "$TEST_HOME/.gandalf/exports" ]] || return 1
    [[ -d "$TEST_HOME/.gandalf/backups" ]] || return 1
    [[ -d "$TEST_HOME/.gandalf/config" ]] || return 1
}

execute_install_command() {
    local flags="$1"
    local spec_override="${2:-$TEST_SPEC_DIR}"

    if [[ -n "$spec_override" ]]; then
        bash -c "GANDALF_SPEC_OVERRIDE='$spec_override' bash '$GANDALF_ROOT/tools/bin/install' $flags"
    else
        bash "$GANDALF_ROOT/tools/bin/install" $flags
    fi
}

setup() {
    shared_setup
    create_minimal_project

    TEST_SPEC_DIR="$TEST_HOME/spec"
    mkdir -p "$TEST_SPEC_DIR"

    export ORIGINAL_GANDALF_SPEC="$GANDALF_ROOT/spec"
}

teardown() {
    [[ -n "$TEST_SPEC_DIR" && -d "$TEST_SPEC_DIR" ]] && rm -rf "$TEST_SPEC_DIR"
    shared_teardown
}

create_test_rules_file() {
    local content="${1:-# Default Test Gandalf Rules for multi-tool validation}"

    mkdir -p "$TEST_SPEC_DIR/rules"

    local test_workflows_file="$TEST_SPEC_DIR/rules/core.md"
    local test_troubleshooting_file="$TEST_SPEC_DIR/rules/troubleshooting.md"

    cat > "$test_workflows_file" << EOF
---
description: Test Gandalf Rules Core
---
# Test Gandalf Rules Core
$content
EOF

    cat > "$test_troubleshooting_file" << 'EOF'
---
description: APPLY WHEN encountering errors, failures, debugging issues, or troubleshooting problems
globs:
alwaysApply: false
---
# Test Gandalf Rules Troubleshooting
Test troubleshooting documentation.
EOF

    export TEST_RULES_FILE="$test_workflows_file"
    export GANDALF_SPEC_OVERRIDE="$TEST_SPEC_DIR"
}

@test "install script shows help message" {
    run bash "$GANDALF_ROOT/tools/bin/install" --help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage: ./gandalf install"
    echo "$output" | grep -q "Configure global MCP server for Cursor, Claude Code, and Windsurf"
    echo "$output" | grep -q -- "--force"
    echo "$output" | grep -q -- "--tool"
}

@test "install script handles invalid arguments" {
    run bash "$GANDALF_ROOT/tools/bin/install" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
    echo "$output" | grep -q "Usage:"
}

@test "install creates rules for all supported tools" {
    create_test_rules_file "# Test Gandalf Rules - This is a test rules file for multi-tool validation."

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "Test Gandalf Rules"
    validate_rules_file_exists "claude" "gandalfRules"
    validate_rules_file_exists "windsurf" "Test Gandalf Rules"
}

@test "install respects existing rules when not forced" {
    create_existing_rules_files

    create_test_rules_file "# New Rules"

    run execute_install_command "--skip-test"
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "Existing Cursor Rules"
    validate_rules_file_exists "claude" "existing rules"
    validate_rules_file_exists "windsurf" "Existing Windsurf Rules"

    validate_rules_file_absent "cursor" "New Rules"
}

@test "install overwrites rules when forced" {
    create_existing_rules_files

    create_test_rules_file "# New Forced Rules"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "New Forced Rules"
    validate_rules_file_exists "claude" "New Forced Rules"
    validate_rules_file_exists "windsurf" "New Forced Rules"
}

@test "install handles large rules file for windsurf truncation" {
    local large_content=""
    for i in {1..200}; do
        large_content+="# Large Rules File Line $i - This is a very long line with lots of content to make it exceed the 6000 character limit for Windsurf rules files. "
    done

    create_test_rules_file "$large_content"

    local char_coun
    char_count=$(wc -c < "$TEST_RULES_FILE")
    [ "$char_count" -gt 6000 ]

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "Large Rules File"
    local cursor_char_coun
    cursor_char_count=$(wc -c < "$TEST_HOME/.cursor/rules/gandalf-rules.mdc")
    [ "$cursor_char_count" -gt 6000 ]

    validate_windsurf_truncation 6000
}

@test "install creates proper claude code settings format" {
    create_test_rules_file $'# Test Rules\n- Rule with "quotes" in it\n- Rule with backslashes in it\n- Rule with \nnewlines in it'

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_claude_json_format
    validate_claude_json_content "quotes"
    validate_claude_json_content "backslashes"
    validate_claude_json_content "newlines"
}

@test "install creates windsurf global rules with correct content" {
    create_test_rules_file "# Test Rules, this is test content for Windsurf rules validation."

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_rules_file_exists "windsurf" "Test Rules"
    validate_rules_file_exists "windsurf" "Windsurf rules validation"
}

@test "install backs up existing claude code settings" {
    create_tool_directories

    cat > "$TEST_HOME/.claude/global_settings.json" << 'EOF'
{
  "existingSetting": "value",
  "otherConfig": true
}
EOF

    create_test_rules_file "# Test Rules"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_backup_created "global_settings.json.backup" "existingSetting"
    validate_rules_file_exists "claude" "gandalfRules"
}

@test "install reports success for multi-tool configuration" {
    create_test_rules_file "# Test Rules"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_success_messages "$output"
}

@test "install handles missing source rules file gracefully" {
    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    echo "$output" | grep -q "No rules files found"
    echo "$output" | grep -q "Skipping rules file creation"
}

@test "install creates proper directory structure" {
    create_test_rules_file "# Test Rules"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_directory_structure
}

@test "install updates installation state with multi-tool results" {
    create_test_rules_file "# Test Rules"

    run execute_install_command "--force --skip-test"
    [ "$status" -eq 0 ]

    validate_installation_state
}

@test "backup system creates organized backups" {
    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"existing": {}}}' > "$TEST_HOME/.cursor/mcp.json"

    run execute_install_command "--force --skip-test" ""
    [ "$status" -eq 0 ]

    validate_backup_created "cursor-mcp.json.backup" ""
}

@test "backup cleanup removes old backups" {
    mkdir -p "$TEST_HOME/.gandalf/backups"

    for i in {1..7}; do
        echo '{}' > "$TEST_HOME/.gandalf/backups/cursor-mcp.json.backup.2024010${i}_120000"
    done

    local initial_coun
    initial_count=$(find "$TEST_HOME/.gandalf/backups" -name "cursor-mcp.json.backup.*" | wc -l)
    [ "$initial_count" -eq 7 ]

    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"test": {}}}' > "$TEST_HOME/.cursor/mcp.json"

    run execute_install_command "--force --skip-test" ""
    [ "$status" -eq 0 ]

    # Should have 5 or fewer backups after cleanup
    local final_coun
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
    
    run execute_install_command "--force --skip-test" ""
    [ "$status" -eq 0 ]
    
    # Cache directory should exist but be empty
    [ -d "$TEST_HOME/.gandalf/cache" ]
    local cache_files_count
    cache_files_count=$(find "$TEST_HOME/.gandalf/cache" -type f | wc -l)
    [ "$cache_files_count" -eq 0 ]
    
    # Verify cache clearing was logged
    echo "$output" | grep -q "Clearing cache directory"
    echo "$output" | grep -q "Cache cleared successfully"
}

@test "install without force flag does not clear cache" {
    create_tool_directories
    
    # Create some cache files
    echo "cache_file_1" > "$TEST_HOME/.gandalf/cache/test_cache_1.txt"
    echo "cache_file_2" > "$TEST_HOME/.gandalf/cache/test_cache_2.json"
    
    # Verify cache files exist
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_1.txt" ]
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_2.json" ]
    
    run execute_install_command "--skip-test" ""
    [ "$status" -eq 0 ]
    
    # Cache files should still exist
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_1.txt" ]
    [ -f "$TEST_HOME/.gandalf/cache/test_cache_2.json" ]
    
    # Verify cache clearing was NOT logged
    ! echo "$output" | grep -q "Clearing cache directory"
}
