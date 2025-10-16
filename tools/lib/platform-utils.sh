#!/usr/bin/env bash
# Platform utilities for cross-platform compatibility

set -euo pipefail

readonly PLATFORM_MACOS="Darwin"
readonly PLATFORM_LINUX="Linux"
readonly PLATFORM_WINDOWS="Windows"
readonly PLATFORM_WSL="Linux"

readonly CURSOR_APP_MACOS="/Applications/Cursor.app"
readonly CURSOR_CONFIG_MACOS="$HOME/Library/Application Support/Cursor/User"
readonly CURSOR_WORKSPACE_MACOS="$HOME/Library/Application Support/Cursor/User/workspaceStorage"

readonly CURSOR_CONFIG_LINUX="$HOME/.config/Cursor/User"
readonly CURSOR_WORKSPACE_LINUX="$HOME/.config/Cursor/User/workspaceStorage"

readonly CURSOR_CONFIG_WSL="$HOME/.config/Cursor/User"
readonly CURSOR_WORKSPACE_WSL="$HOME/.config/Cursor/User/workspaceStorage"

readonly CLAUDE_HOME_MACOS="$HOME/Library/Application Support/Claude"
readonly CLAUDE_HOME_LINUX="$HOME/.config/Claude"

readonly WINDSURF_CONFIG_MACOS="$HOME/Library/Application Support/Windsurf"
readonly WINDSURF_CONFIG_LINUX="$HOME/.config/Windsurf"

# Detect current platform
detect_platform() {
	local uname_output
	uname_output="$(uname -s)"

	case "$uname_output" in
	Darwin*)
		echo "macos"
		;;
	Linux*)
		if is_wsl; then
			echo "wsl"
		else
			echo "linux"
		fi
		;;
	CYGWIN* | MINGW* | MSYS*)
		echo "windows"
		;;
	*)
		echo "unknown"
		;;
	esac
}

# Check if running in WSL
is_wsl() {
	[[ -f /proc/version ]] && grep -qi microsoft /proc/version
}

# Validate path exists and is accessible
validate_path() {
	local path="$1"
	[[ -n "$path" && -e "$path" && -r "$path" ]]
}

# Get platform-specific Cursor configuration directory
get_cursor_config_dir() {
	local platform config_dir
	platform="$(detect_platform)"

	case "$platform" in
	macos)
		config_dir="$CURSOR_CONFIG_MACOS"
		;;
	linux)
		config_dir="$CURSOR_CONFIG_LINUX"
		;;
	wsl)
		config_dir="$CURSOR_CONFIG_WSL"
		;;
	windows)
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

# Get platform-specific Cursor workspace directory
get_cursor_workspace_dir() {
	local platform workspace_dir
	platform="$(detect_platform)"

	case "$platform" in
	macos)
		workspace_dir="$CURSOR_WORKSPACE_MACOS"
		;;
	linux)
		workspace_dir="$CURSOR_WORKSPACE_LINUX"
		;;
	wsl)
		workspace_dir="$CURSOR_WORKSPACE_WSL"
		;;
	windows)
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

# Get platform-specific Cursor application support directory
get_cursor_app_support_dir() {
	local platform support_dir
	platform="$(detect_platform)"

	case "$platform" in
	macos)
		support_dir="$HOME/Library/Application Support/Cursor"
		;;
	linux)
		support_dir="$HOME/.config/Cursor"
		;;
	wsl)
		support_dir="$HOME/.config/Cursor"
		;;
	windows)
		support_dir="${APPDATA:-$HOME}/.cursor"
		;;
	*)
		support_dir="$HOME/.cursor"
		;;
	esac

	if validate_path "$support_dir"; then
		echo "$support_dir"
	else
		echo "$HOME/.cursor"
	fi
}

# Get platform-specific Claude home directory
get_claude_home_dir() {
	local platform claude_dir
	platform="$(detect_platform)"

	case "$platform" in
	macos)
		claude_dir="$CLAUDE_HOME_MACOS"
		;;
	linux | wsl)
		claude_dir="$CLAUDE_HOME_LINUX"
		;;
	windows)
		claude_dir="${APPDATA:-$HOME}/.claude"
		;;
	*)
		claude_dir="$HOME/.claude"
		;;
	esac

	if validate_path "$claude_dir"; then
		echo "$claude_dir"
	else
		echo "$HOME/.claude"
	fi
}

# Get platform-specific Windsurf configuration directory
get_windsurf_config_dir() {
	local platform windsurf_dir
	platform="$(detect_platform)"

	case "$platform" in
	macos)
		windsurf_dir="$WINDSURF_CONFIG_MACOS"
		;;
	linux | wsl)
		windsurf_dir="$WINDSURF_CONFIG_LINUX"
		;;
	windows)
		windsurf_dir="${APPDATA:-$HOME}/.windsurf"
		;;
	*)
		windsurf_dir="$HOME/.windsurf"
		;;
	esac

	if validate_path "$windsurf_dir"; then
		echo "$windsurf_dir"
	else
		echo "$HOME/.windsurf"
	fi
}
