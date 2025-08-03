#!/usr/bin/env bash
# Gandalf Status - Server status monitoring and health checking

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"

readonly SCRIPT_DIR
readonly GANDALF_ROOT
readonly GANDALF_HOME

# Find available server installations
get_available_servers() {
	local servers_dir="$GANDALF_HOME/servers"

	if [[ ! -d "$servers_dir" ]]; then
		return 0
	fi

	for server_path in "$servers_dir"/*; do
		if [[ -d "$server_path" && -f "$server_path/gandalf-server" ]]; then
			basename "$server_path"
		fi
	done
}

# Get the path to a server installation
get_server_path() {
	local server_name="${1:-}"
	[[ -n "${server_name}" ]] || {
		echo "Error: Server name required" >&2
		return 1
	}

	local servers_dir="$GANDALF_HOME/servers"

	if [[ -d "$servers_dir/$server_name" ]]; then
		echo "$servers_dir/$server_name"
		return 0
	fi

	return 1
}

# Get server version
get_server_version() {
	local server_path="${1:-}"
	[[ -n "${server_path}" ]] || {
		echo "Error: Server path required" >&2
		return 1
	}

	if [[ -f "$server_path/VERSION" ]]; then
		cat "$server_path/VERSION"
	else
		echo "unknown"
	fi
}

# Check if server is healthy with a proper JSON-RPC request
check_server_health() {
	local server_name="${1:-}"
	[[ -n "${server_name}" ]] || {
		echo "Error: Server name required" >&2
		return 1
	}

	local timeout_duration=5

	# For MCP servers, send a proper JSON-RPC tools/list request
	local health_response
	if health_response=$(timeout "$timeout_duration" bash -c '
		echo "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}" | 
		"'"$GANDALF_ROOT"'/gandalf" run 2>/dev/null
	' 2>/dev/null); then
		# Check if we got a valid JSON-RPC response with tools
		if echo "$health_response" | jq -e '.result.tools' >/dev/null 2>&1; then
			echo "healthy"
			return 0
		fi
	fi

	echo "unavailable"
	return 1
}

# Get server PID (look for python processes running this specific gandalf instance)
get_server_pid() {
	local server_name="${1:-}"
	[[ -n "${server_name}" ]] || {
		echo "Error: Server name required" >&2
		return 1
	}

	# Look for python processes with --project-root pointing to our server directory
	# This handles multiple gandalf instances in different directories
	local server_path="$GANDALF_ROOT/server"
	local gandalf_pattern="python.*src\.main.*--project-root.*${server_path//\//\\\/}"
	pgrep -f "$gandalf_pattern" 2>/dev/null | head -n1 || echo "none"
}

# Get cache age (time since last cache modification)
get_cache_age() {
	local cache_dir="$GANDALF_HOME/cache"

	if [[ ! -d "$cache_dir" ]]; then
		echo "no cache"
		return 0
	fi

	# Find the most recently modified file in cache
	local newest_file
	newest_file=$(find "$cache_dir" -type f -exec stat -f "%m %N" {} \; 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || true)

	if [[ -z "$newest_file" ]]; then
		echo "empty"
		return 0
	fi

	local mod_time
	mod_time=$(stat -f "%m" "$newest_file" 2>/dev/null || stat -c "%Y" "$newest_file" 2>/dev/null || echo "0")
	local current_time
	current_time=$(date +%s)
	local age_seconds=$((current_time - mod_time))

	# Convert to human-readable format
	if [[ $age_seconds -lt 60 ]]; then
		echo "${age_seconds}s ago"
	elif [[ $age_seconds -lt 3600 ]]; then
		echo "$((age_seconds / 60))m ago"
	elif [[ $age_seconds -lt 86400 ]]; then
		echo "$((age_seconds / 3600))h ago"
	else
		echo "$((age_seconds / 86400))d ago"
	fi
}

# Get available agentic tools
get_available_tools() {
	local tools=()

	# Check for cursor
	if command -v cursor &>/dev/null || [[ -d "/Applications/Cursor.app" ]]; then
		tools+=("cursor")
	fi

	# Check for claude-code
	if [[ -d "$HOME/.claude" ]] || command -v claude &>/dev/null; then
		tools+=("claude-code")
	fi

	# Check for windsurf
	if command -v windsurf &>/dev/null || [[ -d "/Applications/Windsurf.app" ]]; then
		tools+=("windsurf")
	fi

	if [[ ${#tools[@]} -eq 0 ]]; then
		echo "none"
	else
		printf '%s' "${tools[0]}"
		printf ', %s' "${tools[@]:1}"
	fi
}

# Get log path (most recent log file)
get_log_path() {
	local logs_dir="$GANDALF_HOME/logs"

	if [[ ! -d "$logs_dir" ]]; then
		echo "no logs"
		return 0
	fi

	# Find the most recent log file
	local recent_log
	recent_log=$(find "$logs_dir" -name "*.log" -type f -exec stat -f "%m %N" {} \; 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || true)

	if [[ -z "$recent_log" ]]; then
		echo "no logs"
	else
		echo "$recent_log"
	fi
}

# Write readiness status to file
write_readiness_status() {
	local server_name="${1:-}"
	local health_status="${2:-}"
	local pid="${3:-}"
	[[ -n "${server_name}" ]] || {
		echo "Error: Server name required" >&2
		return 1
	}
	[[ -n "${health_status}" ]] || {
		echo "Error: Health status required" >&2
		return 1
	}
	[[ -n "${pid}" ]] || {
		echo "Error: PID required" >&2
		return 1
	}
	local readiness_file="$GANDALF_HOME/readiness.json"

	mkdir -p "$GANDALF_HOME"

	# ISO format
	local timestamp
	timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

	local version="unknown"
	local location="unknown"

	if [[ "$server_name" == "repository" ]]; then
		if [[ -f "$GANDALF_ROOT/server/src/main.py" ]]; then
			location="$GANDALF_ROOT/server"
			version="dev"
		fi
	else
		local server_path
		if server_path=$(get_server_path "$server_name" 2>/dev/null); then
			location="$server_path"
			version=$(get_server_version "$server_path")
		fi
	fi

	# Create readiness status JSON
	cat >"$readiness_file" <<EOF
{
	"timestamp": "$timestamp",
	"server": {
		"name": "$server_name",
		"version": "$version",
		"location": "$location"
	},
	"status": "$health_status",
	"process": {
		"pid": "$pid",
		"running": $(if [[ "$pid" != "none" ]]; then echo "true"; else echo "false"; fi)
	},
	"last_check": "$(date)"
}
EOF

	# Set appropriate permissions (readable by user only for security)
	chmod 600 "$readiness_file"
}

# Get default server name (first available or global)
get_default_server() {
	local available_servers
	available_servers=$(get_available_servers)

	if [[ -n "$available_servers" ]]; then
		echo "$available_servers" | head -n1
	elif [[ -f "$GANDALF_ROOT/server/src/main.py" ]]; then
		echo "repository"
	else
		echo "none"
	fi
}

show_help() {
	cat <<EOH
Gandalf Status - Server status monitoring and health checking

Usage: $0 [OPTIONS]

Options:
    --servers           List all servers with names, versions, and locations
    --server-name NAME  Check status of specific server (default: global)
    -a, --available     List only healthy/available servers
    --help, -h          Show this help message

Helper Commands (for internal use):
    path SERVER_NAME    Get path to specific server installation
    available-names     Get available server names only

Examples:
    $0                    # Show default server status
    $0 --servers          # List all server installations
    $0 --server-name global  # Check specific server status
    $0 --available        # List only healthy servers

EOH
}

# List all servers with details
list_all_servers() {
	local servers_dir="$GANDALF_HOME/servers"
	local found_servers=false

	echo "Server Installations:"
	printf "%-15s %-10s %-50s %s\n" "Name" "Version" "Location" "Status"
	printf "%-15s %-10s %-50s %s\n" "----" "-------" "--------" "------"

	# List server installations
	if [[ -d "$servers_dir" ]]; then
		for server_path in "$servers_dir"/*; do
			if [[ -d "$server_path" ]]; then
				local server_name
				server_name="$(basename "$server_path")"
				local version
				version=$(get_server_version "$server_path")
				local status="installed"

				if [[ ! -f "$server_path/gandalf-server" || ! -x "$server_path/gandalf-server" ]]; then
					status="broken"
				fi

				printf "%-15s %-10s %-50s %s\n" "$server_name" "$version" "$server_path" "$status"
				found_servers=true
			fi
		done
	fi

	# Show repository version if available
	if [[ -f "$GANDALF_ROOT/server/src/main.py" ]]; then
		printf "%-15s %-10s %-50s %s\n" "repository" "dev" "$GANDALF_ROOT/server" "installed"
		found_servers=true
	fi

	if [[ "$found_servers" != "true" ]]; then
		echo "No server installations found"
		echo "Run 'gandalf install' to create server installations"
	fi
}

# Show detailed status of a specific server
show_server_status() {
	local server_name="${1:-}"
	[[ -n "${server_name}" ]] || {
		echo "Error: Server name required" >&2
		return 1
	}
	local server_path=""
	local version="unknown"
	local location="unknown"

	if [[ "$server_name" == "repository" ]]; then
		if [[ -f "$GANDALF_ROOT/server/src/main.py" ]]; then
			location="$GANDALF_ROOT/server"
			version="dev"
		else
			echo "Error: Repository server not found"
			return 1
		fi
	else
		if server_path=$(get_server_path "$server_name" 2>/dev/null); then
			location="$server_path"
			version=$(get_server_version "$server_path")
		else
			echo "Error: Server '$server_name' not found"
			return 1
		fi
	fi

	# Get PID and health
	local pid
	pid=$(get_server_pid "$server_name")
	local health_status
	if health_status=$(check_server_health "$server_name" 2>/dev/null); then
		: # health_status already set
	else
		health_status="unavailable"
	fi

	# Get additional status information
	local cache_age
	cache_age=$(get_cache_age)
	local available_tools
	available_tools=$(get_available_tools)
	local log_path
	log_path=$(get_log_path)

	# Write readiness status to file
	write_readiness_status "$server_name" "$health_status" "$pid"

	cat <<EOF
Server Status: $server_name
	Name:          $server_name
	Version:       $version
	Location:      $location
	PID:           $pid
	Health:        $health_status
	Cache Age:     $cache_age
	Tools:         $available_tools
	Recent Log:    $log_path
	Readiness:     $GANDALF_HOME/readiness.json
EOF
}

# List only available/healthy servers
list_available_servers() {
	local servers_dir="$GANDALF_HOME/servers"
	local available_found=false
	local last_healthy_server=""

	echo "Available Servers:"

	# Check server installations
	if [[ -d "$servers_dir" ]]; then
		for server_path in "$servers_dir"/*; do
			if [[ -d "$server_path" ]]; then
				local server_name
				server_name="$(basename "$server_path")"

				if [[ -f "$server_path/gandalf-server" && -x "$server_path/gandalf-server" ]]; then
					local health
					if health=$(check_server_health "$server_name" 2>/dev/null) && [[ "$health" == "healthy" ]]; then
						local version
						version=$(get_server_version "$server_path")
						echo " $server_name ($version) - healthy"
						available_found=true
						last_healthy_server="$server_name"
					fi
				fi
			fi
		done
	fi

	# Check repository version
	if [[ -f "$GANDALF_ROOT/server/src/main.py" ]]; then
		local health
		if health=$(check_server_health "repository" 2>/dev/null) && [[ "$health" == "healthy" ]]; then
			echo " repository (dev) - healthy"
			available_found=true
			last_healthy_server="repository"
		fi
	fi

	# Write readiness status for the last healthy server found (or indicate no healthy servers)
	if [[ "$available_found" == "true" && -n "$last_healthy_server" ]]; then
		local pid
		pid=$(get_server_pid "$last_healthy_server")
		write_readiness_status "$last_healthy_server" "healthy" "$pid"
	else
		echo " No healthy servers found"
		# Write readiness status indicating no healthy servers
		write_readiness_status "none" "unavailable" "none"
	fi
}

main() {
	local show_servers=false
	local show_available=false
	local server_name=""

	# Handle helper commands first
	case "${1:-}" in
	path)
		if [[ -z "${2:-}" ]]; then
			echo "Error: Server name required for path command" >&2
			exit 1
		fi
		if [[ "$2" == "repository" ]]; then
			echo "$GANDALF_ROOT/server"
		elif server_path=$(get_server_path "$2" 2>/dev/null); then
			echo "$server_path"
		else
			exit 1
		fi
		exit 0
		;;
	available-names)
		get_available_servers
		exit 0
		;;
	esac

	while [[ $# -gt 0 ]]; do
		case "$1" in
		--servers)
			show_servers=true
			shift
			;;
		--server-name)
			server_name="$2"
			shift 2
			;;
		-a | --available)
			show_available=true
			shift
			;;
		--help | -h)
			show_help
			exit 0
			;;
		*)
			echo "Error: Unknown option: $1" >&2
			echo "Run '$0 --help' for usage information" >&2
			exit 1
			;;
		esac
	done

	# Validate exclusive options
	if [[ "$show_servers" == "true" ]] && [[ -n "$server_name" || "$show_available" == "true" ]]; then
		echo "Error: --servers cannot be used with other options" >&2
		exit 1
	fi

	# Execute based on options
	if [[ "$show_servers" == "true" ]]; then
		list_all_servers
	elif [[ "$show_available" == "true" ]]; then
		list_available_servers
	else
		# Show server status (default behavior)
		if [[ -z "$server_name" ]]; then
			server_name=$(get_default_server)
			if [[ "$server_name" == "none" ]]; then
				echo "Error: No servers available"
				exit 1
			fi
		fi
		show_server_status "$server_name"
	fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
