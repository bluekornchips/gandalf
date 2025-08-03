#!/usr/bin/env bash
#
# Cursor IDE Integration Script
# Handles Cursor IDE MCP server configuration and management
#

# Source common libraries
source "$(dirname "$0")/../lib/platform.sh"
source "$(dirname "$0")/../lib/tools.sh"

# Cursor IDE configuration
readonly CURSOR_APP_MACOS="/Applications/Cursor.app"
readonly CURSOR_CONFIG_MACOS="$HOME/Library/Application Support/Cursor/User"
readonly CURSOR_WORKSPACE_MACOS="$HOME/Library/Application Support/Cursor/User/workspaceStorage"
readonly CURSOR_CONFIG_LINUX="$HOME/.config/Cursor/User"
readonly CURSOR_WORKSPACE_LINUX="$HOME/.config/Cursor/User/workspaceStorage"
readonly CURSOR_CONFIG_WSL="$HOME/.config/Cursor/User"
readonly CURSOR_WORKSPACE_WSL="$HOME/.config/Cursor/User/workspaceStorage"

# Get Cursor configuration directory
get_cursor_config_dir() {
  local platform config_dir
  platform=$(get_platform)
  
  case "$platform" in
    "macos")
      config_dir="$CURSOR_CONFIG_MACOS"
      ;;
    "linux")
      config_dir="$CURSOR_CONFIG_LINUX"
      ;;
    "wsl")
      config_dir="$CURSOR_CONFIG_WSL"
      ;;
    "windows")
      config_dir="${APPDATA:-$HOME}/.cursor/User"
      ;;
    *)
      config_dir="$HOME/.cursor/User"
      ;;
  esac
  
  if validate_path "$config_dir"; then
    echo "$config_dir"
  else
    echo "$HOME/.cursor/User"
  fi
}

# Get Cursor workspace directory
get_cursor_workspace_dir() {
  local platform workspace_dir
  platform=$(get_platform)
  
  case "$platform" in
    "macos")
      workspace_dir="$CURSOR_WORKSPACE_MACOS"
      ;;
    "linux")
      workspace_dir="$CURSOR_WORKSPACE_LINUX"
      ;;
    "wsl")
      workspace_dir="$CURSOR_WORKSPACE_WSL"
      ;;
    "windows")
      workspace_dir="${APPDATA:-$HOME}/.cursor/User/workspaceStorage"
      ;;
    *)
      workspace_dir="$HOME/.cursor/User/workspaceStorage"
      ;;
  esac
  
  if validate_path "$workspace_dir"; then
    echo "$workspace_dir"
  else
    echo "$HOME/.cursor/User/workspaceStorage"
  fi
}

# Install Cursor MCP configuration
install_cursor_mcp() {
  local server_name="$1"
  local gandalf_root="$2"
  
  echo "Installing Gandalf MCP for Cursor..."
  
  local config_file="$HOME/.cursor/mcp.json"
  local jq_expr=".mcpServers[\"$server_name\"] = {\"command\": \"$gandalf_root/gandalf.sh\", \"args\": [\"run\"], \"env\": {\"CURSOR=1\", \"CURSOR_ENTRYPOINT=cli\"}}"
  
  # Ensure MCP config file exists
  ensure_mcp_config_file "$config_file" || return 1
  
  # Update MCP configuration
  if update_mcp_config "$config_file" "$server_name" "$gandalf_root" "$jq_expr"; then
    echo "Cursor MCP configuration installed successfully"
    return 0
  else
    # Fallback: manual JSON manipulation
    local temp_file
    temp_file=$(mktemp)
    if jq --arg name "$server_name" \
      --arg cmd "$gandalf_root/gandalf.sh" \
      --argjson env '{"CURSOR": "1", "CURSOR_ENTRYPOINT": "cli"}' \
      '.mcpServers[$name] = {"command": $cmd, "args": ["run"], "env": $env}' \
      "$config_file" >"$temp_file" && mv "$temp_file" "$config_file"; then
      echo "Cursor MCP configuration installed successfully"
      return 0
    else
      echo "Failed to install Cursor MCP configuration" >&2
      return 1
    fi
  fi
}

# Uninstall Cursor MCP configuration
uninstall_cursor_mcp() {
  local server_name="$1"
  
  echo "Removing Cursor configuration..."
  
  local cursor_config="$HOME/.cursor/mcp.json"
  local cursor_rules_dir="$HOME/.cursor/rules"
  local cursor_rules="$cursor_rules_dir/gandalf-rules.mdc"
  
  if [[ -f "$cursor_config" ]]; then
    if command -v jq >/dev/null 2>&1; then
      local temp_file
      temp_file=$(mktemp)
      jq --arg name "$server_name" 'del(.mcpServers[$name])' "$cursor_config" >"$temp_file" && mv "$temp_file" "$cursor_config"
      echo "Removed $server_name from Cursor MCP config"
    else
      rm -f "$cursor_config"
      echo "jq not available, removed entire Cursor MCP config"
    fi
  fi
  
  # Remove rules file
  if [[ -f "$cursor_rules" ]]; then
    rm -f "$cursor_rules"
    echo "Removed Cursor rules file"
  fi
  
  # Clean up empty rules directory
  if [[ -d "$cursor_rules_dir" ]] && [[ -z "$(ls -A "$cursor_rules_dir" 2>/dev/null)" ]]; then
    rmdir "$cursor_rules_dir" 2>/dev/null || true
    echo "Removed empty Cursor rules directory"
  fi
}

# Check Cursor status
check_cursor_status() {
  local cursor_config_dir
  cursor_config_dir=$(get_cursor_config_dir)
  
  if [[ -d "$cursor_config_dir" ]]; then
    echo "Cursor IDE detected (config: $cursor_config_dir)"
    return 0
  else
    echo "Cursor config directory not found: $cursor_config_dir" >&2
    return 1
  fi
}

# Validate Cursor MCP configuration
validate_cursor_mcp() {
  local config_file="$HOME/.cursor/mcp.json"
  
  if [[ -f "$config_file" ]]; then
    if jq . "$config_file" >/dev/null 2>&1; then
      echo "Cursor MCP configuration is valid"
      return 0
    else
      echo "Cursor MCP configuration is invalid" >&2
      return 1
    fi
  else
    echo "Cursor MCP configuration file not found" >&2
    return 1
  fi
}

# Main function
main() {
  case "${1:-}" in
    "install")
      install_cursor_mcp "${2:-gandalf}" "${3:-$(pwd)}"
      ;;
    "uninstall")
      uninstall_cursor_mcp "${2:-gandalf}"
      ;;
    "status")
      check_cursor_status
      ;;
    "validate")
      validate_cursor_mcp
      ;;
    *)
      echo "Usage: $0 {install|uninstall|status|validate} [server_name] [gandalf_root]"
      exit 1
      ;;
  esac
}

main "$@" 