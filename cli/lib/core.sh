#!/usr/bin/env bash
#
# Gandalf Core Library
# Centralized common functionality for all shell scripts and the python server
#
set -eo pipefail

# Detects the current platform and sets GANDALF_PLATFORM
#
# Inputs:
# - None
#
# Side Effects:
# - GANDALF_PLATFORM, sets the global platform variable
detect_platform() {
	if ! command -v uname >/dev/null 2>&1; then
		echo "detect_platform:: uname command not found" >&2
		return 1
	fi

	local uname_output
	uname_output="$(uname -s)"

	case "$uname_output" in
	Darwin*)
		GANDALF_PLATFORM="macos"
		;;
	Linux*)
		GANDALF_PLATFORM="linux"
		;;
	*)
		GANDALF_PLATFORM="unknown"
		return 1
		;;
	esac

	echo "detect_platform:: Detected platform: $GANDALF_PLATFORM"

	export GANDALF_PLATFORM

	return 0
}
