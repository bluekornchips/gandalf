#!/usr/bin/env bash

# Gandalf Core Library
# Centralized common functionality for all shell scripts and the python server

set -eo pipefail

readonly CURSOR_DB_PATHS=(
  # Linux
  "$HOME/.config/Cursor/User/workspaceStorage"
  # macOS
  "$HOME/Library/Application Support/Cursor/User/workspaceStorage"
  # Windows/WSL
  "/mnt/c/Users/$(whoami)/AppData/Roaming/Cursor/User/workspaceStorage"
)

readonly CLAUDE_CODE_DB_PATHS=(
  # Linux
  "$HOME/.claude"
  "$HOME/.config/claude"
  # macOS
  "$HOME/Library/Application Support/Claude"
  # Windows/WSL
  "/mnt/c/Users/$(whoami)/AppData/Roaming/Claude"  
)

readonly WINDSURF_DB_PATHS=(
  # macOS
  "$HOME/Library/Application Support/Windsurf/User/workspaceStorage"
  "$HOME/Library/Application Support/Windsurf/User/globalStorage"
  # Windows/WSL
  "/mnt/c/Users/$(whoami)/AppData/Roaming/Windsurf/User/workspaceStorage"
  "/mnt/c/Users/$(whoami)/AppData/Roaming/Windsurf/User/globalStorage"
  # Linux
  "$HOME/.config/Windsurf/User/workspaceStorage"
  "$HOME/.config/Windsurf/User/globalStorage"
)

readonly GANDALF_TOOL_DB_FILES=(
  "state.vscdb"
  "workspace.db"
  "storage.db"
  "cursor.db"
)

export CURSOR_DB_PATHS
export CLAUDE_CODE_DB_PATHS
export WINDSURF_DB_PATHS

export GANDALF_TOOL_DB_FILES

# Initialize platform detection and establish database paths
detect_platform() {
  local uname_output=""
  uname_output="$(uname -s)"

  case "$uname_output" in
    Darwin*)
      GANDALF_PLATFORM="macos"
      ;;
    Linux*)
      GANDALF_PLATFORM="linux"
      ;;
    *)
      GANDALF_PLATFORM="unknown"
      ;;
  esac

  export GANDALF_PLATFORM

  return 0
}