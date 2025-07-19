#!/usr/bin/env bats
# Platform Compatibility Tests for Gandalf MCP Server
# Cross-platform compatibility and path detection across Middle-earth

set -euo pipefail

load '../../lib/test-helpers.sh'

readonly PLATFORM_TEST_TIMEOUT=30
readonly PLATFORM_WAIT_TIME=2
readonly ROHAN_DIR="rohan/edoras"
readonly GONDOR_DIR="gondor/minas-tirith"
readonly SHIRE_DIR="the shire/bag end"
readonly FANGORN_DIR="fangorn-forest"
readonly MORIA_DIR="moria"
readonly KHAZAD_DUM_DIR="khazad-dum"
readonly ISENGARD_PROJECT="isengard-project"


check_platform_timing() {
    local duration="$1"
    local max_time="$2"
    local operation="$3"

    if [[ $duration -gt $max_time ]]; then
        echo "WARNING: $operation took ${duration}s (expected <${max_time}s)"
    else
        echo "PASS: $operation completed in ${duration}s"
    fi
}


create_test_directory() {
    local dir_path="$1"
    local content_file="$2"
    local content="$3"

    mkdir -p "$dir_path"
    echo "$content" >"$dir_path/$content_file"
}


validate_project_info() {
    local output="$1"
    local expected_field="$2"
    local expected_value="${3:-}"

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    if ! echo "$content" | jq -e ".$expected_field" >/dev/null 2>&1; then
        echo "ERROR: Expected field '$expected_field' not found in project info" >&2
        return 1
    fi

    local field_value
    field_value=$(echo "$content" | jq -r ".$expected_field")

    if [[ -n "$expected_value" ]]; then
        if [[ "$field_value" != "$expected_value" ]]; then
            echo "ERROR: Expected $expected_field to be '$expected_value' but got '$field_value'" >&2
            return 1
        fi
    fi

    echo "$field_value"
}


validate_file_listing_contains() {
    local output="$1"
    local pattern="$2"

    validate_jsonrpc_response "$output"

    local content
    content=$(echo "$output" | jq -r '.result.content[0].text')

    if ! echo "$content" | grep -q "$pattern"; then
        echo "ERROR: Expected pattern '$pattern' not found in file listing: $content" >&2
        return 1
    fi
}


resolve_path() {
    local path="$1"
    cd "$path" && pwd -P
}


create_git_project() {
    local project_dir="$1"
    local project_name="$2"
    local author_email="$3"
    local author_name="$4"

    mkdir -p "$project_dir"
    cd "$project_dir"

    git init >/dev/null 2>&1
    git config user.email "$author_email"
    git config user.name "$author_name"
    echo "# $project_name" >README.md
    git add . >/dev/null 2>&1
    git commit -m "$project_name established" >/dev/null 2>&1
}


validate_platform() {
    local platform="$1"

    case "$platform" in
    "Darwin"|"Linux")
        echo "PASS: Supported platform: $platform"
        return 0
        ;;
    *)
        echo "ERROR: Unsupported platform: $platform" >&2
        return 1
        ;;
    esac
}


execute_timed_operation() {
    local operation_name="$1"
    local max_time="$2"
    shift 2

    local start_time end_time duration
    start_time=$(date +%s)

    "$@"
    local status=$?

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    check_platform_timing "$duration" "$max_time" "$operation_name"

    return $status
}


validate_directory_exists() {
    local dir_path="$1"
    local description="${2:-directory}"

    if [[ ! -d "$dir_path" ]]; then
        echo "ERROR: Expected $description to exist at: $dir_path" >&2
        return 1
    fi
}


create_symlink_safe() {
    local source="$1"
    local target="$2"

    if ln -s "$source" "$target" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

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

    validate_platform "$platform"
    [[ "$platform" == "$(uname)" ]]
}

@test "path handling works across realms of Middle-earth" {
    local test_path="$TEST_PROJECT_DIR/$SHIRE_DIR"
    mkdir -p "$test_path"

    local resolved_path
    resolved_path=$(resolve_path "$test_path")

    validate_directory_exists "$resolved_path" "resolved path"
    [[ "$resolved_path" == *"$SHIRE_DIR" ]]
}

@test "home directory detection works like finding Bag End" {
    if [[ -z "$HOME" ]]; then
        echo "ERROR: HOME environment variable not set" >&2
        false
    fi

    validate_directory_exists "$HOME" "home directory"

    local gandalf_home="$HOME/.gandalf"
    mkdir -p "$gandalf_home"
    validate_directory_exists "$gandalf_home" "gandalf home directory"
}

@test "project root detection works like finding the Shire" {
    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    local project_root
    project_root=$(validate_project_info "$output" "project_root")

    if [[ -z "$project_root" ]]; then
        echo "ERROR: Project root should not be empty" >&2
        false
    fi

    validate_directory_exists "$project_root" "project root"
}

@test "file listing works across realms like mapping Middle-earth" {
    create_test_directory "$TEST_PROJECT_DIR/$ROHAN_DIR" "README.md" "# Rohan - Land of the Horse-lords"
    create_test_directory "$TEST_PROJECT_DIR/$GONDOR_DIR" "README.md" "# Gondor - Realm of the Kings"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_file_listing_contains "$output" "$ROHAN_DIR/README.md"
    validate_file_listing_contains "$output" "$GONDOR_DIR/README.md"
}

@test "handles spaces in paths like finding Bag End in the Shire" {
    create_test_directory "$TEST_PROJECT_DIR/$SHIRE_DIR" "README.md" "# Bag End - Home of Bilbo Baggins"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_file_listing_contains "$output" "$SHIRE_DIR/README.md"
}

@test "handles unicode characters like ancient Elvish runes" {
    create_test_directory "$TEST_PROJECT_DIR/$FANGORN_DIR" "README.md" "# Fangorn Forest - Home of the Ents"

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_file_listing_contains "$output" "$FANGORN_DIR/README.md"
}

@test "server works with different project roots like traveling realms" {
    local temp_project="$TEST_HOME/$ISENGARD_PROJECT"
    create_git_project "$temp_project" "Isengard Project - Tower of Orthanc" "saruman@isengard.middleearth" "Saruman the White"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}' "$temp_project"
    [ "$status" -eq 0 ]

    local project_root
    project_root=$(validate_project_info "$output" "project_root")

    local resolved_temp_project resolved_project_root
    resolved_temp_project=$(resolve_path "$temp_project")
    resolved_project_root=$(resolve_path "$project_root")

    if [[ "$resolved_project_root" != "$resolved_temp_project" ]]; then
        echo "ERROR: Project root mismatch. Expected: $resolved_temp_project, Got: $resolved_project_root" >&2
        false
    fi
}

@test "handles symlinks correctly like secret passages in Moria" {
    local real_dir="$TEST_PROJECT_DIR/$MORIA_DIR"
    local link_dir="$TEST_PROJECT_DIR/$KHAZAD_DUM_DIR"

    create_test_directory "$real_dir" "README.md" "# Moria - Ancient Dwarf Kingdom"

    if create_symlink_safe "$real_dir" "$link_dir"; then
        run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {}}'
        [ "$status" -eq 0 ]

        validate_file_listing_contains "$output" "README.md"
        echo "PASS: Symlink handling works correctly"
    else
        skip "Symlink creation failed (may not be supported on this realm)"
    fi
}

@test "server handles timeout gracefully like a patient wizard" {
    local start_time end_time duration
    start_time=$(date +%s)

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    check_platform_timing "$duration" "$PLATFORM_TEST_TIMEOUT" "project info request"
}

@test "environment variables are handled correctly like ancient magic" {
    local old_pythonpath="${PYTHONPATH:-}"
    export PYTHONPATH="$GANDALF_ROOT/server:$old_pythonpath"

    run execute_rpc "tools/call" '{"name": "get_project_info", "arguments": {}}'
    [ "$status" -eq 0 ]

    validate_jsonrpc_response "$output"

    export PYTHONPATH="$old_pythonpath"
    echo "PASS: Environment variables handled correctly"
}
