#!/usr/bin/env bash
#
# Dependencies Checker
# Validates that required shell dependencies are installed
# Provides helpful installation links when dependencies are missing
#
set -euo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Dependencies Checker
Validates that required shell dependencies are installed
Provides helpful installation links when dependencies are missing

OPTIONS:
  -h, --help  Show this help message

EOF
}

# Check if BATS testing framework is installed
#
# Inputs:
# - None
#
# Side Effects:
# - None
check_bats() {
	local link="https://github.com/bats-core/bats-core"
	if which bats >/dev/null 2>&1; then
		return 0
	fi
	echo "BATS not installed, go to ${link} to install" >&2
	return 1
}

# Check if jq JSON processor is installed
#
# Inputs:
# - None
#
# Side Effects:
# - None
check_jq() {
	local link="https://github.com/jqlang/jq"
	if which jq >/dev/null 2>&1; then
		return 0
	fi
	echo "JQ not installed, go to ${link} to install" >&2
	return 1
}

# Main function that checks all dependencies
#
# Inputs:
# - None
#
# Side Effects:
# - None
main() {
	local bats_result
	local jq_result

	check_bats
	bats_result=$?
	check_jq
	jq_result=$?

	if [[ "${bats_result}" -eq 0 && "${jq_result}" -eq 0 ]]; then
		return 0
	fi
	return 1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			usage
			exit 0
			;;
		*)
			echo "Unknown option '$1'" >&2
			echo "Use '$(basename "$0") --help' for usage information" >&2
			exit 1
			;;
		esac
	done

	main "$@"
fi
