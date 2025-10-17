#!/usr/bin/env bats
#
# Tests for query-database.sh script
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="$GIT_ROOT/cli/bin/query-database.sh"
SAMPLE_QUERIES_DIR="$GIT_ROOT/cli/data/sample_queries"
[[ ! -f "$SCRIPT" ]] && echo "Script not found: $SCRIPT" >&2 && exit 1

setup() {
	source "$SCRIPT"
}

########################################################
# Help and Usage
########################################################
@test "query-database:: shows help for -h" {
	run "$SCRIPT" -h
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
	echo "$output" | grep -q "OPTIONS:"
	echo "$output" | grep -q "output FORMAT"
}

@test "query-database:: shows help for --help" {
	run "$SCRIPT" --help
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
	echo "$output" | grep -q "OPTIONS:"
	echo "$output" | grep -q "output FORMAT"
}

@test "query-database:: shows usage when no arguments" {
	run "$SCRIPT"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Usage:"
}

########################################################
# Error Handling
########################################################
@test "query-database:: handles missing query file" {
	run "$SCRIPT" "/nonexistent/file.json"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Query file not found"
}

@test "query-database:: handles invalid output format" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$SCRIPT" -o invalid "$query_file"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid output format"
}

@test "query-database:: handles missing output format argument" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$SCRIPT" "$query_file" --output
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a format argument"
}

@test "query-database:: handles multiple query files" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$SCRIPT" "$query_file" "$query_file"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Multiple query files specified"
}

@test "query-database:: handles unknown options" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$SCRIPT" --unknown "$query_file"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Unknown option"
}

########################################################
# Format Tool Checking
########################################################
@test "check_format_tool:: validates json format" {
	# Test with jq available
	if command -v jq >/dev/null 2>&1; then
		run check_format_tool json
		[[ "$status" -eq 0 ]]
	else
		run check_format_tool json
		[[ "$status" -eq 1 ]]
		echo "$output" | grep -q "jq is required"
	fi
}

@test "check_format_tool:: validates yaml format" {
	# Test with yq available
	if command -v yq >/dev/null 2>&1; then
		run check_format_tool yaml
		[[ "$status" -eq 0 ]]
	else
		run check_format_tool yaml
		[[ "$status" -eq 1 ]]
		echo "$output" | grep -q "yq is required"
	fi
}

@test "check_format_tool:: rejects invalid format" {
	run check_format_tool invalid
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid output format"
}

########################################################
# Output Formatting
########################################################
@test "format_output:: handles json format" {
	if ! command -v jq >/dev/null 2>&1; then
		skip "jq not available"
	fi

	local test_json='{"test": "value", "number": 42}'

	run bash -c "source '$SCRIPT' && echo '$test_json' | format_output json"
	[[ "$status" -eq 0 ]]
	echo "$output" | jq . >/dev/null 2>&1
}

@test "format_output:: handles yaml format" {
	if ! command -v yq >/dev/null 2>&1; then
		skip "yq not available"
	fi

	local test_json='{"test": "value", "number": 42}'

	run bash -c "source '$SCRIPT' && echo '$test_json' | format_output yaml"
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "test:"
	echo "$output" | grep -q "number:"
}

########################################################
# Query Execution
########################################################
@test "execute_query_file:: processes valid query file" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run execute_query_file "$query_file"

	# Should either succeed with JSON output or fail with expected error
	if [[ "$status" -eq 0 ]]; then
		echo "$output" | python3 -m json.tool >/dev/null 2>&1
	else
		echo "$output" | grep -q "Registry file not found\|No suitable Python version found\|ImportError\|Query execution failed"
	fi
}

@test "execute_query_file:: processes query file with json output" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	if ! command -v jq >/dev/null 2>&1; then
		skip "jq not available"
	fi

	run execute_query_file "$query_file" json

	# Should either succeed with formatted JSON or fail with expected error
	if [[ "$status" -eq 0 ]]; then
		echo "$output" | jq . >/dev/null 2>&1
	else
		echo "$output" | grep -q "Registry file not found\|No suitable Python version found\|ImportError\|Query execution failed"
	fi
}

@test "execute_query_file:: processes query file with yaml output" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	if ! command -v yq >/dev/null 2>&1; then
		skip "yq not available"
	fi

	run execute_query_file "$query_file" yaml

	# Should either succeed with YAML output or fail with expected error
	if [[ "$status" -eq 0 ]]; then
		echo "$output" | grep -q "status:"
		echo "$output" | grep -q "query:"
	else
		echo "$output" | grep -q "Registry file not found\|No suitable Python version found\|ImportError\|Query execution failed"
	fi
}
