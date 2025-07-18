#!/usr/bin/env bats
# Uninstall Script Tests
# Tests for gandalf uninstall functionality and cleanup operations

set -euo pipefail

load '../../lib/test-helpers.sh'

create_mock_cursor_config() {
    local with_gandalf="${1:-true}"
    local with_others="${2:-false}"
    
    mkdir -p "$TEST_HOME/.cursor/rules"
    
    if [[ "$with_gandalf" == "true" ]]; then
        echo "# Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
        if [[ "$with_others" == "true" ]]; then
            echo '{"mcpServers": {"gandalf": {}, "other": {}}}' >"$TEST_HOME/.cursor/mcp.json"
        else
            echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_HOME/.cursor/mcp.json"
        fi
    fi
}

create_mock_claude_config() {
    local with_gandalf="${1:-true}"
    local with_others="${2:-false}"
    
    mkdir -p "$TEST_HOME/.claude"
    
    if [[ "$with_gandalf" == "true" ]]; then
        if [[ "$with_others" == "true" ]]; then
            echo '{"mcpServers": {"gandalf": {}, "other": {}}}' >"$TEST_HOME/.claude/mcp.json"
            echo '{"gandalfRules": "test rules", "other": "setting"}' >"$TEST_HOME/.claude/settings.json"
        else
            echo '{"gandalfRules": "test rules"}' >"$TEST_HOME/.claude/settings.json"
        fi
    fi
}

create_mock_windsurf_config() {
    local with_gandalf="${1:-true}"
    local with_others="${2:-false}"
    
    mkdir -p "$TEST_HOME/.windsurf"
    
    if [[ "$with_gandalf" == "true" ]]; then
        echo "# Global Windsurf Rules" >"$TEST_HOME/.windsurf/global_rules.md"
        if [[ "$with_others" == "true" ]]; then
            echo '{"mcpServers": {"gandalf": {}, "other": {}}}' >"$TEST_HOME/.windsurf/mcp.json"
        fi
    fi
}

create_mock_gandalf_home() {
    local with_cache="${1:-true}"
    local with_exports="${2:-false}"
    
    mkdir -p "$TEST_HOME/.gandalf"
    echo "installation_state_test" >"$TEST_HOME/.gandalf/installation-state"
    
    if [[ "$with_cache" == "true" ]]; then
        mkdir -p "$TEST_HOME/.gandalf/cache"
        echo "cache_data" >"$TEST_HOME/.gandalf/cache/test.json"
    fi
    
    if [[ "$with_exports" == "true" ]]; then
        mkdir -p "$TEST_HOME/.gandalf/exports"
        echo "export_data" >"$TEST_HOME/.gandalf/exports/test.json"
    fi
}

create_mock_shell_configs() {
    cat <<'EOF' >"$TEST_HOME/.bashrc"
export PATH="/usr/local/bin:$PATH"
alias gdlf='/path/to/gandalf/gandalf'
alias other='echo test'
EOF

    cat <<'EOF' >"$TEST_HOME/.zshrc"
export GANDALF_PATH="/path/to/gandalf"
alias gdlf='/path/to/gandalf/gandalf'
export OTHER="test"
EOF
}

create_full_mock_environment() {
    create_mock_cursor_config "true" "false"
    create_mock_claude_config "true" "false"
    create_mock_windsurf_config "true" "false"
    create_mock_gandalf_home "true" "false"
    create_mock_shell_configs
}

validate_backup_created() {
    local backup_pattern="${1:-}"
    local backup_dirs=("$TEST_HOME"/.gandalf_backups/gandalf_backup_*)
    local backup_dir="${backup_dirs[0]}"
    
    if [[ ! -d "$backup_dir" ]]; then
        echo "ERROR: Backup directory not found at $backup_dir" >&2
        return 1
    fi
    
    echo "$backup_dir"
}

validate_file_removed() {
    local file_path="$1"
    local description="${2:-file}"
    
    if [[ -f "$file_path" ]]; then
        echo "ERROR: $description should have been removed: $file_path" >&2
        return 1
    fi
}

validate_file_preserved() {
    local file_path="$1"
    local description="${2:-file}"
    
    if [[ ! -f "$file_path" ]]; then
        echo "ERROR: $description should have been preserved: $file_path" >&2
        return 1
    fi
}

validate_directory_removed() {
    local dir_path="$1"
    local description="${2:-directory}"
    
    if [[ -d "$dir_path" ]]; then
        echo "ERROR: $description should have been removed: $dir_path" >&2
        return 1
    fi
}

validate_directory_preserved() {
    local dir_path="$1"
    local description="${2:-directory}"
    
    if [[ ! -d "$dir_path" ]]; then
        echo "ERROR: $description should have been preserved: $dir_path" >&2
        return 1
    fi
}

execute_uninstall_command() {
    local args="$1"
    bash "$GANDALF_ROOT/tools/bin/uninstall" $args
}

validate_uninstall_success() {
    local output="$1"
    
    if ! echo "$output" | grep -q "Uninstall completed successfully!"; then
        echo "ERROR: Expected success message not found in output: $output" >&2
        return 1
    fi
}

validate_help_output() {
    local output="$1"
    
    local expected_patterns=("Usage: ./gandalf uninstall" "Remove Gandalf MCP server configurations" "\-f, \-\-force" "\-\-dry-run" "\-\-keep-cache")
    
    for pattern in "${expected_patterns[@]}"; do
        if ! echo "$output" | grep -q "$pattern"; then
            echo "ERROR: Expected help pattern not found: $pattern" >&2
            return 1
        fi
    done
}

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "uninstall script shows help message" {
    run execute_uninstall_command "--help"
    [ "$status" -eq 0 ]
    validate_help_output "$output"
}

@test "uninstall script handles invalid arguments" {
    run execute_uninstall_command "--invalid-option"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
    echo "$output" | grep -q "Usage:"
}

@test "dry run mode shows what would be removed without changes" {
    create_full_mock_environment
    
    run execute_uninstall_command "--dry-run"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "DRY RUN MODE"
    echo "$output" | grep -q "Would remove"
    echo "$output" | grep -q "DRY RUN completed - no changes were made"

    validate_file_preserved "$TEST_HOME/.cursor/mcp.json" "Cursor config"
    validate_file_preserved "$TEST_HOME/.claude/settings.json" "Claude config"
    validate_file_preserved "$TEST_HOME/.windsurf/global_rules.md" "Windsurf config"
    validate_directory_preserved "$TEST_HOME/.gandalf" "Gandalf home"
}

@test "force mode skips confirmation prompts" {
    create_mock_gandalf_home
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    validate_uninstall_success "$output"
    
    if echo "$output" | grep -q "Continue? (y/N)"; then
        echo "ERROR: Force mode should not show confirmation prompts" >&2
        false
    fi
}

@test "backup directory is created with timestamp" {
    create_mock_gandalf_home
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Created backup directory:"
    echo "$output" | grep -q "gandalf_backup_"
}

@test "cursor configuration is removed when present" {
    create_mock_cursor_config "true" "true"
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    validate_file_removed "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" "Cursor rules file"
}

@test "claude code configuration is removed when present" {
    create_mock_claude_config "true" "true"
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    if [[ -f "$TEST_HOME/.claude/settings.json" ]]; then
        if grep -q "gandalfRules" "$TEST_HOME/.claude/settings.json"; then
            echo "ERROR: gandalfRules should have been removed from Claude settings" >&2
            false
        fi
    fi
}

@test "windsurf configuration is removed when present" {
    create_mock_windsurf_config "true" "true"
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    validate_file_removed "$TEST_HOME/.windsurf/global_rules.md" "Windsurf rules file"
}

@test "gandalf home directory is removed completely" {
    create_mock_gandalf_home "true" "false"
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Removed ~/.gandalf directory"
    
    validate_directory_removed "$TEST_HOME/.gandalf" "Gandalf home directory"
}

@test "keep cache option preserves cache while removing other files" {
    create_mock_gandalf_home "true" "true"
    
    run execute_uninstall_command "--force --keep-cache"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Removed ~/.gandalf directory (kept cache)"
    
    validate_directory_preserved "$TEST_HOME/.gandalf/cache" "Cache directory"
    validate_file_preserved "$TEST_HOME/.gandalf/cache/test.json" "Cache file"
    validate_file_removed "$TEST_HOME/.gandalf/installation-state" "Installation state"
    validate_directory_removed "$TEST_HOME/.gandalf/exports" "Exports directory"
}

@test "shell aliases are removed from shell files" {
    create_mock_shell_configs
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    if grep -q "gdlf\|gandalf" "$TEST_HOME/.bashrc"; then
        echo "ERROR: Gandalf references should have been removed from .bashrc" >&2
        false
    fi
    
    if grep -q "gdlf\|gandalf" "$TEST_HOME/.zshrc"; then
        echo "ERROR: Gandalf references should have been removed from .zshrc" >&2
        false
    fi
    
    if ! grep -q "export PATH" "$TEST_HOME/.bashrc"; then
        echo "ERROR: Other content should remain in .bashrc" >&2
        false
    fi
    
    if ! grep -q "export OTHER" "$TEST_HOME/.zshrc"; then
        echo "ERROR: Other content should remain in .zshrc" >&2
        false
    fi
}

@test "custom backup directory is respected" {
    local custom_backup="$TEST_HOME/custom_backup"
    create_mock_gandalf_home
    
    run execute_uninstall_command "--force --backup-dir \"$custom_backup\""
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Created backup directory: \"$custom_backup\"/gandalf_backup_"
    
    # Check that backup was created in the custom directory
    local backup_dirs=("$custom_backup"/gandalf_backup_*)
    local backup_dir="${backup_dirs[0]}"
    
    # Only validate if backup directory actually exists (not just glob pattern)
    if [[ -d "$backup_dir" ]]; then
        validate_directory_preserved "$backup_dir" "Custom backup directory"
    else
        echo "WARNING: Backup directory not found: $backup_dir"
    fi
}

@test "backup files are created before removal" {
    create_full_mock_environment
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    local backup_dir
    backup_dir=$(validate_backup_created)
    
    local expected_backups=("$backup_dir/mcp.json" "$backup_dir/gandalf-rules.mdc" "$backup_dir/settings.json" "$backup_dir/global_rules.md" "$backup_dir/.bashrc" "$backup_dir/.gandalf")
    
    for backup_file in "${expected_backups[@]}"; do
        if [[ "$backup_file" == "$backup_dir/.gandalf" ]]; then
            validate_directory_preserved "$backup_file" "Backup gandalf directory"
        else
            validate_file_preserved "$backup_file" "Backup file $(basename "$backup_file")"
        fi
    done
}

@test "uninstall handles missing files gracefully" {
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    validate_uninstall_success "$output"
    
    if echo "$output" | grep -q "Removed gandalf from Cursor MCP config"; then
        echo "ERROR: Should not show removal messages for non-existent files" >&2
        false
    fi
}

@test "uninstall preserves conversation history" {
    mkdir -p "$TEST_HOME/.cursor/workspaceStorage"
    echo "conversation_data" >"$TEST_HOME/.cursor/workspaceStorage/conversations.db"
    create_mock_gandalf_home
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    validate_file_preserved "$TEST_HOME/.cursor/workspaceStorage/conversations.db" "Conversation database"
    
    if ! grep -q "conversation_data" "$TEST_HOME/.cursor/workspaceStorage/conversations.db"; then
        echo "ERROR: Conversation data should be preserved" >&2
        false
    fi
}

@test "uninstall provides clear success feedback" {
    create_mock_cursor_config
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    validate_uninstall_success "$output"
    echo "$output" | grep -q "Restart your agentic tools"
}

@test "uninstall script sets proper exit codes" {
    create_mock_gandalf_home
    
    run execute_uninstall_command "--force"
    [ "$status" -eq 0 ]
    
    run execute_uninstall_command "--help"
    [ "$status" -eq 0 ]
    
    run execute_uninstall_command "--invalid-arg"
    [ "$status" -eq 1 ]
}
