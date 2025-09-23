#!/usr/bin/env bats

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
	SCRIPT_DIR="${BATS_TEST_DIRNAME}"
	cd "$SCRIPT_DIR" || exit 1
	GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
	export GANDALF_PROJECT_ROOT
fi

readonly SCRIPT="${GANDALF_PROJECT_ROOT}/cli/bin/install.sh"
[[ -z "${SCRIPT}" ]] && echo "'SCRIPT' is not set" >&2 && exit 1
[[ ! -f "${SCRIPT}" ]] && echo "'SCRIPT' file does not exist" >&2 && exit 1

setup() {
	TEST_ROOT="$(mktemp -d)"

	# Version File
	VERSION_FILE="${TEST_ROOT}/VERSION"
	echo "0.1.0" >"${VERSION_FILE}"

	# cli
	cp -r "${GANDALF_PROJECT_ROOT}/cli" "${TEST_ROOT}/"

	export HOME="${TEST_ROOT}"
	export VERSION_FILE

	GANDALF_PROJECT_ROOT="${TEST_ROOT}"
	# shellcheck disable=SC1090
	source "${SCRIPT}"

	return 0
}

teardown() {
	if [[ -n "${TEST_ROOT:-}" && -d "${TEST_ROOT}" ]]; then
		rm -rf "${TEST_ROOT}"
	fi
}

@test "get_version::file does not exist" {
	rm -f "${VERSION_FILE}"
	run get_version
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Unable to determine version"
}

@test "get_version::file exists" {
	run get_version
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "0.1.0"
}

@test "run_installer::should source registry script" {
	run run_installer
	[[ "$status" -eq 0 ]]
}

@test "script::should show usage with help flag" {
	run bash "${SCRIPT}" -h
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
}

@test "script::should show version with version flag" {
	run bash "${SCRIPT}" -v
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Gandalf MCP Server v0.1.0"
}

@test "script::should run installer when no arguments provided" {
	run bash "${SCRIPT}"
	[[ "$status" -eq 0 ]]
}
