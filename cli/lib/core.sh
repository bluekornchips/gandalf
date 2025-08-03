#!/usr/bin/env bash

# Gandalf Core Library
# Centralized common functionality for all shell scripts and the python server

set -euo pipefail

readonly LINUX_DB_PATHS=(
	"$HOME/.config/Cursor/User"
	"$HOME/.config/Claude"
	# Windows/WSL
	"/mnt/c/Users/$(whoami)/AppData/Roaming/Cursor/User/workspaceStorage"
)

readonly MACOS_DB_PATHS=(
	"$HOME/Library/Application Support/Cursor/User"
	"$HOME/Library/Application Support/Claude"
)

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

	# Combine macOS and Linux database paths
	GANDALF_DB_PATHS=("${MACOS_DB_PATHS[@]}" "${LINUX_DB_PATHS[@]}")

	export GANDALF_PLATFORM
	export GANDALF_DB_PATHS

	return 0
}