#!/usr/bin/env bats

load fixtures/helpers/test-helpers.sh

setup() {
    shared_setup
    create_minimal_project
    export TEST_MODE=true
}

teardown() {
    shared_teardown
}

@test "uninstall script shows help message" {
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --help
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Usage: uninstall.sh"
}

@test "uninstall script handles unknown options" {
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --invalid-option
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "Unknown option"
}

@test "global uninstall removes cursor config" {
    # Create test cursor config
    mkdir -p "$TEST_HOME/.cursor/rules"
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_HOME/.cursor/mcp.json"
    echo "# Rules" >"$TEST_HOME/.cursor/rules/gandalf-rules.mdc"
    
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    # Verify cursor files were removed
    [ ! -f "$TEST_HOME/.cursor/mcp.json" ]
    [ ! -f "$TEST_HOME/.cursor/rules/gandalf-rules.mdc" ]
}

@test "global uninstall removes claude config" {
    # Create test claude config
    mkdir -p "$TEST_HOME/.claude"
    echo '{"gandalfRules": "test"}' >"$TEST_HOME/.claude/local_settings.json"
    
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    # Verify claude files were removed
    [ ! -f "$TEST_HOME/.claude/local_settings.json" ]
}

@test "global uninstall removes windsurf config" {
    # Create test windsurf config
    mkdir -p "$TEST_HOME/.windsurf"
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_HOME/.windsurf/mcp_config.json"
    echo "# Rules" >"$TEST_HOME/.windsurf/rules.md"
    
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    # Verify windsurf files were removed
    [ ! -f "$TEST_HOME/.windsurf/mcp_config.json" ]
    [ ! -f "$TEST_HOME/.windsurf/rules.md" ]
}

@test "global uninstall removes gandalf directory" {
    # Create test gandalf directory
    mkdir -p "$TEST_HOME/.gandalf"
    echo "test" >"$TEST_HOME/.gandalf/test.txt"
    
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    # Verify gandalf directory was removed
    [ ! -d "$TEST_HOME/.gandalf" ]
}

@test "local uninstall with --local flag" {
    # Create local installation files
    mkdir -p "$TEST_PROJECT_DIR/.cursor/rules"
    mkdir -p "$TEST_PROJECT_DIR/.gandalf"
    
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_PROJECT_DIR/.cursor/mcp.json"
    echo "# Rules" >"$TEST_PROJECT_DIR/.cursor/rules/gandalf-rules.mdc"
    echo "test" >"$TEST_PROJECT_DIR/.gandalf/test.txt"
    
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/uninstall.sh' --local --force"
    [ "$status" -eq 0 ]
    
    # Verify local files were removed
    [ ! -f "$TEST_PROJECT_DIR/.cursor/mcp.json" ]
    [ ! -f "$TEST_PROJECT_DIR/.cursor/rules/gandalf-rules.mdc" ]
    [ ! -d "$TEST_PROJECT_DIR/.gandalf" ]
}

@test "local uninstall with --local-dir option" {
    # Create local installation files
    mkdir -p "$TEST_PROJECT_DIR/.cursor"
    mkdir -p "$TEST_PROJECT_DIR/.gandalf"
    
    echo '{"mcpServers": {"gandalf": {}}}' >"$TEST_PROJECT_DIR/.cursor/mcp.json"
    echo "test" >"$TEST_PROJECT_DIR/.gandalf/test.txt"
    
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --local-dir "$TEST_PROJECT_DIR" --force
    [ "$status" -eq 0 ]
    
    # Verify local files were removed
    [ ! -f "$TEST_PROJECT_DIR/.cursor/mcp.json" ]
    [ ! -d "$TEST_PROJECT_DIR/.gandalf" ]
}

@test "local uninstall handles missing files gracefully" {
    # No files exist, should not fail
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/uninstall.sh' --local --force"
    [ "$status" -eq 0 ]
    
    echo "$output" | grep -q "Local uninstall completed"
}

@test "global uninstall handles missing files gracefully" {
    # No files exist, should not fail
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    echo "$output" | grep -q "Global uninstall completed"
}

@test "uninstall provides success feedback" {
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    echo "$output" | grep -q "Uninstall completed successfully"
}

@test "local uninstall does not affect global files" {
    # Create both global and local files
    mkdir -p "$TEST_HOME/.gandalf"
    mkdir -p "$TEST_PROJECT_DIR/.gandalf"
    
    echo "global" >"$TEST_HOME/.gandalf/global.txt"
    echo "local" >"$TEST_PROJECT_DIR/.gandalf/local.txt"
    
    # Run local uninstall
    run bash -c "cd '$TEST_PROJECT_DIR' && bash '$GANDALF_ROOT/scripts/uninstall.sh' --local --force"
    [ "$status" -eq 0 ]
    
    # Verify global files remain, local files removed
    [ -f "$TEST_HOME/.gandalf/global.txt" ]
    [ ! -d "$TEST_PROJECT_DIR/.gandalf" ]
}

@test "global uninstall does not affect local files" {
    # Create both global and local files
    mkdir -p "$TEST_HOME/.gandalf"
    mkdir -p "$TEST_PROJECT_DIR/.gandalf"
    
    echo "global" >"$TEST_HOME/.gandalf/global.txt"
    echo "local" >"$TEST_PROJECT_DIR/.gandalf/local.txt"
    
    # Run global uninstall
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --force
    [ "$status" -eq 0 ]
    
    # Verify global files removed, local files remain
    [ ! -d "$TEST_HOME/.gandalf" ]
    [ -f "$TEST_PROJECT_DIR/.gandalf/local.txt" ]
}

@test "uninstall validates local directory exists" {
    run bash "$GANDALF_ROOT/scripts/uninstall.sh" --local-dir "/nonexistent/directory" --force
    [ "$status" -eq 1 ]
    
    echo "$output" | grep -q "does not exist"
}
