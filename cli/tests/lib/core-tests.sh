#!/usr/bin/env bats
#
# Core Library Tests
# Tests for core.sh library functions
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/cli/lib/core.sh"
[[ ! -f "${SCRIPT}" ]] && echo "Script not found: ${SCRIPT}" >&2 && exit 1

setup() {
	# shellcheck disable=SC1090,SC1091
	source "${SCRIPT}"
}

########################################################
# Mocks
########################################################
mock_uname_linux() {
	# shellcheck disable=SC2329
	uname() {
		if [[ "$1" == "-s" ]]; then
			echo "Linux"
		fi
	}

	export -f uname
}

mock_uname_darwin() {
	# shellcheck disable=SC2329
	uname() {
		if [[ "$1" == "-s" ]]; then
			echo "Darwin"
		fi
	}

	export -f uname
}

mock_uname_unknown() {
	# shellcheck disable=SC2329
	uname() {
		if [[ "$1" == "-s" ]]; then
			echo "Unknown"
		fi
	}

	export -f uname
}

########################################################
# detect_platform
########################################################
@test "detect_platform:: detects Linux platform" {
	mock_uname_linux

	detect_platform
	[[ "$?" -eq 0 ]]
	[[ "${GANDALF_PLATFORM}" == "linux" ]]
}

@test "detect_platform:: detects macOS platform" {
	mock_uname_darwin

	detect_platform
	[[ "$?" -eq 0 ]]
	[[ "${GANDALF_PLATFORM}" == "macos" ]]
}

@test "detect_platform:: handles unknown platform" {
	mock_uname_unknown

	detect_platform || true
	[[ "${GANDALF_PLATFORM}" == "unknown" ]]
}

@test "detect_platform:: exports GANDALF_PLATFORM variable" {
	mock_uname_linux

	detect_platform
	[[ -n "${GANDALF_PLATFORM}" ]]
	[[ "${GANDALF_PLATFORM}" == "linux" ]]
}

########################################################
# Real tests (no mocks)
########################################################
@test "Real:: detect_platform works with real environment" {
	detect_platform
	[[ "$?" -eq 0 ]]
	[[ -n "${GANDALF_PLATFORM}" ]]
	[[ "${GANDALF_PLATFORM}" == "linux" || "${GANDALF_PLATFORM}" == "macos" ]]
}
