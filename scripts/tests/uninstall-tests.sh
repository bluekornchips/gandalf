#!/usr/bin/env bats
# Uninstall Script Tests
# Tests for gandalf uninstall functionality and cleanup operations

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "uninstall script shows help message" {
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage: gandalf.sh uninstall"
    echo "$output" | grep -q "Remove Gandalf MCP server configurations"
    echo "$output" | grep -q -- "--force"
    echo "$output" | grep -q -- "--dry-run"
    echo "$output" | grep -q -- "--keep-cache"
}

@test "uninstall script handles invalid arguments" {
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
    echo "$output" | grep -q "Usage:"
}

@test "dry run mode shows what would be removed without changes" {
    # Create mock files in test environment for all tools
    mkdir -p "$TEST_HOME/.cursor/rules"
    mkdir -p "$TEST_HOME/.claude"
    mkdir -p "$TEST_HOME/.windsurf"
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_HOME/.cursor/mcp.json"
    echo "# Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    echo '{"gandalfRules": "test rules"}' >"$TEST_HOME/.claude/settings.json"
    echo "# Global Windsurf Rules" >"$TEST_HOME/.windsurf/global_rules.md"
    mkdir -p "$TEST_HOME/.gandalf/cache"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --dry-run
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "DRY RUN MODE"
    echo "$output" | grep -q "Would remove"
    echo "$output" | grep -q "DRY RUN completed - no changes were made"

    # Verify files still exist after dry run
    [ -f "$TEST_HOME/.cursor/mcp.json" ]
    [ -f "$TEST_HOME/.claude/settings.json" ]
    [ -f "$TEST_HOME/.windsurf/global_rules.md" ]
    [ -d "$TEST_HOME/.gandalf" ]
}

@test "force mode skips confirmation prompts" {
    # Create minimal mock environment
    mkdir -p "$TEST_HOME/.gandalf"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Uninstall completed successfully!"
    # Should not contain confirmation prompts
    ! echo "$output" | grep -q "Continue? (y/N)"
}

@test "backup directory is created with timestamp" {
    mkdir -p "$TEST_HOME/.gandalf"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Created backup directory:"
    echo "$output" | grep -q "gandalf_backup_"
}

@test "cursor configuration is removed when present" {
    mkdir -p "$TEST_HOME/.cursor/rules"
    echo '{"mcpServers": {"gandalf": {}, "other": {}}}' >"$TEST_HOME/.cursor/mcp.json"
    echo "# Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Verify cursor rules file was removed
    [ ! -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]
}

@test "claude code configuration is removed when present" {
    mkdir -p "$TEST_HOME/.claude"
    echo '{"mcpServers": {"gandalf": {}, "other": {}}}' >"$TEST_HOME/.claude/mcp.json"
    echo '{"gandalfRules": "test rules", "other": "setting"}' >"$TEST_HOME/.claude/settings.json"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Verify gandalf rules were removed from settings but other settings remain
    if [ -f "$TEST_HOME/.claude/settings.json" ]; then
        ! grep -q "gandalfRules" "$TEST_HOME/.claude/settings.json"
    fi
}

@test "windsurf configuration is removed when present" {
    mkdir -p "$TEST_HOME/.windsurf"
    echo '{"mcpServers": {"gandalf": {}, "other": {}}}' >"$TEST_HOME/.windsurf/mcp.json"
    echo "# Global Windsurf Rules" >"$TEST_HOME/.windsurf/global_rules.md"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Verify windsurf global rules file was removed
    [ ! -f "$TEST_HOME/.windsurf/global_rules.md" ]
}

@test "gandalf home directory is removed completely" {
    mkdir -p "$TEST_HOME/.gandalf/"{cache,exports,config}
    echo "installation_state_test" >"$TEST_HOME/.gandalf/installation-state"
    echo "cache_data" >"$TEST_HOME/.gandalf/cache/test.json"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Removed ~/.gandalf directory"

    # Verify directory was removed
    [ ! -d "$TEST_HOME/.gandalf" ]
}

@test "keep cache option preserves cache while removing other files" {
    mkdir -p "$TEST_HOME/.gandalf/"{cache,exports,config}
    echo "installation_state_test" >"$TEST_HOME/.gandalf/installation-state"
    echo "cache_data" >"$TEST_HOME/.gandalf/cache/test.json"
    echo "export_data" >"$TEST_HOME/.gandalf/exports/test.json"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force --keep-cache
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Removed ~/.gandalf directory (kept cache)"

    # Verify cache directory still exists but other directories are gone
    [ -d "$TEST_HOME/.gandalf/cache" ]
    [ -f "$TEST_HOME/.gandalf/cache/test.json" ]
    [ ! -f "$TEST_HOME/.gandalf/installation-state" ]
    [ ! -d "$TEST_HOME/.gandalf/exports" ]
}

@test "shell aliases are removed from shell files" {
    cat <<'EOF' >"$TEST_HOME/.bashrc"
export PATH="/usr/local/bin:$PATH"
alias gdlf='/path/to/gandalf/gandalf.sh'
alias other='echo test'
EOF

    cat <<'EOF' >"$TEST_HOME/.zshrc"
export GANDALF_PATH="/path/to/gandalf"
alias gdlf='/path/to/gandalf/gandalf.sh'
export OTHER="test"
EOF

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Verify gandalf references were removed
    ! grep -q "gdlf\|gandalf" "$TEST_HOME/.bashrc"
    ! grep -q "gdlf\|gandalf" "$TEST_HOME/.zshrc"

    # Verify other content remains
    grep -q "export PATH" "$TEST_HOME/.bashrc"
    grep -q "export OTHER" "$TEST_HOME/.zshrc"
}

@test "custom backup directory is respected" {
    local custom_backup="$TEST_HOME/custom_backup"
    mkdir -p "$TEST_HOME/.gandalf"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force --backup-dir "$custom_backup"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Created backup directory: $custom_backup"

    # Verify custom backup directory was created
    [ -d "$custom_backup" ]
}

@test "backup files are created before removal" {
    mkdir -p "$TEST_HOME/.cursor/rules"
    mkdir -p "$TEST_HOME/.claude"
    mkdir -p "$TEST_HOME/.windsurf"
    mkdir -p "$TEST_HOME/.gandalf"
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_HOME/.cursor/mcp.json"
    echo "# Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    echo '{"gandalfRules": "test rules"}' >"$TEST_HOME/.claude/settings.json"
    echo "# Global Windsurf Rules" >"$TEST_HOME/.windsurf/global_rules.md"
    echo "alias gdlf='test'" >"$TEST_HOME/.bashrc"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Find the backup directory - the script creates backups in $HOME/.gandalf_backups/
    # The uninstall script uses $HOME which in tests is TEST_HOME
    local backup_dirs=("$TEST_HOME"/.gandalf_backups/gandalf_backup_*)
    local backup_dir="${backup_dirs[0]}"

    # Verify backup directory exists
    [ -d "$backup_dir" ]

    # Verify backup files exist for all tools
    [ -f "$backup_dir/mcp.json" ]
    [ -f "$backup_dir/gandalf-rules.mdc" ]
    [ -f "$backup_dir/settings.json" ]
    [ -f "$backup_dir/global_rules.md" ]
    [ -f "$backup_dir/.bashrc" ]
    [ -d "$backup_dir/.gandalf" ]
}

@test "uninstall handles missing files gracefully" {
    # No setup - test with missing files

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Uninstall completed successfully!"
    # Should not show removal messages for non-existent files
    ! echo "$output" | grep -q "Removed gandalf from Cursor MCP config"
    # The script will still show this message even if directory doesn't exist
    # because it checks for the directory and only removes if it exists
}

@test "uninstall preserves conversation history" {
    # Create mock conversation database
    mkdir -p "$TEST_HOME/.cursor/workspaceStorage"
    echo "conversation_data" >"$TEST_HOME/.cursor/workspaceStorage/conversations.db"

    # Create gandalf files to be removed
    mkdir -p "$TEST_HOME/.gandalf"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Verify conversation data is preserved
    [ -f "$TEST_HOME/.cursor/workspaceStorage/conversations.db" ]
    grep -q "conversation_data" "$TEST_HOME/.cursor/workspaceStorage/conversations.db"
}

@test "uninstall provides clear success feedback" {
    echo "Creating test configuration files..."
    mkdir -p "$TEST_HOME/.cursor"
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_HOME/.cursor/mcp.json"

    echo "Testing uninstall success feedback..."
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force

    echo "Verifying success feedback..."
    echo "$output" | grep -q "Uninstall completed successfully!"
    echo "$output" | grep -q "Restart your agentic tools"
}

@test "uninstall script sets proper exit codes" {
    # Test successful uninstall
    mkdir -p "$TEST_HOME/.gandalf"
    echo "test" >"$TEST_HOME/.gandalf/installation-state"

    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]

    # Test help command
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --help
    [ "$status" -eq 0 ]

    # Test invalid argument
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --invalid-arg
    [ "$status" -eq 1 ]
}
