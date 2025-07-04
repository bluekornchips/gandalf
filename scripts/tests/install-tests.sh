#!/usr/bin/env bats
# Install Script Tests
# Tests for gandalf install functionality and multi-tool rules creation

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

setup() {
    shared_setup
    create_minimal_project

    # Create a temporary spec directory in the test environment
    TEST_SPEC_DIR="$TEST_HOME/spec"
    mkdir -p "$TEST_SPEC_DIR"

    # Override GANDALF_ROOT spec directory for tests to use temp location
    export ORIGINAL_GANDALF_SPEC="$GANDALF_ROOT/spec"

    # Create a temporary symlink or modify the install script's behavior
    # For now, we'll create test rules files in the temp location
    TEST_RULES_FILE="$TEST_SPEC_DIR/gandalf-rules.md"
}

teardown() {
    # Clean up any temporary files we created
    [[ -n "$TEST_SPEC_DIR" && -d "$TEST_SPEC_DIR" ]] && rm -rf "$TEST_SPEC_DIR"
    shared_teardown
}

# Helper function to create test rules file and modify script behavior
create_test_rules_file() {
    local content="${1:-# Default Test Gandalf Rules
This is a test rules file for multi-tool validation.}"

    echo "$content" >"$TEST_RULES_FILE"

    # Temporarily replace the spec directory path in the install script
    # by setting an environment variable that the script can check
    export GANDALF_SPEC_OVERRIDE="$TEST_SPEC_DIR"
}

@test "install script shows help message" {
    run bash "$GANDALF_ROOT/scripts/install.sh" --help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage: gandalf.sh install"
    echo "$output" | grep -q "Configure global MCP server for Cursor, Claude Code, and Windsurf"
    echo "$output" | grep -q -- "--force"
    echo "$output" | grep -q -- "--reset"
    echo "$output" | grep -q -- "--tool"
}

@test "install script handles invalid arguments" {
    run bash "$GANDALF_ROOT/scripts/install.sh" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
    echo "$output" | grep -q "Usage:"
}

@test "install creates rules for all supported tools" {
    # Create test rules file in temp location
    create_test_rules_file "# Test Gandalf Rules
This is a test rules file for multi-tool validation."

    # Run install with force to ensure rules creation, using temp rules file
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify Cursor global rules were created
    [ -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]
    grep -q "Test Gandalf Rules" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"

    # Verify Claude Code global rules were created in settings
    [ -f "$TEST_HOME/.claude/global_settings.json" ]
    grep -q "gandalfRules" "$TEST_HOME/.claude/global_settings.json"

    # Verify Windsurf global rules were created
    [ -f "$TEST_HOME/.windsurf/global_rules.md" ]
    grep -q "Test Gandalf Rules" "$TEST_HOME/.windsurf/global_rules.md"
}

@test "install respects existing rules when not forced" {
    # Create existing global rules files
    mkdir -p "$TEST_HOME/.cursor/rules"
    mkdir -p "$TEST_HOME/.claude"
    mkdir -p "$TEST_HOME/.windsurf"

    echo "# Existing Cursor Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    echo '{"gandalfRules": "existing rules"}' >"$TEST_HOME/.claude/global_settings.json"
    echo "# Existing Windsurf Rules" >"$TEST_HOME/.windsurf/global_rules.md"

    # Create test rules file
    create_test_rules_file "# New Rules"

    # Run install without force
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --skip-test"
    [ "$status" -eq 0 ]

    # Verify existing rules were preserved
    grep -q "Existing Cursor Rules" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    grep -q "existing rules" "$TEST_HOME/.claude/global_settings.json"
    grep -q "Existing Windsurf Rules" "$TEST_HOME/.windsurf/global_rules.md"

    # Verify new rules were NOT applied
    ! grep -q "New Rules" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
}

@test "install overwrites rules when forced" {
    # Create existing global rules files
    mkdir -p "$TEST_HOME/.cursor/rules"
    mkdir -p "$TEST_HOME/.claude"
    mkdir -p "$TEST_HOME/.windsurf"

    echo "# Existing Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    echo '{"gandalfRules": "existing rules"}' >"$TEST_HOME/.claude/global_settings.json"
    echo "# Existing Rules" >"$TEST_HOME/.windsurf/global_rules.md"

    # Create test rules file
    create_test_rules_file "# New Forced Rules"

    # Run install with force
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify rules were overwritten
    grep -q "New Forced Rules" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    grep -q "New Forced Rules" "$TEST_HOME/.claude/global_settings.json"
    grep -q "New Forced Rules" "$TEST_HOME/.windsurf/global_rules.md"
}

@test "install handles large rules file for windsurf truncation" {
    # Create a large rules file (over 6000 characters) in temp location
    large_content=""
    for i in {1..200}; do
        large_content+="# Large Rules File Line $i - This is a very long line with lots of content to make it exceed the 6000 character limit for Windsurf rules files. "
    done

    create_test_rules_file "$large_content"

    # Verify the file is over 6000 characters
    char_count=$(wc -c <"$TEST_RULES_FILE")
    [ "$char_count" -gt 6000 ]

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify Cursor and Claude Code get full content
    [ -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]
    cursor_char_count=$(wc -c <"$TEST_HOME/.cursor/rules/gandalf-rules.mdc")
    [ "$cursor_char_count" -gt 6000 ]

    # Verify Windsurf gets truncated content
    [ -f "$TEST_HOME/.windsurf/global_rules.md" ]
    windsurf_char_count=$(wc -c <"$TEST_HOME/.windsurf/global_rules.md")

    # Since we created a file over 6000 chars, Windsurf should be truncated
    [ "$windsurf_char_count" -le 6000 ]

    # Should contain truncation message
    grep -q "Content truncated to fit Windsurf" "$TEST_HOME/.windsurf/global_rules.md"
}

@test "install creates proper claude code settings format" {
    # Create test rules file with special characters
    create_test_rules_file '# Test Rules
- Rule with "quotes" in it
- Rule with backslashes in it
- Rule with 
newlines in it'

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify Claude Code global settings.json exists and is valid JSON
    [ -f "$TEST_HOME/.claude/global_settings.json" ]

    # Use jq to validate JSON instead of Python (more reliable in test environment)
    jq empty "$TEST_HOME/.claude/global_settings.json"

    # Verify it contains the expected structure
    jq -e '.permissions' "$TEST_HOME/.claude/global_settings.json" >/dev/null
    jq -e '.gandalfRules' "$TEST_HOME/.claude/global_settings.json" >/dev/null

    # Verify the rules content is properly escaped in JSON
    jq -r '.gandalfRules' "$TEST_HOME/.claude/global_settings.json" | grep -q "quotes"
    jq -r '.gandalfRules' "$TEST_HOME/.claude/global_settings.json" | grep -q "backslashes"
    jq -r '.gandalfRules' "$TEST_HOME/.claude/global_settings.json" | grep -q "newlines"
}

@test "install creates windsurf global rules with correct content" {
    # Create test rules file
    create_test_rules_file "# Test Rules
This is test content for Windsurf rules validation."

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify Windsurf global rules file exists
    [ -f "$TEST_HOME/.windsurf/global_rules.md" ]

    # Verify content matches source
    grep -q "Test Rules" "$TEST_HOME/.windsurf/global_rules.md"
    grep -q "Windsurf rules validation" "$TEST_HOME/.windsurf/global_rules.md"
}

@test "install backs up existing claude code settings" {
    # Create existing Claude Code global settings
    mkdir -p "$TEST_HOME/.claude"
    cat >"$TEST_HOME/.claude/global_settings.json" <<'EOF'
{
  "existingSetting": "value",
  "otherConfig": true
}
EOF

    # Create test rules file
    create_test_rules_file "# Test Rules"

    # Run install with force
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify backup was created
    backup_files=("$TEST_HOME/.claude/global_settings.json.backup."*)
    [ -f "${backup_files[0]}" ]

    # Verify backup contains original content
    grep -q "existingSetting" "${backup_files[0]}"

    # Verify new settings contain gandalf rules
    grep -q "gandalfRules" "$TEST_HOME/.claude/global_settings.json"
}

@test "install reports success for multi-tool configuration" {
    # Create test rules file
    create_test_rules_file "# Test Rules"

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify success messages for all tools
    echo "$output" | grep -q "Installing for Cursor IDE"
    echo "$output" | grep -q "Installing for Claude Code"
    echo "$output" | grep -q "Installing for Windsurf IDE"
    echo "$output" | grep -q "Global Rules Files Created"
    echo "$output" | grep -q "Cursor:.*gandalf-rules.mdc"
    echo "$output" | grep -q "Claude Code:.*global_settings.json"
    echo "$output" | grep -q "Windsurf:.*global_rules.md"
}

@test "install handles missing source rules file gracefully" {
    # Ensure no source rules file exists by not creating one
    # The TEST_RULES_FILE won't exist, simulating missing source file

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify warning messages for missing source file
    echo "$output" | grep -q "Source rules file not found"
    echo "$output" | grep -q "Skipping rules file creation"
}

@test "install creates proper directory structure" {
    # Create test rules file
    create_test_rules_file "# Test Rules"

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify all required global directories were created
    [ -d "$TEST_HOME/.cursor/rules" ]
    [ -d "$TEST_HOME/.claude" ]
    [ -d "$TEST_HOME/.windsurf" ]
    [ -d "$TEST_HOME/.gandalf" ]
    [ -d "$TEST_HOME/.gandalf/cache" ]
    [ -d "$TEST_HOME/.gandalf/exports" ]
    [ -d "$TEST_HOME/.gandalf/backups" ]
    [ -d "$TEST_HOME/.gandalf/config" ]
}

@test "install updates installation state with multi-tool results" {
    # Create test rules file
    create_test_rules_file "# Test Rules"

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify installation state file exists and contains multi-tool results
    [ -f "$TEST_HOME/.gandalf/installation-state" ]
    grep -q "CURSOR_INSTALLED=" "$TEST_HOME/.gandalf/installation-state"
    grep -q "CLAUDE_CODE_INSTALLED=" "$TEST_HOME/.gandalf/installation-state"
    grep -q "WIND_SURF_INSTALLED=" "$TEST_HOME/.gandalf/installation-state"
    grep -q "INSTALL_ALL_TOOLS=true" "$TEST_HOME/.gandalf/installation-state"
}

@test "backup system creates organized backups" {
    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"existing": {}}}' >"$TEST_HOME/.cursor/mcp.json"

    run bash "$GANDALF_ROOT/scripts/install.sh" --force --skip-test
    [ "$status" -eq 0 ]

    [ -d "$TEST_HOME/.gandalf/backups" ]
    local backups=($(find "$TEST_HOME/.gandalf/backups" -name "cursor-mcp.json.backup.*" 2>/dev/null))
    [ ${#backups[@]} -ge 1 ]
}

@test "backup cleanup removes old backups" {
    mkdir -p "$TEST_HOME/.gandalf/backups"

    # Create 7 old backups
    for i in {1..7}; do
        echo '{}' >"$TEST_HOME/.gandalf/backups/cursor-mcp.json.backup.2024010${i}_120000"
    done

    # Verify we have 7 files
    local initial_count=$(find "$TEST_HOME/.gandalf/backups" -name "cursor-mcp.json.backup.*" | wc -l)
    [ "$initial_count" -eq 7 ]

    # Test that cleanup function exists by running install (which calls cleanup)
    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"test": {}}}' >"$TEST_HOME/.cursor/mcp.json"

    run bash "$GANDALF_ROOT/scripts/install.sh" --force --skip-test
    [ "$status" -eq 0 ]

    # Should have 5 or fewer backups after cleanup
    local final_count=$(find "$TEST_HOME/.gandalf/backups" -name "cursor-mcp.json.backup.*" | wc -l)
    [ "$final_count" -le 5 ]
}
