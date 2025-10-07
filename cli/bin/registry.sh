#!/usr/bin/env bash
#
# Registry Management for Gandalf
# Manages tool registrations and database paths for the Gandalf system
#
set -euo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Registry Management for Gandalf
Manages tool registrations and database paths for the Gandalf system

OPTIONS:
  -h, --help  Show this help message

ENVIRONMENT VARIABLES (If any)
  GANDALF_REGISTRY_FILE  # Path to registry file (default: ~/.gandalf/registry.json)

EOF
}

# Registry Schema:
# {
#     "tool-name": [
#         "path/to/tool/db",
#         "path/to/tool/db",
#         ...
#     ]
# }

# Initialize the registry file if it does not exist
#
# Inputs:
# - None
#
# Side Effects:
# - REGISTRY_FILE, creates directory and file if needed
init_registry() {
	if [[ ! -f "${REGISTRY_FILE}" ]]; then
		local registry_dir
		registry_dir="$(dirname "${REGISTRY_FILE}")"

		if ! mkdir -p "${registry_dir}"; then
			log_error "Failed to create registry directory: ${registry_dir}" >&2
			return 1
		fi

		if ! echo "{}" >"${REGISTRY_FILE}"; then
			log_error "Failed to create registry file: ${REGISTRY_FILE}" >&2
			return 1
		fi
	fi

	return 0
}

# Update registry with tool information
#
# Inputs:
# - $1, tool_name, name of the tool
# - $2+, tool_paths, array of paths to tool databases
#
# Side Effects:
# - REGISTRY_FILE, updates the registry file with tool paths
update_registry() {
	local tool_name="${1:-}"
	local tool_paths=("${@:2}")
	local registry_data

	if [[ -z "${tool_name:-}" ]]; then
		log_error "Tool name is required" >&2
		return 1
	fi

	[[ ! -f "${REGISTRY_FILE}" ]] && init_registry

	if [[ ${#tool_paths[@]} -eq 0 ]]; then
		if ! registry_data=$(jq -r \
			--arg tool_name "${tool_name}" \
			'.[$tool_name] = []' "${REGISTRY_FILE}"); then
			log_error "Failed to update registry for ${tool_name}" >&2
			return 1
		fi
	else
		if ! registry_data=$(jq -r \
			--arg tool_name "${tool_name}" \
			--arg tool_paths "$(printf '%s\n' "${tool_paths[@]}")" \
			'.[$tool_name] = ($tool_paths | split("\n") | map(select(. != "")))' \
			"${REGISTRY_FILE}"); then
			log_error "Failed to update registry for ${tool_name}" >&2
			return 1
		fi
	fi

	if ! echo "${registry_data}" >"${REGISTRY_FILE}"; then
		log_error "Failed to write registry file: ${REGISTRY_FILE}" >&2
		return 1
	fi

	return 0
}

# Search for database files across all tool paths
#
# Inputs:
# - $1+, combined_paths, array of paths to search
#
# Side Effects:
# - REGISTRY_CURSOR_PATHS, sets array of Cursor database paths
# - REGISTRY_CLAUDE_PATHS, sets array of Claude database paths
check_available_tools() {
	local combined_paths=("${@:1}")

	local cursor_db_paths=()
	local claude_code_db_paths=()
	local path
	local db_file
	local found_file
	local found_path

	log_info "Searching for database files across all paths."

	for path in "${combined_paths[@]}"; do
		for db_file in "${GANDALF_TOOL_DB_FILES[@]}"; do
			while IFS= read -r -d '' found_file; do
				found_path="$(dirname "${found_file}")"

				[[ "${found_path}" == *"Cursor"* ]] && cursor_db_paths+=("${found_path}")
				[[ "${found_path}" == *"Claude"* ]] && claude_code_db_paths+=("${found_path}")
			done < <(find "${path}" -name "${db_file}" -print0 2>/dev/null)
		done
	done

	REGISTRY_CURSOR_PATHS=("${cursor_db_paths[@]}")
	REGISTRY_CLAUDE_PATHS=("${claude_code_db_paths[@]}")

	log_block <<EOF
========================================
Databases Found
========================================
Cursor: ${#REGISTRY_CURSOR_PATHS[@]}
$(printf '%s\n' "${REGISTRY_CURSOR_PATHS[@]}")
Claude Code: ${#REGISTRY_CLAUDE_PATHS[@]}
$(printf '%s\n' "${REGISTRY_CLAUDE_PATHS[@]}")

EOF

	return 0
}

# Main entry point
main() {
	REGISTRY_FILE="${GANDALF_REGISTRY_FILE:-${HOME:-$HOME}/.gandalf/registry.json}"
	export REGISTRY_FILE

	# Initialize music-of-the-ainur
	#shellcheck disable=SC1091
	if ! source "${GANDALF_PROJECT_ROOT}/cli/lib/music-of-the-ainur.sh"; then
		log_error "Failed to source music-of-the-ainur.sh" >&2
		return 1
	fi

	# Initialize project root if not set
	if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
		SCRIPT_PATH="$(realpath "${BASH_SOURCE:-$0}")"
		SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
		GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
	fi

	if [[ -z "${HOME:-}" ]]; then
		log_error "'HOME' environment variable is not set" >&2
		return 1
	fi
	log_debug "Home directory set to: ${HOME}"

	# Initialize arrays
	CURSOR_DB_PATHS=()
	CLAUDE_CODE_DB_PATHS=()

	export CURSOR_DB_PATHS
	export CLAUDE_CODE_DB_PATHS

	[[ ! -f "${REGISTRY_FILE}" ]] && init_registry
	combined_paths=("${CURSOR_DB_PATHS[@]}" "${CLAUDE_CODE_DB_PATHS[@]}")
	check_available_tools "${combined_paths[@]}"

	if ! update_registry "claude" "${REGISTRY_CLAUDE_PATHS[@]}"; then
		log_error "Failed to update registry for Claude" >&2
		return 1
	fi
	if ! update_registry "cursor" "${REGISTRY_CURSOR_PATHS[@]}"; then
		log_error "Failed to update registry for Cursor" >&2
		return 1
	fi

	log_info "Registry set: $(jq -r '.' "${REGISTRY_FILE}")"

	return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			usage
			return 0
			;;
		*)
			log_error "Unknown option '$1'" >&2
			log_error "Use '$(basename "$0") --help' for usage information" >&2
			return 1
			;;
		esac
	done
fi

main "$@"
