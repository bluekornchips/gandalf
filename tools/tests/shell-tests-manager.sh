#!/usr/bin/env bash
# Test Manager for Gandalf MCP Server

set -euo pipefail

readonly SHELL_MANAGER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${0}}")" && pwd -P)"
readonly GANDALF_ROOT="$(cd "$SHELL_MANAGER_DIR/../.." && pwd -P)"
readonly TESTS_DIR="$GANDALF_ROOT/tools/tests"



declare -A SHELL_TEST_SUITES=(
	["platform-compatibility"]="Cross-platform compatibility and path detection"
	["core"]="Core MCP server functionality"
	["cli"]="CLI functionality and server management"
	["file"]="File operations"
	["project"]="Project operations"
	["workspace-detection"]="Workspace detection strategies"
	["conversation-export"]="Conversation export functionality"
	["context-intelligence"]="Context intelligence and relevance scoring"
	["security"]="Security validation and edge cases"
	["performance"]="Performance and load testing"
	["integration"]="Integration tests"
	["install"]="MCP server installation and configuration"
	["create-rules"]="Rules creation for Cursor, Claude Code, and Windsurf"
	["uninstall"]="Uninstall script functionality and cleanup operations"
)

# Function to get test suite description
get_test_suite_description() {
	local suite="$1"
	echo "${SHELL_TEST_SUITES[$suite]}"
}

# Function to get all test suite names
get_all_test_suites() {
	echo "${!SHELL_TEST_SUITES[@]}"
}

# Function to check if test suite exists
test_suite_exists() {
	local suite="$1"
	echo "${SHELL_TEST_SUITES[$suite]}"
}

source "$GANDALF_ROOT/tools/lib/test-helpers.sh"

DEPENDENCIES_CHECKED=false

validate_positive_integer() {
	local value="$1"
	local name="$2"
	local max_value="${3:-}"

	source "$GANDALF_ROOT/tools/config/test-config.sh"

	if [[ ! "$value" =~ ^[0-9]+$ ]]; then
		echo "$name must be a positive integer" >&2
		return 1
	fi

	if [[ "$value" -le 0 ]]; then
		echo "$name must be greater than 0" >&2
		return 1
	fi

	# Apply timeout bounds validation for timeout parameters
	if [[ "$name" == *"timeout"* ]]; then
		if [[ "$value" -lt $MIN_TIMEOUT_VALUE ]]; then
			echo "$name must be at least $MIN_TIMEOUT_VALUE seconds" >&2
			return 1
		fi

		if [[ "$value" -gt $MAX_TIMEOUT_VALUE ]]; then
			echo "$name cannot exceed $MAX_TIMEOUT_VALUE seconds" >&2
			return 1
		fi
	fi

	if [[ -n "$max_value" && "$value" -gt "$max_value" ]]; then
		echo "$name cannot exceed $max_value" >&2
		return 1
	fi
}

validate_suite_name() {
	local suite="$1"

	if [[ -z "$suite" ]]; then
		echo "ERROR: Suite name cannot be empty" >&2
		return 1
	fi
}

validate_test_suite() {
	local suite="$1"

	validate_suite_name "$suite"

	if ! is_valid_test_suite "$suite"; then
		echo "ERROR: Unknown test suite: $suite" >&2
		return 1
	fi

	if ! suite_exists "$suite"; then
		echo "ERROR: Test suite file not found: $suite" >&2
		return 1
	fi
}

prepare_bats_args() {
	local verbose="$1"
	local timing="$2"

	local bats_args=("--pretty")

	printf '%s\n' "${bats_args[@]}"
}

setup_test_environment() {
	local suite="$1"

	local job_temp_dir
	job_temp_dir=$(mktemp -d -t gandalf_test.XXXXXX)
	export BATS_TMPDIR="$job_temp_dir"

	if [[ "$suite" == "uninstall" ]]; then
		export TEST_MODE=true
	fi

	echo "$job_temp_dir"
}

cleanup_test_environment() {
	local suite="$1"
	local job_temp_dir="$2"

	if [[ "$suite" == "uninstall" ]]; then
		unset TEST_MODE
	fi

	if [[ -n "$job_temp_dir" && -d "$job_temp_dir" ]]; then
		rm -rf "$job_temp_dir"
	fi
}

get_existing_suites() {
	local suites=()

	for suite in $(get_all_test_suites); do
		if suite_exists "$suite"; then
			suites+=("$suite")
		else
			echo "Warning: Skipping $suite (test file not found)" >&2
		fi
	done

	# Sort suites for consistent execution order
	printf '%s\n' "${suites[@]}" | sort
}

check_dependencies() {
	[[ "$DEPENDENCIES_CHECKED" == "true" ]] && return 0

	echo "Checking test dependencies..." >&2
	# Source centralized configuration
	source "$GANDALF_ROOT/tools/config/test-config.sh"

	if ! timeout "$TEST_TIMEOUT_DEPENDENCY_CHECK" bash -c "source '$GANDALF_ROOT/tools/lib/test-helpers.sh' && check_test_dependencies"; then
		echo "Test dependencies not satisfied. Aborting test run." >&2
		return 1
	fi

	DEPENDENCIES_CHECKED=true
	return 0
}

is_valid_test_suite() {
	local suite="$1"
	[[ -n "${suite}" ]] || return 1

	# Check if suite exists by checking if its test file exists
	# This avoids relying on the associative array which doesn't export well
	local test_file
	test_file=$(get_test_file "$suite")
	[[ -f "$TESTS_DIR/$test_file" ]]
}

list_suites() {
	local suite
	for suite in $(get_all_test_suites); do
		echo "$suite $(get_test_suite_description "$suite")"
	done
}

get_test_file() {
	local suite="$1"
	validate_suite_name "$suite"

	if [[ -f "$TESTS_DIR/unit/${suite}-tests.sh" ]]; then
		echo "unit/${suite}-tests.sh"
	elif [[ -f "$TESTS_DIR/integration/${suite}-tests.sh" ]]; then
		echo "integration/${suite}-tests.sh"
	else
		echo "unit/${suite}-tests.sh"
	fi
}

suite_exists() {
	local suite="$1"
	[[ -n "${suite}" ]] || return 1
	local test_file
	test_file=$(get_test_file "$suite")
	[[ -f "$TESTS_DIR/$test_file" ]]
}

count_suite_tests() {
	local suite="$1"
	[[ -n "${suite}" ]] || {
		echo "0"
		return
	}
	local test_file
	test_file=$(get_test_file "$suite")

	if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
		echo "0"
		return
	fi

	grep -c "^@test" "$TESTS_DIR/$test_file" 2>/dev/null || echo "0"
}

count_all_tests() {
	local total=0
	local suite

	for suite in $(get_all_test_suites); do
		if suite_exists "$suite"; then
			local count
			count=$(count_suite_tests "$suite")
			total=$((total + count))
		fi
	done

	echo "$total"
}



run_suite() {
	local suite="$1"
	local verbose="${2:-false}"
	local timing="${3:-false}"

	validate_test_suite "$suite"

	if ! check_dependencies; then
		return 1
	fi

	local test_file
	test_file=$(get_test_file "$suite")

	if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
		echo "Warning: Test file not found: $test_file" >&2
		return 0
	fi

	echo "Running $(get_test_suite_description "$suite")"

	local bats_args_array=()
	while IFS= read -r arg; do
		bats_args_array+=("$arg")
	done < <(prepare_bats_args "$verbose" "$timing")

	local start_time end_time duration
	start_time=$(date +%s)

	local exit_code=0
	local temp_dir
	temp_dir=$(setup_test_environment "$suite")

	if [[ -z "${TEST_TIMEOUT_INTEGRATION:-}" ]]; then
		source "$GANDALF_ROOT/tools/config/test-config.sh"
	fi

	if ! timeout "$TEST_TIMEOUT_INTEGRATION" bats "${bats_args_array[@]}" "$TESTS_DIR/$test_file"; then
		exit_code=1
	fi

	cleanup_test_environment "$suite" "$temp_dir"

	end_time=$(date +%s)
	duration=$((end_time - start_time))

	if [[ "$timing" == "true" ]]; then
		echo "Suite '$suite' completed in ${duration}s"
	fi

	return $exit_code
}

run_all_tests() {
	local verbose="${1:-false}"
	local timing="${2:-false}"

	if ! check_dependencies; then
		return 1
	fi

	echo "Running all tests sequentially..."

	local start_time end_time duration
	start_time=$(date +%s)

	local total_passed=0
	local total_failed=0
	local failed_suites=()

	local suites_list
	suites_list=$(get_existing_suites)

	if [[ -z "$suites_list" ]]; then
		echo "No test suites found to run" >&2
		return 1
	fi

	while IFS= read -r suite; do
		[[ -z "$suite" ]] && continue

		echo "Running suite: $suite"
		if run_suite "$suite" "$verbose" "$timing"; then
			total_passed=$((total_passed + 1))
			echo "$suite: PASSED"
		else
			total_failed=$((total_failed + 1))
			failed_suites+=("$suite")
			echo "$suite: FAILED"
		fi
		echo ""
	done <<<"$suites_list"

	end_time=$(date +%s)
	duration=$((end_time - start_time))

	cat <<EOF
=========================================
Test Summary:
Total suites: $((total_passed + total_failed))
Passed: $total_passed
Failed: $total_failed
Total execution time: ${duration}s
EOF

	if [[ $total_failed -gt 0 ]]; then
		echo "Failed suites:"
		printf "  - %s\n" "${failed_suites[@]}"
		return 1
	fi

	return 0
}

show_test_counts() {
	cat <<EOF
Tests (bats):
EOF

	local suite
	for suite in $(get_all_test_suites | sort); do
		if suite_exists "$suite"; then
			printf "%-15s %s\n" "$suite:" "$(count_suite_tests "$suite")"
		else
			printf "%-15s %s\n" "$suite:" "0 (missing)"
		fi
	done

	cat <<EOF

Total tests: $(count_all_tests)
EOF
}

main() {
	local verbose=false
	local timing=false
	local suite=""
	local action=""

	# Parse command line arguments
	while [[ $# -gt 0 ]]; do
		case $1 in
		--help | -h)
			show_help
			exit 0
			;;
		--list | -l)
			echo "Available test suites:"
			list_suites | sort | while read -r suite_name description; do
				printf "  %-20s %s\n" "$suite_name" "$description"
			done
			exit 0
			;;
		--count | -c)
			show_test_counts
			exit 0
			;;
		--verbose | -v)
			verbose=true
			shift
			;;
		--timing | -t)
			timing=true
			shift
			;;  
		run)
			action="run"
			shift
			if [[ -n "$1" && ! "$1" =~ ^-- ]]; then
				suite="$1"
				shift
			fi
			;;
		--*)
			echo "Error: Unknown option $1" >&2
			show_help
			exit 1
			;;
		*)
			if [[ -z "$action" ]]; then
				action="run"
			fi
			if [[ -z "$suite" ]]; then
				suite="$1"
			fi
			shift
			;;
		esac
	done

	# Default action is to run all tests
	if [[ -z "$action" ]]; then
		action="run"
	fi

	# Execute based on action
	case "$action" in
	run)
		if [[ -n "$suite" ]]; then
			if is_valid_test_suite "$suite"; then
				echo "Running $suite test suite..."
				if ! run_suite "$suite" "$verbose" "$timing"; then
					echo "Test suite $suite failed" >&2
					exit 1
				fi
			else
				echo "Error: Invalid test suite: $suite" >&2
				echo "Available suites: $(get_all_test_suites | tr '\n' ' ')" >&2
				exit 1
			fi
		else
			echo "Running all test suites..."
			if ! run_all_tests "$verbose" "$timing"; then
				echo "Some tests failed" >&2
				exit 1
			fi
		fi
		;;
	*)
		echo "Error: Unknown action: $action" >&2
		show_help
		exit 1
		;;
	esac
}

# Show help message
show_help() {
	cat <<EOF
Usage: $0 [OPTIONS] [ACTION] [SUITE]

ACTIONS:
    run [SUITE]     Run tests (default action)
                    If SUITE is specified, run only that suite
                    If no SUITE, run all suites

OPTIONS:
    --help, -h      Show this help message
    --list, -l      List available test suites
    --count, -c     Show test counts for each suite
    --verbose, -v   Enable verbose output
    --timing, -t    Show execution timing

EXAMPLES:
    $0                          # Run all tests
    $0 run core                 # Run only core tests
    $0 --verbose --timing       # Run with detailed output

AVAILABLE SUITES:
EOF
	list_suites | sort | while read -r suite_name description; do
		printf "    %-20s %s\n" "$suite_name" "$description"
	done
}

# Only run main if this script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
