#!/bin/bash
# Platform Utilities for Cross-Platform Compatibility
# Provides consistent platform detection and path resolution across different operating systems

set -euo pipefail

readonly PLATFORM_MACOS="Darwin"
readonly PLATFORM_LINUX="Linux"

readonly CURSOR_APP_MACOS="/Applications/Cursor.app"
readonly CURSOR_CONFIG_MACOS="$HOME/Library/Application Support/Cursor/User"
readonly CURSOR_WORKSPACE_MACOS="$HOME/Library/Application Support/Cursor/User/workspaceStorage"

readonly CURSOR_CONFIG_LINUX="$HOME/.config/Cursor/User"
readonly CURSOR_WORKSPACE_LINUX="$HOME/.config/Cursor/User/workspaceStorage"

readonly CLAUDE_HOME_DIR="$HOME/.claude"
readonly WINDSURF_CONFIG_DIR="$HOME/.codeium/windsurf"

detect_platform() {
    local platform
    platform="$(uname)"

    case "$platform" in
    "$PLATFORM_MACOS")
        echo "macos"
        ;;
    "$PLATFORM_LINUX")
        echo "linux"
        ;;
    *)
        echo "unknown"
        ;;
    esac
}

get_cursor_config_dir() {
    local platform
    platform="$(detect_platform)"

    case "$platform" in
    macos)
        echo "$CURSOR_CONFIG_MACOS"
        ;;
    linux)
        echo "$CURSOR_CONFIG_LINUX"
        ;;
    *)
        echo "$HOME/.cursor"
        ;;
    esac
}

get_cursor_workspace_storage() {
    local platform
    platform="$(detect_platform)"

    case "$platform" in
    macos)
        echo "$CURSOR_WORKSPACE_MACOS"
        ;;
    linux)
        echo "$CURSOR_WORKSPACE_LINUX"
        ;;
    *)
        echo "$HOME/.cursor/workspaceStorage"
        ;;
    esac
}

get_cursor_app_support_dir() {
    local platform
    platform="$(detect_platform)"

    case "$platform" in
    macos)
        echo "$HOME/Library/Application Support/Cursor"
        ;;
    linux)
        echo "$HOME/.config/Cursor"
        ;;
    *)
        echo "$HOME/.cursor"
        ;;
    esac
}

get_application_paths() {
    local app_name="$1"
    local platform
    platform="$(detect_platform)"

    case "$app_name" in
    cursor)
        case "$platform" in
        macos)
            echo "$CURSOR_APP_MACOS"
            ;;
        linux)
            command -v cursor 2>/dev/null || echo ""
            ;;
        *)
            echo ""
            ;;
        esac
        ;;
    claude-code)
        command -v claude 2>/dev/null || echo ""
        ;;
    windsurf)
        case "$platform" in
        macos)
            echo "/Applications/Windsurf.app"
            ;;
        linux)
            command -v windsurf 2>/dev/null || echo ""
            ;;
        *)
            echo ""
            ;;
        esac
        ;;
    *)
        echo ""
        ;;
    esac
}

is_application_installed() {
    local app_name="$1"
    local app_path
    app_path="$(get_application_paths "$app_name")"

    if [[ -n "$app_path" ]]; then
        if [[ -d "$app_path" ]] || [[ -f "$app_path" ]]; then
            return 0
        fi
    fi

    return 1
}

get_claude_home_dir() {
    echo "$CLAUDE_HOME_DIR"
}

get_windsurf_config_dir() {
    echo "$WINDSURF_CONFIG_DIR"
}

normalize_path() {
    local path="$1"

    # Handle tilde expansion
    if [[ "$path" == "~"* ]]; then
        path="${path/#~/$HOME}"
    fi

    # Resolve to absolute path if possible
    if [[ -e "$path" ]]; then
        path="$(cd "$path" && pwd -P)"
    fi

    echo "$path"
}
