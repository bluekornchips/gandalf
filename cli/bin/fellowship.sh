#!/usr/bin/env bash

set -euo pipefail

# The Fellowship
# Shell Test Manager for Gandalf MCP Server

cd "$(dirname "${BASH_SOURCE[0]}")" || {
	echo "Unable to change to test directory" >&2
	exit 1
}

if [[ -z "${GANDALF_ROOT:-}" ]]; then
  GIT_ROOT="$(git rev-parse --show-toplevel)"
  GANDALF_ROOT="${GIT_ROOT}"
	export GANDALF_ROOT
fi

readonly TESTS_DIR="${GANDALF_ROOT}/cli/tests"
readonly DEPENDENCIES_SCRIPT="${GANDALF_ROOT}/cli/etc/dependencies.sh"
readonly BATS_ARGS=("--pretty" "--timing")

test_config=""

usage() {
	cat <<EOF
Usage: $0 [OPTIONS] [FILE]

OPTIONS:
    --list, -l      List available test files
    --help, -h      Show this help message

EXAMPLES:
    $0                                    # Run all tests
    $0 music-of-the-ainur-tests.sh        # Run only music-of-the-ainur tests

Available tests
$(list_files)
EOF
}

check_dependencies() {
	if ! source "${DEPENDENCIES_SCRIPT}"; then
		echo "Test dependencies not satisfied. Aborting test run." >&2
		return 1
	fi

	return 0
}

load_test_config() {
	test_config=$(
		jq -n \
			--arg test_dir "${TESTS_DIR}" \
			'[
        {
          "name": "mota",
          "file": "\($test_dir)/lib/music-of-the-ainur-tests.sh",
          "description": "Music of the Ainur logging library functionality"
        },
				{
          "name": "core",
          "file": "\($test_dir)/lib/core-tests.sh",
          "description": "Core library functionality"
        }
      ]'
	)

	export test_config
}

run_test() {
	local test_file="$1"
	local job_dir
	local result

	job_dir=$(mktemp -d -t gandalf_test.XXXXXX)

	result=1 # default to failure

	if bats "${BATS_ARGS[@]}" "${test_file}"; then
		result=0
	fi

	rm -rf "${job_dir}"

	return ${result}
}

list_files() {
	[[ -z "${test_config}" ]] || load_test_config

	local test_names
	local longest_name_length
	local padding
	local name
	local test_description

	test_names=$(jq -r '.[] | .name' <<<"${test_config}" | sort)
	longest_name_length=$(echo "${test_names}" | wc -L)
	padding=$((longest_name_length + 4))

	printf "%-${padding}s %s\n" "Name" "Description"
	printf "%-${padding}s %s\n" "-----" "-----------"
	for name in ${test_names}; do
		test_description=$(jq -r ".[] | select(.name == \"${name}\") | .description" <<<"${test_config}")
		printf "%-${padding}s %s\n" "${name}" "${test_description}"
	done
}

run_tests() {
	local tests=("$@")

	local tests_count
	local time_start
	local failed_file_names
	local success_file_names
	local test
	local test_file
	local time_end
	local duration
	
	tests_count=0
	time_start=$(date +%s)
	failed_file_names=()
	success_file_names=()

	cat <<EOF

========================================
The Fellowship of the Shell
========================================

EOF

	if [[ -z "${tests[*]}" ]]; then
		echo "No test names input provided, running all tests:"
		mapfile -t tests < <(jq -r '.[] | .name' <<<"${test_config}")
	fi

	for test in "${tests[@]}"; do
		test_file=$(jq -r ".[] | select(.name == \"${test}\") | .file" <<<"${test_config}")
		tests_count=$((tests_count + $(bats --count "${test_file}")))

		if ! run_test "${test_file}"; then
			failed_file_names+=("${test}")
		else
			success_file_names+=("${test}")
		fi
	done

	time_end=$(date +%s)
	duration=$((time_end - time_start))

	cat <<EOF
========================================
Results
========================================
Test Files: ${tests[*]}
Duration: ${duration}s
Total Tests Ran: ${tests_count}

EOF
	if [[ ${#success_file_names[@]} -gt 0 ]]; then
		echo "Success: ${success_file_names[*]}"
	fi
	if [[ ${#failed_file_names[@]} -gt 0 ]]; then
		echo "Failed: ${failed_file_names[*]}"
	fi

	return 0
}

main() {
	if ! check_dependencies; then
		echo "Test dependencies not satisfied. Aborting test run." >&2
		return 1
	fi

	load_test_config

	while [[ $# -gt 0 ]]; do
		case $1 in
		--help | -h)
			usage
			return 0
			;;
		--list | -l)
			list_files
			return 0
			;;
		*)
			run_tests "$@"
			return 0
			;;
		esac
	done

	run_tests "$@"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
