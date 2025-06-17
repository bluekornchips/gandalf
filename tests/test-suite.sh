#!/bin/bash
set -eo pipefail

# Manages all test execution and reporting

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"
TESTS_DIR="$GANDALF_ROOT/tests"

usage() {
    cat <<'EOF'
Test Runner for Gandalf MCP Server

USAGE:
    test-suite.sh [TEST_SUITE] [BATS_OPTIONS]

TEST SUITES:
    gandalf                     Core functionality tests
    conversations               Conversation management tests
    git                         Git operations tests
    logging                     MCP logging tests
    integration                 Integration tests
    context-intelligence        Context Intelligence tests
    load-generic-content        Load Generic Content tests
    async-storage               Async Storage tests
    dynamic-project             Dynamic Project tests
    
    (no arguments)  Run all test suites

BATS OPTIONS:
    --show-output-of-passing-tests  Show detailed test output
    --count         Show only test count
    --tap           Output in TAP format
    --timing        Show test execution timing
    --help          Show bats help

EXAMPLES:
    test-suite.sh                           # Run all tests
    test-suite.sh gandalf                   # Run core tests only
    test-suite.sh conversations --show-output-of-passing-tests   # Run conv tests with details
    test-suite.sh --count                   # Count all tests
    test-suite.sh git --tap                 # Git tests in TAP format

EOF
}

VALID_SUITES=("gandalf" "conversations" "git" "logging" "integration" "context-intelligence" "load-generic-content" "async-storage" "dynamic-project")
# Note: refresh functionality has been removed

is_valid_suite() {
    local suite_name="$1"
    for valid_suite in "${VALID_SUITES[@]}"; do
        if [[ "$suite_name" == "$valid_suite" ]]; then
            return 0
        fi
    done
    return 1
}

get_test_file() {
    local suite_name="$1"
    case "$suite_name" in
    "gandalf") echo "gandalf-tests.sh" ;;
    "conversations") echo "conversations-tests.sh" ;;
    "git") echo "git-tests.sh" ;;
    "logging") echo "logging-tests.sh" ;;
    "integration") echo "integration-tests.sh" ;;
    "context-intelligence") echo "context-intelligence-tests.sh" ;;
    "load-generic-content") echo "load-generic-content-tests.sh" ;;
    "async-storage") echo "async-storage-tests.sh" ;;
    "dynamic-project") echo "dynamic-project-tests.sh" ;;
    *) echo "" ;;
    esac
}

get_test_description() {
    local suite_name="$1"
    case "$suite_name" in
    "gandalf") echo "Core functionality tests" ;;
    "conversations") echo "Conversation management tests" ;;
    "git") echo "Git operations tests" ;;
    "logging") echo "MCP logging tests" ;;
    "integration") echo "Integration tests" ;;
    "context-intelligence") echo "Context Intelligence tests" ;;
    "load-generic-content") echo "Load Generic Content tests" ;;
    "async-storage") echo "Async Storage tests" ;;
    "dynamic-project") echo "Dynamic Project tests" ;;
    *) echo "" ;;
    esac
}

parse_bats_output() {
    local output="$1"
    local exit_code="$2"

    local test_count=0
    local passed_count=0
    local failed_count=0
    local test_status="unknown"

    if [[ $exit_code -eq 0 ]]; then
        # 'BASH_REMATCH' is a special variable that contains the matches of the last regex as an array
        if [[ "$output" =~ ([0-9]+)\ tests,\ ([0-9]+)\ failures ]]; then
            test_count="${BASH_REMATCH[1]}"
            failed_count="${BASH_REMATCH[2]}"
            passed_count=$((test_count - failed_count))
        else
            # Fallback parsing using ok/not ok lines
            test_count=$(echo "$output" | grep -c "^ok\|^not ok" || true)
            failed_count=$(echo "$output" | grep -c "^not ok" || true)
            passed_count=$((test_count - failed_count))
        fi

        test_status="partial"
        [[ $failed_count -eq 0 ]] && test_status="passed"
    else
        # Some test failures, but did still run the script
        if [[ "$output" =~ ([0-9]+)\.\.([0-9]+) ]] || echo "$output" | grep -q "^ok\|^not ok"; then
            test_count=$(echo "$output" | grep -c "^ok\|^not ok" || true)
            failed_count=$(echo "$output" | grep -c "^not ok" || true)
            passed_count=$((test_count - failed_count))

            test_status="partial"
            [[ $failed_count -eq 0 ]] && test_status="passed"
        else
            # A complete failure to run the script
            test_status="failed_to_run"
            test_count=0
            passed_count=0
            failed_count=1
        fi
    fi

    echo "$test_count $passed_count $failed_count $test_status"
}

format_test_result() {
    local suite_name="$1"
    local test_count="$2"
    local passed_count="$3"
    local failed_count="$4"
    local status="$5"

    case "$status" in
    "passed")
        echo "✓ $suite_name: $test_count/$test_count passed"
        ;;
    "partial")
        echo "✗ $suite_name: $passed_count/$test_count passed ($failed_count failed)"
        ;;
    "failed_to_run")
        echo "✗ $suite_name: FAILED TO RUN"
        ;;
    *)
        echo "? $suite_name: UNKNOWN STATUS"
        ;;
    esac
}

run_test_suite() {
    local suite_name="$1"
    shift
    local bats_options=("$@")

    local test_file=$(get_test_file "$suite_name")
    if [[ -z "$test_file" ]]; then
        echo "Error: Unknown test suite: $suite_name"
        exit 1
    fi

    if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
        echo "Error: Test file not found: $test_file"
        exit 1
    fi

    echo "Running $(get_test_description "$suite_name")..."
    cd "$GANDALF_ROOT"

    local output exit_code
    output=$(timeout 60 bats "${bats_options[@]}" "$TESTS_DIR/$test_file" 2>&1)
    exit_code=$?

    local result_data=($(parse_bats_output "$output" "$exit_code"))
    local test_count="${result_data[0]}"
    local passed_count="${result_data[1]}"
    local failed_count="${result_data[2]}"
    local status="${result_data[3]}"

    format_test_result "$suite_name" "$test_count" "$passed_count" "$failed_count" "$status"

    # Show detailed failure output if there were any failures
    if [[ "$status" != "passed" ]]; then
        cat <<EOF
DETAILED FAILURE INFORMATION:
=============================
$output
EOF
    fi

    [[ "$status" == "passed" ]] && return 0
    return 1
}

run_all_tests() {
    local bats_options=("$@")
    local total_passed=0
    local total_failed=0
    local suite_results=()
    local failed_outputs=()

    cat <<EOF
Running Gandalf MCP Server Test Suite
=====================================

EOF

    for suite in "${VALID_SUITES[@]}"; do
        echo "→ Running $(get_test_description "$suite")..."

        local test_file=$(get_test_file "$suite")
        cd "$GANDALF_ROOT"

        local output exit_code
        output=$(timeout 60 bats "${bats_options[@]}" "$TESTS_DIR/$test_file" 2>&1)
        exit_code=$?

        local result_data=($(parse_bats_output "$output" "$exit_code"))
        local test_count="${result_data[0]}"
        local passed_count="${result_data[1]}"
        local failed_count="${result_data[2]}"
        local status="${result_data[3]}"

        total_passed=$((total_passed + passed_count))
        total_failed=$((total_failed + failed_count))

        suite_results+=("$(format_test_result "$suite" "$test_count" "$passed_count" "$failed_count" "$status")")

        if [[ "$status" != "passed" ]]; then
            failed_outputs+=("=== $suite Test Failures ===")
            failed_outputs+=("$output")
            failed_outputs+=("")
        fi

        echo ""
    done

    # Summary
    cat <<EOF
Test Suite Summary
==================
EOF
    printf '%s\n' "${suite_results[@]}"
    echo ""
    echo "Total: $((total_passed + total_failed)) tests, $total_passed passed, $total_failed failed"

    if [[ $total_failed -gt 0 ]]; then
        cat <<EOF

DETAILED FAILURE INFORMATION:
============================="
${failed_outputs[@]}
EOF
        exit 1
    fi
}

count_suite_tests() {
    local suite_name="$1"

    local test_file=$(get_test_file "$suite_name")
    if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
        echo "Error: Test file not found: $test_file"
        exit 1
    fi

    pushd "$GANDALF_ROOT" >/dev/null
    bats --count "$TESTS_DIR/$test_file"
    popd >/dev/null
}

count_all_tests() {
    local total=0

    for suite in "${VALID_SUITES[@]}"; do
        local test_file=$(get_test_file "$suite")
        if [[ -f "$TESTS_DIR/$test_file" ]]; then
            cd "$GANDALF_ROOT"
            local count=$(bats --count "$TESTS_DIR/$test_file" 2>/dev/null || echo "0")
            if [[ "$count" =~ ^[0-9]+$ ]]; then
                total=$((total + count))
            fi
        fi
    done

    echo "$total"
}

# Main execution
main() {
    # Check for help first
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        usage
        exit 0
    fi

    # Check bats availability
    if ! command -v bats >/dev/null 2>&1; then
        cat <<EOF
Error: bats is required for testing but not found.

Install bats:
    macOS: brew install bats-core
    Ubuntu/Debian: apt-get install bats
    Other: https://github.com/bats-core/bats-core#installation
EOF
        exit 1
    fi

    # Handle count option
    if [[ "$1" == "--count" ]]; then
        if [[ -n "$2" ]]; then
            # Count specific suite
            count_suite_tests "$2"
        else
            # Count all tests
            count_all_tests
        fi
        exit 0
    fi

    # Parse arguments
    local suite_name=""
    local bats_options=()

    if [[ -n "$1" ]]; then
        if is_valid_suite "$1"; then
            suite_name="$1"
            shift
        elif [[ "$1" != --* ]]; then
            cat <<EOF
Error: Unknown test suite: '$1'

Valid test suites are: ${VALID_SUITES[*]}

Use 'test-suite.sh --help' for more information.
EOF
            exit 1
        fi
    fi

    # Remaining arguments are bats options
    bats_options=("$@")

    # Handle count for specific suite
    for arg in "${bats_options[@]}"; do
        if [[ "$arg" == "--count" ]]; then
            if [[ -n "$suite_name" ]]; then
                count_suite_tests "$suite_name"
            else
                count_all_tests
            fi
            exit 0
        fi
    done

    # Run tests
    if [[ -n "$suite_name" ]]; then
        # Run specific test suite
        run_test_suite "$suite_name" "${bats_options[@]}"
    else
        # Run all test suites
        run_all_tests "${bats_options[@]}"
    fi
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
