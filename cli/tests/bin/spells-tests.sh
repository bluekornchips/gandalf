#!/usr/bin/env bats
#
# Spell Management Tests
# Tests for spell registration and management functionality
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/cli/lib/spells.sh"
[[ ! -f "${SCRIPT}" ]] && echo "setup:: Script not found: ${SCRIPT}" >&2 && exit 1

setup() {
	# shellcheck disable=SC1090,SC1091
	source "${SCRIPT}"

	local test_dir
	test_dir="$(mktemp -d)"
	TEST_REGISTRY_FILE="${test_dir}/registry.json"
	export TEST_REGISTRY_FILE
	export GANDALF_REGISTRY_FILE="${TEST_REGISTRY_FILE}"
}

teardown() {
	if [[ -n "${TEST_REGISTRY_FILE}" ]] && [[ -f "${TEST_REGISTRY_FILE}" ]]; then
		rm -f "${TEST_REGISTRY_FILE}"
	fi
}

########################################################
# Script existence and structure
########################################################

@test "spells:: script exists and is executable" {
	[[ -f "${SCRIPT}" ]]
	[[ -x "${SCRIPT}" ]]
}

########################################################
# usage
########################################################

@test "spells:: usage displays help information" {
	run usage
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
	echo "$output" | grep -q "Commands:"
	echo "$output" | grep -q "add"
	echo "$output" | grep -q "remove"
	echo "$output" | grep -q "list"
}

@test "spells:: usage shows help for -h" {
	run main -h
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
}

@test "spells:: usage shows help for --help" {
	run main --help
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
}

########################################################
# init_registry
########################################################

@test "init_registry:: creates registry file if it doesn't exist" {
	run init_registry "${TEST_REGISTRY_FILE}"
	[[ "$status" -eq 0 ]]
	[[ -f "${TEST_REGISTRY_FILE}" ]]
	[[ "$(cat "${TEST_REGISTRY_FILE}")" == "{}" ]]
}

@test "init_registry:: doesn't overwrite existing registry file" {
	echo '{"existing": "data"}' >"${TEST_REGISTRY_FILE}"
	run init_registry "${TEST_REGISTRY_FILE}"
	[[ "$status" -eq 0 ]]
	[[ "$(cat "${TEST_REGISTRY_FILE}")" == '{"existing": "data"}' ]]
}

@test "init_registry:: creates parent directory if needed" {
	local test_file
	test_file="$(mktemp -d)/subdir/registry.json"
	run init_registry "${test_file}"
	[[ "$status" -eq 0 ]]
	[[ -f "${test_file}" ]]
	rm -rf "$(dirname "${test_file}")"
}

@test "init_registry:: fails if directory cannot be created" {
	run init_registry "/nonexistent/path/registry.json"
	[[ "$status" -eq 1 ]]
}

########################################################
# load_registry
########################################################

@test "load_registry:: loads valid JSON registry file" {
	echo '{"spells": {"test": {}}}' >"${TEST_REGISTRY_FILE}"
	run load_registry "${TEST_REGISTRY_FILE}"
	[[ "$status" -eq 0 ]]
	[[ -n "${REGISTRY_DATA}" ]]
}

@test "load_registry:: fails if jq is not installed" {
	if ! command -v jq >/dev/null 2>&1; then
		skip "jq not installed"
	fi

	# Mock jq as unavailable
	PATH_ORIG="${PATH}"
	PATH="/nonexistent/bin"
	export PATH

	run load_registry "${TEST_REGISTRY_FILE}"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "jq is required"

	PATH="${PATH_ORIG}"
	export PATH
}

@test "load_registry:: fails if registry file doesn't exist" {
	run load_registry "/nonexistent/registry.json"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "not found"
}

########################################################
# save_registry
########################################################

@test "save_registry:: saves valid JSON data" {
	local test_data
	test_data='{"spells": {"test": {"name": "test"}}}'
	run save_registry "${TEST_REGISTRY_FILE}" "${test_data}"
	[[ "$status" -eq 0 ]]
	[[ -f "${TEST_REGISTRY_FILE}" ]]
	[[ "$(cat "${TEST_REGISTRY_FILE}")" == "${test_data}" ]]
}

@test "save_registry:: fails with invalid JSON" {
	run save_registry "${TEST_REGISTRY_FILE}" "invalid json"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid JSON"
}

@test "save_registry:: fails if file cannot be written" {
	local readonly_file
	readonly_file="$(mktemp)"
	chmod 444 "${readonly_file}"
	run save_registry "${readonly_file}" '{"test": "data"}'
	[[ "$status" -eq 1 ]]
	chmod 644 "${readonly_file}"
	rm -f "${readonly_file}"
}

########################################################
# add_spell
########################################################

@test "add_spell:: adds spell to empty registry" {
	init_registry "${TEST_REGISTRY_FILE}"
	run add_spell "test-spell" "Test description" "echo test" "" "" "" ""
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Added spell 'test-spell'"

	local spell_config
	spell_config=$(jq '.spells."test-spell"' "${TEST_REGISTRY_FILE}")
	[[ "$(echo "${spell_config}" | jq -r '.name')" == "test-spell" ]]
	[[ "$(echo "${spell_config}" | jq -r '.description')" == "Test description" ]]
	[[ "$(echo "${spell_config}" | jq -r '.command')" == "echo test" ]]
}

@test "add_spell:: adds spell with path" {
	init_registry "${TEST_REGISTRY_FILE}"
	run add_spell "test-spell" "Test" "echo test" "/some/path" "" "" ""
	[[ "$status" -eq 0 ]]

	local spell_config
	spell_config=$(jq '.spells."test-spell"' "${TEST_REGISTRY_FILE}")
	[[ "$(echo "${spell_config}" | jq -r '.path')" == "/some/path" ]]
}

@test "add_spell:: adds spell with allowed_paths" {
	init_registry "${TEST_REGISTRY_FILE}"
	run add_spell "test-spell" "Test" "echo test" "" "/path1,/path2" "" ""
	[[ "$status" -eq 0 ]]

	local spell_config
	spell_config=$(jq '.spells."test-spell"' "${TEST_REGISTRY_FILE}")
	local paths
	paths=$(echo "${spell_config}" | jq -r '.allowed_paths | length')
	[[ "${paths}" -eq 2 ]]
}

@test "add_spell:: adds spell with allowed_commands" {
	init_registry "${TEST_REGISTRY_FILE}"
	run add_spell "test-spell" "Test" "echo test" "" "" "echo,curl" ""
	[[ "$status" -eq 0 ]]

	local spell_config
	spell_config=$(jq '.spells."test-spell"' "${TEST_REGISTRY_FILE}")
	local commands
	commands=$(echo "${spell_config}" | jq -r '.allowed_commands | length')
	[[ "${commands}" -eq 2 ]]
}

@test "add_spell:: adds spell with timeout" {
	init_registry "${TEST_REGISTRY_FILE}"
	run add_spell "test-spell" "Test" "echo test" "" "" "" "60"
	[[ "$status" -eq 0 ]]

	local spell_config
	spell_config=$(jq '.spells."test-spell"' "${TEST_REGISTRY_FILE}")
	[[ "$(echo "${spell_config}" | jq -r '.timeout')" == "60" ]]
}

@test "add_spell:: fails if spell already exists" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" ""
	run add_spell "test-spell" "Test" "echo test" "" "" "" ""
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "already exists"
}

@test "add_spell:: preserves existing registry data" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"cursor": ["/path"], "spells": {}}' >"${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" ""
	local cursor_data
	cursor_data=$(jq -r '.cursor[0]' "${TEST_REGISTRY_FILE}")
	[[ "${cursor_data}" == "/path" ]]
}

########################################################
# remove_spell
########################################################

@test "remove_spell:: removes existing spell" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" ""
	run remove_spell "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Removed spell 'test-spell'"

	local spell_exists
	spell_exists=$(jq -e '.spells."test-spell" // empty' "${TEST_REGISTRY_FILE}" 2>/dev/null)
	[[ -z "${spell_exists}" ]] || [[ "${spell_exists}" == "null" ]]
}

@test "remove_spell:: fails if spell doesn't exist" {
	init_registry "${TEST_REGISTRY_FILE}"
	run remove_spell "nonexistent"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "not found"
}

@test "remove_spell:: preserves other spells" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "spell1" "Test1" "echo test1" "" "" "" ""
	add_spell "spell2" "Test2" "echo test2" "" "" "" ""
	remove_spell "spell1"
	local spell2_exists
	spell2_exists=$(jq -e '.spells."spell2" // empty' "${TEST_REGISTRY_FILE}" 2>/dev/null)
	[[ -n "${spell2_exists}" ]] && [[ "${spell2_exists}" != "null" ]]
}

########################################################
# list_spells
########################################################

@test "list_spells:: lists no spells when registry is empty" {
	init_registry "${TEST_REGISTRY_FILE}"
	run list_spells
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "No spells registered"
}

@test "list_spells:: lists registered spells" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "spell1" "Test1" "echo test1" "" "" "" ""
	add_spell "spell2" "Test2" "echo test2" "" "" "" ""
	run list_spells
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "spell1"
	echo "$output" | grep -q "spell2"
}

@test "list_spells:: handles registry without spells key" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"cursor": []}' >"${TEST_REGISTRY_FILE}"
	run list_spells
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "No spells registered"
}

########################################################
# show_spell
########################################################

@test "show_spell:: displays spell configuration" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test description" "echo test" "" "" "" ""
	run show_spell "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "test-spell"
	echo "$output" | grep -q "Test description"
	echo "$output" | grep -q "echo test"
}

@test "show_spell:: fails if spell doesn't exist" {
	init_registry "${TEST_REGISTRY_FILE}"
	run show_spell "nonexistent"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "not found"
}

@test "show_spell:: outputs valid JSON" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" ""
	run show_spell "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | jq . >/dev/null
}

########################################################
# validate_spell
########################################################

@test "validate_spell:: validates correct spell configuration" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test description" "echo test" "" "" "" ""
	run validate_spell "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "configuration is valid"
}

@test "validate_spell:: fails if spell doesn't exist" {
	init_registry "${TEST_REGISTRY_FILE}"
	run validate_spell "nonexistent"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "not found"
}

@test "validate_spell:: detects missing name field" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"spells": {"test-spell": {"description": "Test", "command": "echo test"}}}' >"${TEST_REGISTRY_FILE}"
	run validate_spell "test-spell"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Missing required field 'name'"
}

@test "validate_spell:: detects missing description field" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"spells": {"test-spell": {"name": "test-spell", "command": "echo test"}}}' >"${TEST_REGISTRY_FILE}"
	run validate_spell "test-spell"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Missing required field 'description'"
}

@test "validate_spell:: detects missing command field" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"spells": {"test-spell": {"name": "test-spell", "description": "Test"}}}' >"${TEST_REGISTRY_FILE}"
	run validate_spell "test-spell"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Missing required field 'command'"
}

@test "validate_spell:: detects invalid timeout value" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"spells": {"test-spell": {"name": "test-spell", "description": "Test", "command": "echo test", "timeout": 500}}}' >"${TEST_REGISTRY_FILE}"
	run validate_spell "test-spell"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid timeout value"
}

@test "validate_spell:: detects negative timeout" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"spells": {"test-spell": {"name": "test-spell", "description": "Test", "command": "echo test", "timeout": -1}}}' >"${TEST_REGISTRY_FILE}"
	run validate_spell "test-spell"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid timeout value"
}

@test "validate_spell:: detects zero timeout" {
	init_registry "${TEST_REGISTRY_FILE}"
	echo '{"spells": {"test-spell": {"name": "test-spell", "description": "Test", "command": "echo test", "timeout": 0}}}' >"${TEST_REGISTRY_FILE}"
	run validate_spell "test-spell"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid timeout value"
}

@test "validate_spell:: accepts valid timeout" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" "60"
	run validate_spell "test-spell"
	[[ "$status" -eq 0 ]]
}

########################################################
# main function - add command
########################################################

@test "main:: add command requires name, description, and command" {
	run main add
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires name, description, and command"
}

@test "main:: add command adds spell successfully" {
	init_registry "${TEST_REGISTRY_FILE}"
	run main add "test-spell" "Test description" "echo test"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Added spell"
}

@test "main:: add command handles --path option" {
	init_registry "${TEST_REGISTRY_FILE}"
	run main add "test-spell" "Test" "echo test" --path "/some/path"
	[[ "$status" -eq 0 ]]
	local path
	path=$(jq -r '.spells."test-spell".path' "${TEST_REGISTRY_FILE}")
	[[ "${path}" == "/some/path" ]]
}

@test "main:: add command handles --allowed-paths option" {
	init_registry "${TEST_REGISTRY_FILE}"
	run main add "test-spell" "Test" "echo test" --allowed-paths "/path1,/path2"
	[[ "$status" -eq 0 ]]
	local paths_count
	paths_count=$(jq '.spells."test-spell".allowed_paths | length' "${TEST_REGISTRY_FILE}")
	[[ "${paths_count}" -eq 2 ]]
}

@test "main:: add command handles --allowed-commands option" {
	init_registry "${TEST_REGISTRY_FILE}"
	run main add "test-spell" "Test" "echo test" --allowed-commands "echo,curl"
	[[ "$status" -eq 0 ]]
	local commands_count
	commands_count=$(jq '.spells."test-spell".allowed_commands | length' "${TEST_REGISTRY_FILE}")
	[[ "${commands_count}" -eq 2 ]]
}

@test "main:: add command handles --timeout option" {
	init_registry "${TEST_REGISTRY_FILE}"
	run main add "test-spell" "Test" "echo test" --timeout "120"
	[[ "$status" -eq 0 ]]
	local timeout
	timeout=$(jq -r '.spells."test-spell".timeout' "${TEST_REGISTRY_FILE}")
	[[ "${timeout}" == "120" ]]
}

@test "main:: add command handles unknown options" {
	run main add "test-spell" "Test" "echo test" --unknown-option
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Unknown option"
}

########################################################
# main function - remove command
########################################################

@test "main:: remove command requires spell name" {
	run main remove
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a spell name"
}

@test "main:: remove command removes spell successfully" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" ""
	run main remove "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Removed spell"
}

########################################################
# main function - list command
########################################################

@test "main:: list command lists spells" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "spell1" "Test1" "echo test1" "" "" "" ""
	run main list
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "spell1"
}

########################################################
# main function - show command
########################################################

@test "main:: show command requires spell name" {
	run main show
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a spell name"
}

@test "main:: show command displays spell details" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test description" "echo test" "" "" "" ""
	run main show "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "test-spell"
}

########################################################
# main function - validate command
########################################################

@test "main:: validate command requires spell name" {
	run main validate
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a spell name"
}

@test "main:: validate command validates spell" {
	init_registry "${TEST_REGISTRY_FILE}"
	add_spell "test-spell" "Test" "echo test" "" "" "" ""
	run main validate "test-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "configuration is valid"
}

########################################################
# main function - error handling
########################################################

@test "main:: handles empty command" {
	run main ""
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Command required"
}

@test "main:: handles unknown command" {
	run main unknown-command
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Unknown command"
}

########################################################
# Integration tests
########################################################

@test "integration:: full workflow add list show remove" {
	init_registry "${TEST_REGISTRY_FILE}"

	# Add spell
	run main add "workflow-spell" "Workflow test" "echo workflow" --timeout "45"
	[[ "$status" -eq 0 ]]

	# List spells
	run main list
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "workflow-spell"

	# Show spell
	run main show "workflow-spell"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Workflow test"

	# Validate spell
	run main validate "workflow-spell"
	[[ "$status" -eq 0 ]]

	# Remove spell
	run main remove "workflow-spell"
	[[ "$status" -eq 0 ]]

	# Verify removed
	run main list
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "No spells registered"
}

@test "integration:: multiple spells management" {
	init_registry "${TEST_REGISTRY_FILE}"

	main add "spell1" "First" "echo first" "" "" "" ""
	main add "spell2" "Second" "echo second" "" "" "" ""
	main add "spell3" "Third" "echo third" "" "" "" ""

	run main list
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "spell1"
	echo "$output" | grep -q "spell2"
	echo "$output" | grep -q "spell3"

	main remove "spell2"

	run main list
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "spell1"
	echo "$output" | grep -q "spell3"
	echo "$output" | grep -q -v "spell2"
}
