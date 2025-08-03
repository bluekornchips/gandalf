#!/usr/bin/env bats

# Gandalf Core Library Tests
# Tests for centralized common functionality

if [[ -z "${GANDALF_ROOT:-}" ]]; then
  GIT_ROOT="$(git rev-parse --show-toplevel)"
  GANDALF_ROOT="${GIT_ROOT}"

	if [[ -z "${GANDALF_HOME:-}" ]]; then
		GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"
	fi
fi

readonly CORE_SCRIPT="$GANDALF_ROOT/cli/lib/core.sh"
[[ -z "$CORE_SCRIPT" ]] && echo "'CORE_SCRIPT' is not set" && exit 1
[[ ! -f "$CORE_SCRIPT" ]] && echo "'CORE_SCRIPT' file does not exist" && exit 1

setup() {
	unset GANDALF_PLATFORM
	unset GANDALF_DB_PATHS
	# shellcheck disable=SC1090,SC1091
	source "$CORE_SCRIPT"
}

@test "'CORE_SCRIPT' exists and is executable" {
	[[ -f "$CORE_SCRIPT" ]]
	[[ -x "$CORE_SCRIPT" ]]
}

@test "detect_platform::macos, mocked uname" {
	export MOCKED_UNAME_RETURN_VALUE="Darwin"
	uname() { echo "$MOCKED_UNAME_RETURN_VALUE"; }
	
	detect_platform
	[[ "$GANDALF_PLATFORM" == "macos" ]]
}

@test "detect_platform::linux, mocked uname" {
	export MOCKED_UNAME_RETURN_VALUE="Linux"
	uname() { echo "$MOCKED_UNAME_RETURN_VALUE"; }
	
	detect_platform
	[[ "$GANDALF_PLATFORM" == "linux" ]]
}

@test "detect_platform::unknown, mocked uname" {
	export MOCKED_UNAME_RETURN_VALUE="Unknown"
	uname() { echo "$MOCKED_UNAME_RETURN_VALUE"; }
	
	detect_platform
	[[ "$GANDALF_PLATFORM" == "unknown" ]]
}

@test "detect_platform::real, check db paths" {
	detect_platform
	[[ "${#GANDALF_DB_PATHS[@]}" -eq 5 ]]
}