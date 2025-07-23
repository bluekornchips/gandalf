#!/usr/bin/env bats
# Status Command Tests for Gandalf MCP Server
# Tests for status monitoring, server health checking, and listing functionality

set -euo pipefail

load '../../lib/test-helpers.sh'

setup() {
	shared_setup
	export GANDALF_HOME="$TEST_HOME/.gandalf"
}

teardown() {
	shared_teardown
}

# Helper function to execute status command with proper env isolation
execute_status_command() {
	if [[ -n "${TEMP_GANDALF_ROOT:-}" ]]; then
		env GANDALF_ROOT="$TEMP_GANDALF_ROOT" bash "$GANDALF_ROOT/tools/bin/status" "$@"
	else
		bash "$GANDALF_ROOT/tools/bin/status" "$@"
	fi
}

# Create mock server installation for testing
create_mock_server_installation() {
	local installation_name="${1:-legolas}"
	local server_dir="$TEST_HOME/.gandalf/servers/$installation_name"
	local version="${2:-1.5.0}"

	mkdir -p "$server_dir"

	# Create mock gandalf-server executable
	cat >"$server_dir/gandalf-server" <<EOF
#!/usr/bin/env bash
# Mock Gandalf server for testing
case "\${1:-}" in
    --help)
        echo "Usage: gandalf-server [OPTIONS]"
        echo "Mock Gandalf MCP server for testing"
        ;;
    *)
        echo "Mock server running with args: \$*"
        ;;
esac
EOF
	chmod +x "$server_dir/gandalf-server"

	# Create VERSION file
	echo "$version" >"$server_dir/VERSION"

	echo "$server_dir"
}

# Create broken server installation
create_broken_server_installation() {
	local installation_name="${1:-broken_aragorn}"
	local server_dir="$TEST_HOME/.gandalf/servers/$installation_name"

	mkdir -p "$server_dir"
	
	# Create non-executable or missing gandalf-server
	echo "#!/bin/bash" >"$server_dir/gandalf-server"
	# Don't make it executable - this makes it "broken"
	
	echo "1.0.0" >"$server_dir/VERSION"
	echo "$server_dir"
}

# Create repository server mock in temp directory
create_repository_server_mock() {
	local mock_server_dir="$TEST_HOME/mock_gandalf_root/server/src"
	mkdir -p "$mock_server_dir"
	cat >"$mock_server_dir/main.py" <<'EOF'
#!/usr/bin/env python3
# Mock repository server for testing
print("Mock repository server")
EOF
	# Set temp GANDALF_ROOT for execute_status_command
	export TEMP_GANDALF_ROOT="$TEST_HOME/mock_gandalf_root"
}

# Remove repository server mock and clean up temp env
remove_repository_server_mock() {
	unset TEMP_GANDALF_ROOT
	rm -rf "$TEST_HOME/mock_gandalf_root"
}

@test "status script exists and is executable" {
	[ -f "$GANDALF_ROOT/tools/bin/status" ]
	[ -x "$GANDALF_ROOT/tools/bin/status" ]
}

@test "status help displays usage information" {
	run execute_status_command --help
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Gandalf Status"
	echo "$output" | grep -q "Usage:"
	echo "$output" | grep -q "\-\-servers"
	echo "$output" | grep -q "\-\-available"
	echo "$output" | grep -q "\-\-server-name"
}

@test "status help with -h flag works" {
	run execute_status_command -h
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Usage:"
}

@test "status --servers lists server installations with formatted output" {
	create_mock_server_installation "gandalf" "2.1.0"
	create_mock_server_installation "saruman" "1.8.5"
	create_repository_server_mock

	run execute_status_command --servers
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Server Installations:"
	echo "$output" | grep -q "Name.*Version.*Location.*Status"
	echo "$output" | grep -q "gandalf.*2.1.0.*installed"
	echo "$output" | grep -q "saruman.*1.8.5.*installed"
	echo "$output" | grep -q "repository.*dev.*installed"

	remove_repository_server_mock
}

@test "status --servers shows broken server status" {
	create_broken_server_installation "broken_boromir"

	run execute_status_command --servers
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "broken_boromir.*broken"
}

@test "status --servers with no installations shows helpful message" {
	run execute_status_command --servers
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "No server installations found"
	echo "$output" | grep -q "Run 'gandalf install'"
}

@test "status default behavior shows server status details" {
	create_repository_server_mock

	run execute_status_command
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Server Status: repository"
	echo "$output" | grep -q "Name:.*repository"
	echo "$output" | grep -q "Version:.*dev"
	echo "$output" | grep -q "Location:.*server"
	echo "$output" | grep -q "PID:.*none"
	echo "$output" | grep -q "Health:.*unavailable"

	remove_repository_server_mock
}

@test "status with specific server name" {
	local server_dir
	server_dir=$(create_mock_server_installation "frodo" "3.0.0")

	run execute_status_command --server-name frodo
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Server Status: frodo"
	echo "$output" | grep -q "Version:.*3.0.0"
	echo "$output" | grep -q "Location:.*$server_dir"
}

@test "status with nonexistent server name shows error" {
	run execute_status_command --server-name nonexistent_server
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: Server 'nonexistent_server' not found"
}

@test "status --available lists only healthy servers" {
	create_mock_server_installation "sam" "2.0.0"
	create_broken_server_installation "gollum"

	run execute_status_command --available
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Available Servers:"
	# Since we can't mock actual health checks, expect "No healthy servers found"
	echo "$output" | grep -q "No healthy servers found"
}

@test "status mutual exclusivity: --servers cannot be used with --available" {
	run execute_status_command --servers --available
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: --servers cannot be used with other options"
}

@test "status mutual exclusivity: --servers cannot be used with --server-name" {
	run execute_status_command --servers --server-name test
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: --servers cannot be used with other options"
}

@test "status handles unknown options gracefully" {
	run execute_status_command --invalid-option
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: Unknown option: --invalid-option"
	echo "$output" | grep -q "Run.*--help"
}

@test "status helper command: path returns server path" {
	local server_dir
	server_dir=$(create_mock_server_installation "gimli")

	run execute_status_command path gimli
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "$server_dir"
}

@test "status helper command: path with repository" {
	create_repository_server_mock

	run execute_status_command path repository
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "$TEST_HOME/mock_gandalf_root/server"

	remove_repository_server_mock
}

@test "status helper command: path with nonexistent server fails" {
	run execute_status_command path nonexistent
	[ "$status" -eq 1 ]
}

@test "status helper command: path requires server name" {
	run execute_status_command path
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: Server name required for path command"
}

@test "status helper command: available-names lists server names" {
	create_mock_server_installation "merry"
	create_mock_server_installation "pippin"

	run execute_status_command available-names
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "merry"
	echo "$output" | grep -q "pippin"
}

@test "status with no servers available shows error" {
	# Remove repository mock if it exists
	remove_repository_server_mock 2>/dev/null || true

	run execute_status_command
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: No servers available"
}

@test "status version detection works correctly" {
	local server_dir
	server_dir=$(create_mock_server_installation "elrond" "4.2.1")

	run execute_status_command --server-name elrond
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Version:.*4.2.1"
}

@test "status version unknown when VERSION file missing" {
	local installation_name="arwen"
	local server_dir="$TEST_HOME/.gandalf/servers/$installation_name"

	mkdir -p "$server_dir"
	cat >"$server_dir/gandalf-server" <<'EOF'
#!/bin/bash
echo "mock server"
EOF
	chmod +x "$server_dir/gandalf-server"
	# Don't create VERSION file

	run execute_status_command --server-name arwen
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Version:.*unknown"
}

@test "status output formatting is consistent" {
	create_repository_server_mock

	run execute_status_command
	[ "$status" -eq 0 ]
	# Check that all status fields are properly aligned
	echo "$output" | grep -E "^\s+Name:\s+repository$"
	echo "$output" | grep -E "^\s+Version:\s+dev$"
	echo "$output" | grep -E "^\s+Location:\s+"
	echo "$output" | grep -E "^\s+PID:\s+"
	echo "$output" | grep -E "^\s+Health:\s+"

	remove_repository_server_mock
}

@test "status --servers table formatting is aligned" {
	create_mock_server_installation "celeborn" "1.0.0"

	run execute_status_command --servers
	[ "$status" -eq 0 ]
	# Check header formatting
	echo "$output" | grep -q "Name.*Version.*Location.*Status"
	echo "$output" | grep -q "----.*-------.*--------.*------"

	# Check data row formatting
	echo "$output" | grep -E "celeborn\s+1\.0\.0\s+.*\s+installed"
}

@test "status can handle multiple server installations" {
	create_mock_server_installation "rivendell" "2.0.0"
	create_mock_server_installation "lothlórien" "2.1.0"
	create_mock_server_installation "minas_tirith" "1.9.0"

	run execute_status_command --servers
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "rivendell"
	echo "$output" | grep -q "lothlórien"
	echo "$output" | grep -q "minas_tirith"
}

@test "status repository fallback works when no other servers exist" {
	create_repository_server_mock

	run execute_status_command
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Server Status: repository"

	remove_repository_server_mock
}

@test "status prefers installed servers over repository" {
	create_mock_server_installation "théoden" "2.4.0"
	create_repository_server_mock

	run execute_status_command
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Server Status: théoden"

	remove_repository_server_mock
}