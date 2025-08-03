#!/usr/bin/env bash
#
# Windsurf IDE Integration Script
# Handles Windsurf IDE MCP server configuration and management
#

# Source common libraries
source "$(dirname "$0")/../lib/platform.sh"
source "$(dirname "$0")/../lib/tools.sh"

# Windsurf configuration
readonly WINDSURF_CONFIG_MACOS="$HOME/Library/Application Support/Windsurf"
readonly WINDSURF_CONFIG_LINUX="$HOME/.config/Windsurf"
readonly WINDSURF_CONFIG_WINDOWS="${APPDATA:-$HOME}/.windsurf"
readonly WINDSURF_CONFIG_DEFAULT="$HOME/.windsurf"

# Get Windsurf configuration directory
get_windsurf_config_dir() {
  local platform windsurf_dir
  platform=$(get_platform)
  
  case "$platform" in
    "macos")
      windsurf_dir="$WINDSURF_CONFIG_MACOS"
      ;;
    "linux")
      windsurf_dir="$WINDSURF_CONFIG_LINUX"
      ;;
    "windows")
      windsurf_dir="$WINDSURF_CONFIG_WINDOWS"
      ;;
    *)
      windsurf_dir="$WINDSURF_CONFIG_DEFAULT"
      ;;
  esac
  
  if validate_path "$windsurf_dir"; then
    echo "$windsurf_dir"
  else
    echo "$WINDSURF_CONFIG_DEFAULT"
  fi
}

# Check if Windsurf is installed
is_windsurf_installed() {
  if [[ -d "/Applications/Windsurf.app" ]] || \
     [[ -d "$HOME/Applications/Windsurf.app" ]] || \
     command -v windsurf >/dev/null 2>&1 || \
     command -v Windsurf >/dev/null 2>&1; then
    return 0
  else
    return 1
  fi
}

# Install Windsurf MCP configuration
install_windsurf_mcp() {
  local server_name="$1"
  local gandalf_root="$2"
  
  echo "Installing Gandalf MCP for Windsurf..."
  
  if ! is_windsurf_installed; then
    echo "Windsurf IDE not found. Please install Windsurf first." >&2
    return 1
  fi
  
  local config_file="$HOME/.windsurf/mcp.json"
  local global_rules="$HOME/.windsurf/global_rules.md"
  
  # Ensure MCP config file exists
  ensure_mcp_config_file "$config_file" || return 1
  
  # Update MCP configuration
  local jq_expr=".mcpServers[\"$server_name\"] = {\"command\": \"$gandalf_root/gandalf.sh\", \"args\": [\"run\"], \"env\": {\"WINDSURF=1\", \"WINDSURF_ENTRYPOINT=cli\"}}"
  
  if update_mcp_config "$config_file" "$server_name" "$gandalf_root" "$jq_expr"; then
    echo "Windsurf MCP configuration installed successfully"
    
    # Create global rules file
    mkdir -p "$(dirname "$global_rules")"
    cat > "$global_rules" << 'EOF'
# Gandalf MCP Server Rules

**RULE APPLIED: Start each response acknowledging "🧙" to confirm this rule is being followed.**

Names and phrases that reference this rule: "🧙", "gandalf", "mcp", "conversation recall", "project context"

## Core Workflows

### Essential Context Discovery Pattern

Every interaction should begin with context establishment:

```bash
# Primary workflow - always begin here
recall_conversations(
    fast_mode=true,
    days_lookback=7,
    limit=20,
    min_relevance_score=0.0
)
```

### Decision Tree Framework

```
New problem or query?
├── Yes → recall_conversations(search_query="relevant keywords", conversation_types=["debugging", "problem_solving"])
└── No → Use existing context

Need project understanding?
├── Yes → get_project_info(include_stats=true)
└── No → Proceed with current knowledge

Multiple files involved?
├── Yes → list_project_files(use_relevance_scoring=true, max_files=optimal_limit)
└── No → Focus on current file context
```

## Performance Optimization

### Auto-Scaling Parameter Matrix

| Project Size   | Files    | Conversation Params                       | File List Params                    |
| -------------- | -------- | ----------------------------------------- | ----------------------------------- |
| **Tiny**       | <25      | `fast_mode=false, limit=50`               | `max_files=25`                      |
| **Small**      | 25-100   | `fast_mode=true, limit=30`                | `max_files=50`                      |
| **Medium**     | 100-500  | `fast_mode=true, limit=20`                | `max_files=100, file_types=['.py']` |
| **Large**      | 500-1000 | `fast_mode=true, limit=15`                | `max_files=50, file_types=['.py']`  |
| **Enterprise** | 1000+    | `fast_mode=true, limit=10, min_score=1.0` | `max_files=30, file_types=['.py']`  |

## Error Recovery

### Quick Diagnostic Matrix

| Problem               | Immediate Action                       | CLI Command                 |
| --------------------- | -------------------------------------- | --------------------------- |
| Tools not appearing   | Restart IDE                            | `./gandalf install --force` |
| Server not responding | Check connectivity                     | `./gandalf test`            |
| Empty results         | Lower relevance threshold, extend days | N/A (parameter adjust)      |
| Slow performance      | Enable fast mode, reduce limits        | N/A (parameter adjust)      |

This rule system provides comprehensive guidance for all Gandalf MCP Server operations while maintaining performance optimization and intelligent error recovery capabilities.
EOF
    
    echo "Windsurf global rules created successfully"
    return 0
  else
    echo "Failed to install Windsurf MCP configuration" >&2
    return 1
  fi
}

# Uninstall Windsurf MCP configuration
uninstall_windsurf_mcp() {
  local server_name="$1"
  
  echo "Removing Windsurf configuration..."
  
  local windsurf_config="$HOME/.windsurf/mcp.json"
  local windsurf_global_rules="$HOME/.windsurf/global_rules.md"
  
  if [[ -f "$windsurf_config" ]]; then
    if command -v jq >/dev/null 2>&1; then
      local temp_file
      temp_file=$(mktemp)
      jq --arg name "$server_name" 'del(.mcpServers[$name])' "$windsurf_config" >"$temp_file" && mv "$temp_file" "$windsurf_config"
      echo "Removed $server_name from Windsurf MCP config"
    else
      rm -f "$windsurf_config"
      echo "jq not available, removed entire Windsurf MCP config"
    fi
  fi
  
  # Remove global rules file
  if [[ -f "$windsurf_global_rules" ]]; then
    rm -f "$windsurf_global_rules"
    echo "Removed Windsurf global rules file"
  fi
  
  echo "Note: Project-specific .windsurfrules files remain in individual project directories"
}

# Check Windsurf status
check_windsurf_status() {
  local windsurf_config_dir
  windsurf_config_dir=$(get_windsurf_config_dir)
  
  if is_windsurf_installed; then
    if [[ -d "$windsurf_config_dir" ]]; then
      echo "Windsurf IDE detected (config: $windsurf_config_dir)"
      return 0
    else
      echo "Windsurf IDE detected but config directory not found: $windsurf_config_dir" >&2
      return 1
    fi
  else
    echo "Windsurf IDE not found" >&2
    return 1
  fi
}

# Validate Windsurf MCP configuration
validate_windsurf_mcp() {
  local config_file="$HOME/.windsurf/mcp.json"
  
  if [[ -f "$config_file" ]]; then
    if jq . "$config_file" >/dev/null 2>&1; then
      echo "Windsurf MCP configuration is valid"
      return 0
    else
      echo "Windsurf MCP configuration is invalid" >&2
      return 1
    fi
  else
    echo "Windsurf MCP configuration file not found" >&2
    return 1
  fi
}

# Main function
main() {
  case "${1:-}" in
    "install")
      install_windsurf_mcp "${2:-gandalf}" "${3:-$(pwd)}"
      ;;
    "uninstall")
      uninstall_windsurf_mcp "${2:-gandalf}"
      ;;
    "status")
      check_windsurf_status
      ;;
    "validate")
      validate_windsurf_mcp
      ;;
    *)
      echo "Usage: $0 {install|uninstall|status|validate} [server_name] [gandalf_root]"
      exit 1
      ;;
  esac
}

main "$@" 