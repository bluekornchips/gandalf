#!/usr/bin/env bash
#
# Gandalf gandalf CLI entry point
# Provides command-line interface for the Gandalf project
#
set -euo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") COMMAND [OPTIONS]

Commands:
  -i, --install       			Install and configure Gandalf MCP Server
  -u, --uninstall     			Uninstall Gandalf MCP Server
  -s, --server        			Manage Gandalf MCP Server (start, stop, status, pid)
  -q, --query-from-file 		Execute database query from JSON file
  -v, --version       			Show version
  -h, --help          			Show help for specific command

Query Options:
  -o, --output FORMAT    Output format: json (requires jq) or yaml (requires yq)

Options:

For more information, see: ${GANDALF_ROOT}/README.md

EOF

	return 1
}

# Defaults
DEFAULT_GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_INSTALL_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/install.sh"
DEFAULT_UNINSTALL_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/uninstall.sh"
DEFAULT_MANAGE_SERVER_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/manage-server.sh"
DEFAULT_QUERY_DATABASE_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/query-database.sh"

# Get version from VERSION file
#
# Inputs:
# - None
#
# Side Effects:
# - None
get_version() {
	if [[ -z "${GANDALF_ROOT:-}" ]]; then
		echo "get_version:: GANDALF_ROOT is not set" >&2
		return 1
	fi

	local version_file
	version_file="$GANDALF_ROOT/VERSION"

	if [[ ! -f "${version_file}" ]]; then
		echo "unknown"
		return 0
	fi

	cat "${version_file}"

	return 0
}

# Handle query command with optional output formatting
#
# Inputs:
# - $@, All remaining arguments after -q
#
# Side Effects:
# - Executes query and outputs results
handle_query() {
	if [[ $# -eq 0 ]]; then
		echo "handle_query:: --query-from-file requires a file path" >&2
		return 1
	fi

	if [[ -z "${QUERY_DATABASE_SCRIPT:-}" ]]; then
		echo "handle_query:: QUERY_DATABASE_SCRIPT is not set" >&2
		return 1
	fi

	local query_file="$1"
	shift

	# Collect any additional arguments for the query script
	local query_args=("$query_file")
	while [[ $# -gt 0 ]]; do
		case $1 in
		-o | --output)
			if [[ $# -lt 2 ]]; then
				echo "handle_query:: --output requires a format argument" >&2
				return 1
			fi
			query_args+=("$1" "$2")
			shift 2
			;;
		*)
			echo "handle_query:: Unknown query option $1" >&2
			return 1
			;;
		esac
	done

	if ! "${QUERY_DATABASE_SCRIPT}" "${query_args[@]}"; then
		return 1
	fi
	return 0
}

# gandalf CLI function that handles command routing
#
# Inputs:
# - None
#
# Side Effects:
# - Executes commands or shows help
gandalf() {

	GANDALF_ROOT="${GANDALF_ROOT:-$DEFAULT_GANDALF_ROOT}"
	INSTALL_SCRIPT="${INSTALL_SCRIPT:-$DEFAULT_INSTALL_SCRIPT}"
	UNINSTALL_SCRIPT="${UNINSTALL_SCRIPT:-$DEFAULT_UNINSTALL_SCRIPT}"
	MANAGE_SERVER_SCRIPT="${MANAGE_SERVER_SCRIPT:-$DEFAULT_MANAGE_SERVER_SCRIPT}"
	QUERY_DATABASE_SCRIPT="${QUERY_DATABASE_SCRIPT:-$DEFAULT_QUERY_DATABASE_SCRIPT}"

	export GANDALF_ROOT

	while [[ $# -gt 0 ]]; do
		case $1 in
		-i | --install)
			shift
			if ! "${INSTALL_SCRIPT}" "$@"; then
				return 1
			fi
			return 0
			;;
		-u | --uninstall)
			shift
			if ! "${UNINSTALL_SCRIPT}" "$@"; then
				return 1
			fi
			return 0
			;;
		-s | --server)
			shift
			if ! "${MANAGE_SERVER_SCRIPT}" "$@"; then
				return 1
			fi
			return 0
			;;
		-q | --query-from-file)
			shift
			if ! handle_query "$@"; then
				return 1
			fi
			return 0
			;;
		-v | --version)
			get_version
			return 0
			;;
		-h | --help)
			usage
			return 1
			;;
		*)
			echo "gandalf:: Unknown option: $1" >&2
			usage
			return 1
			;;
		esac
	done

	return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	if [[ $# -gt 0 ]]; then
		gandalf "$@"
	else
		usage
	fi
fi
