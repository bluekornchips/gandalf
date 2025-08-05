#!/usr/bin/env bats

# Registry Management Tests
# Tests for registry file management and database path detection

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
	SCRIPT_DIR="${BATS_TEST_DIRNAME}"
	cd "$SCRIPT_DIR" || exit 1
	GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
	export GANDALF_PROJECT_ROOT
fi

readonly REGISTRY_SCRIPT="${GANDALF_PROJECT_ROOT}/cli/bin/registry.sh"
[[ -z "${REGISTRY_SCRIPT}" ]] && echo "'REGISTRY_SCRIPT' is not set" >&2 && exit 1
[[ ! -f "${REGISTRY_SCRIPT}" ]] && echo "'REGISTRY_SCRIPT' file does not exist" >&2 && exit 1

setup() {
	TEST_DIR="$(mktemp -d)"
	export TEST_DIR

	export HOME="${TEST_DIR}"
	export GANDALF_REGISTRY_FILE="${TEST_DIR}/.gandalf/registry.json"

	# shellcheck disable=SC1090,SC1091
	source "${REGISTRY_SCRIPT}"
}

teardown() {
	if [[ -n "${TEST_DIR:-}" && -d "${TEST_DIR}" ]]; then
		rm -rf "${TEST_DIR}"
	fi
}

@test "REGISTRY_SCRIPT exists and is executable" {
	[[ -f "${REGISTRY_SCRIPT}" ]]
	[[ -x "${REGISTRY_SCRIPT}" ]]
}

@test "HOME not set, should exit with error" {
	unset HOME
	run bash "${REGISTRY_SCRIPT}"
	[[ "${status}" -eq 1 ]]
	echo "${output}" | grep -q "'HOME' environment variable is not set"
}

@test "init_registry::creates registry file when it does not exist" {
	[[ -f "${REGISTRY_FILE}" ]]
}

@test "init_registry::creates directory structure when needed" {
	# Since the script executes when sourced, the directory shoud already exist
	local registry_dir
	registry_dir="$(dirname "${REGISTRY_FILE}")"
	[[ -d "${registry_dir}" ]]
}

@test "init_registry::initializes with JSON object" {
	[[ -f "${REGISTRY_FILE}" ]]
	jq -e 'type == "object"' "${REGISTRY_FILE}" >/dev/null
}

@test "init_registry::does not overwrite existing registry file" {
	mkdir -p "$(dirname "${REGISTRY_FILE}")"
	echo '{"test": "data"}' >"${REGISTRY_FILE}"
	local original_content
	original_content="$(cat "${REGISTRY_FILE}")"
	init_registry >/dev/null
	[[ "$(cat "${REGISTRY_FILE}")" == "${original_content}" ]]
}

@test "'REGISTRY_FILE' constant is properly defined" {
	[[ -n "${REGISTRY_FILE:-}" ]]
	[[ "${REGISTRY_FILE}" == "${HOME}/.gandalf/registry.json" ]]
}

@test "check_available_tools::function exists and is callable" {
	run check_available_tools
	[[ "${status}" -eq 0 ]]
}

@test "check_available_tools::function works correctly" {
	run check_available_tools
	[[ "${status}" -eq 0 ]]
	echo "${output}" | grep -q "Searching for database files across all paths"
}

@test "check_available_tools::handles real system paths" {
	run check_available_tools
	[[ "${status}" -eq 0 ]]
	# Should handle real paths without error
	echo "${output}" | grep -q "Searching for database files across all paths"
}

@test "update_registry::function exists and is callable" {
	run update_registry
	[[ "${status}" -eq 1 ]]
	echo "${output}" | grep -q "Tool name is required"
}

@test "update_registry::requires tool name parameter" {
	run update_registry "" '["/path/to/tool"]'
	[[ "${status}" -eq 1 ]]
	echo "${output}" | grep -q "Tool name is required"
}

@test "update_registry::handles empty tool paths" {
	init_registry
	run update_registry "test-tool"
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e '.["test-tool"] | length == 0'
}

@test "update_registry::creates registry file if it does not exist" {
	[[ -f "${REGISTRY_FILE}" ]]
	run update_registry "test-tool" '["/path/to/tool"]'
	[[ "${status}" -eq 0 ]]
}

@test "update_registry::adds new tool to empty registry" {
	init_registry
	run update_registry "cursor" "/path/to/cursor"
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e '.cursor[0] == "/path/to/cursor"'
}

@test "script::executes main logic when sourced" {
	[[ -f "${REGISTRY_FILE}" ]]
	jq -e 'type == "object"' "${REGISTRY_FILE}" >/dev/null
}

@test "update_registry::updates existing tool paths" {
	init_registry
	update_registry "cursor" "/old/path"

	run update_registry "cursor" "/new/path"
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e '.cursor[0] == "/new/path"'
}

@test "update_registry::handles multiple tool paths" {
	init_registry
	run update_registry "cursor" "/path1" "/path2" "/path3"
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e '.cursor | length == 3'
	echo "${registry_content}" | jq -e '.cursor[0] == "/path1"'
	echo "${registry_content}" | jq -e '.cursor[1] == "/path2"'
	echo "${registry_content}" | jq -e '.cursor[2] == "/path3"'
}

@test "update_registry::adds multiple tools to registry" {
	init_registry
	update_registry "cursor" "/cursor/path"
	run update_registry "claude" "/claude/path"
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e 'has("cursor")'
	echo "${registry_content}" | jq -e 'has("claude")'
	echo "${registry_content}" | jq -e '.cursor[0] == "/cursor/path"'
	echo "${registry_content}" | jq -e '.claude[0] == "/claude/path"'
}

@test "update_registry::maintains registry structure" {
	init_registry
	run update_registry "test-tool" '["/test/path"]'
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e 'type == "object"'
	echo "${registry_content}" | jq -e 'has("test-tool")'
}

@test "update_registry::handles empty tool paths array" {
	init_registry
	run update_registry "test-tool"
	[[ "${status}" -eq 0 ]]

	local registry_content
	registry_content="$(cat "${REGISTRY_FILE}")"
	echo "${registry_content}" | jq -e '.["test-tool"] | length == 0'
}
