#!/usr/bin/env bash
#
# Spell Management for Gandalf
# Manages spell registrations for external API tools
#
set -eo pipefail

# Defaults
DEFAULT_GANDALF_REGISTRY_FILE="${HOME}/.gandalf/registry.json"

# Display usage information
#
# Inputs:
# - None
#
# Side Effects:
# - Prints usage to stdout
usage() {
	cat <<EOF
Usage: $(basename "$0") [COMMAND] [OPTIONS]

Manage spell registrations for Gandalf MCP server.

Commands:
  add <name> <description> <command> [options]  Add a new spell
  remove <name>                                  Remove a spell
  list                                           List all registered spells
  show <name>                                    Show spell details
  validate <name>                                Validate spell configuration

Options for 'add':
  --path <path>                                  Working directory for spell execution
  --allowed-paths <path1,path2,...>              Comma-separated list of allowed paths
  --allowed-commands <cmd1,cmd2,...>             Comma-separated list of allowed commands
  --timeout <seconds>                            Execution timeout (default: 30, max: 300)

Examples:
  $(basename "$0") add weather-api "Get weather data" "curl -X GET https://api.example.com/data"
  $(basename "$0") add script-tool "Run script" "./scripts/my-script.sh" --path "/home/user/scripts" --allowed-paths "/home/user/scripts"
  $(basename "$0") remove weather-api
  $(basename "$0") list

EOF
}

# Initialize the registry file if it does not exist
#
# Inputs:
# - $1 registry_file, path to registry file
#
# Side Effects:
# - Creates registry file and directory if needed
init_registry() {
	local registry_file="$1"

	[[ -f "${registry_file}" ]] && return 0

	echo "spells:: Creating registry file: ${registry_file}"

	local registry_dir
	registry_dir="$(dirname "${registry_file}")"

	if ! mkdir -p "${registry_dir}"; then
		echo "spells:: Failed to create registry directory: ${registry_dir}" >&2
		return 1
	fi

	echo "{}" >"${registry_file}"

	return 0
}

# Load registry file
#
# Inputs:
# - $1 registry_file, path to registry file
#
# Side Effects:
# - REGISTRY_DATA, sets JSON content of registry file
load_registry() {
	local registry_file="$1"

	if ! command -v jq >/dev/null 2>&1; then
		echo "spells:: jq is required for spell management but not installed" >&2
		echo "spells:: Install jq from: https://github.com/jqlang/jq" >&2
		return 1
	fi

	if [[ ! -f "${registry_file}" ]]; then
		echo "spells:: Registry file not found: ${registry_file}" >&2
		return 1
	fi

	REGISTRY_DATA=$(cat "${registry_file}")

	export REGISTRY_DATA

	return 0
}

# Save registry file
#
# Inputs:
# - $1 registry_file, path to registry file
# - $2 registry_data, JSON content to write
#
# Side Effects:
# - Updates registry file with new data
save_registry() {
	local registry_file="$1"
	local registry_data="$2"

	if ! echo "${registry_data}" | jq . >/dev/null 2>&1; then
		echo "spells:: Invalid JSON data" >&2
		return 1
	fi

	if ! echo "${registry_data}" >"${registry_file}"; then
		echo "spells:: Failed to write registry file: ${registry_file}" >&2
		return 1
	fi

	return 0
}

# Add a spell to the registry
#
# Inputs:
# - $1 name, spell name
# - $2 description, spell description
# - $3 command, command to execute
# - $4 path, optional working directory
# - $5 allowed_paths, optional comma-separated allowed paths
# - $6 allowed_commands, optional comma-separated allowed commands
# - $7 timeout, optional timeout in seconds
#
# Side Effects:
# - Updates registry file with new spell
add_spell() {
	local name="$1"
	local description="$2"
	local command="$3"
	local path="$4"
	local allowed_paths="$5"
	local allowed_commands="$6"
	local timeout="$7"

	local registry_file="${GANDALF_REGISTRY_FILE:-${DEFAULT_GANDALF_REGISTRY_FILE}}"

	if ! init_registry "${registry_file}"; then
		return 1
	fi

	if ! load_registry "${registry_file}"; then
		return 1
	fi

	# Check if spell already exists
	if echo "${REGISTRY_DATA}" | jq -e ".spells.\"${name}\" // empty" >/dev/null 2>&1; then
		echo "spells:: Spell '${name}' already exists" >&2
		return 1
	fi

	# Build spell configuration
	local spell_config
	spell_config=$(jq -n \
		--arg name "${name}" \
		--arg description "${description}" \
		--arg command "${command}" \
		'{
			name: $name,
			description: $description,
			command: $command
		}')

	# Add optional fields
	if [[ -n "${path}" ]]; then
		spell_config=$(echo "${spell_config}" | jq --arg path "${path}" '. + {path: $path}')
	fi

	if [[ -n "${allowed_paths}" ]]; then
		local paths_array
		paths_array=$(echo "${allowed_paths}" | tr ',' '\n' | jq -R . | jq -s .)
		spell_config=$(echo "${spell_config}" | jq --argjson paths "${paths_array}" '. + {allowed_paths: $paths}')
	fi

	if [[ -n "${allowed_commands}" ]]; then
		local commands_array
		commands_array=$(echo "${allowed_commands}" | tr ',' '\n' | jq -R . | jq -s .)
		spell_config=$(echo "${spell_config}" | jq --argjson commands "${commands_array}" '. + {allowed_commands: $commands}')
	fi

	if [[ -n "${timeout}" ]]; then
		spell_config=$(echo "${spell_config}" | jq --argjson timeout "${timeout}" '. + {timeout: $timeout}')
	fi

	# Update registry
	local updated_registry
	updated_registry=$(echo "${REGISTRY_DATA}" | jq --argjson spell "${spell_config}" '.spells = (.spells // {}) + {($spell.name): $spell}')

	if ! save_registry "${registry_file}" "${updated_registry}"; then
		return 1
	fi

	echo "spells:: Added spell '${name}'"
	return 0
}

# Remove a spell from the registry
#
# Inputs:
# - $1 name, spell name
#
# Side Effects:
# - Updates registry file removing the spell
remove_spell() {
	local name="$1"
	local registry_file="${GANDALF_REGISTRY_FILE:-${DEFAULT_GANDALF_REGISTRY_FILE}}"

	if ! load_registry "${registry_file}"; then
		return 1
	fi

	# Check if spell exists
	if ! echo "${REGISTRY_DATA}" | jq -e ".spells.\"${name}\" // empty" >/dev/null 2>&1; then
		echo "spells:: Spell '${name}' not found" >&2
		return 1
	fi

	# Remove spell
	local updated_registry
	updated_registry=$(echo "${REGISTRY_DATA}" | jq "del(.spells.\"${name}\")")

	if ! save_registry "${registry_file}" "${updated_registry}"; then
		return 1
	fi

	echo "spells:: Removed spell '${name}'"
	return 0
}

# List all registered spells
#
# Inputs:
# - None
#
# Side Effects:
# - Prints spell list to stdout
list_spells() {
	local registry_file="${GANDALF_REGISTRY_FILE:-${DEFAULT_GANDALF_REGISTRY_FILE}}"

	if ! load_registry "${registry_file}"; then
		return 1
	fi

	local spells
	spells=$(echo "${REGISTRY_DATA}" | jq -r '.spells // {} | keys[]' 2>/dev/null)

	if [[ -z "${spells}" ]]; then
		echo "spells:: No spells registered"
		return 0
	fi

	echo "spells:: Registered spells:"
	while IFS= read -r name; do
		if [[ -n "${name}" ]]; then
			echo "spells::   - ${name}"
		fi
	done <<<"${spells}"

	return 0
}

# Show spell details
#
# Inputs:
# - $1 name, spell name
#
# Side Effects:
# - Prints spell details to stdout
show_spell() {
	local name="$1"
	local registry_file="${GANDALF_REGISTRY_FILE:-${DEFAULT_GANDALF_REGISTRY_FILE}}"

	if ! load_registry "${registry_file}"; then
		return 1
	fi

	local spell_config
	spell_config=$(echo "${REGISTRY_DATA}" | jq ".spells.\"${name}\"" 2>/dev/null)

	if [[ -z "${spell_config}" ]] || [[ "${spell_config}" == "null" ]]; then
		echo "spells:: Spell '${name}' not found" >&2
		return 1
	fi

	echo "spells:: Spell '${name}':"
	echo "${spell_config}" | jq .

	return 0
}

# Validate spell configuration
#
# Inputs:
# - $1 name, spell name
#
# Side Effects:
# - Prints validation results to stdout
validate_spell() {
	local name="$1"
	local registry_file="${GANDALF_REGISTRY_FILE:-${DEFAULT_GANDALF_REGISTRY_FILE}}"

	if ! load_registry "${registry_file}"; then
		return 1
	fi

	local spell_config
	spell_config=$(echo "${REGISTRY_DATA}" | jq ".spells.\"${name}\"" 2>/dev/null)

	if [[ -z "${spell_config}" ]] || [[ "${spell_config}" == "null" ]]; then
		echo "spells:: Spell '${name}' not found" >&2
		return 1
	fi

	local errors=0

	# Check required fields
	if ! echo "${spell_config}" | jq -e '.name // empty' >/dev/null 2>&1; then
		echo "spells:: Error: Missing required field 'name'" >&2
		errors=$((errors + 1))
	fi

	if ! echo "${spell_config}" | jq -e '.description // empty' >/dev/null 2>&1; then
		echo "spells:: Error: Missing required field 'description'" >&2
		errors=$((errors + 1))
	fi

	if ! echo "${spell_config}" | jq -e '.command // empty' >/dev/null 2>&1; then
		echo "spells:: Error: Missing required field 'command'" >&2
		errors=$((errors + 1))
	fi

	# Check timeout if present
	local timeout
	timeout=$(echo "${spell_config}" | jq -r '.timeout // empty')
	if [[ -n "${timeout}" ]]; then
		if ! [[ "${timeout}" =~ ^[0-9]+$ ]] || [[ "${timeout}" -le 0 ]] || [[ "${timeout}" -gt 300 ]]; then
			echo "spells:: Error: Invalid timeout value (must be 1-300)" >&2
			errors=$((errors + 1))
		fi
	fi

	if [[ ${errors} -eq 0 ]]; then
		echo "spells:: Spell '${name}' configuration is valid"
		return 0
	else
		echo "spells:: Spell '${name}' has ${errors} error(s)" >&2
		return 1
	fi
}

# Main entry point
main() {
	local command="$1"
	shift || true

	case "${command}" in
	add)
		if [[ $# -lt 3 ]]; then
			echo "spells:: Error: 'add' requires name, description, and command" >&2
			usage >&2
			return 1
		fi

		local name="$1"
		local description="$2"
		local command="$3"
		shift 3 || true

		local path=""
		local allowed_paths=""
		local allowed_commands=""
		local timeout=""

		while [[ $# -gt 0 ]]; do
			case "$1" in
			--path)
				path="$2"
				shift 2 || true
				;;
			--allowed-paths)
				allowed_paths="$2"
				shift 2 || true
				;;
			--allowed-commands)
				allowed_commands="$2"
				shift 2 || true
				;;
			--timeout)
				timeout="$2"
				shift 2 || true
				;;
			*)
				echo "spells:: Unknown option: $1" >&2
				usage >&2
				return 1
				;;
			esac
		done

		add_spell "${name}" "${description}" "${command}" "${path}" "${allowed_paths}" "${allowed_commands}" "${timeout}"
		;;
	remove)
		if [[ $# -lt 1 ]]; then
			echo "spells:: Error: 'remove' requires a spell name" >&2
			usage >&2
			return 1
		fi
		remove_spell "$1"
		;;
	list)
		list_spells
		;;
	show)
		if [[ $# -lt 1 ]]; then
			echo "spells:: Error: 'show' requires a spell name" >&2
			usage >&2
			return 1
		fi
		show_spell "$1"
		;;
	validate)
		if [[ $# -lt 1 ]]; then
			echo "spells:: Error: 'validate' requires a spell name" >&2
			usage >&2
			return 1
		fi
		validate_spell "$1"
		;;
	-h | --help)
		usage
		return 0
		;;
	"")
		echo "spells:: Error: Command required" >&2
		usage >&2
		return 1
		;;
	*)
		echo "spells:: Unknown command: ${command}" >&2
		usage >&2
		return 1
		;;
	esac
}

# Allow script to be executed directly with arguments, or sourced
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	main "$@"
	exit $?
fi
