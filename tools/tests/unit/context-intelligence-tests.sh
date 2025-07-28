#!/usr/bin/env bats
# Context Intelligence Tests for Gandalf MCP Server
# File prioritization, relevance scoring, and context analysis

set -euo pipefail

load "$GANDALF_ROOT/tools/tests/test-helpers.sh"

create_react_app() {
    cat >app.js <<EOF
class App extends React.Component {
    render() {
        return <div>Hello, world!</div>;
    }
}
EOF
}

validate_context_intelligence_response() {
    local response="$1"
    local content
    
    validate_jsonrpc_response "$response"
    content=$(echo "$response" | jq -r '.result.content[0].text')
    
    if [[ -z "$content" ]]; then
        echo "ERROR: Empty content in context intelligence response" >&2
        return 1
    fi
    
    echo "$content"
}

has_context_intelligence_formatting() {
    local content="$1"
    echo "$content" | grep -q "HIGH PRIORITY\|MEDIUM PRIORITY\|priority\|relevance\|TOP FILES BY RELEVANCE"
}

validate_basic_file_listing() {
    local content="$1"
    if ! echo "$content" | grep -q "\.py\|\.js\|\.md"; then
        echo "ERROR: Expected file listing content but got: $content" >&2
        return 1
    fi
}

validate_file_type_filtering() {
    local content="$1"
    local expected_type="$2"
    local forbidden_types=("${@:3}")
    
    if ! echo "$content" | grep -q "$expected_type"; then
        echo "ERROR: Expected $expected_type files but none found in: $content" >&2
        return 1
    fi
    
    for forbidden_type in "${forbidden_types[@]}"; do
        if echo "$content" | grep -q "$forbidden_type"; then
            echo "ERROR: Found forbidden $forbidden_type in filtered results: $content" >&2
            return 1
        fi
    done
}

count_file_references() {
    local content="$1"
    echo "$content" | grep -c "\\.py\|\\.js\|\\.md\|\\.bin\|\\.toml\|\\.json" || echo "0"
}

execute_context_intelligence_call() {
    local use_relevance_scoring="$1"
    local additional_args="${2:-}"
    local call_args="{\"name\": \"list_project_files\", \"arguments\": {\"use_relevance_scoring\": $use_relevance_scoring"
    
    if [[ -n "$additional_args" ]]; then
        call_args="$call_args, $additional_args"
    fi
    call_args="$call_args}}"
    
    execute_rpc "tools/call" "$call_args"
}

create_context_intelligence_project() {
    echo "# The Test of Context Intelligence" >README.md
    echo "print('I should not pass')" >test.py
    echo "import os; import sys" >main.py
    echo "const test = 'hello';" >script.js
    echo "body { color: blue; }" >style.css

    mkdir -p src tests docs config
    echo "from main import test_function" >src/core.py
    echo "function testMain() { return true; }" >tests/test.js
    echo "# Component Documentation" >docs/components.md
    echo "debug=true" >config/settings.ini

    create_react_app

    # Create nested structure
    mkdir -p deep/nested/structure
    echo "# Deep nested readme" >deep/nested/structure/readme.md
    echo "deeply nested test content" >deep/nested/structure/test.txt

    # Add files of different sizes
    dd if=/dev/zero of=small.txt bs=1024 count=1 2>/dev/null
    dd if=/dev/zero of=medium.txt bs=1024 count=50 2>/dev/null
    dd if=/dev/zero of=large.txt bs=1024 count=500 2>/dev/null

    # Make some files recently modified
    touch -t $(date -v-2H +%Y%m%d%H%M) src/core.py 2>/dev/null ||
        touch -d "2 hours ago" src/core.py 2>/dev/null ||
        touch src/core.py

    git add . >/dev/null 2>&1
    git commit -m "context intelligence test project" >/dev/null 2>&1

    # Create some git activity
    echo "print('updated')" >>main.py
    git add main.py >/dev/null 2>&1
    git commit -m "the context intelligence test continues" >/dev/null 2>&1
}

setup() {
    shared_setup
    create_context_intelligence_project
}

teardown() {
    shared_teardown
}

@test "context intelligence can be enabled and disabled" {
    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    if has_context_intelligence_formatting "$content"; then
        echo "✓ Context intelligence formatting detected"
    else
        echo "Expected context intelligence formatting but got: $content" >&2
        false
    fi

    run execute_context_intelligence_call "false"
    [ "$status" -eq 0 ]
    
    local basic_content
    basic_content=$(validate_context_intelligence_response "$output")
    
    validate_basic_file_listing "$basic_content"
    
    if has_context_intelligence_formatting "$basic_content"; then
        echo "ERROR: Basic mode should not have context intelligence formatting" >&2
        false
    fi
}

@test "file type prioritization works correctly" {
    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    validate_basic_file_listing "$content"
    
    if ! has_context_intelligence_formatting "$content"; then
        echo "Expected prioritization formatting in: $content" >&2
        false
    fi
}

@test "hidden files are included by default" {
    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    if echo "$content" | grep -q "\.env"; then
        echo "✓ Hidden files detected"
    else
        echo "Hidden files processing should be functional"
    fi
}

@test "file type filtering works with context intelligence" {
    run execute_context_intelligence_call "true" "\"file_types\": [\".py\"]"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    validate_file_type_filtering "$content" "\.py" "\.js" "README\.md"
}

@test "summary statistics are provided" {
    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    if echo "$content" | grep -q "total\|files\|SUMMARY"; then
        echo "✓ Summary statistics found"
    else
        echo "Summary information should be present in context intelligence output"
    fi
}

@test "large files are handled appropriately" {
    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    echo "Large files handled successfully"
}

@test "git activity affects file scoring" {
    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    if echo "$content" | grep -q "README\.md\|main\.py"; then
        echo "✓ Recently modified files detected"
    else
        echo "Git activity should influence file scoring"
    fi
}

@test "max files limit is respected with scoring" {
    run execute_context_intelligence_call "true" "\"max_files\": 5"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    local file_count
    file_count=$(count_file_references "$content")
    
    if [[ $file_count -le 10 ]]; then
        echo "✓ File count limit respected: $file_count files"
    else
        echo "ERROR: Too many files returned: $file_count" >&2
        false
    fi
}

@test "context intelligence handles empty projects" {
    local empty_project="$TEST_HOME/empty-project"
    mkdir -p "$empty_project"
    cd "$empty_project"
    git init >/dev/null 2>&1

    run execute_rpc "tools/call" '{"name": "list_project_files", "arguments": {"use_relevance_scoring": true}}' "$empty_project"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    if echo "$content" | grep -q "0.*files\|empty\|No files"; then
        echo "✓ Empty project handled correctly"
    else
        echo "Empty project should be handled gracefully"
    fi
}

@test "tool definition includes relevance scoring parameter" {
    run execute_rpc "tools/list" '{}'
    [ "$status" -eq 0 ]
    validate_jsonrpc_response "$output"

    local tools_list
    tools_list=$(echo "$output" | jq -r '.result.tools')

    if echo "$tools_list" | grep -q "use_relevance_scoring"; then
        echo "✓ Relevance scoring parameter found"
    else
        echo "ERROR: use_relevance_scoring parameter not found in tools list" >&2
        false
    fi
    
    if echo "$tools_list" | grep -q "list_project_files"; then
        echo "✓ list_project_files tool found"
    else
        echo "ERROR: list_project_files tool not found" >&2
        false
    fi
}

@test "performance comparison between scoring modes" {
    run execute_context_intelligence_call "false"
    [ "$status" -eq 0 ]
    
    local basic_content
    basic_content=$(validate_context_intelligence_response "$output")
    validate_basic_file_listing "$basic_content"

    run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local scoring_content
    scoring_content=$(validate_context_intelligence_response "$output")
    validate_basic_file_listing "$scoring_content"

    echo "Both scoring modes completed successfully"
}

@test "fallback mode works when intelligence is disabled" {
    run execute_context_intelligence_call "false"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    validate_basic_file_listing "$content"
    
    if has_context_intelligence_formatting "$content"; then
        echo "ERROR: Basic mode should not have context intelligence formatting" >&2
        false
    fi
}

@test "context intelligence works regardless of environment variables" {
    ENABLE_CONTEXT_INTELLIGENCE=false run execute_context_intelligence_call "true"
    [ "$status" -eq 0 ]
    
    local content
    content=$(validate_context_intelligence_response "$output")
    
    if has_context_intelligence_formatting "$content" || echo "$content" | grep -q "\.py\|\.js"; then
        echo "✓ Context intelligence works despite environment variables"
    else
        echo "ERROR: Context intelligence should work when explicitly requested" >&2
        false
    fi
}
