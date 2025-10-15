#!/usr/bin/env bats

# Registry Management Tests
# Tests for registry file management and database path detection

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/cli/bin/registry.sh"
[[ ! -f "${SCRIPT}" ]] && echo "'SCRIPT' file does not exist" >&2 && exit 1

setup() {
	# shellcheck disable=SC1090,SC1091
	source "${SCRIPT}"
}

########################################################
# mocks
########################################################
mock_find_database_folders() {
	# shellcheck disable=SC2329
	find_database_folders() {
		DB_PATH_DATA=$(jq -n '{"cursor":["/test/cursor"],"claude":["/test/claude"]}')
		export DB_PATH_DATA
		return 0
	}

	export -f find_database_folders
}

mock_update_registry() {
	# shellcheck disable=SC2329
	update_registry() {
		return 0
	}

	export -f update_registry
}

@test "SCRIPT exists and is executable" {
	[[ -f "${SCRIPT}" ]]
	[[ -x "${SCRIPT}" ]]
}

########################################################
# init_registry
########################################################

@test "init_registry:: registry file exists already" {
	local test_file
	test_file="$(mktemp -d)/registry.json"

	run init_registry "${test_file}"
	[[ "$status" -eq 0 ]]
}

@test "init_registry:: fails to create registry file directory" {
	run init_registry "/nonexistent/directory/registry.json"
	[[ "$status" -eq 1 ]]
}

@test "init_registry:: creates registry file" {
	local test_file
	test_file="$(mktemp -d)/registry.json"

	run init_registry "${test_file}"
	[[ "$status" -eq 0 ]]
	[[ -f "${test_file}" ]]

	[[ "$(cat "${test_file}")" == "{}" ]]
}

########################################################
# find_database_folders
########################################################

@test "find_database_folders:: sets DB_PATH_DATA variable" {
	find_database_folders
	[[ "$?" -eq 0 ]]
	[[ -n "${DB_PATH_DATA}" ]]
}

@test "find_database_folders:: returns valid JSON" {
	find_database_folders
	[[ "$?" -eq 0 ]]

	echo "${DB_PATH_DATA}" | jq . >/dev/null
}

@test "find_database_folders:: contains expected structure" {
	find_database_folders
	[[ "$?" -eq 0 ]]

	echo "${DB_PATH_DATA}" | jq -e '.cursor' >/dev/null
	echo "${DB_PATH_DATA}" | jq -e '.claude' >/dev/null
}

########################################################
# update_registry
########################################################

@test "update_registry:: fails without registry file" {
	unset GANDALF_REGISTRY_FILE
	run update_registry
	[[ "$status" -eq 1 ]]
}

@test "update_registry:: fails without DB_PATH_DATA" {
	GANDALF_REGISTRY_FILE="$(mktemp -d)/registry.json"
	unset DB_PATH_DATA
	run update_registry
	[[ "$status" -eq 1 ]]
}

@test "update_registry:: updates registry file" {
	local test_file
	test_file="$(mktemp -d)/registry.json"
	local test_data='{"test": "data"}'

	export GANDALF_REGISTRY_FILE="${test_file}"
	export DB_PATH_DATA="${test_data}"

	run update_registry
	[[ "$status" -eq 0 ]]
	[[ -f "${test_file}" ]]
	[[ "$(cat "${test_file}")" == "${test_data}" ]]
}

########################################################
# registry
########################################################

@test "registry:: creates registry file if it doesn't exist" {
	mock_find_database_folders
	mock_update_registry

	# Set a test registry file
	GANDALF_REGISTRY_FILE="$(mktemp -d)/registry.json"
	export GANDALF_REGISTRY_FILE

	run registry
	[[ "$status" -eq 0 ]]
	[[ -f "${GANDALF_REGISTRY_FILE}" ]]
}

@test "registry:: handles find_database_folders failure" {
	# shellcheck disable=SC2329
	find_database_folders() {
		return 1
	}
	export -f find_database_folders

	GANDALF_REGISTRY_FILE="$(mktemp -d)/registry.json"
	export GANDALF_REGISTRY_FILE

	run registry
	[[ "$status" -eq 1 ]]
}

@test "registry:: handles update_registry failure" {
	mock_find_database_folders

	# shellcheck disable=SC2329
	update_registry() {
		return 1
	}
	export -f update_registry

	GANDALF_REGISTRY_FILE="$(mktemp -d)/registry.json"
	export GANDALF_REGISTRY_FILE

	run registry
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Failed to update registry"

}
