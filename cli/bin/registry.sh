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

# Initialize the registry file if it does not exist
init_registry() {
	if [[ ! -f "${REGISTRY_FILE}" ]]; then
		mkdir -p "$(dirname "${REGISTRY_FILE}")"
		echo "{}" >"${REGISTRY_FILE}"
		echo "Registry initialized"
	fi
}

# Update registry with tool information
update_registry() {
	local tool_name="${1}"
	local tool_paths="${2}"

	if [[ -z "${tool_name:-}" ]]; then
		echo "Tool name is required" >&2
		return 1
	fi

	if [[ -z "${tool_paths:-}" ]]; then
		echo "Tool paths are required" >&2
		return 1
	fi

	[[ ! -f "${REGISTRY_FILE}" ]] && init_registry

	local registry_data

	registry_data=$(jq --arg tool_name "${tool_name}" \
		--argjson tool_paths "${tool_paths}" \
		'.[$tool_name] = $tool_paths' "${REGISTRY_FILE}")

	echo "${registry_data}" >"${REGISTRY_FILE}"
}

# Search for database files across all tool paths
check_available_tools() {
	local cursor_db_paths=()
	local claude_code_db_paths=()
	local windsurf_db_paths=()

	echo "Searching for database files across all paths."
	COMBINED_PATHS=("${CURSOR_DB_PATHS[@]}" "${CLAUDE_CODE_DB_PATHS[@]}" "${WINDSURF_DB_PATHS[@]}")

	for path in "${COMBINED_PATHS[@]}"; do
		for db_file in "${GANDALF_TOOL_DB_FILES[@]}"; do
			while IFS= read -r -d '' found_file; do
				local found_path
				found_path="$(dirname "$found_file")"

				[[ "${found_path}" == *"Cursor"* ]] && cursor_db_paths+=("${found_path}")
				[[ "${found_path}" == *"Claude"* ]] && claude_code_db_paths+=("${found_path}")
				[[ "${found_path}" == *"Windsurf"* ]] && windsurf_db_paths+=("${found_path}")
			done < <(find "${path}" -name "${db_file}" -print0 2>/dev/null)
		done
	done

	cat <<EOF
========================================
Databases Found
========================================
Cursor: ${#cursor_db_paths[@]}
$(printf '%s\n' "${cursor_db_paths[@]}")

Claude Code: ${#claude_code_db_paths[@]}
$(printf '%s\n' "${claude_code_db_paths[@]}")

Windsurf: ${#windsurf_db_paths[@]}
$(printf '%s\n' "${windsurf_db_paths[@]}")

EOF
}

main() {
	if [[ ! -f "${REGISTRY_FILE}" ]]; then
		init_registry
	fi
	check_available_tools
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
