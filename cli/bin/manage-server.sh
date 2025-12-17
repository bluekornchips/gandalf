#!/usr/bin/env bash
#
# Manages the Gandalf MCP Server
#
set -eo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [COMMAND] [OPTIONS]

Manage Gandalf MCP Server

COMMANDS:
  test         Test server functionality
  status       Show server status
  start        Start the server
  stop         Stop the server
  pid          Show server PID
  version      Show server version
  
NOTE: Gandalf is an MCP (Model Context Protocol) server that runs via stdio.
It is automatically started by your IDE (Cursor/Claude Desktop) when needed.
Use 'test' to verify the server works correctly.

OPTIONS:
  -h, --help   Show this help message and exit

EOF
}

# Defaults
DEFAULT_GANDALF_HOME="${HOME}/.gandalf"
# Safety guard, set it here.
GANDALF_HOME="${GANDALF_HOME:-$DEFAULT_GANDALF_HOME}"

# Gets the server PID from the PID file
#
# Inputs:
# - None
#
# Returns:
# - 0 always, prints PID if found, empty if not
get_server_pid() {
	if [[ -z "${GANDALF_HOME:-}" ]]; then
		echo "get_server_pid:: GANDALF_HOME is not set" >&2
		return 1
	fi

	local pid_file="$GANDALF_HOME/server.pid"
	if [[ -f "$pid_file" ]]; then
		cat "$pid_file"
	fi
	return 0
}

# Checks if a server process is running
#
# Inputs:
# - $1: PID to check
#
# Returns:
# - 0 if process is running, 1 if not
is_server_running() {
	local pid="$1"
	if [[ -z "$pid" ]]; then
		return 1
	fi

	if kill -0 "$pid" 2>/dev/null; then
		return 0
	else
		return 1
	fi
}

# Starts the MCP server
#
# Inputs:
# - None
#
# Returns:
# - 0 if server started successfully, 1 if failed
start_server() {
	if [[ -z "${GANDALF_ROOT:-}" ]]; then
		echo "start_server:: GANDALF_ROOT is not set" >&2
		return 1
	fi

	if [[ -z "${GANDALF_HOME:-}" ]]; then
		echo "start_server:: GANDALF_HOME is not set" >&2
		return 1
	fi

	local server_path="$GANDALF_ROOT/server/main.py"
	local python_path="$GANDALF_ROOT/.venv/bin/python3"
	local pid_file="$GANDALF_HOME/server.pid"

	# Check if server is already running
	local current_pid
	current_pid=$(get_server_pid)
	if [[ -n "$current_pid" ]] && is_server_running "$current_pid"; then
		echo "start_server:: Server is already running (PID: $current_pid)"
		return 0
	fi

	if [[ ! -f "$server_path" ]]; then
		echo "start_server:: Server file not found: $server_path" >&2
		return 1
	fi

	if [[ ! -f "$python_path" ]]; then
		echo "start_server:: Python executable not found: $python_path" >&2
		return 1
	fi

	# Start server in background
	cd "$GANDALF_ROOT/server" || return 1
	GANDALF_HOME="$GANDALF_HOME" "$python_path" "$server_path" &
	local server_pid=$!

	# Save PID
	echo "$server_pid" >"$pid_file"

	# Give it a moment to start
	sleep 1

	if is_server_running "$server_pid"; then
		echo "start_server:: Server started successfully (PID: $server_pid)"
		return 0
	else
		echo "start_server:: Failed to start server" >&2
		rm -f "$pid_file"
		return 1
	fi
}

# Stops the MCP server
#
# Inputs:
# - None
#
# Returns:
# - 0 always
stop_server() {
	local pid_file="$GANDALF_HOME/server.pid"
	local current_pid
	current_pid=$(get_server_pid)

	if [[ -z "$current_pid" ]]; then
		echo "stop_server:: Server is not running"
		return 0
	fi

	if ! is_server_running "$current_pid"; then
		echo "stop_server:: Server is not running"
		rm -f "$pid_file"
		return 0
	fi

	# Try graceful shutdown first
	if kill "$current_pid" 2>/dev/null; then
		# Wait a bit for graceful shutdown
		sleep 1

		if is_server_running "$current_pid"; then
			# Force kill if still running
			kill -9 "$current_pid" 2>/dev/null || true
			sleep 0.5
		fi
	fi

	# Clean up PID file
	rm -f "$pid_file"

	if is_server_running "$current_pid"; then
		echo "stop_server:: Failed to stop server" >&2
		return 1
	else
		echo "stop_server:: Server stopped"
		return 0
	fi
}

# Shows the server PID
#
# Inputs:
# - None
#
# Returns:
# - 0 if PID found, 1 if not
show_pid() {
	local current_pid
	current_pid=$(get_server_pid)

	if [[ -z "$current_pid" ]]; then
		echo "show_pid:: No PID file found" >&2
		return 1
	fi

	echo "$current_pid"
	return 0
}

# Tests the MCP server functionality
#
# Inputs:
# - None
#
# Returns:
# - 0 if server works correctly, 1 if not
test_server() {
	if [[ -z "${GANDALF_ROOT:-}" ]]; then
		echo "test_server:: GANDALF_ROOT is not set" >&2
		return 1
	fi

	local server_path="$GANDALF_ROOT/server/main.py"
	local python_path="$GANDALF_ROOT/.venv/bin/python3"

	if [[ ! -f "$server_path" ]]; then
		echo "test_server:: Server file not found: $server_path" >&2
		return 1
	fi

	if [[ ! -f "$python_path" ]]; then
		echo "test_server:: Python executable not found: $python_path" >&2
		return 1
	fi

	local test_input='{"jsonrpc": "2.0", "method": "initialize", "id": 1}'
	local result

	cd "$GANDALF_ROOT/server" || return 1
	result=$(echo "$test_input" | GANDALF_HOME="$GANDALF_HOME" "$python_path" "$server_path" 2>&1)

	if ! echo "$result" | grep -q '"result"'; then
		echo "test_server:: Server test failed." >&2
		echo "test_server:: Response: $result" >&2
		return 1
	fi

	echo "test_server:: Server responds to initialize request, server is working correctly"

	return 0
}

# Shows MCP server configuration status
#
# Inputs:
# - None
#
# Side Effects:
# - Prints MCP configuration status to stdout
show_status() {
	local current_pid
	current_pid=$(get_server_pid)

	if [[ -n "$current_pid" ]] && is_server_running "$current_pid"; then
		echo "show_status:: Server is running (PID: $current_pid)"
		return 0
	else
		echo "show_status:: Server is not running"
		return 1
	fi
}

# Shows server version
#
# Inputs:
# - None
#
# Side Effects:
# - Prints version information to stdout
show_version() {
	if [[ -z "${GANDALF_ROOT:-}" ]]; then
		echo "show_version:: GANDALF_ROOT is not set" >&2
		return 1
	fi

	if [[ ! -f "$GANDALF_ROOT/VERSION" ]]; then
		echo "show_version:: Version file not found" >&2
		return 1
	fi

	cat "$GANDALF_ROOT/VERSION"

	return 0
}

# Main command dispatcher
#
# Inputs:
# - $@: Command and arguments
#
# Side Effects:
# - Executes the requested command
manage_server() {
	if [[ $# -eq 0 ]]; then
		usage
		return 1
	fi

	local command="$1"
	shift

	case "$command" in
	test)
		test_server
		;;
	status)
		show_status
		;;
	start)
		start_server
		;;
	stop)
		stop_server
		;;
	pid)
		show_pid
		;;
	version)
		show_version
		;;
	-h | --help)
		usage
		return 0
		;;
	*)
		echo "manage_server:: Unknown command: $command" >&2
		echo "manage_server:: Use '$(basename "$0") --help' for usage information" >&2
		return 1
		;;
	esac

	return $?
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	manage_server "$@"
fi
