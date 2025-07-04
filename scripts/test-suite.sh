#!/usr/bin/env bash
set -euo pipefail
set +x

# Main Test Suite Coordinator for Gandalf MCP Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(dirname "$SCRIPT_DIR")"

export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export GANDALF_TEST_MODE="true"

SHELL_MANAGER="$SCRIPT_DIR/tests/shell-tests-manager.sh"

[[ ! -f "$SHELL_MANAGER" ]] && echo "Error: Shell test manager not found: $SHELL_MANAGER" >&2 && exit 1

source "$SHELL_MANAGER"

declare -A TEST_CATEGORIES=(
    ["all"]="project workspace-detection conversation-export performance integration core file context-intelligence security platform-compatibility" # Both shell and Python tests by default
    ["core"]="project workspace-detection conversation-export core file context-intelligence platform-compatibility"                                 # Quick tests - basic functionality
    ["e2e"]="integration conversation-export performance install uninstall"                                                                          # End-to-end tests: integration workflows and performance
    ["smoke"]="workspace-detection conversation-export core platform-compatibility"
    ["security"]="security python-security"
    ["performance"]="performance"
    ["shell"]="project workspace-detection conversation-export integration core file context-intelligence platform-compatibility" # Shell tests only (no Python)
    ["python"]="python-security"                                                                                                  # Python tests only (no shell)
)

usage() {
    cat <<EOF
Test Suite Coordinator for $MCP_SERVER_NAME MCP Server

USAGE:
    test-suite.sh [SUITE|CATEGORY] [OPTIONS]

ACTIVE SHELL TEST SUITES (bats):
$(shell_list_suites | while read -r suite desc; do
        printf "    %-20s %s\n" "$suite" "$desc"
    done | sort)

PYTHON TESTS:
    python              All Python tests (pytest)

CATEGORIES:
$(for category in "${!TEST_CATEGORIES[@]}"; do
        printf "    %-20s %s\n" "$category" "${TEST_CATEGORIES[$category]}"
    done | sort)

OPTIONS:
    --verbose, -v       Show detailed output (illuminate every detail)
    --count             Show test count only (count the Fellowship)
    --timing            Show execution timing (measure the journey)
    --shell             Run shell tests only
    --python            Run Python tests only
    --help, -h          Show this help (seek Elrond's counsel)

EXAMPLES:
    test-suite.sh                   # Run all tests (shell + python)
    test-suite.sh --shell           # Run shell tests only
    test-suite.sh --python          # Run Python tests only
    test-suite.sh project           # Run project functionality tests (shell)
    test-suite.sh smoke --verbose   # Run smoke tests with verbose output

"You shall not pass...if tests are failing." - Gandalf

EOF
}

python_tests_exist() {
    [[ -d "$GANDALF_ROOT/server/tests" ]]
}

run_python_tests() {
    local verbose="${1:-false}"
    local timing="${2:-false}"

    if ! python_tests_exist; then
        echo "Warning: Python tests not found at server/tests/" >&2
        return 0
    fi

    echo "Running Python tests with pytest..."

    local start_time end_time duration
    start_time=$(date +%s)

    cd "$GANDALF_ROOT/server"

    if [[ -f "../.venv/bin/activate" ]]; then
        echo "Activating virtual environment..."
        source ../.venv/bin/activate
    fi

    local pytest_args=()
    [[ "$verbose" == "true" ]] && pytest_args+=("-v")
    [[ "$timing" == "true" ]] && pytest_args+=("--durations=10")

    pytest_args+=("tests/")

    local exit_code=0
    if ! PYTHONPATH=src python3 -m pytest "${pytest_args[@]}"; then
        exit_code=1
    fi

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    if [[ "$timing" == "true" ]]; then
        echo "Python tests completed in ${duration}s"
    fi

    return $exit_code
}

count_python_tests() {
    if ! python_tests_exist; then
        echo "0"
        return
    fi

    cd "$GANDALF_ROOT/server"

    if [[ -f "../.venv/bin/activate" ]]; then
        source ../.venv/bin/activate >/dev/null 2>&1
    fi

    local count
    count=$(PYTHONPATH=src python3 -m pytest tests/ --collect-only -q 2>/dev/null | grep -c "::" 2>/dev/null || echo "0")
    echo "$count"
}

is_valid_suite() {
    local suite="$1"
    shell_is_valid_suite "$suite" || [[ "$suite" == "python" ]]
}

is_valid_category() {
    local category="$1"
    [[ -n "${TEST_CATEGORIES[$category]:-}" ]]
}

get_category_suites() {
    local category="$1"
    echo "${TEST_CATEGORIES[$category]:-}"
}

run_test_suite() {
    local suite="$1"
    local verbose="${2:-false}"
    local timing="${3:-false}"

    if [[ "$suite" == "python" ]]; then
        run_python_tests "$verbose" "$timing"
    elif shell_is_valid_suite "$suite"; then
        shell_run_suite "$suite" "$verbose" "$timing"
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
        local suite_exists=false

        if [[ "$suite" == "python" ]] && python_tests_exist; then
            suite_exists=true
        elif shell_is_valid_suite "$suite" && shell_suite_exists "$suite"; then
            suite_exists=true
        fi

        if ! $suite_exists; then
            echo "Warning: Skipping $suite (test suite not found or not configured)"
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

    cat <<EOF

Test Summary
============
Total suites: $((total_passed + total_failed))
Passed: $total_passed
Failed: $total_failed

EOF

    if [[ $total_failed -gt 0 ]]; then
        cat <<EOF
Failed Suites
-------------
EOF
        for suite in "${failed_suites[@]}"; do
            echo "  $suite"
        done
        echo ""
        return 1
    fi

    echo "All tests passed"
    return 0
}

show_test_counts() {
    local target="${1:-all}"

    if [[ "$target" == "all" ]]; then
        local shell_count python_count total_count
        shell_count=$(shell_count_all_tests)
        python_count=$(count_python_tests)
        total_count=$((shell_count + python_count))

        cat <<EOF
Total tests: $total_count

Shell tests (bats): $shell_count
Python tests (pytest): $python_count
EOF

    elif [[ "$target" == "python" ]]; then
        count_python_tests
    elif [[ "$target" == "shell" ]]; then
        shell_count_all_tests
    elif shell_is_valid_suite "$target"; then
        shell_count_suite_tests "$target"
    elif is_valid_category "$target"; then
        local suites total=0
        suites=$(get_category_suites "$target")
        for suite in $suites; do
            if shell_is_valid_suite "$suite" && shell_suite_exists "$suite"; then
                total=$((total + $(shell_count_suite_tests "$suite")))
            fi
        done
        echo "$total"
    else
        echo "Error: Unknown suite or category: $target" >&2
        exit 1
    fi
}

main() {
    local VERBOSE=false
    local TIMING=false
    local COUNT_ONLY=false
    local FORCE_SHELL=false
    local FORCE_PYTHON=false
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
        --shell)
            FORCE_SHELL=true
            ;;
        --python)
            FORCE_PYTHON=true
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

    # Validate conflicting flags
    if [[ "$FORCE_SHELL" == "true" && "$FORCE_PYTHON" == "true" ]]; then
        echo "Error: Cannot specify both --shell and --python" >&2
        exit 1
    fi

    [[ -z "$target" ]] && target="all"

    if [[ "$COUNT_ONLY" == "true" ]]; then
        if [[ "$FORCE_PYTHON" == "true" ]]; then
            show_test_counts "python"
        elif [[ "$FORCE_SHELL" == "true" ]]; then
            show_test_counts "shell"
        else
            show_test_counts "$target"
        fi
        exit 0
    fi

    local suites_to_run=()

    if [[ "$FORCE_PYTHON" == "true" ]]; then
        if python_tests_exist; then
            suites_to_run=("python")
        else
            echo "Warning: No Python tests found" >&2
            exit 0
        fi
    elif [[ "$FORCE_SHELL" == "true" ]]; then
        if [[ "$target" == "all" ]]; then
            while IFS= read -r suite; do
                if shell_suite_exists "$suite"; then
                    suites_to_run+=("$suite")
                fi
            done < <(shell_get_all_suites)
        else
            # Run specific shell suite or category with shell tests only
            if shell_is_valid_suite "$target"; then
                suites_to_run=("$target")
            elif [[ "$target" == "shell" ]]; then
                while IFS= read -r suite; do
                    if shell_suite_exists "$suite"; then
                        suites_to_run+=("$suite")
                    fi
                done < <(shell_get_all_suites)
            else
                echo "Error: $target is not a valid shell suite when using --shell" >&2
                exit 1
            fi
        fi
    else
        if [[ "$target" == "all" ]]; then
            while IFS= read -r suite; do
                if shell_suite_exists "$suite"; then
                    suites_to_run+=("$suite")
                fi
            done < <(shell_get_all_suites)
            # Add Python tests if they exist
            if python_tests_exist; then
                suites_to_run+=("python")
            fi
        elif [[ "$target" == "python" ]]; then
            if python_tests_exist; then
                suites_to_run=("python")
            fi
        elif [[ "$target" == "shell" ]]; then
            while IFS= read -r suite; do
                if shell_suite_exists "$suite"; then
                    suites_to_run+=("$suite")
                fi
            done < <(shell_get_all_suites)
        elif is_valid_suite "$target"; then
            suites_to_run=("$target")
        elif is_valid_category "$target"; then
            local category_suites
            category_suites=$(get_category_suites "$target")
            for suite in $category_suites; do
                if shell_is_valid_suite "$suite" && shell_suite_exists "$suite"; then
                    suites_to_run+=("$suite")
                fi
            done
        else
            cat <<EOF
Error: Unknown suite or category: $target

Valid shell suites: $(shell_get_all_suites | tr '\n' ' ')
Valid categories: ${!TEST_CATEGORIES[*]}
Valid targets: python
EOF
            exit 1
        fi
    fi

    if [[ ${#suites_to_run[@]} -eq 0 ]]; then
        echo "Warning: No test suites found to run" >&2
        exit 0
    fi

    cat <<EOF
$MCP_SERVER_NAME Test Suite
=========================================
EOF

    if [[ ${#suites_to_run[@]} -eq 1 ]]; then
        run_test_suite "${suites_to_run[0]}" "$VERBOSE" "$TIMING"
    else
        run_test_suites "${suites_to_run[@]}"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
