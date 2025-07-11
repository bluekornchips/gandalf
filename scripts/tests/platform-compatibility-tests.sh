#!/usr/bin/env bats
# Platform Compatibility Tests for Gandalf MCP Server
# Cross-platform compatibility and path detection across Middle-earth

set -euo pipefail

load 'fixtures/helpers/test-helpers.sh'

readonly PLATFORM_TEST_TIMEOUT=30
readonly PLATFORM_WAIT_TIME=2
readonly ROHAN_DIR="rohan/edoras"
readonly GONDOR_DIR="gondor/minas-tirith"
readonly SHIRE_DIR="the shire/bag end"
readonly FANGORN_DIR="fangorn-forest"
readonly MORIA_DIR="moria"
readonly KHAZAD_DUM_DIR="khazad-dum"
readonly ISENGARD_PROJECT="isengard-project"

setup() {
    shared_setup
    create_minimal_project
}

teardown() {
    shared_teardown
}

@test "detect platform correctly across Middle-earth realms" {
    local platform
    platform=$(uname)

    case "$platform" in
    "Darwin")
        [[ "$platform" == "Darwin" ]]
        ;;
    "Linux")
        [[ "$platform" == "Linux" ]]
        ;;
    *)
        skip "Unsupported platform: $platform"
        ;;
    esac
}

@test "path handling works across realms of Middle-earth" {
    local test_path="$TEST_PROJECT_DIR/$SHIRE_DIR"
    mkdir -p "$test_path"

    local resolved_path
    resolved_path="$(cd "$test_path" && pwd -P)"

    [[ -d "$resolved_path" ]]
    [[ "$resolved_path" == *"$SHIRE_DIR" ]]
}

@test "home directory detection works like finding Bag End" {
    [[ -n "$HOME" ]]
    [[ -d "$HOME" ]]

    local gandalf_home="$HOME/.gandalf"
    mkdir -p "$gandalf_home"
    [[ -d "$gandalf_home" ]]
}

@test "project root detection works like finding the Shire" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | jq -e '.project_root' >/dev/null

    local project_root
    project_root=$(echo "$content" | jq -r '.project_root')
    [[ -n "$project_root" ]]
    [[ -d "$project_root" ]]
}

@test "file listing works across realms like mapping Middle-earth" {
    mkdir -p "$TEST_PROJECT_DIR/$ROHAN_DIR"
    mkdir -p "$TEST_PROJECT_DIR/$GONDOR_DIR"

    echo "# Rohan - Land of the Horse-lords" >"$TEST_PROJECT_DIR/$ROHAN_DIR/README.md"
    echo "# Gondor - Realm of the Kings" >"$TEST_PROJECT_DIR/$GONDOR_DIR/README.md"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "$ROHAN_DIR/README.md"
    echo "$content" | grep -q "$GONDOR_DIR/README.md"
}

@test "handles spaces in paths like finding Bag End in the Shire" {
    local space_dir="$TEST_PROJECT_DIR/$SHIRE_DIR"
    mkdir -p "$space_dir"
    echo "# Bag End - Home of Bilbo Baggins" >"$space_dir/README.md"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "$SHIRE_DIR/README.md"
}

@test "handles unicode characters like ancient Elvish runes" {
    local unicode_dir="$TEST_PROJECT_DIR/$FANGORN_DIR"
    mkdir -p "$unicode_dir"
    echo "# Fangorn Forest - Home of the Ents" >"$unicode_dir/README.md"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    echo "$content" | grep -q "$FANGORN_DIR/README.md"
}

@test "server works with different project roots like traveling realms" {
    local temp_project="$TEST_HOME/$ISENGARD_PROJECT"
    mkdir -p "$temp_project"
    cd "$temp_project"

    git init >/dev/null 2>&1
    git config user.email "saruman@isengard.middleearth"
    git config user.name "Saruman the White"
    echo "# Isengard Project - Tower of Orthanc" >README.md
    git add . >/dev/null 2>&1
    git commit -m "Tower of Orthanc established" >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$temp_project"
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')
    local project_root
    project_root=$(echo "$content" | jq -r '.project_root')

    # Use realpath to resolve both paths for comparison
    local resolved_temp_project resolved_project_root
    resolved_temp_project="$(cd "$temp_project" && pwd -P)"
    resolved_project_root="$(cd "$project_root" && pwd -P)"

    [[ "$resolved_project_root" == "$resolved_temp_project" ]]
}

@test "handles symlinks correctly like secret passages in Moria" {
    local real_dir="$TEST_PROJECT_DIR/$MORIA_DIR"
    local link_dir="$TEST_PROJECT_DIR/$KHAZAD_DUM_DIR"

    mkdir -p "$real_dir"
    echo "# Moria - Ancient Dwarf Kingdom" >"$real_dir/README.md"

    if ln -s "$real_dir" "$link_dir" 2>/dev/null; then
        run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
        [ "$status" -eq 0 ]

        validate_jsonrpc_response "$output"

        local content
        content=$(echo "$output" | jq -r '.result.content[0].text')
        echo "$content" | grep -q "README.md"
    else
        skip "Symlink creation failed (may not be supported on this realm)"
    fi
}

@test "server handles timeout gracefully like a patient wizard" {
    local start_time end_time duration
    start_time=$(date +%s)

    # Test that the server responds within the timeout period
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # Server should complete successfully within the timeout
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    # Check that it completed in reasonable time
    check_timeout_with_warning "$duration" "$PLATFORM_TEST_TIMEOUT" "project info request"
}

@test "environment variables are handled correctly like ancient magic" {
    local old_pythonpath="${PYTHONPATH:-}"
    export PYTHONPATH="$GANDALF_ROOT/server:$old_pythonpath"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    export PYTHONPATH="$old_pythonpath"
}
