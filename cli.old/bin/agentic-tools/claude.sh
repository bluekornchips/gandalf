#!/usr/bin/env bash
#
# Claude Code Integration Script
# Handles Claude Code MCP server configuration and management
#

# Source common libraries
source "$(dirname "$0")/../lib/platform.sh"
source "$(dirname "$0")/../lib/tools.sh"

# Claude Code configuration
readonly CLAUDE_HOME_MACOS="$HOME/Library/Application Support/Claude"
readonly CLAUDE_HOME_LINUX="$HOME/.config/Claude"
readonly CLAUDE_HOME_WINDOWS="${APPDATA:-$HOME}/.claude"
readonly CLAUDE_HOME_DEFAULT="$HOME/.claude"

# Get Claude Code home directory
get_claude_home_dir() {
  local platform claude_dir
  platform=$(get_platform)
  
  case "$platform" in
    "macos")
      claude_dir="$CLAUDE_HOME_MACOS"
      ;;
    "linux")
      claude_dir="$CLAUDE_HOME_LINUX"
      ;;
    "windows")
      claude_dir="$CLAUDE_HOME_WINDOWS"
      ;;
    *)
      claude_dir="$CLAUDE_HOME_DEFAULT"
      ;;
  esac
  
  if validate_path "$claude_dir"; then
    echo "$claude_dir"
  else
    echo "$CLAUDE_HOME_DEFAULT"
  fi
}

# Install Claude Code MCP configuration
install_claude_mcp() {
  local server_name="$1"
  local gandalf_root="$2"
  
  echo "Installing Gandalf MCP for Claude Code..."
  
  if ! is_application_installed "claude"; then
    echo "Claude Code not found. Please install Claude Code first." >&2
    return 1
  fi
  
  if ! command -v claude &>/dev/null; then
    echo "Claude CLI not available for MCP configuration" >&2
    echo "Claude Code detected but CLI not found. Skipping MCP setup"
    echo "Note: Claude Code MCP may need manual configuration"
    return 1
  fi
  
  echo "Attempting Claude Code MCP configuration."
  
  # Remove existing configuration
  claude mcp remove "$server_name" -s local 2>/dev/null || true
  claude mcp remove "$server_name" -s user 2>/dev/null || true
  
  # Add new configuration
  if claude mcp add "$server_name" "$gandalf_root/gandalf.sh" -s user "run" \
    -e "CLAUDECODE=1" \
    -e "CLAUDE_CODE_ENTRYPOINT=cli" 2>/dev/null; then
    echo "Claude Code MCP configuration installed successfully"
    return 0
  else
    echo "Claude Code MCP configuration failed, but continuing installation" >&2
    echo "Note: Claude Code may need manual MCP configuration"
    return 1
  fi
}

# Uninstall Claude Code MCP configuration
uninstall_claude_mcp() {
  local server_name="$1"
  
  echo "Removing Claude Code configuration..."
  
  if command -v claude >/dev/null 2>&1; then
    claude mcp remove "$server_name" -s user 2>/dev/null || true
    claude mcp remove "$server_name" -s local 2>/dev/null || true
    echo "Removed Claude Code MCP configuration"
  else
    echo "Claude CLI not available - checking manual config files"
    
    local claude_config="$HOME/.claude/mcp.json"
    if [[ -f "$claude_config" ]]; then
      if command -v jq >/dev/null 2>&1; then
        local temp_file
        temp_file=$(mktemp)
        jq --arg name "$server_name" 'del(.mcpServers[$name])' "$claude_config" >"$temp_file" && mv "$temp_file" "$claude_config"
        echo "Removed $server_name from Claude Code MCP config"
      else
        rm -f "$claude_config"
        echo "jq not available, removed entire Claude Code MCP config"
      fi
    fi
  fi
}

# Check Claude Code status
check_claude_status() {
  local claude_config_dir
  claude_config_dir=$(get_claude_home_dir)
  
  if [[ -d "$claude_config_dir" ]]; then
    echo "Claude Code detected (config: $claude_config_dir)"
    return 0
  else
    echo "Claude Code config directory not found: $claude_config_dir" >&2
    return 1
  fi
}

# Main function
main() {
  case "${1:-}" in
    "install")
      install_claude_mcp "${2:-gandalf}" "${3:-$(pwd)}"
      ;;
    "uninstall")
      uninstall_claude_mcp "${2:-gandalf}"
      ;;
    "status")
      check_claude_status
      ;;
    *)
      echo "Usage: $0 {install|uninstall|status} [server_name] [gandalf_root]"
      exit 1
      ;;
  esac
}

main "$@" 