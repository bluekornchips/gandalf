#!/usr/bin/env bash
#
# Gandalf Core Library
# Centralized common functionality for all shell scripts and the python server
#
set -euo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Gandalf Core Library
Centralized common functionality for all shell scripts and the python server

OPTIONS:
  -h, --help  Show this help message

ENVIRONMENT VARIABLES (If any)
  GANDALF_PLATFORM=linux  # Platform detection (linux, macos, unknown)

EOF
}

# Detects the current platform and sets GANDALF_PLATFORM
#
# Inputs:
# - None
#
# Side Effects:
# - GANDALF_PLATFORM, sets the global platform variable
detect_platform() {
	local uname_output
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

	echo "$GANDALF_PLATFORM"

	return 0
}

# Main entry point
# No
main() {
	echo -e "\n=== Entry: ${BASH_SOURCE[0]:-$0} ===\n"

	CURSOR_DB_PATHS=(
		# Linux
		"$HOME/.config/Cursor/User/workspaceStorage"
		# macOS
		"$HOME/Library/Application Support/Cursor/User/workspaceStorage"
		# Windows/WSL
		"/mnt/c/Users/$(whoami)/AppData/Roaming/Cursor/User/workspaceStorage"
	)

	CLAUDE_CODE_DB_PATHS=(
		# Linux
		"$HOME/.claude"
		"$HOME/.config/claude"
		# macOS
		"$HOME/Library/Application Support/Claude"
		# Windows/WSL
		"/mnt/c/Users/$(whoami)/AppData/Roaming/Claude"
	)

	GANDALF_TOOL_DB_FILES=(
		"state.vscdb"
		"workspace.db"
		"storage.db"
		"cursor.db"
	)

	export CURSOR_DB_PATHS
	export CLAUDE_CODE_DB_PATHS
	export GANDALF_TOOL_DB_FILES

	GANDALF_PLATFORM=$(detect_platform)

	export GANDALF_PLATFORM

	echo -e "\n=== Exit: ${BASH_SOURCE[0]:-$0} ===\n"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	main "$@"
fi
