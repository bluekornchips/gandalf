#!/usr/bin/env bash
#
# Uninstalls the Gandalf MCP Server and its dependencies
#
set -eo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Uninstall Gandalf MCP Server
Removes the Gandalf MCP Server and its dependencies

OPTIONS:
  -h, --help      Show this help message and exit
  -v, --version   Show version information and exit
  -f, --force     Force removal without confirmation

EOF
}

# Defaults
DEFAULT_GANDALF_HOME="${HOME}/.gandalf"

# Removes MCP server connections from editors
#
# Inputs:
# - None
#
# Side Effects:
# - Removes gandalf config from $HOME/.cursor/mcp.json
# - Removes gandalf config from $HOME/.claude/claude_desktop_config
# - Removes Claude Code MCP configuration via claude mcp remove
remove_mcp_connections() {
	local cursor_config
	local claude_config

	cursor_config="$HOME/.cursor/mcp.json"
	claude_config="$HOME/.claude/claude_desktop_config"

	remove_editor_config "$cursor_config" "Cursor"
	remove_editor_config "$claude_config" "Claude"

	remove_claude_code_mcp

	return 0
}

# Removes MCP configuration for a specific editor
#
# Inputs:
# - $1: config file path
# - $2: editor name
#
# Side Effects:
# - Removes gandalf server config from the specified config file
remove_editor_config() {
	local config_file
	local editor_name

	config_file="$1"
	editor_name="$2"

	if [[ ! -f "$config_file" ]]; then
		echo "$editor_name MCP configuration not found: $config_file"
		return 0
	fi

	if ! jq -e '.mcpServers.gandalf' "$config_file" >/dev/null 2>&1; then
		echo "$editor_name MCP configuration does not contain gandalf config: $config_file"
		return 0
	fi

	local existing_content
	existing_content="$(cat "$config_file")"

	jq 'del(.mcpServers.gandalf)' <<<"$existing_content" >"$config_file"
	echo "$editor_name MCP configuration updated: $config_file"

	return 0
}

# Removes Claude Code MCP configuration using claude mcp commands
#
# Inputs:
# - None
#
# Side Effects:
# - Removes Claude Code MCP server for current project
remove_claude_code_mcp() {
	if ! command -v claude >/dev/null 2>&1; then
		echo "Claude Code CLI not found, skipping Claude Code MCP removal"
		return 0
	fi

	if claude mcp remove gandalf 2>/dev/null; then
		echo "Claude Code MCP configuration removed successfully"
	else
		echo "Failed to remove Claude Code MCP configuration. This is optional and can be done manually later" >&2
	fi

	return 0
}

# Removes Gandalf home directory
#
# Inputs:
# - None
#
# Side Effects:
# - Removes $GANDALF_HOME directory and all contents
remove_gandalf_home() {
	if [[ ! -d "$GANDALF_HOME" ]]; then
		echo "Gandalf home directory not found: $GANDALF_HOME"
		return 0
	fi

	rm -rf "$GANDALF_HOME"
	echo "Removed Gandalf home directory: $GANDALF_HOME"

	return 0
}

# Removes Python virtual environment
#
# Inputs:
# - None
#
# Side Effects:
# - Removes .venv directory from GANDALF_ROOT
remove_python_env() {
	local venv_dir
	venv_dir="${GANDALF_ROOT}/.venv"

	if [[ ! -d "$venv_dir" ]]; then
		echo "Python virtual environment not found: $venv_dir"
		return 0
	fi

	rm -rf "$venv_dir"
	echo "Removed Python virtual environment: $venv_dir"

	return 0
}

uninstall() {
	echo "=== Entry: ${0} ==="

	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			usage
			return 0
			;;
		-f | --force)
			FORCE_UNINSTALL="true"
			shift
			;;
		*)
			echo "Unknown option '$1'" >&2
			echo "Use '$(basename "$0") --help' for usage information" >&2
			return 1
			;;
		esac
	done

	cat <<EOF

=============================================
Gandalf Uninstallation
=============================================

EOF

	if [[ -z "${GANDALF_ROOT}" ]]; then
		echo "GANDALF_ROOT is not set" >&2
		return 1
	fi

	GANDALF_HOME="${DEFAULT_GANDALF_HOME:-${DEFAULT_GANDALF_HOME}}"

	if [[ -z "${FORCE_UNINSTALL}" ]]; then
		echo "This will remove Gandalf MCP Server and all its configurations."
		echo "Are you sure you want to continue? (y/N)"
		read -r response
		if [[ "$response" != "y" && "$response" != "Y" ]]; then
			echo "Uninstallation cancelled."
			return 0
		fi
	fi

	if ! remove_mcp_connections; then
		return 1
	fi

	if ! remove_gandalf_home; then
		return 1
	fi

	if ! remove_python_env; then
		return 1
	fi

	echo "Gandalf MCP Server has been successfully uninstalled."

	return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	uninstall "$@"
fi
