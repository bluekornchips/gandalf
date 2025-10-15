#!/usr/bin/env bash
#
# Gandalf gandalf CLI entry point
# Provides command-line interface for the Gandalf project
#
set -eo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") COMMAND [OPTIONS]

Commands:
  -i, --install       Install and configure Gandalf MCP Server
  -u, --uninstall     Uninstall Gandalf MCP Server
  -s, --server        Manage Gandalf MCP Server (start, stop, status, pid)
  -v, --version       Show version
  -h, --help          Show help for specific command

Options:

For more information, see: ${GANDALF_ROOT}/README.md

EOF

	return 1
}

# Defaults
DEFAULT_GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_INSTALL_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/install.sh"
DEFAULT_UNINSTALL_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/uninstall.sh"
DEFAULT_MANAGE_SERVER_SCRIPT="$DEFAULT_GANDALF_ROOT/cli/bin/manage-server"

# Get version from VERSION file
#
# Inputs:
# - None
#
# Side Effects:
# - None
get_version() {
	local version_file
	version_file="$GANDALF_ROOT/VERSION"

	if [[ ! -f "${version_file}" ]]; then
		echo "unknown"
		return 0
	fi

	cat "${version_file}"

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
		-v | --version)
			get_version
			return 0
			;;
		-h | --help)
			usage
			return 1
			;;
		*)
			echo "Unknown option: $1" >&2
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
