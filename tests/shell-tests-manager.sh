#!/usr/bin/env bash
# Shell Test Manager for Gandalf MCP Server
# Handles all shell/bats test functionality

# Get the script directory and set up paths
SHELL_MANAGER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(cd "$SHELL_MANAGER_DIR/.." && pwd -P)"
TESTS_DIR="$GANDALF_ROOT/tests/shell"

# Several test suites have been temporarily disabled during migration to Python tests
# The following suites are being migrated from shell/bats to Python/pytest for better maintainability:
# - file: Complex JSON-RPC testing better suited for Python
# - context-intelligence: Scoring algorithms need direct Python testing  
# - security: Security validation requires precise exception testing
# - core: Server initialization and JSON-RPC handling better tested in Python
# See tests/MIGRATION_GAMEPLAN.md for full migration plan

declare -A SHELL_TEST_SUITES=(
    # ["core"]="Core MCP server functionality"                    # DISABLED: Migrating to Python tests
    # ["file"]="File operations"                                  # DISABLED: Migrating to Python tests
    ["project"]="Project operations"
    ["workspace-detection"]="Workspace detection strategies"
    ["conversation-export"]="Conversation export functionality"
    # ["context-intelligence"]="Context intelligence and relevance scoring"  # DISABLED: Migrating to Python tests
    # ["security"]="Security validation and edge cases"          # DISABLED: Migrating to Python tests
    ["performance"]="Performance and load testing"
    ["integration"]="Integration tests"
)

source "$TESTS_DIR/fixtures/helpers/test-helpers.sh"

shell_check_dependencies() {
    echo "Checking test dependencies..."
    if ! check_test_dependencies; then
        echo "Test dependencies not satisfied. Aborting test run." >&2
        return 1
    fi
    return 0
}

shell_is_valid_suite() {
    local suite="$1"
    [[ -n "${SHELL_TEST_SUITES[$suite]:-}" ]]
}

shell_list_suites() {
    for suite in "${!SHELL_TEST_SUITES[@]}"; do
        echo "$suite ${SHELL_TEST_SUITES[$suite]}"
    done
}

shell_get_all_suites() {
    printf '%s\n' "${!SHELL_TEST_SUITES[@]}"
}

shell_get_test_file() {
    local suite="$1"
    echo "${suite}-tests.sh"
}

shell_suite_exists() {
    local suite="$1"
    local test_file
    test_file=$(shell_get_test_file "$suite")
    [[ -f "$TESTS_DIR/$test_file" ]]
}

shell_count_suite_tests() {
    local suite="$1"
    local test_file
    test_file=$(shell_get_test_file "$suite")

    if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
        echo "0"
        return
    fi

    grep -c "^@test" "$TESTS_DIR/$test_file" 2>/dev/null || echo "0"
}

shell_count_all_tests() {
    local total=0

    for suite in "${!SHELL_TEST_SUITES[@]}"; do
        if shell_suite_exists "$suite"; then
            local count
            count=$(shell_count_suite_tests "$suite")
            total=$((total + count))
        fi
    done

    echo "$total"
}

# Run a single shell test suite
shell_run_suite() {
    local suite="$1"
    local verbose="${2:-false}"
    local timing="${3:-false}"

    if ! shell_check_dependencies; then
        return 1
    fi

    if ! shell_is_valid_suite "$suite"; then
        echo "Error: Unknown shell test suite: $suite" >&2
        return 1
    fi

    local test_file
    test_file=$(shell_get_test_file "$suite")

    if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
        echo "Warning: Test file not found: $test_file" >&2
        return 0
    fi

    echo "Running ${SHELL_TEST_SUITES[$suite]}"

    local bats_args=()
    [[ "$verbose" == "true" ]] && bats_args+=("--show-output-of-passing-tests")
    [[ "$timing" == "true" ]] && bats_args+=("--timing")

    local start_time end_time duration
    start_time=$(date +%s)

    local exit_code=0
    if ! bats "${bats_args[@]}" "$TESTS_DIR/$test_file"; then
        exit_code=1
    fi

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    if [[ "$timing" == "true" ]]; then
        echo "Suite '$suite' completed in ${duration}s"
    fi

    return $exit_code
}

shell_run_all_tests() {
    local verbose="${1:-false}"
    local timing="${2:-false}"

    if ! shell_check_dependencies; then
        return 1
    fi

    echo "Running all shell tests..."

    local start_time end_time duration
    start_time=$(date +%s)

    local total_passed=0
    local total_failed=0
    local failed_suites=()

    for suite in "${!SHELL_TEST_SUITES[@]}"; do
        if ! shell_suite_exists "$suite"; then
            echo "Warning: Skipping $suite (test file not found)"
            continue
        fi

        if shell_run_suite "$suite" "$verbose" "$timing"; then
            total_passed=$((total_passed + 1))
            echo "$suite: PASSED"
        else
            total_failed=$((total_failed + 1))
            failed_suites+=("$suite")
            echo "$suite: FAILED"
        fi
        echo ""
    done

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    # Summary
    cat <<EOF
=========================================
Shell Test Summary:
Total suites: $((total_passed + total_failed))
Passed: $total_passed
Failed: $total_failed

EOF

    if [[ "$timing" == "true" ]]; then
        echo "All shell tests completed in ${duration}s"
    fi

    if [[ $total_failed -gt 0 ]]; then
        echo "Failed suites:"
        printf "  - %s\n" "${failed_suites[@]}"
        return 1
    fi

    return 0
}

shell_show_test_counts() {
    cat <<EOF
Shell tests (bats):
EOF

    for suite in $(printf '%s\n' "${!SHELL_TEST_SUITES[@]}" | sort); do
        if shell_suite_exists "$suite"; then
            printf "%-15s %s\n" "$suite:" "$(shell_count_suite_tests "$suite")"
        else
            printf "%-15s %s\n" "$suite:" "0 (missing)"
        fi
    done

    echo -e "\nTotal shell tests: $(shell_count_all_tests)"
}
