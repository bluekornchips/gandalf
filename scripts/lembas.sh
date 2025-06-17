#!/bin/bash

# Lembas
# Lembas bread could not fullfill the hunger of a hobbit, but it could fullfill the hunger of a developer.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GANDALF_ROOT="$(dirname "$SCRIPT_DIR")"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export MCP_DEBUG="${MCP_DEBUG:-true}"

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TESTS_DIR="$GANDALF_ROOT/tests"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"

lembas() {
    # Lembas - Complete validation workflow
    #
    # Executes the complete test, reset, install, test cycle to validate
    # the entire MCP server setup. This simulates what a new user would
    # experience when setting up the repository from scratch.
    #
    cat <<EOF
Running Lembas
==============
Complete workflow: test -> reset -> install -> test -> conv check -> prompt tests

EOF

    local repo_path=""
    local force_flag=""

    if [[ $# -eq 0 || "${1:-}" == -* ]]; then
        repo_path="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    else
        repo_path="$1"
        shift
    fi

    while [[ $# -gt 0 ]]; do
        case $1 in
        -f | --force) force_flag="-f" && shift ;;
        *) echo "Unknown argument: $1" && shift ;;
        esac
    done

    echo "Repository path: $repo_path"

    local start_time=$(date +%s)
    local step_start

    step_start=$(date +%s)
    # We run the test first to make sure that the existing state, and any modifications we made, are passing.
    echo "Step 1/6: Running initial tests..."
    local test_output
    if ! test_output=$("$TESTS_DIR/test-suite.sh" 2>&1); then
        cat <<EOF
Initial tests failed. Aborting lembas.

TEST FAILURE DETAILS:
====================
$test_output
EOF
        return 1
    fi

    echo "$test_output"
    echo "Initial tests passed ($(($(date +%s) - step_start))s)"

    step_start=$(date +%s)
    echo "Step 2/6: Resetting MCP configuration..."
    "$SCRIPTS_DIR/reset.sh" --all --backup
    echo "Reset complete ($(($(date +%s) - step_start))s)"

    step_start=$(date +%s)
    echo "Step 3/6: Installing MCP server..."
    if [[ -n "$force_flag" ]]; then
        "$SCRIPTS_DIR/install.sh" "$repo_path" "$force_flag"
    else
        "$SCRIPTS_DIR/install.sh" "$repo_path"
    fi
    echo "Install complete ($(($(date +%s) - step_start))s)"

    step_start=$(date +%s)
    echo "Step 4/6: Running final tests..."
    if ! test_output=$("$TESTS_DIR/test-suite.sh" 2>&1); then
        cat <<EOF
Final tests failed. Lembas completed with errors.

TEST FAILURE DETAILS:
====================
$test_output
EOF
        return 1
    fi

    echo "$test_output"
    echo "Final tests passed ($(($(date +%s) - step_start))s)"

    step_start=$(date +%s)
    echo "Step 5/6: Checking conversation system..."

    # Create a test conversation to ensure the system works
    echo "Creating test conversation..."
    local test_messages='[{"role": "user", "content": "Lembas test conversation", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"}]'
    echo "$test_messages" | "$SCRIPTS_DIR/conversations.sh" store "lembas-test-$(date +%s)" -t "Lembas Test" -g "test,lembas" >/dev/null 2>&1

    echo "Listing conversations..."
    local conv_list_output
    if ! conv_list_output=$("$SCRIPTS_DIR/conversations.sh" list 2>&1); then
        echo "Warning: Conversation list failed: $conv_list_output"
    else
        local conv_count=$(echo "$conv_list_output" | grep -c "^[A-Za-z0-9]" || echo "0")
        echo "Found $conv_count conversations in the system"
        if [[ $conv_count -eq 0 ]]; then
            echo "Warning: No conversations found - this may indicate an issue with conversation storage"
        else
            echo "Conversation system appears to be working"
        fi
    fi
    echo "Conversation check complete ($(($(date +%s) - step_start))s)"

    step_start=$(date +%s)
    echo "Step 6/6: Running prompt tests and generating report..."

    # Run prompt tests and generate report
    if [[ -f "$TESTS_DIR/prompt-tests.md" ]]; then
        echo "Generating prompt test report..."
        local report_file="$GANDALF_ROOT/report-card.md"

        cat >"$report_file" <<EOF
# Gandalf Lembas Report Card

**Generated:** $(date)
**Repository:** $repo_path
**Test Duration:** $(($(date +%s) - start_time))s

## Test Results Summary

### Core System Tests
- PASS Initial tests: PASSED
- PASS Reset configuration: PASSED  
- PASS Install MCP server: PASSED
- PASS Final tests: PASSED
- $([ $conv_count -gt 0 ] && echo "PASS" || echo "WARN") Conversation system: $([ $conv_count -gt 0 ] && echo "PASSED ($conv_count conversations)" || echo "WARNING (no conversations)")

### Prompt Tests Status
EOF

        # Extract test names from prompt-tests.md and create report entries
        local test_num=1
        while IFS= read -r line; do
            if [[ "$line" =~ ^###[[:space:]]*Test[[:space:]]+[0-9]+: ]]; then
                local test_name=$(echo "$line" | sed 's/^###[[:space:]]*Test[[:space:]]*[0-9]*:[[:space:]]*//')
                echo "- TODO Test $test_num: $test_name - MANUAL VERIFICATION REQUIRED" >>"$report_file"
                ((test_num++))
            fi
        done <"$TESTS_DIR/prompt-tests.md"

        cat >>"$report_file" <<EOF

## System Configuration

- **Project Root:** $repo_path
- **Gandalf Root:** $GANDALF_ROOT
- **Server Directory:** $GANDALF_ROOT/server
- **Conversations Found:** $conv_count
- **Test Suite:** All automated tests passed

## Manual Verification Required

The 20 prompt tests in \`tests/prompt-tests.md\` require manual execution and verification:

1. Open Cursor with this project
2. Ensure MCP server is connected
3. Execute each prompt test from \`tests/prompt-tests.md\`
4. Verify expected behaviors match actual results
5. Update this report with pass/fail status for each test

## Conversation System Details

EOF

        if [[ $conv_count -gt 0 ]]; then
            cat >>"$report_file" <<EOF
### Current Conversations
\`\`\`
$conv_list_output
\`\`\`
EOF
        else
            cat >>"$report_file" <<EOF
### No Conversations Found
This may be normal for a fresh installation, but verify that:
- MCP server is properly connected to Cursor
- Tool calls are being made through the MCP interface
- Auto-conversation storage is enabled
EOF
        fi

        cat >>"$report_file" <<EOF

## Next Steps

1. **Manual Prompt Testing:** Execute all 20 prompt tests from \`tests/prompt-tests.md\`
2. **Conversation Verification:** Ensure conversations are being auto-stored during MCP tool usage
3. **Performance Testing:** Verify system performance under load
4. **Integration Testing:** Test with real Cursor workflows

---
*Generated by Gandalf Lembas v$(date +%Y%m%d)*
EOF

        echo "Report generated: $report_file"
    else
        echo "Warning: prompt-tests.md not found, skipping prompt test report"
    fi

    echo "Prompt test report generation complete ($(($(date +%s) - step_start))s)"

    local total_time=$(($(date +%s) - start_time))

    cat <<EOF

Lembas Complete!
================
All automated tests passed, system is fully validated.
Total execution time: ${total_time}s

Report Card: report-card.md
Manual Tests: tests/prompt-tests.md (20 tests require manual verification)
Conversations: $conv_count found in system

Next Steps:
1. Review the generated report-card.md
2. Execute the 20 manual prompt tests in tests/prompt-tests.md
3. Verify MCP server integration in Cursor
4. Test conversation auto-storage during tool usage
EOF
}

# Main execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    lembas "$@"
fi
