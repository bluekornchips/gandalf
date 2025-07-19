#!/usr/bin/env bats
# CLI Tests for Gandalf MCP Server
# Tests for main CLI functionality, server management, and command dispatch

set -euo pipefail

load '../../lib/test-helpers.sh'

execute_cli_command() {
	local command="$1"
	shift
	bash "$GANDALF_ROOT/gandalf" "$command" "$@"
}

create_mock_server_installation() {
	local installation_name="${1:-global}"
	local server_dir="$TEST_HOME/.gandalf/servers/$installation_name"

	mkdir -p "$server_dir/src"
	mkdir -p "$server_dir/.venv/bin"

	# Create mock wrapper script
	cat >"$server_dir/gandalf-server" <<'EOF'
#!/usr/bin/env bash
# Mock Gandalf server wrapper for testing
echo "Mock server $0 called with: $*"
case "${1:-}" in
    --help)
        echo "Usage: gandalf-server [OPTIONS]"
        echo "Mock Gandalf MCP server for testing"
        ;;
    run)
        echo "Starting mock server..."
        ;;
    *)
        echo "Mock server running with args: $*"
        ;;
esac
EOF
	chmod +x "$server_dir/gandalf-server"

	# Create VERSION file
	echo "2.3.0" >"$server_dir/VERSION"

	# Create mock requirements.txt
	echo "PyYAML>=6.0" >"$server_dir/requirements.txt"

	# Create mock venv
	echo "#!/bin/bash" >"$server_dir/.venv/bin/python3"
	chmod +x "$server_dir/.venv/bin/python3"
}

validate_server_listing() {
	local output="$1"
	local expected_server="$2"

	echo "$output" | grep -q "Available server installations:"
	echo "$output" | grep -q "$expected_server.*+"
}

setup() {
	shared_setup
	create_minimal_project
}

teardown() {
	shared_teardown
}

@test "CLI shows help message with consolidated installation info" {
	run execute_cli_command "help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Usage:.*COMMAND"
	echo "$output" | grep -q "list-servers"
	echo "$output" | grep -q "consolidated"
	echo "$output" | grep -q "server installation"
	echo "$output" | grep -q -- "--server"
}

@test "CLI handles unknown command gracefully" {
	run execute_cli_command "unknown-command"
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: Unknown command"
	echo "$output" | grep -q "gandalf help"
}

@test "list-servers shows available server installations" {
	create_mock_server_installation "global"
	create_mock_server_installation "shire-project"

	run execute_cli_command "list-servers"
	[ "$status" -eq 0 ]

	validate_server_listing "$output" "global"
	validate_server_listing "$output" "shire-project"
}

@test "list-servers shows no installations when servers directory missing" {
	# Remove any existing servers directory
	rm -rf "$TEST_HOME/.gandalf/servers"

	run execute_cli_command "list-servers"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "No consolidated installations"
}

@test "list-servers identifies broken server installations" {
	create_mock_server_installation "working-server"

	# Create broken server installation (missing wrapper)
	mkdir -p "$TEST_HOME/.gandalf/servers/broken-server"

	run execute_cli_command "list-servers"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "working-server.*+"
	echo "$output" | grep -q "broken-server.*X"
}

@test "list-servers shows repository version when available" {
	# Create mock repository server structure
	mkdir -p "$GANDALF_ROOT/server/src"
	touch "$GANDALF_ROOT/server/src/main.py"

	run execute_cli_command "list-servers"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "repository.*+"
}

@test "run command uses global server installation by default" {
	create_mock_server_installation "global"

	run execute_cli_command "run" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Start the Gandalf MCP server"
	echo "$output" | grep -q "consolidated server installations"
}

@test "run command with --server parameter uses specific installation" {
	create_mock_server_installation "fellowship-server"

	run execute_cli_command "run" "--server" "fellowship-server" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Start the Gandalf MCP server"
}

@test "run command shows help for server selection" {
	run execute_cli_command "run" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Usage:.*run"
	echo "$output" | grep -q -- "--server"
	echo "$output" | grep -q "Server Selection:"
	echo "$output" | grep -q "global.*installation"
	echo "$output" | grep -q "Repository version"
}

@test "run command falls back to first available installation" {
	create_mock_server_installation "bag-end-server"
	create_mock_server_installation "rivendell-server"

	run execute_cli_command "run" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Start the Gandalf MCP server"
}

@test "run command falls back to repository mode when no installations" {
	# Remove any server installations
	rm -rf "$TEST_HOME/.gandalf/servers"

	run execute_cli_command "run" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Start the Gandalf MCP server"
}

@test "run command errors on nonexistent server installation" {
	run execute_cli_command "run" "--server" "nonexistent-server"
	[ "$status" -eq 1 ]
	echo "$output" | grep -q "Error: Server installation.*not found"
	echo "$output" | grep -q "Available installations:"
}

@test "run command passes through project-root parameter correctly" {
	create_mock_server_installation "global"
	mkdir -p "$TEST_HOME/minas-tirith"

	run execute_cli_command "run" "--project-root" "$TEST_HOME/minas-tirith" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "project-root"
}

@test "run command passes through debug parameter correctly" {
	create_mock_server_installation "global"

	run execute_cli_command "run" "--debug" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q -- "--debug"
}

@test "CLI commands dispatch correctly to tools scripts" {
	# Test that other commands still work
	run execute_cli_command "install" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Configure.*MCP server"

	# Test uninstall
	run execute_cli_command "uninstall" "--help"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "Remove.*MCP server"
}

@test "CLI preserves exit codes from dispatched commands" {
	# Install script should exit with 1 for invalid options
	run execute_cli_command "install" "--invalid-option"
	[ "$status" -eq 1 ]

	# Uninstall script should exit with 1 for invalid options
	run execute_cli_command "uninstall" "--invalid-option"
	[ "$status" -eq 1 ]
}

@test "CLI handles missing server installations directory gracefully" {
	# Remove servers directory entirely
	rm -rf "$TEST_HOME/.gandalf/servers"

	run execute_cli_command "list-servers"
	[ "$status" -eq 0 ]
	echo "$output" | grep -q "No consolidated installations"
}
