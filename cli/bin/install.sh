#!/usr/bin/env bash
#
# Install Gandalf MCP Server
# Installs the Gandalf MCP Server and its dependencies
#
set -euo pipefail

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

# Get version from VERSION file
#
# Inputs:
# - None
#
# Side Effects:
# - None
get_version() {
	VERSION_FILE="${GANDALF_PROJECT_ROOT}/VERSION"
	if [[ ! -f "${VERSION_FILE}" ]]; then
		echo "Unable to determine version" >&2
		return 1
	fi

	cat "${VERSION_FILE}"

	return 0
}

# Run the installer by sourcing registry
#
# Inputs:
# - None
#
# Side Effects:
# - Sources registry.sh
run_installer() {
	log_debug "Running installer."
	# shellcheck disable=SC1091
	if ! source "${GANDALF_PROJECT_ROOT}/cli/bin/registry.sh"; then
		echo "Failed to source registry.sh" >&2
		return 1
	fi

	return 0
}

main() {
	if [[ $# -eq 0 ]]; then
		# Initialize music-of-the-ainur
		#shellcheck disable=SC1091
		source "${GANDALF_PROJECT_ROOT}/cli/lib/music-of-the-ainur.sh"
		init_logging

		log_info "Music of the Ainur (logging)initialized."
		log_debug "Running installer."
		# run_installer
	fi

	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			usage
			exit 0
			;;
		-v | --version)
			echo "Gandalf MCP Server v$(get_version)"
			exit 0
			;;
		*)
			echo "Unknown option '$1'" >&2
			echo "Use '$(basename "$0") --help' for usage information" >&2
			exit 1
			;;
		esac
	done
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	main "$@"
fi
