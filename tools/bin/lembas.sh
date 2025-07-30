#!/usr/bin/env bash
# Lembas bread could not fulfill the hunger of a hobbit, but it could fulfill the hunger of a developer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"

export GANDALF_HOME
readonly SCRIPT_DIR
readonly GANDALF_ROOT

cleanup_handler() {
	echo -e "\nLembas interrupted. Cleaning up..." >&2
	exit 130
}
trap cleanup_handler INT TERM

readonly DEFAULT_TIMEOUT=300
readonly DEFAULT_WAIT_TIME=2

print_header() {
	local message="$1"
	cat <<EOF

==========================================
$message
==========================================
EOF
}

show_help() {
	cat <<EOF
Lembas - Complete Server Restart and Comprehensive Test Suite

Usage: $0 [OPTIONS]

Options:
    --fast              fast tests only (core + essential, ~2min)
    --core              core tests only (default)
    --all               all tests (MCP + shell + python, ~10min)
    --shell-only        shell tests only
    --python-only       python tests only
    --validate-mcp      validate MCP installation in temporary directory
    --timeout SECONDS   Set test timeout (default: $DEFAULT_TIMEOUT)
    --verbose           Enable verbose output
    --help, -h          Show this help message

Examples:
    $0                    # Run core tests
    $0 --all              # Run all tests
    $0 --validate-mcp     # Validate MCP installation in temporary directory

The name 'Lembas' comes from the Elvish waybread that sustained travelers
on long journeys, just as this test suite sustains the development process.

EOF
}

check_test_environment() {
	echo "Checking test environment..."

	local -a required_dirs=("server" "tools/tests")
	local -a required_files=("server/src/main.py" "tools/tests/shell-tests-manager.sh")

	for dir in "${required_dirs[@]}"; do
		if [[ ! -d "$GANDALF_ROOT/$dir" ]]; then
			echo "Required directory missing: $dir" >&2
			return 1
		fi
	done

	for file in "${required_files[@]}"; do
		if [[ ! -f "$GANDALF_ROOT/$file" ]]; then
			echo "Required file missing: $file" >&2
			return 1
		fi
	done

	if ! command -v python3 &>/dev/null; then
		echo "Python 3 not found" >&2
		return 1
	fi

	local python_version
	python_version=$(python --version 2>/dev/null)
	echo "Python $python_version found"

	if ! command -v bats &>/dev/null; then
		echo "BATS not found (needed for shell tests)" >&2
		return 1
	fi

	echo "Test environment verified"
	return 0
}

perform_server_restart() {
	print_header "Restarting Server Completely"

	echo "Running 'gandalf install -f --skip-test' to completely restart server..."

	if ! "$GANDALF_ROOT/gandalf" install -f --skip-test; then
		echo "Server restart failed" >&2
		return 1
	fi

	echo "Server restart completed successfully"

	sleep "$DEFAULT_WAIT_TIME"

	return 0
}

run_shell_tests() {
	local verbose="${1:-false}"
	local timeout="${2:-$DEFAULT_TIMEOUT}"

	if ! perform_server_restart; then
		return 1
	fi

	print_header "Running Shell Tests"

	local test_args=()

	# Ensure we're in the correct working directory
	cd "$GANDALF_ROOT"
	
	if timeout "$timeout" bash "$GANDALF_ROOT/tools/bin/test-runner.sh" --shell ${test_args[@]+"${test_args[@]}"}; then
		echo "Shell tests completed successfully"
		return 0
	else
		echo "Shell tests failed" >&2
		return 1
	fi
}

run_python_tests() {
	local verbose="${1:-false}"
	local timeout="${2:-$DEFAULT_TIMEOUT}"

	if ! perform_server_restart; then
		return 1
	fi

	print_header "Running Python Tests"

	local test_args=()

	# Ensure we're in the correct working directory
	cd "$GANDALF_ROOT"
	
	if timeout "$timeout" bash "$GANDALF_ROOT/tools/bin/test-runner.sh" --python ${test_args[@]+"${test_args[@]}"}; then
		echo "Python tests completed successfully"
		return 0
	else
		echo "Python tests failed" >&2
		return 1
	fi
}

run_fast_tests() {
	local verbose="${1:-false}"
	local timeout="${2:-120}"

	if ! perform_server_restart; then
		return 1
	fi

	print_header "Running Fast Tests (Core + Essential)"

	# Run only essential test suites for quick validation
	local test_args=("--suites" "core,file,project")

	# Ensure we're in the correct working directory
	cd "$GANDALF_ROOT"
	
	if timeout "$timeout" bash "$GANDALF_ROOT/tools/bin/test-runner.sh" --shell ${test_args[@]+"${test_args[@]}"}; then
		echo "Fast tests completed successfully"
		return 0
	else
		echo "Fast tests failed" >&2
		return 1
	fi
}

run_core_tests() {
	local verbose="${1:-false}"
	local timeout="${2:-$DEFAULT_TIMEOUT}"

	if ! perform_server_restart; then
		return 1
	fi

	print_header "Running Core Tests"

	local test_args=()

	# Ensure we're in the correct working directory
	cd "$GANDALF_ROOT"
	
	if timeout "$timeout" bash "$GANDALF_ROOT/tools/bin/test-runner.sh" --shell ${test_args[@]+"${test_args[@]}"}; then
		echo "Core tests completed successfully"
		return 0
	else
		echo "Core tests failed" >&2
		return 1
	fi
}

run_all_tests() {
	local verbose="${1:-false}"
	local timeout="${2:-$DEFAULT_TIMEOUT}"

	if ! perform_server_restart; then
		return 1
	fi

	print_header "Running All Tests (MCP + Shell + Python)"

	echo "Step 1: MCP validation..."
	if ! validate_mcp_installation; then
		echo "MCP validation failed, stopping all tests" >&2
		return 1
	fi
	echo "MCP validation passed"

	echo "Step 2: Shell and Python tests..."
	local test_args=()

	# Ensure we're in the correct working directory
	cd "$GANDALF_ROOT"
	
	if timeout "$timeout" bash "$GANDALF_ROOT/tools/bin/test-runner.sh" ${test_args[@]+"${test_args[@]}"}; then
		echo "All tests completed successfully"
		return 0
	else
		echo "Shell/Python tests failed" >&2
		return 1
	fi
}

validate_mcp_installation() {
	echo "Creating temporary directory for MCP validation."
	local temp_dir
	temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/gandalf-mcp-validation-XXXXXX")

	echo "Starting temporary MCP server in: $temp_dir"
	cd "$temp_dir"

	echo "Testing minimum required method: tools/list"
	local request='{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
	echo "Request: $request"
	local response

	if response=$(echo "$request" | "$GANDALF_ROOT/gandalf" run --project-root "$temp_dir" 2>&1); then
		echo "Response:"
		if command -v jq >/dev/null 2>&1; then
			echo "$response" | jq . 2>/dev/null || echo "$response"
		else
			echo "$response"
		fi
		echo "tools/list working"
		echo "---"
	else
		echo "Response: $response"
		echo "tools/list failed" >&2
		return 1
	fi

	local test_tools=(
		"get_project_info"
		"list_project_files"
		"recall_conversations"
		"export_individual_conversations"
	)

	for tool in "${test_tools[@]}"; do
		echo "Testing tool: $tool"
		local request="{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":{}}}"

		echo "Request: $request"
		local response
		if response=$(echo "$request" | "$GANDALF_ROOT/gandalf" run --project-root "$temp_dir" 2>&1); then
			echo "Response:"
			if command -v jq >/dev/null 2>&1; then
				echo "$response" | jq . 2>/dev/null || echo "$response"
			else
				echo "$response"
			fi
			echo "$tool working"
			echo "---"
		else
			echo "Response: $response"
			echo "$tool failed" >&2
			return 1
		fi
	done

	echo "MCP validation completed successfully"
	return 0
}

run_mcp_validation_tests() {
	print_header "Running MCP Installation Validation"

	local start_time end_time duration
	start_time=$(date +%s)

	if validate_mcp_installation; then
		end_time=$(date +%s)
		duration=$((end_time - start_time))
		echo "MCP validation completed successfully in ${duration}s"
		return 0
	else
		echo "MCP validation failed" >&2
		return 1
	fi
}

parse_arguments() {
	local test_type="core"
	local verbose="false"
	local timeout="$DEFAULT_TIMEOUT"

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--core)
			test_type="core"
			shift
			;;
		--fast)
			test_type="fast"
			shift
			;;
		--all)
			test_type="all"
			shift
			;;
		--shell-only)
			test_type="shell"
			shift
			;;
		--python-only)
			test_type="python"
			shift
			;;
		--validate-mcp)
			test_type="mcp"
			shift
			;;
		--verbose)
			verbose="true"
			shift
			;;
		--timeout)
			timeout="$2"
			if ! [[ "$timeout" =~ ^[0-9]+$ ]]; then
				echo "Timeout must be a positive integer" >&2
				return 1
			fi
			shift 2
			;;
		--help | -h)
			show_help
			exit 0
			;;
		*)
			echo "Unknown option: $1" >&2
			show_help
			return 1
			;;
		esac
	done

	export LEMBAS_TEST_TYPE="$test_type"
	export LEMBAS_VERBOSE="$verbose"
	export LEMBAS_TIMEOUT="$timeout"
	return 0
}

main() {
	if ! parse_arguments "$@"; then
		exit 1
	fi

	print_header "Lembas - Comprehensive Test Suite"
	cat <<EOF
Test type: $LEMBAS_TEST_TYPE
Verbose: $LEMBAS_VERBOSE
Timeout: ${LEMBAS_TIMEOUT}s
EOF

	if ! check_test_environment; then
		exit 1
	fi

	local start_time end_time duration
	start_time=$(date +%s)

	case "$LEMBAS_TEST_TYPE" in
	fast)
		run_fast_tests "$LEMBAS_VERBOSE" "$LEMBAS_TIMEOUT"
		;;
	core)
		run_core_tests "$LEMBAS_VERBOSE" "$LEMBAS_TIMEOUT"
		;;
	all)
		run_all_tests "$LEMBAS_VERBOSE" "$LEMBAS_TIMEOUT"
		;;
	shell)
		run_shell_tests "$LEMBAS_VERBOSE" "$LEMBAS_TIMEOUT"
		;;
	python)
		run_python_tests "$LEMBAS_VERBOSE" "$LEMBAS_TIMEOUT"
		;;
	mcp)
		run_mcp_validation_tests
		;;
	*)
		echo "Unknown test type: $LEMBAS_TEST_TYPE" >&2
		exit 1
		;;
	esac

	local exit_code=$?
	end_time=$(date +%s)
	duration=$((end_time - start_time))

	if [[ $exit_code -eq 0 ]]; then
		print_header "Lembas Complete - Journey Successful!"
		echo "Total time: ${duration}s"
	else
		print_header "Lembas Failed - Journey Interrupted"
		echo "Tests failed after ${duration}s" >&2
	fi

	exit $exit_code
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
