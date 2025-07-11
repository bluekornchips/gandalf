#!/usr/bin/env bats
# Install Script Tests
# Tests for gandalf install functionality and multi-tool rules creation

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

setup() {
    shared_setup
    create_minimal_project

    # Create a temporary directory for spec files
    TEST_SPEC_DIR="$TEST_HOME/spec"
    mkdir -p "$TEST_SPEC_DIR"

    # Override GANDALF_ROOT spec directory for tests to use temp location
    export ORIGINAL_GANDALF_SPEC="$GANDALF_ROOT/spec"

    # Create test project directory for local installations
    TEST_PROJECT_DIR="$TEST_HOME/test-project"
    mkdir -p "$TEST_PROJECT_DIR"
}

teardown() {
    # Clean up any temporary files we created
    [[ -n "$TEST_SPEC_DIR" && -d "$TEST_SPEC_DIR" ]] && rm -rf "$TEST_SPEC_DIR"
    [[ -n "$TEST_PROJECT_DIR" && -d "$TEST_PROJECT_DIR" ]] && rm -rf "$TEST_PROJECT_DIR"
    shared_teardown
}

# Helper function to create test rules file and modify script behavior
create_test_rules_file() {
    local content="${1:-# Default Test Gandalf Rules for multi-tool validation}"

    mkdir -p "$TEST_SPEC_DIR/rules"

    # Create the split files for the new structure
    local test_workflows_file="$TEST_SPEC_DIR/rules/core.md"
    local test_troubleshooting_file="$TEST_SPEC_DIR/rules/troubleshooting.md"

    # Create minimal split files for testing
    cat >"$test_workflows_file" <<EOF
---
description: Test Gandalf Rules Core
---
# Test Gandalf Rules Core
$content
EOF

    cat >"$test_troubleshooting_file" <<'EOF'
---
description: APPLY WHEN encountering errors, failures, debugging issues, or troubleshooting problems
globs:
alwaysApply: false
---
# Test Gandalf Rules Troubleshooting  
Test troubleshooting documentation.
EOF

    # Set the TEST_RULES_FILE variable for tests that need it
    export TEST_RULES_FILE="$test_workflows_file"

    # Temporarily replace the spec directory path in the install script
    # by setting an environment variable that the script can check
    export GANDALF_SPEC_OVERRIDE="$TEST_SPEC_DIR"
}

@test "install script shows help message" {
    run bash "$GANDALF_ROOT/scripts/install.sh" --help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage: gandalf.sh install"
    echo "$output" | grep -q "Configure MCP server for Cursor, Claude Code, and Windsurf"
    echo "$output" | grep -q -- "--force"
    echo "$output" | grep -q -- "--local"
}

@test "install script handles invalid arguments" {
    run bash "$GANDALF_ROOT/scripts/install.sh" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
    echo "$output" | grep -q "Usage:"
}

@test "install creates rules for all supported tools" {
    # Create test rules file in temp location
    create_test_rules_file "# Test Gandalf Rules - This is a test rules file for multi-tool validation."

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

    # Verify Windsurf gets truncated content
    [ -f "$TEST_HOME/.windsurf/global_rules.md" ]
    windsurf_char_count=$(wc -c <"$TEST_HOME/.windsurf/global_rules.md")
    [ "$windsurf_char_count" -le 6000 ]
    grep -q "Content truncated to fit Windsurf" "$TEST_HOME/.windsurf/global_rules.md"
}

@test "install creates proper claude code settings format" {
    # Create test rules file with special characters
    create_test_rules_file $'# Test Rules\n- Rule with "quotes" in it\n- Rule with backslashes in it\n- Rule with \nnewlines in it'

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify Claude Code global settings.json exists and is valid JSON
    [ -f "$TEST_HOME/.claude/global_settings.json" ]
    jq empty "$TEST_HOME/.claude/global_settings.json"
    jq -e '.gandalfRules' "$TEST_HOME/.claude/global_settings.json" >/dev/null
}

@test "install handles missing source rules file gracefully" {
    # Ensure no source rules file exists by not creating one
    # The TEST_RULES_FILE won't exist, simulating missing source file

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify warning messages for missing source file
    echo "$output" | grep -q "No rules files found"
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
}

@test "install updates installation state" {
    # Create test rules file
    create_test_rules_file "# Test Rules"

    # Run install
    run bash -c "GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify installation state file exists
    [ -f "$TEST_HOME/.gandalf/installation-state" ]
    grep -q "CURSOR_INSTALLED=" "$TEST_HOME/.gandalf/installation-state"
    grep -q "CLAUDE_CODE_INSTALLED=" "$TEST_HOME/.gandalf/installation-state"
    grep -q "WIND_SURF_INSTALLED=" "$TEST_HOME/.gandalf/installation-state"
}

@test "local install with --local flag" {
    create_test_rules_file "# Test Rules for Local Flag Test"

    # Run local installation in test project directory
    run bash -c "cd '$TEST_PROJECT_DIR' && GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify local scope is detected
    echo "$output" | grep -q "Scope: local"
    echo "$output" | grep -q "Install directory: $TEST_PROJECT_DIR"

    # Verify local directory structure created
    [ -d "$TEST_PROJECT_DIR/.gandalf" ]
    [ -d "$TEST_PROJECT_DIR/.gandalf/logs" ]
    [ -d "$TEST_PROJECT_DIR/.gandalf/cache" ]
}

@test "local install creates cursor project configuration" {
    # Run local installation
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify local Cursor configuration created
    [ -f "$TEST_PROJECT_DIR/.cursor/mcp.json" ]
    grep -q "GANDALF_LOCAL_DIR" "$TEST_PROJECT_DIR/.cursor/mcp.json"
    grep -q "GANDALF_SCOPE" "$TEST_PROJECT_DIR/.cursor/mcp.json"
}

@test "local install creates windsurf project configuration" {
    # Run local installation
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify local Windsurf configuration created
    [ -f "$TEST_PROJECT_DIR/.windsurf/mcp_config.json" ]
    grep -q "GANDALF_LOCAL_DIR" "$TEST_PROJECT_DIR/.windsurf/mcp_config.json"
    grep -q "GANDALF_SCOPE" "$TEST_PROJECT_DIR/.windsurf/mcp_config.json"
}

@test "local install creates local registry" {
    # Run local installation
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify local registry was created
    [ -f "$TEST_PROJECT_DIR/.gandalf/registry.json" ]
    jq -e '.installations' "$TEST_PROJECT_DIR/.gandalf/registry.json" >/dev/null
    jq -e '.installations | keys | length > 0' "$TEST_PROJECT_DIR/.gandalf/registry.json" >/dev/null
}

@test "local install creates local rules files" {
    # Create test rules file in temp location
    create_test_rules_file "# Local Rules Test"

    # Run local installation
    run bash -c "cd '$TEST_PROJECT_DIR' && GANDALF_SPEC_OVERRIDE='$TEST_SPEC_DIR' bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify local rules files were created
    [ -f "$TEST_PROJECT_DIR/.cursor/rules/gandalf-rules.mdc" ]
    [ -f "$TEST_PROJECT_DIR/.claude/local_settings.json" ]
    [ -f "$TEST_PROJECT_DIR/.windsurf/rules.md" ]

    # Verify local rules files contain the test content
    grep -q "Local Rules Test" "$TEST_PROJECT_DIR/.cursor/rules/gandalf-rules.mdc"
    grep -q "Local Rules Test" "$TEST_PROJECT_DIR/.claude/local_settings.json"
    grep -q "Local Rules Test" "$TEST_PROJECT_DIR/.windsurf/rules.md"

    # Verify global rules files were NOT created
    [ ! -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]
    [ ! -f "$TEST_HOME/.claude/global_settings.json" ]
    [ ! -f "$TEST_HOME/.windsurf/global_rules.md" ]
}

@test "local install does not create global installation state" {
    # Run local installation
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]

    # Verify global installation state is NOT created for local installations
    [ ! -f "$TEST_HOME/.gandalf/installation-state" ]
}

@test "install command line parameters work correctly" {
    # Test that --local enables local scope
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/install.sh' --local --force --skip-test"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Scope: local"
    
    # Test default behavior is global
    run bash "$GANDALF_ROOT/scripts/install.sh" --force --skip-test
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Scope: global"
}
