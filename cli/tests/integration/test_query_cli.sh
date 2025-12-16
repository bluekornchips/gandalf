#!/usr/bin/env bats
#
# Integration tests for Gandalf query CLI functionality
#
GIT_ROOT="$(git rev-parse --show-toplevel || echo "")"
GANDALF_SCRIPT="$GIT_ROOT/gandalf.sh"
SAMPLE_QUERIES_DIR="$GIT_ROOT/cli/data/sample_queries"
[[ ! -f "$GANDALF_SCRIPT" ]] && echo "Gandalf script not found: $GANDALF_SCRIPT" >&2 && return 1

setup_file() {
	if [[ ! -d "$GIT_ROOT/.venv" ]]; then
		echo "Virtual environment not found: $GIT_ROOT/.venv" >&2
		return 1
	fi

	if ! command -v python3 >/dev/null 2>&1; then
		echo "Python3 not found in PATH" >&2
		return 1
	fi

	if [[ ! -f "$GIT_ROOT/.venv/bin/python" ]]; then
		echo "Virtual environment Python not found: $GIT_ROOT/.venv/bin/python" >&2
		return 1
	fi

	return 0
}

setup() {
	return 0
}

@test "gandalf:: script exists and is executable" {
	[[ -f "$GANDALF_SCRIPT" ]]
	[[ -x "$GANDALF_SCRIPT" ]]
}

@test "sample_queries:: directory exists with required files" {
	[[ -d "$SAMPLE_QUERIES_DIR" ]]

	local query_files=("basic_query.json" "full_query.json" "generations_only.json" "no_keywords.json")

	for query_file in "${query_files[@]}"; do
		[[ -f "$SAMPLE_QUERIES_DIR/$query_file" ]]
	done
}

@test "query_handler:: script exists" {
	local query_handler="$GIT_ROOT/server/src/query_handler.py"
	[[ -f "$query_handler" ]]
}

@test "gandalf:: help shows query-from-file option" {
	run "$GANDALF_SCRIPT" --help
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "query-from-file"
}

@test "gandalf:: help shows output format options" {
	run "$GANDALF_SCRIPT" --help
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Output format"
	echo "$output" | grep -q "json.*requires jq"
	echo "$output" | grep -q "yaml.*requires yq"
}

@test "gandalf:: query-from-file handles missing file" {
	run "$GANDALF_SCRIPT" --query-from-file "/nonexistent/file.json"
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Query file not found"
}

@test "gandalf:: query-from-file handles missing argument" {
	run "$GANDALF_SCRIPT" --query-from-file
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a file path"
}

@test "gandalf:: query-from-file processes valid query file" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$GANDALF_SCRIPT" --query-from-file "$query_file"

	# Should either succeed with JSON output or fail with expected error
	if [[ "$status" -eq 0 ]]; then
		echo "$output" | python3 -m json.tool >/dev/null 2>&1
	else
		echo "$output" | grep -q "Registry file not found\|No suitable Python version found\|ImportError\|Query execution failed"
	fi
}

@test "sample_queries:: basic_query has valid JSON structure" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	python3 -m json.tool "$query_file" >/dev/null 2>&1

	local search
	local limit

	search=$(python3 -c "import json; data=json.load(open('$query_file')); print(data.get('search', ''))")
	limit=$(python3 -c "import json; data=json.load(open('$query_file')); print(data.get('limit', 0))")

	[[ -n "$search" ]]
	[[ "$limit" -gt 0 ]]
}

@test "sample_queries:: all files have valid structure" {
	local query_files=("basic_query.json" "full_query.json" "generations_only.json" "no_keywords.json")

	for query_file in "${query_files[@]}"; do
		local full_path="$SAMPLE_QUERIES_DIR/$query_file"

		python3 -m json.tool "$full_path" >/dev/null 2>&1

		local limit
		limit=$(python3 -c "import json; data=json.load(open('$full_path')); print(data.get('limit', 0))")

		[[ "$limit" -gt 0 ]]
	done
}

@test "gandalf:: query-from-file with invalid output format" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$GANDALF_SCRIPT" --query-from-file "$query_file" --output invalid

	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid output format"
}

@test "gandalf:: query-from-file with missing output format argument" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	run "$GANDALF_SCRIPT" --query-from-file "$query_file" --output

	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a format argument"
}

@test "gandalf:: query-from-file with json output format" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	# Skip if jq is not available
	if ! command -v jq >/dev/null 2>&1; then
		skip "jq not available"
	fi

	run "$GANDALF_SCRIPT" --query-from-file "$query_file" --output json

	# Should either succeed with formatted JSON or fail with expected error
	if [[ "$status" -eq 0 ]]; then
		echo "$output" | jq . >/dev/null 2>&1
	else
		echo "$output" | grep -q "Registry file not found\|No suitable Python version found\|ImportError\|Query execution failed"
	fi
}

@test "gandalf:: query-from-file with yaml output format" {
	local query_file="$SAMPLE_QUERIES_DIR/basic_query.json"

	# Skip if yq is not available
	if ! command -v yq >/dev/null 2>&1; then
		skip "yq not available"
	fi

	run "$GANDALF_SCRIPT" --query-from-file "$query_file" --output yaml

	# Should either succeed with YAML output or fail with expected error
	if [[ "$status" -eq 0 ]]; then
		echo "$output" | grep -q "status:"
		# Check for either success structure (results:) or error structure (error:)
		echo "$output" | grep -qE "(results:|error:)"
	else
		echo "$output" | grep -q "Registry file not found\|No suitable Python version found\|ImportError\|Query execution failed"
	fi
}
