#!/bin/bash
set -eo pipefail
set +x

# Test Suite Manager for Gandalf MCP Server - Shell Tests Only

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/fixtures/helpers/test-helpers.sh"

# Check dependencies before running tests
echo "Checking test dependencies..."
if ! check_test_dependencies; then
    echo "Test dependencies not satisfied. Aborting test run." >&2
    exit 1
fi

export PYTHONPATH="$GANDALF_ROOT:${PYTHONPATH:-}"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export GANDALF_TEST_MODE="true"

# MIGRATION NOTE: Several test suites have been temporarily disabled during migration to Python tests
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
    # ["context-intelligence"]="Context intelligence and relevance scoring"  # DISABLED: Migrating to Python tests
    # ["security"]="Security validation and edge cases"          # DISABLED: Migrating to Python tests
    ["performance"]="Performance and load testing"
    ["integration"]="Integration tests"
)

# MIGRATION NOTE: Test categories updated to exclude disabled suites
# Keeping only integration and performance tests that benefit from shell testing
declare -A TEST_CATEGORIES=(
    ["unit"]="project workspace-detection" # Reduced scope during migration
    # ["security"]="security"                                     # DISABLED: Migrating to Python tests
    ["performance"]="performance"
    ["integration"]="integration"
    ["smoke"]="workspace-detection"                      # Reduced scope during migration
    ["lembas"]="project workspace-detection integration" # Fast tests for lembas (excludes performance)
    ["shell"]="project workspace-detection performance integration"
    ["all"]="project workspace-detection performance integration"
)

usage() {
    cat <<EOF
Test Suite Manager for $MCP_SERVER_NAME MCP Server

MIGRATION NOTICE:
Several test suites are temporarily disabled during migration to Python tests.
The following suites are being migrated for better maintainability and reliability:
- core, file, context-intelligence, security

Active test suites will continue to work while Python tests are developed.
See tests/MIGRATION_GAMEPLAN.md for the complete migration plan.

USAGE:
    test-suite-manager.sh [SUITE|CATEGORY] [OPTIONS]

ACTIVE SHELL TEST SUITES (bats):
$(for suite in "${!SHELL_TEST_SUITES[@]}"; do
        printf "    %-20s %s\n" "$suite" "${SHELL_TEST_SUITES[$suite]}"
    done | sort)

CATEGORIES:
$(for category in "${!TEST_CATEGORIES[@]}"; do
        printf "    %-20s %s\n" "$category" "${TEST_CATEGORIES[$category]}"
    done | sort)

OPTIONS:
    --verbose, -v       Show detailed output (illuminate every detail)
    --count             Show test count only (count the Fellowship)
    --timing            Show execution timing (measure the journey)
    --help, -h          Show this help (seek Elrond's counsel)

EXAMPLES:
    test-suite-manager.sh                    # Run all active tests
    test-suite-manager.sh project           # Run project functionality tests
    test-suite-manager.sh shell             # Run all active shell tests
    test-suite-manager.sh smoke --verbose   # Run smoke tests with verbose output

DISABLED SUITES (migrating to Python):
    core                 # Core MCP server functionality → Python tests
    file                 # File operations → Python tests  
    context-intelligence # Context intelligence → Python tests
    security             # Security validation → Python tests

"You shall not pass...if tests are failing." - Gandalf (but these ones are temporarily closed for renovation)

EOF
}

is_valid_shell_suite() {
    local suite="$1"
    [[ -n "${SHELL_TEST_SUITES[$suite]:-}" ]]
}

is_valid_suite() {
    local suite="$1"
    is_valid_shell_suite "$suite"
}

is_valid_category() {
    local category="$1"
    [[ -n "${TEST_CATEGORIES[$category]:-}" ]]
}

# Get test file path for a shell suite
get_shell_test_file() {
    local suite="$1"
    echo "${suite}-tests.sh"
}

# Check if shell test file exists
shell_test_file_exists() {
    local suite="$1"
    local test_file
    test_file=$(get_shell_test_file "$suite")
    [[ -f "$TESTS_DIR/$test_file" ]]
}

# Count tests in a shell suite
count_shell_suite_tests() {
    local suite="$1"
    local test_file
    test_file=$(get_shell_test_file "$suite")

    if [[ ! -f "$TESTS_DIR/$test_file" ]]; then
        echo "0"
        return
    fi

    grep -c "^@test" "$TESTS_DIR/$test_file" 2>/dev/null || echo "0"
}

# Run a single shell test suite
run_shell_test_suite() {
    local suite="$1"
    local verbose="${2:-false}"
    local timing="${3:-false}"

    if ! is_valid_shell_suite "$suite"; then
        echo "Error: Unknown shell test suite: $suite" >&2
        return 1
    fi

    local test_file
    test_file=$(get_shell_test_file "$suite")

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

# Run a single test suite (shell only)
run_test_suite() {
    local suite="$1"
    local verbose="${2:-false}"
    local timing="${3:-false}"

    if is_valid_shell_suite "$suite"; then
        run_shell_test_suite "$suite" "$verbose" "$timing"
    else
        echo "Error: Unknown test suite: $suite" >&2
        return 1
    fi
}

run_test_suites() {
    local suites=("$@")
    local total_passed=0
    local total_failed=0
    local failed_suites=()

    for suite in "${suites[@]}"; do
        if ! shell_test_file_exists "$suite"; then
            echo "Warning: Skipping $suite (test file not found)"
            continue
        fi

        if run_test_suite "$suite" "$VERBOSE" "$TIMING"; then
            total_passed=$((total_passed + 1))
            echo "$suite: PASSED"
        else
            total_failed=$((total_failed + 1))
            failed_suites+=("$suite")
            echo "$suite: FAILED"
        fi
        echo ""
    done

    # Summary
    cat <<EOF
=========================================
Test Summary:
Total suites: $((total_passed + total_failed))
Passed: $total_passed
Failed: $total_failed

EOF

    if [[ $total_failed -gt 0 ]]; then
        echo "Failed suites:"
        printf "  - %s\n" "${failed_suites[@]}"
        return 1
    fi

    return 0
}

# Get suites for a category
get_category_suites() {
    local category="$1"
    echo "${TEST_CATEGORIES[$category]:-}"
}

count_all_tests() {
    local total=0

    # Count shell tests only
    for suite in "${!SHELL_TEST_SUITES[@]}"; do
        if shell_test_file_exists "$suite"; then
            local count
            count=$(count_shell_suite_tests "$suite")
            total=$((total + count))
        fi
    done

    echo "$total"
}

# Show test counts
show_test_counts() {
    local target="${1:-all}"

    if [[ "$target" == "all" ]]; then
        cat <<EOF
Total tests: $(count_all_tests)

Shell tests (bats):
EOF

        for suite in $(printf '%s\n' "${!SHELL_TEST_SUITES[@]}" | sort); do
            if shell_test_file_exists "$suite"; then
                printf "%-15s %s\n" "$suite:" "$(count_shell_suite_tests "$suite")"
            else
                printf "%-15s %s\n" "$suite:" "0 (missing)"
            fi
        done

    elif is_valid_shell_suite "$target"; then
        count_shell_suite_tests "$target"
    elif is_valid_category "$target"; then
        local suites
        suites=$(get_category_suites "$target")
        local total=0
        for suite in $suites; do
            if shell_test_file_exists "$suite"; then
                total=$((total + $(count_shell_suite_tests "$suite")))
            fi
        done
        echo "$total"
    else
        echo "Error: Unknown suite or category: $target" >&2
        exit 1
    fi
}

# Main execution
main() {
    local VERBOSE=false
    local TIMING=false
    local COUNT_ONLY=false
    local target=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
        --help | -h)
            usage
            exit 0
            ;;
        --verbose | -v)
            VERBOSE=true
            ;;
        --timing)
            TIMING=true
            ;;
        --count)
            COUNT_ONLY=true
            ;;
        --*)
            echo "Error: Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$target" ]]; then
                target="$1"
            else
                echo "Error: Multiple targets specified" >&2
                exit 1
            fi
            ;;
        esac
        shift
    done

    # Set default target
    [[ -z "$target" ]] && target="all"

    # Handle count-only mode
    if [[ "$COUNT_ONLY" == "true" ]]; then
        show_test_counts "$target"
        exit 0
    fi

    # Determine what to run
    local suites_to_run=()

    if [[ "$target" == "all" ]]; then
        # Run all available suites
        for suite in "${!SHELL_TEST_SUITES[@]}"; do
            if shell_test_file_exists "$suite"; then
                suites_to_run+=("$suite")
            fi
        done
    elif is_valid_suite "$target"; then
        suites_to_run=("$target")
    elif is_valid_category "$target"; then
        local category_suites
        category_suites=$(get_category_suites "$target")
        for suite in $category_suites; do
            if shell_test_file_exists "$suite"; then
                suites_to_run+=("$suite")
            fi
        done
    else
        cat <<EOF
Error: Unknown suite or category: $target

Valid shell suites: ${!SHELL_TEST_SUITES[*]}
Valid categories: ${!TEST_CATEGORIES[*]}
EOF
        exit 1
    fi

    if [[ ${#suites_to_run[@]} -eq 0 ]]; then
        echo "Warning: No test suites found to run" >&2
        exit 0
    fi

    # Run the tests
    cat <<EOF
$MCP_SERVER_NAME Test Suite
=========================================
EOF

    if [[ ${#suites_to_run[@]} -eq 1 ]]; then
        # Single suite
        run_test_suite "${suites_to_run[0]}" "$VERBOSE" "$TIMING"
    else
        # Multiple suites
        run_test_suites "${suites_to_run[@]}"
    fi
}

# Execute main if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
