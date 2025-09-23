#!/usr/bin/env bats
#
# Gandalf Core Library Tests
# Tests for centralized common functionality

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
	SCRIPT_DIR="${BATS_TEST_DIRNAME}"
	cd "$SCRIPT_DIR" || exit 1
	GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
	export GANDALF_PROJECT_ROOT
fi

readonly CORE_SCRIPT="$GANDALF_PROJECT_ROOT/cli/lib/core.sh"
[[ -z "$CORE_SCRIPT" ]] && echo "'CORE_SCRIPT' is not set" >&2 && exit 1
[[ ! -f "$CORE_SCRIPT" ]] && echo "'CORE_SCRIPT' file does not exist" >&2 && exit 1

setup() {
	# Source the script
	# shellcheck disable=SC1090
	source "$CORE_SCRIPT"

	unset GANDALF_PLATFORM

	return 0
}

########################################################
# Mocks
########################################################
# Mock uname for platform detection
mock_uname() {
	# Mock uname for platform detection
	# shellcheck disable=SC2329
	uname() {
		echo "${MOCKED_UNAME_RETURN_VALUE:-Linux}"
	}

	export -f uname
}

@test "CORE_SCRIPT exists and is executable" {
	[[ -f "$CORE_SCRIPT" ]]
	[[ -x "$CORE_SCRIPT" ]]
}

########################################################
# detect_platform
########################################################
@test "detect_platform::macos, mocked uname" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Darwin"

	detect_platform
	[[ "$GANDALF_PLATFORM" == "macos" ]]
}

@test "detect_platform::linux, mocked uname" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Linux"

	detect_platform
	[[ "$GANDALF_PLATFORM" == "linux" ]]
}

@test "detect_platform::unknown, mocked uname" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Unknown"

	detect_platform
	[[ "$GANDALF_PLATFORM" == "unknown" ]]
}

@test "detect_platform::exports platform variable correctly" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Linux"

	detect_platform
	[[ -n "${GANDALF_PLATFORM:-}" ]]
}

@test "detect_platform::returns correct platform string" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Linux"

	local result
	result=$(detect_platform)
	[[ "$result" == "linux" ]]
}

@test "detect_platform::returns macos for Darwin" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Darwin"

	local result
	result=$(detect_platform)
	[[ "$result" == "macos" ]]
}

########################################################
# main
########################################################
@test "main::sets up arrays and calls detect_platform" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Linux"

	main
	[[ -n "${CURSOR_DB_PATHS:-}" ]]
	[[ -n "${CLAUDE_CODE_DB_PATHS:-}" ]]
	[[ -n "${GANDALF_TOOL_DB_FILES:-}" ]]
	[[ "$GANDALF_PLATFORM" == "linux" ]]
}

@test "main::db path arrays contain expected elements" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Linux"

	main
	local found_cursor=0
	local found_claude=0

	for path in "${CURSOR_DB_PATHS[@]}"; do
		if [[ "$path" == *"Cursor"* ]]; then
			found_cursor=$((found_cursor + 1))
		fi
	done

	for path in "${CLAUDE_CODE_DB_PATHS[@]}"; do
		if [[ "$path" == *"Claude"* ]]; then
			found_claude=$((found_claude + 1))
		fi
	done

	[[ $found_cursor -gt 0 ]]
	[[ $found_claude -gt 0 ]]
}

@test "main::detect_platform integration" {
	mock_uname
	MOCKED_UNAME_RETURN_VALUE="Darwin"

	main
	[[ "$GANDALF_PLATFORM" == "macos" ]]
}
