#!/usr/bin/env bash

# Install Gandalf MCP Server
# Installs the Gandalf MCP Server and its dependencies

usage() {
	cat <<EOF
  Usage: $0 [OPTIONS]

  Options:
    -h, --help      Show this help message and exit
    -v, --version   Show version information and exit
    -f, --force     Force overwrite existing config

EOF
}
set -eo pipefail

# Initialize project root if not set
if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
	SCRIPT_PATH="$(realpath "${BASH_SOURCE:-$0}")"
	SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
	GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

if [[ -z "${HOME:-}" ]]; then
	echo "'HOME' environment variable is not set" >&2
	exit 1
fi

get_version() {
	VERSION_FILE="${GANDALF_PROJECT_ROOT}/VERSION"
	if [[ -f "${VERSION_FILE}" ]]; then
		cat "${VERSION_FILE}"
	else
		echo "Unable to determine version" >&2
		exit 1
	fi
}

run_installer() {
	# Setup registry
	source "${GANDALF_PROJECT_ROOT}/cli/bin/registry.sh"
}

if [[ $# -eq 0 ]]; then
	run_installer
fi

while getopts "hv" opt; do
	case $opt in
	h)
		usage
		exit 0
		;;
	v)
		echo "Gandalf MCP Server v$(get_version)"
		exit 0
		;;
	*)
		usage
		exit 1
		;;
	esac
done
