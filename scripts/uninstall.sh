#!/bin/bash
# Gandalf MCP Server Uninstall Script
# Simple removal of all Gandalf MCP server configurations

set -euo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

usage() {
    cat <<EOF
Usage: uninstall.sh [OPTIONS]

Remove Gandalf MCP server configurations.

Options:
    --force            Skip confirmation prompts
    --local            Remove from current directory only
    --local-dir <dir>  Remove from specific directory
    --help             Show this help

Environment Variables:
    TEST_MODE=true     Auto-run mode for testing (skips prompts)

Examples:
    uninstall.sh                        # Remove global installation
    uninstall.sh --local                # Remove from current directory
    uninstall.sh --local-dir /path      # Remove from specific directory
    uninstall.sh --force                # Skip confirmation
    TEST_MODE=true uninstall.sh         # Auto-run for testing

EOF
}

FORCE_MODE=false
LOCAL_MODE=false
LOCAL_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
    --force)
        FORCE_MODE=true
        shift
        ;;
    --local)
        LOCAL_MODE=true
        LOCAL_DIR="$(pwd)"
        shift
        ;;
    --local-dir)
        LOCAL_MODE=true
        LOCAL_DIR="$2"
        if [[ ! -d "$LOCAL_DIR" ]]; then
            echo "Error: Directory does not exist: $LOCAL_DIR" >&2
            exit 1
        fi
        LOCAL_DIR="$(cd "$LOCAL_DIR" && pwd)"
        shift 2
        ;;
    --help)
        usage
        exit 0
        ;;
    *)
        echo "Unknown option: $1" >&2
        usage
        exit 1
        ;;
    esac
done

# Simple confirmation without hanging prompts
if [[ "$FORCE_MODE" == "false" && "${TEST_MODE:-false}" != "true" ]]; then
    if [[ "$LOCAL_MODE" == "true" ]]; then
        echo "Remove Gandalf from: $LOCAL_DIR"
    else
        echo "Remove Gandalf globally"
    fi
    echo -n "Continue? (y/N): "
    read -r response
    if [[ "$response" != "y" && "$response" != "Y" ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

remove_cursor_config() {
    local config_dir="$1"
    local mcp_file="$config_dir/.cursor/mcp.json"
    local rules_file="$config_dir/.cursor/rules/gandalf-rules.mdc"
    
    if [[ -f "$mcp_file" ]]; then
        # Simple removal - just delete the file if it only has gandalf
        if grep -q "gandalf" "$mcp_file" 2>/dev/null; then
            rm -f "$mcp_file"
            echo "Removed Cursor MCP config"
        fi
    fi
    
    if [[ -f "$rules_file" ]]; then
        rm -f "$rules_file"
        echo "Removed Cursor rules file"
    fi
    
    # Clean up empty directories
    if [[ -d "$config_dir/.cursor/rules" && -z "$(ls -A "$config_dir/.cursor/rules")" ]]; then
        rmdir "$config_dir/.cursor/rules" 2>/dev/null || true
    fi
}

remove_claude_config() {
    local config_dir="$1"
    local settings_file="$config_dir/.claude/local_settings.json"
    
    if [[ -f "$settings_file" ]]; then
        rm -f "$settings_file"
        echo "Removed Claude Code settings"
    fi
    
    # Clean up empty directories
    if [[ -d "$config_dir/.claude" && -z "$(ls -A "$config_dir/.claude")" ]]; then
        rmdir "$config_dir/.claude" 2>/dev/null || true
    fi
}

remove_windsurf_config() {
    local config_dir="$1"
    local mcp_file="$config_dir/.windsurf/mcp_config.json"
    local rules_file="$config_dir/.windsurf/rules.md"
    
    if [[ -f "$mcp_file" ]]; then
        rm -f "$mcp_file"
        echo "Removed Windsurf MCP config"
    fi
    
    if [[ -f "$rules_file" ]]; then
        rm -f "$rules_file"
        echo "Removed Windsurf rules file"
    fi
    
    # Clean up empty directories
    if [[ -d "$config_dir/.windsurf" && -z "$(ls -A "$config_dir/.windsurf")" ]]; then
        rmdir "$config_dir/.windsurf" 2>/dev/null || true
    fi
}

remove_gandalf_directory() {
    local gandalf_dir="$1"
    
    if [[ -d "$gandalf_dir" ]]; then
        rm -rf "$gandalf_dir"
        echo "Removed .gandalf directory"
    fi
}

if [[ "$LOCAL_MODE" == "true" ]]; then
    echo "Local uninstall mode for: $LOCAL_DIR"
    
    # Remove local configurations
    remove_cursor_config "$LOCAL_DIR"
    remove_claude_config "$LOCAL_DIR"
    remove_windsurf_config "$LOCAL_DIR"
    remove_gandalf_directory "$LOCAL_DIR/.gandalf"
    
    echo "Local uninstall completed"
else
    echo "Global uninstall mode"
    
    # Stop any running gandalf processes
    if ! [[ "${TEST_MODE:-false}" == "true" ]]; then
        pkill -f "gandalf.*main.py" 2>/dev/null || true
    fi
    
    # Remove global configurations
    remove_cursor_config "$HOME"
    remove_claude_config "$HOME"
    remove_windsurf_config "$HOME"
    remove_gandalf_directory "$HOME/.gandalf"
    
    echo "Global uninstall completed"
fi

echo "Uninstall completed successfully!"
