#!/usr/bin/env bash

# Registry Management for Gandalf
# Manages tool registrations and database paths for the Gandalf system

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

# shellcheck disable=SC1091
source "${GANDALF_PROJECT_ROOT}/cli/lib/core.sh"
detect_platform

readonly REGISTRY_FILE="${GANDALF_REGISTRY_FILE:-${HOME}/.gandalf/registry.json}"
# Registry Schema:
# {
#     "tool-name": [
#         "path/to/tool/db",
#         "path/to/tool/db",
#         ...
#     ]
# }
# Local copies of database paths for this script
REGISTRY_CURSOR_PATHS=()
REGISTRY_CLAUDE_PATHS=()
REGISTRY_WINDSURF_PATHS=()

# Initialize the registry file if it does not exist
init_registry() {
	if [[ ! -f "${REGISTRY_FILE}" ]]; then
		local registry_dir
		registry_dir="$(dirname "${REGISTRY_FILE}")"
		
		if ! mkdir -p "${registry_dir}"; then
			echo "Failed to create registry directory: ${registry_dir}" >&2
			return 1
		fi
		
		if ! echo "{}" >"${REGISTRY_FILE}"; then
			echo "Failed to create registry file: ${REGISTRY_FILE}" >&2
			return 1
		fi
		
		echo "Registry initialized"
	fi
}

# Update registry with tool information
update_registry() {
	local tool_name="${1:-}"
	local tool_paths=("${@:2}")
	local registry_data

	if [[ -z "${tool_name:-}" ]]; then
		echo "Tool name is required" >&2
		return 1
	fi

	[[ ! -f "${REGISTRY_FILE}" ]] && init_registry

	if [[ ${#tool_paths[@]} -eq 0 ]]; then
		if ! registry_data=$(jq -r \
			--arg tool_name "${tool_name}" \
			'.[$tool_name] = []' "${REGISTRY_FILE}"); then
			echo "Failed to update registry for ${tool_name}" >&2
			return 1
		fi
	else
		if ! registry_data=$(jq -r \
		--arg tool_name "${tool_name}" \
			--arg tool_paths "$(printf '%s\n' "${tool_paths[@]}")" \
			'.[$tool_name] = ($tool_paths | split("\n") | map(select(. != "")))' \
			"${REGISTRY_FILE}"); then
			echo "Failed to update registry for ${tool_name}" >&2
			return 1
		fi
	fi

	if ! echo "${registry_data}" >"${REGISTRY_FILE}"; then
		echo "Failed to write registry file: ${REGISTRY_FILE}" >&2
		return 1
	fi
}

# Search for database files across all tool paths
check_available_tools() {
	local combined_paths=("${@:1}")
	
	local cursor_db_paths=()
	local claude_code_db_paths=()
	local windsurf_db_paths=()
	local path
	local db_file
	local found_file
	local found_path
	
	echo "Searching for database files across all paths."

	for path in "${combined_paths[@]}"; do
		for db_file in "${GANDALF_TOOL_DB_FILES[@]}"; do
			while IFS= read -r -d '' found_file; do
				found_path="$(dirname "${found_file}")"

				[[ "${found_path}" == *"Cursor"* ]] && cursor_db_paths+=("${found_path}")
				[[ "${found_path}" == *"Claude"* ]] && claude_code_db_paths+=("${found_path}")
				[[ "${found_path}" == *"Windsurf"* ]] && windsurf_db_paths+=("${found_path}")
			done < <(find "${path}" -name "${db_file}" -print0 2>/dev/null)
		done
	done

	REGISTRY_CURSOR_PATHS=("${cursor_db_paths[@]}")
	REGISTRY_CLAUDE_PATHS=("${claude_code_db_paths[@]}")
	REGISTRY_WINDSURF_PATHS=("${windsurf_db_paths[@]}")

	cat <<EOF
========================================
Databases Found
========================================
Cursor: ${#REGISTRY_CURSOR_PATHS[@]}
$(printf '%s\n' "${REGISTRY_CURSOR_PATHS[@]}")
Claude Code: ${#REGISTRY_CLAUDE_PATHS[@]}
$(printf '%s\n' "${REGISTRY_CLAUDE_PATHS[@]}")
Windsurf: ${#REGISTRY_WINDSURF_PATHS[@]}
$(printf '%s\n' "${REGISTRY_WINDSURF_PATHS[@]}")

EOF
}

main() {
	local combined_paths

	[[ ! -f "${REGISTRY_FILE}" ]] && init_registry
	combined_paths=("${CURSOR_DB_PATHS[@]}" "${CLAUDE_CODE_DB_PATHS[@]}" "${WINDSURF_DB_PATHS[@]}")
	check_available_tools "${combined_paths[@]}"

	if ! update_registry "claude" "${REGISTRY_CLAUDE_PATHS[@]}"; then
		echo "Failed to update registry for Claude" >&2
		return 1
	fi
	if ! update_registry "cursor" "${REGISTRY_CURSOR_PATHS[@]}"; then
		echo "Failed to update registry for Cursor" >&2
		return 1
	fi
	if ! update_registry "windsurf" "${REGISTRY_WINDSURF_PATHS[@]}"; then
		echo "Failed to update registry for Windsurf" >&2
		return 1
	fi

	echo "Registry set."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
