#!/usr/bin/env bash
set -euo pipefail
set +x

# Main Test Suite Coordinator for Gandalf MCP Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"

cleanup_handler() {
	echo -e "\nTest suite interrupted" >&2
	exit 130
}
trap cleanup_handler INT TERM

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

usage() {
	cat <<EOF
Test Suite for $MCP_SERVER_NAME

OPTIONS:
    --shell             Run shell tests only
    --python            Run Python tests only
    --suites SUITES     Run specific shell suites (comma-separated)
    --help, -h          Show this help

EOF
}

python_tests_exist() {
	[[ -d "$GANDALF_ROOT/server/tests" ]]
}

run_python_tests() {
	if ! python_tests_exist; then
		echo "Warning: Python tests not found at server/tests/" >&2
		return 0
	fi

	echo "Running Python tests..."
	cd "$GANDALF_ROOT/server"
	python3 -m pytest tests/ --tb=short
}

main() {
	local run_shell=true
	local run_python=true
	local suite_list=""

	while [[ $# -gt 0 ]]; do
		case $1 in
		--shell)
			run_python=false
			shift
			;;
		--python)
			run_shell=false
			shift
			;;
		--suites)
			suite_list="$2"
			shift 2
			;;
		--help | -h)
			usage
			exit 0
			;;
		*)
			echo "Error: Unknown option $1" >&2
			usage
			exit 1
			;;
		esac
	done

	cat <<EOF
$MCP_SERVER_NAME Test Suite
=========================================
EOF

	local start_time end_time duration
	start_time=$(date +%s)
	local total_passed=0 total_failed=0
	local failed_suites=()

	if [[ "$run_shell" == "true" ]]; then
		echo "Running shell tests..."
		if [[ -n "$suite_list" ]]; then
			IFS=',' read -ra suites <<<"$suite_list"
			for suite in "${suites[@]}"; do
				if bash "$GANDALF_ROOT/tools/tests/shell-tests-manager.sh" run "$suite"; then
					total_passed=$((total_passed + 1))
				else
					total_failed=$((total_failed + 1))
					failed_suites+=("$suite")
				fi
			done
		else
			if bash "$GANDALF_ROOT/tools/tests/shell-tests-manager.sh"; then
				total_passed=$((total_passed + 1))
			else
				total_failed=$((total_failed + 1))
				failed_suites+=("shell")
			fi
		fi
	fi

	if [[ "$run_python" == "true" ]]; then
		if run_python_tests; then
			total_passed=$((total_passed + 1))
		else
			total_failed=$((total_failed + 1))
			failed_suites+=("python")
		fi
	fi

	end_time=$(date +%s)
	duration=$((end_time - start_time))

	cat <<EOF
=========================================
Test Summary:
Total test suites: $((total_passed + total_failed))
Passed: $total_passed
Failed: $total_failed
Total execution time: ${duration}s
EOF

	if [[ $total_failed -gt 0 ]]; then
		echo "Failed suites:"
		printf "  - %s\n" "${failed_suites[@]}"
		exit 1
	fi

	echo "All tests passed!"
	exit 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
