#!/bin/bash
# Platform detection utilities for cross-platform compatibility

detect_platform() {
    case "$(uname -s)" in
    Darwin*)
        echo "macos"
        ;;
    Linux*)
        echo "linux"
        ;;
    CYGWIN* | MINGW32* | MSYS* | MINGW*)
        echo "windows"
        ;;
    *)
        echo "unknown"
        ;;
    esac
}

get_cursor_config_dir() {
    case "$(detect_platform)" in
    macos)
        echo "$HOME/.cursor"
        ;;
    linux)
        echo "$HOME/.config/Cursor/User"
        ;;
    *)
        echo "$HOME/.cursor"
        ;;
    esac
}

get_cursor_app_support_dir() {
    case "$(detect_platform)" in
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

get_cursor_workspace_storage() {
    case "$(detect_platform)" in
    macos)
        echo "$HOME/Library/Application Support/Cursor/workspaceStorage"
        ;;
    linux)
        echo "$HOME/.config/Cursor/workspaceStorage"
        ;;
    *)
        echo "$HOME/.cursor/workspaceStorage"
        ;;
    esac
}

get_application_paths() {
    local app_name="$1"
    case "$(detect_platform)" in
    macos)
        case "$app_name" in
        cursor)
            echo "/Applications/Cursor.app"
            ;;
        windsurf)
            echo "/Applications/Windsurf.app"
            ;;
        *)
            echo ""
            ;;
        esac
        ;;
    linux)
        # On Linux, applications are typically in PATH or installed via package managers
        # Check common installation locations
        case "$app_name" in
        cursor)
            for path in "/usr/bin/cursor" "/usr/local/bin/cursor" "/opt/cursor/cursor" "$HOME/.local/bin/cursor"; do
                if [[ -x "$path" ]]; then
                    echo "$path"
                    return 0
                fi
            done
            ;;
        windsurf)
            for path in "/usr/bin/windsurf" "/usr/local/bin/windsurf" "/opt/windsurf/windsurf" "$HOME/.local/bin/windsurf"; do
                if [[ -x "$path" ]]; then
                    echo "$path"
                    return 0
                fi
            done
            ;;
        esac
        echo ""
        ;;
    *)
        echo ""
        ;;
    esac
}

is_application_installed() {
    local app_name="$1"
    local app_path
    app_path=$(get_application_paths "$app_name")

    if [[ -n "$app_path" ]]; then
        case "$(detect_platform)" in
        macos)
            [[ -d "$app_path" ]]
            ;;
        linux)
            [[ -x "$app_path" ]]
            ;;
        *)
            [[ -e "$app_path" ]]
            ;;
        esac
    else
        # Fallback: check if command is in PATH
        command -v "$app_name" >/dev/null 2>&1
    fi
}
