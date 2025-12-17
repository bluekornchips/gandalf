#!/usr/bin/env bats
#
# Gandalf CLI Tests
# Tests for the gandalf CLI entry point (gandalf.sh)
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/gandalf.sh"
[[ ! -f "${SCRIPT}" ]] && echo "Script not found: ${SCRIPT}" >&2 && exit 1

setup() {
	source "${SCRIPT}"

	GANDALF_ROOT="$(mktemp -d)"

	TEST_VERSION="1.2.3"

	echo "${TEST_VERSION}" >"${GANDALF_ROOT}/VERSION"

	export GANDALF_ROOT
}

mock_install() {
	INSTALL_SCRIPT="$(mktemp -d)/install.sh"
	cat <<EOF >"${INSTALL_SCRIPT}"
#!/usr/bin/env bash
exit 0
EOF
	chmod +x "${INSTALL_SCRIPT}"
}

########################################################
# get_version
########################################################
@test "get_version:: returns version from VERSION file" {
	run get_version
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "${TEST_VERSION}"
}

@test "get_version:: returns unknown when VERSION file does not exist" {
	rm -f "${GANDALF_ROOT}/VERSION"

	run get_version
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "unknown"
}

########################################################
# gandalf
########################################################
@test "gandalf:: shows help for -h" {
	run gandalf -h
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Usage:"
}

@test "gandalf:: shows help for --help" {
	run gandalf --help
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Usage:"
}

@test "gandalf:: shows version for -v" {
	run gandalf -v
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "${TEST_VERSION}"
}

@test "gandalf:: routes --install option" {
	mock_install

	run gandalf --install
	[[ "$status" -eq 0 ]]
}

########################################################
# handle_query
########################################################
@test "handle_query:: handles missing file argument" {
	run handle_query
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "requires a file path"
}

@test "handle_query:: handles invalid output format" {
	local test_file="$(mktemp)"
	echo '{"test": "value"}' >"$test_file"

	# Mock the query database script to avoid actual execution
	QUERY_DATABASE_SCRIPT="$(mktemp)"
	cat <<EOF >"$QUERY_DATABASE_SCRIPT"
#!/usr/bin/env bash
echo "Invalid output format: invalid. Supported formats: json, yaml" >&2
exit 1
EOF
	chmod +x "$QUERY_DATABASE_SCRIPT"

	run handle_query "$test_file" --output invalid
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Invalid output format"

	rm -f "$test_file" "$QUERY_DATABASE_SCRIPT"
}

@test "handle_query:: handles missing output format argument" {
	local test_file="$(mktemp)"
	echo '{"test": "value"}' >"$test_file"

	QUERY_DATABASE_SCRIPT="$(mktemp)"
	cat <<EOF >"$QUERY_DATABASE_SCRIPT"
#!/usr/bin/env bash
exit 0
EOF
	chmod +x "$QUERY_DATABASE_SCRIPT"

	run handle_query "$test_file" --output
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "handle_query:: --output requires a format argument"

	rm -f "$test_file" "$QUERY_DATABASE_SCRIPT"
}

@test "handle_query:: handles unknown query options" {
	local test_file="$(mktemp)"
	echo '{"test": "value"}' >"$test_file"

	QUERY_DATABASE_SCRIPT="$(mktemp)"
	cat <<EOF >"$QUERY_DATABASE_SCRIPT"
#!/usr/bin/env bash
exit 0
EOF
	chmod +x "$QUERY_DATABASE_SCRIPT"

	run handle_query "$test_file" --unknown
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "handle_query:: Unknown query option"

	rm -f "$test_file" "$QUERY_DATABASE_SCRIPT"
}
