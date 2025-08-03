#!/usr/bin/env bash
# Gandalf MCP Server Installation Script (Simplified)
# Uses core library for common functionality

set -euo pipefail

# Source core libraries
readonly SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
readonly GANDALF_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_PATH")")")"
readonly LIB_DIR="$GANDALF_ROOT/tools/lib"

# Source core libraries
if [[ -f "$LIB_DIR/core.sh" ]]; then
  source "$LIB_DIR/core.sh"
else
  echo "Core library not found: $LIB_DIR/core.sh" >&2
  exit 1
fi

if [[ -f "$LIB_DIR/config.sh" ]]; then
  source "$LIB_DIR/config.sh"
else
  echo "Config library not found: $LIB_DIR/config.sh" >&2
  exit 1
fi

if [[ -f "$LIB_DIR/tools.sh" ]]; then
  source "$LIB_DIR/tools.sh"
else
  echo "Tools library not found: $LIB_DIR/tools.sh" >&2
  exit 1
fi

# Installation constants
readonly INSTALL_VERSION="2.0.0"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export GANDALF_HOME="${GANDALF_HOME:-$HOME/.${MCP_SERVER_NAME}}"

# Installation state variables
CURSOR_INSTALLED=false
CLAUDE_CODE_INSTALLED=false
WIND_SURF_INSTALLED=false

# Verify prerequisites
verify_prerequisites() {
  echo "Verifying system requirements..."

  if ! check_required_tools; then
    echo "Prerequisite check failed" >&2
    show_installation_help
    return 1
  fi

  if ! validate_directory "$GANDALF_ROOT/server" "Server directory"; then
    echo "Server directory validation failed" >&2
    return 1
  fi

  if ! validate_file "$GANDALF_ROOT/server/src/main.py" "Main server file"; then
    echo "Server file validation failed" >&2
    return 1
  fi

  echo "Prerequisites verified successfully"
  return 0
}

show_installation_help() {
  cat <<EOF

System Requirements Check Failed

Installation Options:

1. Full Development Environment (Recommended):
    Run the system setup script to install all development tools:
    ./gandalf setup

2. Minimal Installation:
    Install missing tools manually:
    - Python 3.12+: brew install python3 (macOS) or apt install python3 (Linux)
    - Git: brew install git (macOS) or apt install git (Linux)

3. Python Dependencies Only:
    pip install -r server/requirements.txt

EOF
}

# Detect and install for all tools
install_for_all_tools() {
  local server_name="$1"
  local gandalf_root="$2"
  local primary_tool="$3"

  echo "Installing Gandalf MCP for all supported tools..."

  local workspace_path="$(pwd -P)"

  # Install for each tool
  local -a tools=("cursor" "claude-code" "windsurf")
  local -a install_functions=("install_for_cursor" "install_for_claude" "install_for_windsurf")
  local -a success_vars=("CURSOR_INSTALLED" "CLAUDE_CODE_INSTALLED" "WIND_SURF_INSTALLED")
  local -a tool_names=("Cursor IDE" "Claude Code" "Windsurf IDE")

  for i in "${!tools[@]}"; do
    local tool="${tools[$i]}"
    local install_func="${install_functions[$i]}"
    local success_var="${success_vars[$i]}"
    local tool_name="${tool_names[$i]}"

    echo "=== Installing for ${tool_name} ==="

    if "$install_func" "$server_name" "$gandalf_root" "$workspace_path"; then
      declare "$success_var=true"
      echo "${tool_name} installation completed successfully"
    else
      echo "${tool_name} installation failed" >&2
    fi
  done

  # Update installation state
  local state_file="$GANDALF_HOME/$STATE_FILE_NAME"
  if [[ -f "$state_file" ]]; then
    update_installation_state "$state_file" "$CURSOR_INSTALLED" "$CLAUDE_CODE_INSTALLED" "$WIND_SURF_INSTALLED"
  fi

  # Show summary
  echo "=== Installation Summary ==="
  echo "Cursor:     $([ "$CURSOR_INSTALLED" = true ] && echo "Success" || echo "Failed")"
  echo "Claude Code: $([ "$CLAUDE_CODE_INSTALLED" = true ] && echo "Success" || echo "Failed")"
  echo "Windsurf:   $([ "$WIND_SURF_INSTALLED" = true ] && echo "Success" || echo "Failed")"

  if [[ "$CURSOR_INSTALLED" = true || "$CLAUDE_CODE_INSTALLED" = true || "$WIND_SURF_INSTALLED" = true ]]; then
    echo "At least one tool was configured successfully"
    return 0
  else
    echo "No tools were configured successfully" >&2
    return 1
  fi
}

# Create rules files
create_rules_files() {
  echo "Creating global rules files using create-rules script..."

  local create_rules_script="$GANDALF_ROOT/tools/bin/create-rules.sh"

  if [[ ! -f "$create_rules_script" ]]; then
    echo "create-rules script not found: $create_rules_script" >&2
    echo "Skipping rules file creation"
    return 0
  fi

  local force_flag=""
  if [[ "${FORCE:-false}" == "true" ]]; then
    force_flag="--force"
  fi

  if "$create_rules_script" $force_flag; then
    echo "Rules creation completed successfully"
    return 0
  else
    echo "Rules creation failed" >&2
    return 1
  fi
}

# Initialize agentic tools registry
initialize_registry() {
  echo "Initializing agentic tools registry..."

  if auto_register_all; then
    echo "Registry initialization completed successfully"
    return 0
  else
    echo "Registry initialization failed, but continuing..." >&2
    echo "You may need to run './gandalf registry auto-register' manually"
    return 1
  fi
}

# Check server connectivity
check_server_connectivity() {
  local max_attempts="${1:-$DEFAULT_MAX_ATTEMPTS}"
  local wait_time="${2:-$DEFAULT_WAIT_TIME}"
  local tool="${3:-cursor}"

  echo "Testing server connectivity for $tool..."
  echo "Waiting ${wait_time}s for $tool to recognize MCP server..."

  sleep "$wait_time"

  if wait_with_timeout "$max_attempts" "$wait_time" "server connectivity"; then
    echo "Server connectivity test: Success"
    return 0
  else
    echo "Server connectivity test failed after $max_attempts attempts" >&2
    return 1
  fi
}

# Parse command line arguments
parse_arguments() {
  FORCE_TOOL=""
  SKIP_TEST="false"
  DEBUG="false"
  WAIT_TIME="$DEFAULT_WAIT_TIME"

  while [[ $# -gt 0 ]]; do
    case "$1" in
    -f | --force)
      FORCE=true
      shift
      ;;
    --tool)
      FORCE_TOOL="$2"
      if [[ "$FORCE_TOOL" != "cursor" && "$FORCE_TOOL" != "claude-code" && "$FORCE_TOOL" != "windsurf" ]]; then
        echo "--tool must be 'cursor', 'claude-code', or 'windsurf'" >&2
        return 1
      fi
      shift 2
      ;;
    --skip-test)
      SKIP_TEST="true"
      shift
      ;;
    --wait-time)
      WAIT_TIME="$2"
      if ! [[ "$WAIT_TIME" =~ ^[0-9]+$ ]]; then
        echo "--wait-time must be a positive integer" >&2
        return 1
      fi
      shift 2
      ;;
    --debug)
      DEBUG="true"
      export MCP_DEBUG="true"
      shift
      ;;
    -h | --help)
      show_usage
      return 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_usage
      return 1
      ;;
    esac
  done

  return 0
}

show_usage() {
  cat <<EOF
Usage: ./gandalf install [OPTIONS]

Configure global MCP server for Cursor, Claude Code, and Windsurf.

Options:
    -f, --force             Force setup (overwrite existing config, clear cache)
    --tool <tool>           Force specific agentic tool (cursor|claude-code|windsurf)
    -h, --help              Show this help
    --skip-test             Skip connectivity testing
    --wait-time <seconds>   Wait time for tool recognition (default: 1)
    --debug                 Enable debug logging

Examples:   
    gandalf install                      # Install globally (auto-detect tools)
    gandalf install -f                   # Force overwrite existing config
    gandalf install --tool cursor        # Force Cursor installation only
    gandalf install --debug              # Enable debug output

EOF
}

# Main installation function
main() {
  if ! parse_arguments "$@"; then
    exit 1
  fi

  echo "Starting Gandalf MCP Server installation..."

  if ! verify_prerequisites; then
    exit 1
  fi

  if ! create_directory_structure "$GANDALF_HOME"; then
    exit 1
  fi

  if [[ "${FORCE:-false}" == "true" ]]; then
    if ! clear_cache "$GANDALF_HOME"; then
      echo "Cache clearing failed, but continuing..." >&2
    fi
  fi

  local detected_tool
  if [[ -n "$FORCE_TOOL" ]]; then
    detected_tool="$FORCE_TOOL"
    echo "Using forced tool: $detected_tool"
  else
    detected_tool=$(detect_agentic_tool)
    echo "Detected tool: $detected_tool"
  fi

  if ! create_installation_state "$GANDALF_ROOT" "unknown" "$detected_tool" "$FORCE_TOOL" "$(pwd)" "$MCP_SERVER_NAME" "$GANDALF_HOME"; then
    echo "Failed to create installation state" >&2
    exit 1
  fi

  if ! install_for_all_tools "$MCP_SERVER_NAME" "$GANDALF_ROOT" "$detected_tool"; then
    echo "Installation failed for all tools" >&2
    exit 1
  fi

  if ! create_rules_files; then
    echo "Rules file creation failed, but continuing..." >&2
  fi

  # Initialize agentic tools registry with all available tools
  echo "Initializing agentic tools registry..."
  if ! initialize_registry; then
    echo "Registry initialization failed, but continuing..." >&2
    echo "You may need to run './gandalf registry auto-register' manually"
  fi

  if [[ "$SKIP_TEST" != "true" ]]; then
    if ! check_server_connectivity "$DEFAULT_MAX_ATTEMPTS" "$WAIT_TIME" "$detected_tool"; then
      echo "Server connectivity test failed, but installation completed" >&2
    fi
  else
    echo "Skipping connectivity tests"
  fi

  echo "Gandalf MCP Server installation completed successfully!"

  cat <<EOF

Global MCP Configuration Complete!

Configuration Summary:
    Primary tool: $detected_tool
    Server Name: $MCP_SERVER_NAME
    Installation Type: Global (works in all projects)
    Gandalf Home: $GANDALF_HOME

Next Steps:
    1. Restart your configured tools completely
    2. Wait a few moments after restart for MCP server initialization
    3. Test MCP integration by asking: "What files are in my project?"

Troubleshooting:
    - If MCP tools aren't available, restart your tool and wait 30 seconds
    - Run with --debug for detailed logging
    - Use --skip-test for faster installation without connectivity tests

EOF
}

# Run main function
main "$@" 