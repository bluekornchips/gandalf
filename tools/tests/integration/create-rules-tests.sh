#!/usr/bin/env bats
# Create Rules Script Tests
# Tests for gandalf create-rules functionality

set -euo pipefail

load '../../lib/test-helpers.sh'

readonly CREATE_RULES_SCRIPT="$GANDALF_ROOT/tools/bin/create-rules"

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

validate_rules_file_exists() {
    local tool="$1"
    local expected_content="$2"

    case "$tool" in
        "cursor")
            [[ -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]] || return 1
            grep -q "$expected_content" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" || return 1
            ;;
        "claude")
            [[ -f "$TEST_HOME/.claude/CLAUDE.md" ]] || return 1
            grep -q "$expected_content" "$TEST_HOME/.claude/CLAUDE.md" || return 1
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

validate_local_rules_file_exists() {
    local tool="$1"
    local expected_content="$2"

    case "$tool" in
        "cursor")
            [[ -f "./.cursor/rules/gandalf-rules.mdc" ]] || return 1
            grep -q "$expected_content" "./.cursor/rules/gandalf-rules.mdc" || return 1
            ;;
        "claude")
            [[ -f "./CLAUDE.md" ]] || return 1
            grep -q "$expected_content" "./CLAUDE.md" || return 1
            ;;
        "windsurf")
            [[ -f "./.windsurf/global_rules.md" ]] || return 1
            grep -q "$expected_content" "./.windsurf/global_rules.md" || return 1
            ;;
        *)
            return 1
            ;;
    esac
}

create_existing_local_rules_files() {
    local cursor_content="${1:-# Existing Local Cursor Rules}"
    local claude_content="${2:-# Existing Local Claude Rules

Some existing content.

#####----- GANDALF RULES -----#####

existing gandalf rules content

#####----- END GANDALF RULES -----#####

More existing content.}"
    local windsurf_content="${3:-# Existing Local Windsurf Rules}"

    mkdir -p "./.cursor/rules"
    mkdir -p "./.windsurf"
    echo "$cursor_content" > "./.cursor/rules/gandalf-rules.mdc"
    echo "$claude_content" > "./CLAUDE.md"
    echo "$windsurf_content" > "./.windsurf/global_rules.md"
}

validate_rules_file_absent() {
    local tool="$1"
    local content="$2"

    case "$tool" in
        "cursor")
            ! grep -q "$content" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" 2>/dev/null || return 1
            ;;
        "claude")
            ! grep -q "$content" "$TEST_HOME/.claude/CLAUDE.md" 2>/dev/null || return 1
            ;;
        "windsurf")
            ! grep -q "$content" "$TEST_HOME/.windsurf/global_rules.md" 2>/dev/null || return 1
            ;;
        *)
            return 1
            ;;
    esac
}

validate_local_rules_file_absent() {
    local tool="$1"
    local content_to_avoid="$2"

    case "$tool" in
        "cursor")
            [[ ! -f "./.cursor/rules/gandalf-rules.mdc" ]] && return 0
            ! grep -q "$content_to_avoid" "./.cursor/rules/gandalf-rules.mdc" || return 1
            ;;
        "claude")
            [[ ! -f "./CLAUDE.md" ]] && return 0
            ! grep -q "$content_to_avoid" "./CLAUDE.md" || return 1
            ;;
        "windsurf")
            [[ ! -f "./.windsurf/global_rules.md" ]] && return 0
            ! grep -q "$content_to_avoid" "./.windsurf/global_rules.md" || return 1
            ;;
        *)
            return 1
            ;;
    esac
}

create_existing_rules_files() {
    # Create existing rules files for testing overwrite behavior
    mkdir -p "$TEST_HOME/.cursor/rules"
    mkdir -p "$TEST_HOME/.claude"
    mkdir -p "$TEST_HOME/.windsurf"

    # Create existing Cursor rules
    cat > "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" << 'EOF'
---
description: Existing Cursor Rules
globs:
alwaysApply: true
---

# Existing Cursor Rules
These are existing cursor rules that should be preserved when not forced.
EOF

    # Create existing Claude rules with markers
    cat > "$TEST_HOME/.claude/CLAUDE.md" << 'EOF'
# Some existing content

#####----- GANDALF RULES -----#####

existing gandalf rules content

#####----- END GANDALF RULES -----#####

# More existing content
EOF

    # Create existing Windsurf rules
    cat > "$TEST_HOME/.windsurf/global_rules.md" << 'EOF'
# Existing Windsurf Rules
These are existing windsurf rules that should be preserved when not forced.
EOF
}

validate_claude_markdown_format() {
    local claude_file="$TEST_HOME/.claude/CLAUDE.md"

    [[ -f "$claude_file" ]] || return 1
    grep -q "#####----- GANDALF RULES -----#####" "$claude_file" || return 1
    grep -q "#####----- END GANDALF RULES -----#####" "$claude_file" || return 1
}

validate_claude_markdown_content() {
    local claude_file="$TEST_HOME/.claude/CLAUDE.md"
    local expected_content="$1"

    validate_claude_markdown_format || return 1
    grep -q "$expected_content" "$claude_file" || return 1
}

validate_backup_created() {
    local backup_pattern="$1"
    local expected_content="$2"

    # Check for Claude backups in .claude directory
    if [[ "$backup_pattern" == "CLAUDE.md.backup" ]]; then
        local backup_files=("$TEST_HOME/.claude/"${backup_pattern}.*)
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

validate_windsurf_truncation() {
    local max_chars="$1"
    local windsurf_file="$TEST_HOME/.windsurf/global_rules.md"
    
    [[ -f "$windsurf_file" ]] || return 1
    local char_count=$(wc -c < "$windsurf_file")
    [[ "$char_count" -le "$max_chars" ]] || return 1
    grep -q "truncated to fit Windsurf" "$windsurf_file" || return 1
}

validate_success_messages() {
    local output="$1"

    echo "$output" | grep -q "Installing.*rules for Cursor IDE" || return 1
    echo "$output" | grep -q "Installing.*rules for Claude Code" || return 1
    echo "$output" | grep -q "Installing.*rules for Windsurf IDE" || return 1
    echo "$output" | grep -q "Rules Files Created" || return 1
    echo "$output" | grep -q "Cursor:.*gandalf-rules.mdc" || return 1
    echo "$output" | grep -q "Claude Code:.*CLAUDE.md" || return 1
    echo "$output" | grep -q "Windsurf:.*global_rules.md" || return 1
}

# Basic functionality tests
@test "create-rules script shows help message" {
    run "$CREATE_RULES_SCRIPT" --help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Create global and local rules files for Cursor, Claude Code, and Windsurf"
    echo "$output" | grep -q "\-\-force.*Overwrite existing rules"
    echo "$output" | grep -q "\-\-local.*Create rules in current directory only"
    echo "$output" | grep -q "\-\-global.*Create global rules only"
    echo "$output" | grep -q "\-\-debug.*Enable debug logging"
}

@test "create-rules script handles invalid arguments" {
    run "$CREATE_RULES_SCRIPT" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
}

# Rules creation tests
@test "create-rules creates rules for all supported tools" {
    create_test_rules_file "# Test Gandalf Rules - This is a test rules file for multi-tool validation."

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "Test Gandalf Rules"
    validate_rules_file_exists "claude" "Test Gandalf Rules"
    validate_rules_file_exists "windsurf" "Test Gandalf Rules"
}

@test "create-rules respects existing rules when not forced" {
    create_existing_rules_files

    create_test_rules_file "# New Rules"

    run "$CREATE_RULES_SCRIPT"
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "Existing Cursor Rules"
    validate_rules_file_exists "claude" "existing gandalf rules content"
    validate_rules_file_exists "windsurf" "Existing Windsurf Rules"

    validate_rules_file_absent "cursor" "New Rules"
}

@test "create-rules overwrites rules when forced" {
    create_existing_rules_files

    create_test_rules_file "# New Forced Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "New Forced Rules"
    validate_rules_file_exists "claude" "New Forced Rules"
    validate_rules_file_exists "windsurf" "New Forced Rules"
}

@test "create-rules handles large rules file for windsurf truncation" {
    local large_content=""
    for i in {1..200}; do
        large_content+="# Large Rules File Line $i - This is a very long line with lots of content to make it exceed the 6000 character limit for Windsurf rules files. "
    done

    create_test_rules_file "$large_content"

    local char_count
    char_count=$(wc -c < "$TEST_RULES_FILE")
    [ "$char_count" -gt 6000 ]

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_rules_file_exists "cursor" "Large Rules File"
    local cursor_char_count
    cursor_char_count=$(wc -c < "$TEST_HOME/.cursor/rules/gandalf-rules.mdc")
    [ "$cursor_char_count" -gt 6000 ]

    validate_windsurf_truncation 6000
}

@test "create-rules creates proper claude code markdown format" {
    create_test_rules_file $'# Test Rules\n- Rule with "quotes" in it\n- Rule with backslashes in it\n- Rule with \nnewlines in it'

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_claude_markdown_format
    validate_claude_markdown_content "quotes"
    validate_claude_markdown_content "backslashes"
    validate_claude_markdown_content "newlines"
}

@test "create-rules creates windsurf global rules with correct content" {
    create_test_rules_file "# Test Rules, this is test content for Windsurf rules validation."

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_rules_file_exists "windsurf" "Test Rules"
    validate_rules_file_exists "windsurf" "Windsurf rules validation"
}

@test "create-rules backs up existing claude code settings" {
    create_tool_directories

    cat > "$TEST_HOME/.claude/CLAUDE.md" << 'EOF'
# My existing Claude rules

Some existingSetting content.

#####----- GANDALF RULES -----#####

Old gandalf rules here.

#####----- END GANDALF RULES -----#####

More content.
EOF

    create_test_rules_file "# Test Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_backup_created "CLAUDE.md.backup" "existingSetting"
    validate_rules_file_exists "claude" "Test Rules"
}

@test "create-rules reports success for multi-tool configuration" {
    create_test_rules_file "# Test Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    validate_success_messages "$output"
}

@test "create-rules handles missing source rules file gracefully" {
    # Remove the test spec files to simulate missing rules
    rm -rf "$TEST_SPEC_DIR"
    export GANDALF_SPEC_OVERRIDE="$TEST_SPEC_DIR"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    echo "$output" | grep -q "No rules files found"
    echo "$output" | grep -q "Skipping rules file creation"
}

@test "create-rules handles CLAUDE.md with markers correctly" {
    mkdir -p "$TEST_HOME/.claude"
    cat > "$TEST_HOME/.claude/CLAUDE.md" << 'EOF'
# My existing Claude rules

Some existing content.

#####----- GANDALF RULES -----#####

Old gandalf content here.

#####----- END GANDALF RULES -----#####

More existing content.
EOF

    create_test_rules_file "# New Rules Content"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    grep -q "My existing Claude rules" "$TEST_HOME/.claude/CLAUDE.md"
    grep -q "More existing content" "$TEST_HOME/.claude/CLAUDE.md"
    grep -q "#####----- GANDALF RULES -----#####" "$TEST_HOME/.claude/CLAUDE.md"
    grep -q "New Rules Content" "$TEST_HOME/.claude/CLAUDE.md"
    ! grep -q "Old gandalf content here" "$TEST_HOME/.claude/CLAUDE.md"
}

@test "create-rules creates proper cursor frontmatter" {
    create_test_rules_file "# Test Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    head -n 5 "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" | grep -q "^---$"
    grep -q "^description:" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    grep -q "^alwaysApply:" "$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
}

@test "create-rules handles windsurf character limit" {
    create_test_rules_file "# Test Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]

    local windsurf_file="$TEST_HOME/.windsurf/global_rules.md"
    [ -f "$windsurf_file" ]
    
    local char_count=$(wc -c < "$windsurf_file")
    [ "$char_count" -le 6000 ]
}

@test "create-rules shows success message" {
    create_test_rules_file "# Test Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Gandalf Rules Creation completed successfully"
}

@test "create-rules local only flag creates only local rules" {
    create_test_rules_file "# Test Local Rules"

    run "$CREATE_RULES_SCRIPT" --local --force
    [ "$status" -eq 0 ]
    
    # Verify local rules were created
    validate_local_rules_file_exists "cursor" "Test Local Rules"
    validate_local_rules_file_exists "claude" "Test Local Rules"
    validate_local_rules_file_exists "windsurf" "Test Local Rules"
    
    # Verify global rules were NOT created (only check the new ones, not existing)
    echo "$output" | grep -q "Creating local workspace rules files"
    ! echo "$output" | grep -q "Creating global rules files"
}

@test "create-rules global only flag creates only global rules" {
    create_test_rules_file "# Test Global Rules"

    run "$CREATE_RULES_SCRIPT" --global --force
    [ "$status" -eq 0 ]
    
    # Verify global rules were created
    validate_rules_file_exists "cursor" "Test Global Rules"
    validate_rules_file_exists "claude" "Test Global Rules"
    validate_rules_file_exists "windsurf" "Test Global Rules"
    
    # Verify local rules were NOT created
    echo "$output" | grep -q "Creating global rules files"
    ! echo "$output" | grep -q "Creating local workspace rules files"
}

@test "create-rules default creates both global and local rules" {
    create_test_rules_file "# Test Both Rules"

    run "$CREATE_RULES_SCRIPT" --force
    [ "$status" -eq 0 ]
    
    # Verify both global and local rules were created
    echo "$output" | grep -q "Creating global rules files"
    echo "$output" | grep -q "Creating local workspace rules files"
    
    validate_rules_file_exists "cursor" "Test Both Rules"
    validate_rules_file_exists "claude" "Test Both Rules"
    validate_rules_file_exists "windsurf" "Test Both Rules"
    
    validate_local_rules_file_exists "cursor" "Test Both Rules"
    validate_local_rules_file_exists "claude" "Test Both Rules"
    validate_local_rules_file_exists "windsurf" "Test Both Rules"
}

@test "create-rules local flag updates existing local claude rules" {
    create_test_rules_file "# Updated Local Rules"
    create_existing_local_rules_files

    run "$CREATE_RULES_SCRIPT" --local --force
    [ "$status" -eq 0 ]
    
    # Verify local rules were updated
    validate_local_rules_file_exists "claude" "Updated Local Rules"
    ! grep -q "existing gandalf rules content" "./CLAUDE.md"
}

@test "create-rules rejects both local and global flags" {
    run "$CREATE_RULES_SCRIPT" --local --global
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Cannot specify both --local and --global options"
} 