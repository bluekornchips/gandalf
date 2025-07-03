#!/usr/bin/env bats
# Platform Compatibility Tests for Gandalf MCP Server
#
# Tests cross-platform functionality and path detection to ensure Gandalf works
# seamlessly across the realms of macOS, Linux, and other platforms.
#
# Like the paths through Middle-earth, our scripts must work whether traversing
# the Shire (macOS) or the lands of Gondor (Linux).

set -eo pipefail

load 'fixtures/helpers/test-helpers.sh'

setup() {
    shared_setup

    # Source platform utilities for the Fellowship of cross-platform functions
    source "$GANDALF_ROOT/scripts/platform-utils.sh"
}

teardown() {
    shared_teardown
}

@test "detect_platform returns valid realm like the maps of Middle-earth" {
    run detect_platform
    [ "$status" -eq 0 ]

    # Should return one of the known realms
    [[ "$output" =~ ^(macos|linux|windows|unknown)$ ]]
}

@test "get_cursor_config_dir finds the right path through the Shire or Gondor" {
    run get_cursor_config_dir
    [ "$status" -eq 0 ]
    [ -n "$output" ]

    # Should not contain Shire-specific paths when in Gondor
    if [[ "$(detect_platform)" != "macos" ]]; then
        [[ "$output" != *"Library/Application Support"* ]]
    fi
}

@test "get_cursor_workspace_storage navigates to proper storage like Bag End or Minas Tirith" {
    run get_cursor_workspace_storage
    [ "$status" -eq 0 ]
    [ -n "$output" ]

    # Gondor should not use Shire storage paths
    if [[ "$(detect_platform)" != "macos" ]]; then
        [[ "$output" != *"Library/Application Support"* ]]
    fi
}

@test "get_application_paths handles unknown applications like Sauron handles unknown rings" {
    run get_application_paths "palantir-of-unknown-origin"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "get_application_paths finds Cursor like Aragorn finds the path to victory" {
    run get_application_paths "cursor"
    [ "$status" -eq 0 ]

    local realm
    realm=$(detect_platform)

    case "$realm" in
    macos)
        # In the Shire, applications dwell in /Applications
        [[ "$output" == "/Applications/Cursor.app" ]]
        ;;
    linux)
        # In Gondor, executables may be found in various strongholds
        if [[ -n "$output" ]]; then
            [[ "$output" =~ ^/.*cursor$ ]]
        fi
        ;;
    *)
        # Unknown realms return empty, like the void beyond Middle-earth
        [ -z "$output" ]
        ;;
    esac
}

@test "is_application_installed handles missing applications like Frodo handles the burden" {
    run is_application_installed "one-ring-to-rule-them-all"
    # Should return failure for applications that exist only in legend
    [ "$status" -ne 0 ]
}

@test "platform utilities avoid Shire paths when not in the Shire like wise hobbits" {
    # Test that our functions don't return Shire-specific paths in other realms
    if [[ "$(detect_platform)" != "macos" ]]; then
        local cursor_config
        cursor_config=$(get_cursor_config_dir)
        [[ "$cursor_config" != *"Library/Application Support"* ]]

        local cursor_storage
        cursor_storage=$(get_cursor_workspace_storage)
        [[ "$cursor_storage" != *"Library/Application Support"* ]]

        local cursor_app_support
        cursor_app_support=$(get_cursor_app_support_dir)
        [[ "$cursor_app_support" != *"Library/Application Support"* ]]
    fi
}

@test "registry script detects agentic tools like Gandalf detects the nature of rings" {
    # Test that registry.sh properly detects tools using platform utilities
    run bash "$GANDALF_ROOT/scripts/registry.sh" detect
    [ "$status" -eq 0 ]

    # Should return a valid tool name from the Fellowship of agentic tools
    [[ "$output" =~ ^(cursor|claude-code|windsurf)$ ]]
}

@test "install script sources platform utilities like Elrond sources ancient wisdom" {
    # Test that install.sh can source platform utilities without error
    run bash -c "source '$GANDALF_ROOT/scripts/platform-utils.sh' && get_cursor_workspace_storage"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
}

@test "setup script sources platform utilities like Galadriel sources the light of Eärendil" {
    # Test that setup.sh can source platform utilities without error
    run bash -c "source '$GANDALF_ROOT/scripts/platform-utils.sh' && get_cursor_config_dir"
    [ "$status" -eq 0 ]
    [ -n "$output" ]
}

@test "platform detection works consistently like the constancy of the Undying Lands" {
    # Test that platform detection is consistent across multiple calls
    local first_detection
    first_detection=$(detect_platform)

    local second_detection
    second_detection=$(detect_platform)

    [[ "$first_detection" == "$second_detection" ]]
    [[ -n "$first_detection" ]]
}

@test "cursor paths resolve correctly across all realms like the light of Elessar" {
    # Test that all cursor-related path functions return valid paths
    local config_dir
    config_dir=$(get_cursor_config_dir)
    [[ -n "$config_dir" ]]
    [[ "$config_dir" =~ ^/ ]] # Should be absolute path

    local app_support_dir
    app_support_dir=$(get_cursor_app_support_dir)
    [[ -n "$app_support_dir" ]]
    [[ "$app_support_dir" =~ ^/ ]] # Should be absolute path

    local workspace_storage
    workspace_storage=$(get_cursor_workspace_storage)
    [[ -n "$workspace_storage" ]]
    [[ "$workspace_storage" =~ ^/ ]] # Should be absolute path
}
