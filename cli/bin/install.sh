#!/usr/bin/env bash
#
# Installs the Gandalf MCP Server and its dependencies
#
set -eo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install Gandalf MCP Server
Installs the Gandalf MCP Server and its dependencies

OPTIONS:
  -h, --help      Show this help message and exit
  -v, --version   Show version information and exit
  -f, --force     Force overwrite existing config

EOF
}

# Constants
RULES_MARKER="###GANDALFRULES###"

# Defaults
DEFAULT_CHECK_DEPENDENCIES_SCRIPT="$GANDALF_ROOT/cli/etc/check-dependencies.sh"
DEFAULT_REGISTRY_SCRIPT="$GANDALF_ROOT/cli/bin/registry.sh"
DEFAULT_CORE_SCRIPT="$GANDALF_ROOT/cli/lib/core.sh"
DEFAULT_GANDALF_HOME="${HOME}/.gandalf"

DEFAULT_SERVER_PATH="$GANDALF_ROOT/server/main.py"
DEFAULT_PYTHON_PATH="$GANDALF_ROOT/.venv/bin/python3"

DEFAULT_CURSOR_CONFIG="$HOME/.cursor/mcp.json"
DEFAULT_CLAUDE_CONFIG="$HOME/.claude/claude_desktop_config"

DEFAULT_GANDALF_RULES_FILE="$GANDALF_ROOT/spec/gandalf-rules.md"

# Delete any existing gandalf home dir if the -f flag was passed in.
# Create the folder structure
# $HOME/.gandalf/
# - logs/
#	- registry/
setup_gandalf_home() {
	if [[ "$FORCE_INSTALL" == "true" && -d "$GANDALF_HOME" ]]; then
		rm -rf "$GANDALF_HOME"
	fi

	mkdir -p "$GANDALF_HOME/logs"
	mkdir -p "$GANDALF_HOME/registry"

	return 0
}

# Sets up MCP server connections for editors
#
# Inputs:
# - None
#
# Side Effects:
# - Creates $HOME/.cursor/mcp.json with gandalf config
# - Creates $HOME/.claude/claude_desktop_config with gandalf config
# - Configures Claude Code MCP settings via claude mcp add-json
setup_mcp_connections() {

	setup_editor_config "Cursor" "$CURSOR_CONFIG"

	setup_editor_config "Claude" "$CLAUDE_CONFIG"

	setup_claude_code_mcp

	return 0
}

# Creates or updates the specified config file with gandalf server config
#
# Inputs:
# - $1, editor_name, name of the editor (Cursor/Claude)
# - $2, config_file, path to the configuration file
#
# Side Effects:
# - Creates or updates MCP configuration file
setup_editor_config() {
	local editor_name="$1"
	local config_file="$2"

	local python_path="${PYTHON_PATH:-${DEFAULT_PYTHON_PATH}}"
	local server_dir="${GANDALF_ROOT}/server"

	if [[ ! -f "$config_file" ]] || [[ ! -s "$config_file" ]]; then
		local config_dir
		config_dir="$(dirname "$config_file")"
		mkdir -p "$config_dir"

		jq -n \
			--arg server_path "$SERVER_PATH" \
			--arg gandalf_home "$GANDALF_HOME" \
			--arg python_path "$python_path" \
			--arg server_dir "$server_dir" \
			'{
				"mcpServers": {
					"gandalf": {
						"command": $python_path,
						"args": [$server_path],
						"cwd": $server_dir,
						"env": {
							"GANDALF_HOME": $gandalf_home
						}
					}
				}
			}' >"$config_file"
		echo "$editor_name MCP configuration created: $config_file"
	elif [[ -n "${FORCE_INSTALL}" ]] || ! jq -e '.mcpServers.gandalf' "$config_file" >/dev/null 2>&1; then
		# File exists and either force flag is set or gandalf config doesn't exist, update it
		# Read existing file content to variable, modify it, and write back
		local existing_content
		existing_content="$(cat "$config_file")"

		jq \
			--arg server_path "$SERVER_PATH" \
			--arg gandalf_home "$GANDALF_HOME" \
			--arg python_path "$python_path" \
			--arg server_dir "$server_dir" \
			'.mcpServers.gandalf = {
				"command": $python_path,
				"args": [$server_path],
				"cwd": $server_dir,
				"env": {
					"GANDALF_HOME": $gandalf_home
				}
			}' <<<"$existing_content" >"$config_file"
		echo "$editor_name MCP configuration updated: $config_file"
	else
		echo "$editor_name MCP configuration already exists: $config_file"
	fi

	return 0
}

# Sets up Claude Code MCP configuration using claude mcp commands
#
# Inputs:
# - None
#
# Side Effects:
# - Configures Claude Code MCP server for current project
setup_claude_code_mcp() {
	local python_path="${PYTHON_PATH:-${DEFAULT_PYTHON_PATH}}"
	local server_path="${SERVER_PATH:-${DEFAULT_SERVER_PATH}}"
	local server_dir="${GANDALF_ROOT}/server"

	if ! command -v claude >/dev/null 2>&1; then
		echo "Claude Code CLI not found, skipping Claude Code MCP configuration"
		return 0
	fi

	claude mcp remove gandalf 2>/dev/null || true

	local mcp_config
	mcp_config="$(jq -n \
		--arg python_path "$python_path" \
		--arg server_path "$server_path" \
		--arg server_dir "$server_dir" \
		--arg gandalf_home "$GANDALF_HOME" \
		'{
			"type": "stdio",
			"command": $python_path,
			"args": [$server_path],
			"cwd": $server_dir,
			"env": {
				"GANDALF_HOME": $gandalf_home
			}
		}')"

	if claude mcp add-json gandalf "$mcp_config" 2>/dev/null; then
		echo "Claude Code MCP configuration added successfully"
	else
		echo "Failed to configure Claude Code MCP. This is optional and can be done manually later" >&2
		return 1
	fi

	return 0
}

# Sets up Cursor rules by copying gandalf-rules.md to the appropriate location
#
# Inputs:
# - None
#
# Side Effects:
# - Creates .cursor/rules directory if needed
# - Copies gandalf-rules.md to .cursor/rules/
setup_cursor_rules() {
	local installation_root="$1"
	local rules_file="$2"

	RULES_HEADER=$(
		cat <<EOF
---
description: Rules for using the Gandalf MCP Server.
globs:
alwaysApply: true
---
EOF
	)

	if [[ -z "$installation_root" ]]; then
		installation_root="$(pwd)"
	fi

	local rules_dir="$installation_root/.cursor/rules"
	local rules_dest="$rules_dir/gandalf-rules.mdc"

	mkdir -p "$rules_dir"

	rm -f "$rules_dest"

	# Read rules content from source file
	local rules_content
	rules_content="$(cat "$rules_file" 2>/dev/null || echo "")"

	# Write rules file
	echo "$RULES_HEADER" >"$rules_dest"
	echo "$rules_content" >>"$rules_dest"
	echo "Cursor rules installed: $rules_dest"

	return 0
}

# Sets up Claude rules by managing CLAUDE.md file with rules content
#
# Inputs:
# - $1, installation_root, root directory for installation
# - $2, rules_file, path to the rules source file
#
# Side Effects:
# - Creates or updates CLAUDE.md with rules content
setup_claude_rules() {
	local installation_root="$1"
	local rules_file="$2"

	if [[ -z "$installation_root" ]]; then
		installation_root="$(pwd)"
	fi

	local claude_file="$installation_root/CLAUDE.md"
	local rules_content
	rules_content="$(cat "$rules_file" 2>/dev/null || echo "")"

	# If CLAUDE.md doesn't exist, create it with rules
	if [[ ! -f "$claude_file" ]]; then
		echo "$RULES_MARKER" >"$claude_file"
		echo "$rules_content" >>"$claude_file"
		echo "$RULES_MARKER" >>"$claude_file"
		echo "Claude rules created: $claude_file"
		return 0
	fi

	# Check if RULES_MARKER exists twice (complete rules section)
	if grep -c "$RULES_MARKER" "$claude_file" | grep -q "^2$"; then
		# Replace content between markers
		local temp_file
		temp_file="$(mktemp)"

		# Write content up to first marker
		sed "/^$RULES_MARKER$/,\$d" "$claude_file" >>"$temp_file"

		# Write content after second marker
		sed "1,/^$RULES_MARKER$/d" "$claude_file" | sed "1,/^$RULES_MARKER$/d" >>"$temp_file"

		# Write new rules section
		echo "$RULES_MARKER" >>"$temp_file"
		echo "$rules_content" >>"$temp_file"
		echo "$RULES_MARKER" >>"$temp_file"

		mv "$temp_file" "$claude_file"
		echo "Claude rules updated: $claude_file"
	else
		# Append rules content
		echo "$RULES_MARKER" >>"$claude_file"
		echo "$rules_content" >>"$claude_file"
		echo "$RULES_MARKER" >>"$claude_file"
		echo "Claude rules appended: $claude_file"
	fi

	return 0
}

install() {
	echo "=== Entry: ${0} ==="

	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			usage
			return 0
			;;
		-f | --force)
			FORCE_INSTALL="true"
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
Gandalf Installation
=============================================

EOF

	GIT_ROOT=$(git rev-parse --show-toplevel) || true

	if [[ -z "${GANDALF_ROOT}" ]]; then
		GANDALF_ROOT="$GIT_ROOT"
	fi

	CHECK_DEPENDENCIES_SCRIPT="${CHECK_DEPENDENCIES_SCRIPT:-${DEFAULT_CHECK_DEPENDENCIES_SCRIPT}}"
	REGISTRY_SCRIPT="${REGISTRY_SCRIPT:-${DEFAULT_REGISTRY_SCRIPT}}"
	CORE_SCRIPT="${CORE_SCRIPT:-${DEFAULT_CORE_SCRIPT}}"
	GANDALF_HOME="${GANDALF_HOME:-${DEFAULT_GANDALF_HOME}}"
	CURSOR_CONFIG="${CURSOR_CONFIG:-${DEFAULT_CURSOR_CONFIG}}"
	CLAUDE_CONFIG="${CLAUDE_CONFIG:-${DEFAULT_CLAUDE_CONFIG}}"

	SERVER_PATH="${SERVER_PATH:-${DEFAULT_SERVER_PATH}}"
	PYTHON_PATH="${PYTHON_PATH:-${DEFAULT_PYTHON_PATH}}"

	GANDALF_RULES_FILE="${GANDALF_RULES_FILE:-${DEFAULT_GANDALF_RULES_FILE}}"

	# Check dependencies
	if ! "$CHECK_DEPENDENCIES_SCRIPT"; then
		return 1
	fi

	# Setup GANDALF_HOME directory hierarchy
	if ! setup_gandalf_home; then
		return 1
	fi

	# Setup registry
	if ! source "$REGISTRY_SCRIPT" || ! registry; then
		return 1
	fi

	# Setup MCP connections
	if ! setup_mcp_connections; then
		return 1
	fi

	# If the registry file .cursor array is not empty, setup Cursor rules
	if [[ -n "${DB_PATH_DATA}" ]] && [[ $(jq -e '.cursor' <<<"${DB_PATH_DATA}") != "[]" ]]; then
		if ! setup_cursor_rules "$GIT_ROOT" "$GANDALF_RULES_FILE"; then
			return 1
		fi
	fi

	# Setup Claude rules
	# If the registry file .claude array is not empty, setup Claude rules
	if [[ -n "${DB_PATH_DATA}" ]] && [[ $(jq -e '.claude' <<<"${DB_PATH_DATA}") != "[]" ]]; then
		if ! setup_claude_rules "$GIT_ROOT" "$GANDALF_RULES_FILE"; then
			return 1
		fi
	fi

	return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	install "$@"
fi
