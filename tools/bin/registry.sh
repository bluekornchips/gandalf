#!/usr/bin/env bash

# Simple Agentic Tool Registry Management for Gandalf
# Manages ~/.gandalf/registry.json with agentic tool name and folder location

set -euo pipefail

REGISTRY_FILE="$HOME/.gandalf/registry.json"

# Missing function: Get Cursor config directory
get_cursor_config_dir() {
    echo "$HOME/.cursor"
}

# Missing function: Check if application is installed
is_application_installed() {
    local app_name="$1"
    
    # Check common installation paths
    case "$app_name" in
        "cursor")
            if [[ -d "/Applications/Cursor.app" ]] || \
               [[ -d "$HOME/Applications/Cursor.app" ]] || \
               command -v cursor >/dev/null 2>&1 || \
               command -v Cursor >/dev/null 2>&1; then
                return 0
            fi
            ;;
        "claude")
            if [[ -d "/Applications/Claude.app" ]] || \
               [[ -d "$HOME/Applications/Claude.app" ]] || \
               command -v claude >/dev/null 2>&1 || \
               command -v claude-code >/dev/null 2>&1 || \
               [[ -d "$HOME/.claude" ]] || \
               [[ -d "$HOME/.config/claude" ]]; then
                return 0
            fi
            ;;
        "windsurf")
            if [[ -d "/Applications/Windsurf.app" ]] || \
               [[ -d "$HOME/Applications/Windsurf.app" ]] || \
               command -v windsurf >/dev/null 2>&1 || \
               command -v Windsurf >/dev/null 2>&1; then
                return 0
            fi
            ;;
        *)
            # Generic check
            if command -v "$app_name" >/dev/null 2>&1; then
                return 0
            fi
            ;;
    esac
    
    return 1
}

detect_agentic_tool() {
    # Check for Claude Code environment variables
    if [[ "${CLAUDECODE:-}" == "1" ]] || [[ "${CLAUDE_CODE_ENTRYPOINT:-}" == "cli" ]]; then
        echo "claude-code"
        return 0
    fi

    # Check for Cursor environment variables
    if [[ -n "${CURSOR_TRACE_ID:-}" ]] || [[ -n "${CURSOR_WORKSPACE:-}" ]] || [[ "${VSCODE_INJECTION:-}" == "1" ]]; then
        echo "cursor"
        return 0
    fi

    if command -v pgrep >/dev/null 2>&1; then
        if pgrep -f "claude" >/dev/null 2>&1 || pgrep -i "claude" >/dev/null 2>&1; then
            echo "claude-code"
            return 0
        fi

        # Cursor might appear as "Cursor", "cursor", or "cursor.exe" on different platforms
        if pgrep -f "Cursor" >/dev/null 2>&1 || pgrep -f "cursor" >/dev/null 2>&1 || pgrep -i "cursor" >/dev/null 2>&1; then
            echo "cursor"
            return 0
        fi

        # Windsurf might appear differently on different platforms
        if pgrep -f "Windsurf" >/dev/null 2>&1 || pgrep -f "windsurf" >/dev/null 2>&1 || pgrep -i "windsurf" >/dev/null 2>&1; then
            echo "windsurf"
            return 0
        fi
    fi

    # Check for configuration directories
    if [[ -d "$HOME/.claude" ]] || [[ -d "$HOME/.config/claude" ]]; then
        echo "claude-code"
        return 0
    fi

    local cursor_config_dir
    cursor_config_dir=$(get_cursor_config_dir)
    if [[ -d "$cursor_config_dir" ]]; then
        echo "cursor"
        return 0
    fi

    if [[ -d "$HOME/.codeium/windsurf" ]]; then
        echo "windsurf"
        return 0
    fi

    # Check for application installation using platform-aware detection
    if is_application_installed "cursor"; then
        echo "cursor"
        return 0
    fi

    if is_application_installed "claude"; then
        echo "claude-code"
        return 0
    fi

    if is_application_installed "windsurf"; then
        echo "windsurf"
        return 0
    fi

    # Default fallback
    echo "${GANDALF_FALLBACK_TOOL:-cursor}"
}

auto_register_cursor() {
    echo "Auto-registering Cursor IDE..."

    local cursor_config_dir
    cursor_config_dir=$(get_cursor_config_dir)

    if [[ -d "$cursor_config_dir" ]]; then
        register_agentic_tool "cursor" "$cursor_config_dir"
        echo "Auto-registered Cursor IDE"
    else
        echo "Cursor config directory not found: $cursor_config_dir"
        return 1
    fi
}

auto_register_claude_code() {
    echo "Auto-registering Claude Code..."

    local claude_config_dir="$HOME/.claude"
    local claude_alt_config_dir="$HOME/.config/claude"

    # Use whichever config directory exists
    if [[ -d "$claude_config_dir" ]]; then
        register_agentic_tool "claude-code" "$claude_config_dir"
        echo "Auto-registered Claude Code"
    elif [[ -d "$claude_alt_config_dir" ]]; then
        register_agentic_tool "claude-code" "$claude_alt_config_dir"
        echo "Auto-registered Claude Code"
    else
        echo "Claude Code config directory not found"
        return 1
    fi
}

auto_register_windsurf() {
    echo "Auto-registering Windsurf IDE..."

    local windsurf_config_dir="$HOME/.codeium/windsurf"

    if [[ -d "$windsurf_config_dir" ]]; then
        register_agentic_tool "windsurf" "$windsurf_config_dir"
        echo "Auto-registered Windsurf IDE"
    else
        echo "Windsurf config directory not found: $windsurf_config_dir"
        return 1
    fi
}

auto_register_detected() {
    local detected_tool
    detected_tool=$(detect_agentic_tool)

    echo "Auto-registering detected agentic tool: $detected_tool"

    case "$detected_tool" in
    "cursor")
        auto_register_cursor
        ;;
    "claude-code")
        auto_register_claude_code
        ;;
    "windsurf")
        auto_register_windsurf
        ;;
    *)
        echo "Unknown agentic tool type: $detected_tool"
        return 1
        ;;
    esac
}

# Core registry functions
ensure_registry_file() {
    if [[ ! -f "$REGISTRY_FILE" ]]; then
        mkdir -p "$(dirname "$REGISTRY_FILE")"
        echo '{}' >"$REGISTRY_FILE"
    fi
}

register_agentic_tool() {
    local tool_name="$1"
    local tool_path="$2"

    ensure_registry_file

    # Use jq to update the registry
    local temp_file
    temp_file=$(mktemp)
    jq --arg name "$tool_name" --arg path "$tool_path" '. + {($name): $path}' "$REGISTRY_FILE" >"$temp_file"
    mv "$temp_file" "$REGISTRY_FILE"

    echo "Registered $tool_name at $tool_path"
}

unregister_agentic_tool() {
    local tool_name="$1"

    if [[ ! -f "$REGISTRY_FILE" ]]; then
        echo "Registry file not found"
        return 1
    fi

    local temp_file
    temp_file=$(mktemp)
    jq --arg name "$tool_name" 'del(.[$name])' "$REGISTRY_FILE" >"$temp_file"
    mv "$temp_file" "$REGISTRY_FILE"

    echo "Unregistered $tool_name"
}

list_agentic_tools() {
    ensure_registry_file

    echo "Registered agentic tools:"
    jq -r 'to_entries[] | "\(.key): \(.value)"' "$REGISTRY_FILE"
}

get_agentic_tool_path() {
    local tool_name="$1"

    if [[ ! -f "$REGISTRY_FILE" ]]; then
        return 1
    fi

    jq -r --arg name "$tool_name" '.[$name] // empty' "$REGISTRY_FILE"
}

usage() {
    cat <<EOF
Usage: $0 {register|unregister|list|get|detect|auto-register} [args...]

Commands:
    register <tool_name> <tool_path>  Register an agentic tool manually
    unregister <tool_name>            Unregister an agentic tool
    list                              List all registered agentic tools
    get <tool_name>                   Get path for an agentic tool
    detect                            Detect current agentic tool environment
    auto-register [tool_name]         Auto-register agentic tool (detected or specified)

Examples:
    $0 register cursor /Users/user/.cursor
    $0 list
    $0 detect
    $0 auto-register
    $0 auto-register cursor

Registry Location: $REGISTRY_FILE
EOF
}

main() {
    case "${1:-}" in
    register)
        if [[ $# -ne 3 ]]; then
            echo "Usage: $0 register <tool_name> <tool_path>"
            exit 1
        fi
        register_agentic_tool "$2" "$3"
        ;;
    unregister)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 unregister <tool_name>"
            exit 1
        fi
        unregister_agentic_tool "$2"
        ;;
    list)
        list_agentic_tools
        ;;
    get)
        if [[ $# -ne 2 ]]; then
            echo "Usage: $0 get <tool_name>"
            exit 1
        fi
        get_agentic_tool_path "$2"
        ;;
    detect)
        detect_agentic_tool
        ;;
    auto-register)
        if [[ $# -eq 2 ]]; then
            # Auto-register specific tool
            case "$2" in
            "cursor")
                auto_register_cursor
                ;;
            "claude-code")
                auto_register_claude_code
                ;;
            "windsurf")
                auto_register_windsurf
                ;;
            *)
                echo "Unknown agentic tool: $2"
                exit 1
                ;;
            esac
        else
            # Auto-register detected tool
            auto_register_detected
        fi
        ;;
    *)
        usage
        exit 1
        ;;
    esac
}

main "$@"
