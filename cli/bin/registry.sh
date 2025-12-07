#!/usr/bin/env bash
#
# Registry Management for Gandalf
# Manages tool registrations and database paths for
#
set -eo pipefail

# Defaults
DEFAULT_GANDALF_REGISTRY_FILE="${HOME}/.gandalf/registry.json"

# Find all folders with database files in supported directories
#
# Inputs:
# - None
#
# Side Effects:
# - DB_PATH_DATA, sets array of found database folders
find_database_folders() {

	if ! command -v jq >/dev/null 2>&1; then
		echo "jq is required for database folder detection but not installed" >&2
		echo "Install jq from: https://github.com/jqlang/jq" >&2
		return 1
	fi

	CURSOR_DB_PATHS=(
		# Linux
		"$HOME/.config/Cursor/User/workspaceStorage"
		# macOS
		"$HOME/Library/Application Support/Cursor/User/workspaceStorage"
		# Windows/WSL
		"/mnt/c/Users/$(whoami)/AppData/Roaming/Cursor/User/workspaceStorage"
	)

	CLAUDE_CODE_DB_PATHS=(
		# Linux
		"$HOME/.claude"
		"$HOME/.config/claude"
		# macOS
		"$HOME/Library/Application Support/Claude"
		# Windows/WSL
		"/mnt/c/Users/$(whoami)/AppData/Roaming/Claude"
	)

	SUPPORTED_DB_FILES=(
		"state.vscdb"
		"workspace.db"
		"storage.db"
		"cursor.db"
		"claude.db"
	)

	local found_cursor_db_paths=()
	for cursor_db_path in "${CURSOR_DB_PATHS[@]}"; do
		if [[ -d "$cursor_db_path" ]]; then
			# Check if any database files exist in subdirectories
			local found_db=false
			for db_file in "${SUPPORTED_DB_FILES[@]}"; do
				if find "$cursor_db_path" -name "$db_file" -type f 2>/dev/null | head -n 1 | grep -q .; then
					found_db=true
					break
				fi
			done
			if [[ "$found_db" == "true" ]]; then
				found_cursor_db_paths+=("$cursor_db_path")
			fi
		fi
	done

	local found_claude_code_db_paths=()
	for claude_code_db_path in "${CLAUDE_CODE_DB_PATHS[@]}"; do
		if [[ -d "$claude_code_db_path" ]]; then
			local found_db=false
			for db_file in "${SUPPORTED_DB_FILES[@]}"; do
				if find "$claude_code_db_path" -name "$db_file" -type f 2>/dev/null | head -n 1 | grep -q .; then
					found_db=true
					break
				fi
			done
			if [[ "$found_db" == "true" ]]; then
				found_claude_code_db_paths+=("$claude_code_db_path")
			fi
		fi
	done

	# Convert bash arrays to JSON arrays
	local cursor_db_paths_json
	if [[ ${#found_cursor_db_paths[@]} -eq 0 ]]; then
		cursor_db_paths_json="[]"
	else
		cursor_db_paths_json=$(printf '%s\n' "${found_cursor_db_paths[@]}" | jq -R . | jq -s .)
	fi

	local claude_code_db_paths_json
	if [[ ${#found_claude_code_db_paths[@]} -eq 0 ]]; then
		claude_code_db_paths_json="[]"
	else
		claude_code_db_paths_json=$(printf '%s\n' "${found_claude_code_db_paths[@]}" | jq -R . | jq -s .)
	fi

	DB_PATH_DATA=$(
		jq -n \
			--argjson cursor_db_paths "$cursor_db_paths_json" \
			--argjson claude_code_db_paths "$claude_code_db_paths_json" \
			'{
			cursor: $cursor_db_paths,
			claude: $claude_code_db_paths
			}'
	)

	export DB_PATH_DATA

	return 0
}

# Initialize the registry file if it does not exist
#
# Inputs:
# - None
#
# Side Effects:
# - REGISTRY_FILE, creates directory and file if needed
init_registry() {
	local registry_file="$1"

	[[ -f "${registry_file}" ]] && return 0

	echo "Creating registry file: ${registry_file}"

	local registry_dir
	registry_dir="$(dirname "${registry_file}")"

	if ! mkdir -p "${registry_dir}"; then
		echo "Failed to create registry directory: ${registry_dir}" >&2
		return 1
	fi

	echo "{}" >"${registry_file}"

	echo "Created registry file: ${registry_file}"

	return 0
}

# Update the registry with the database folders, overwriting any existing registry
#
# Inputs:
# - None
#
# Side Effects:
# - REGISTRY_FILE, updates the registry file with database folders
update_registry() {
	[[ -z "${GANDALF_REGISTRY_FILE}" ]] && echo "Registry file is required" >&2 && return 1
	[[ -z "${DB_PATH_DATA}" ]] && echo "Database folders JSON date is required" >&2 && return 1

	if ! command -v jq >/dev/null 2>&1; then
		echo "jq is required for registry updates but not installed" >&2
		echo "Install jq from: https://github.com/jqlang/jq" >&2
		return 1
	fi

	if ! echo "${DB_PATH_DATA}" >"${GANDALF_REGISTRY_FILE}"; then
		echo "Failed to write registry file: ${GANDALF_REGISTRY_FILE}" >&2
		return 1
	fi

	echo "Updated registry file: ${GANDALF_REGISTRY_FILE}"
	jq . "${GANDALF_REGISTRY_FILE}"

	return 0
}

registry() {
	GANDALF_REGISTRY_FILE="${GANDALF_REGISTRY_FILE:-${DEFAULT_GANDALF_REGISTRY_FILE}}"

	export GANDALF_REGISTRY_FILE

	if [[ ! -f "${GANDALF_REGISTRY_FILE}" ]]; then
		init_registry "${GANDALF_REGISTRY_FILE}"
	fi

	if ! find_database_folders; then
		return 1
	fi

	if ! update_registry; then
		echo "Failed to update registry" >&2
		return 1
	fi

	return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	registry "$@"
fi
