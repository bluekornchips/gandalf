#!/usr/bin/env bash
# Gandalf MCP Server Installation Script

set -euo pipefail

readonly SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
readonly GANDALF_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_PATH")")")"
readonly SCRIPTS_DIR="$GANDALF_ROOT/tools/bin"

readonly DEFAULT_WAIT_TIME=1
readonly DEFAULT_MAX_ATTEMPTS=3
readonly DEFAULT_BACKUP_COUNT=5

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export GANDALF_HOME="${GANDALF_HOME:-$HOME/.${MCP_SERVER_NAME}}"

validate_directory() {
	local dir="$1"
	local description="${2:-directory}"

	if [[ ! -d "$dir" ]]; then
		echo "Error: $description not found: $dir" >&2
		return 1
	fi
	return 0
}

validate_file() {
	local file="$1"
	local description="${2:-file}"

	[[ ! -f "$file" ]] && echo "Error: $description not found: $file" >&2 && return 1
	return 0
}

validate_executable() {
	local cmd="$1"
	local description="${2:-command}"

	if ! command -v "$cmd" &>/dev/null; then
		echo "Error: $description not found: $cmd" >&2
		return 1
	fi
	return 0
}

create_directory_structure() {
	local gandalf_home="$1"

	echo "Creating directory structure at $gandalf_home..."

	local -a directories=(
		"$gandalf_home"
		"$gandalf_home/logs"
		"$gandalf_home/cache"
		"$gandalf_home/config"
		"$gandalf_home/exports"
		"$gandalf_home/backups"
	)

	for dir in "${directories[@]}"; do
		if ! mkdir -p "$dir"; then
			echo "Error: Failed to create directory: $dir" >&2
			return 1
		fi
	done

	echo "Directory structure created successfully"
	return 0
}

clear_cache() {
	local gandalf_home="$1"
	local cache_dir="$gandalf_home/cache"

	if [[ ! -d "$cache_dir" ]]; then
		echo "Cache directory does not exist: $cache_dir"
		return 0
	fi

	echo "Clearing cache directory: $cache_dir"
	if rm -rf "${cache_dir:?}"/*; then
		echo "Cache cleared successfully"
		return 0
	else
		echo "Warning: Failed to clear some cache files" >&2
		return 0
	fi
}

# Installation state management
create_installation_state() {
	local state_file="$GANDALF_HOME/installation-state"
	local gandalf_root="${1:-$GANDALF_ROOT}"
	local gandalf_version="${2:-unknown}"
	local detected_tool="${3:-unknown}"
	local force_tool="${4:-}"
	local repo_root="${5:-$(pwd)}"
	local server_name="${6:-$MCP_SERVER_NAME}"

	echo "Creating installation state: $state_file"

	cat >"$state_file" <<EOF
# Gandalf MCP Server Installation State
# Generated on $(date -u +"%Y-%m-%dT%H:%M:%SZ")

GANDALF_ROOT="$gandalf_root"
GANDALF_VERSION="$gandalf_version"
INSTALLATION_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
DETECTED_TOOL="$detected_tool"
FORCE_TOOL="$force_tool"
REPO_ROOT="$repo_root"
SERVER_NAME="$server_name"
GANDALF_HOME="$GANDALF_HOME"
EOF

	chmod 644 "$state_file" || {
		echo "Error: Failed to set permissions on state file" >&2
		return 1
	}

	echo "Installation state created successfully"
	return 0
}

update_installation_state() {
	local state_file="$GANDALF_HOME/installation-state"
	local cursor_success="${1:-false}"
	local claude_success="${2:-false}"
	local windsurf_success="${3:-false}"

	if [[ ! -f "$state_file" ]]; then
		echo "Error: Installation state file not found: $state_file" >&2
		return 1
	fi

	cat >>"$state_file" <<EOF

# Installation Results ($(date -u +"%Y-%m-%dT%H:%M:%SZ"))
CURSOR_INSTALLED=$cursor_success
CLAUDE_CODE_INSTALLED=$claude_success
WIND_SURF_INSTALLED=$windsurf_success
INSTALL_ALL_TOOLS=true
LAST_UPDATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
EOF

	echo "Installation state updated successfully"
	return 0
}

create_backup() {
	local source_file="$1"
	local backup_name="$2"
	local backup_dir="$GANDALF_HOME/backups"

	if [[ ! -f "$source_file" ]]; then
		if [[ "${DEBUG:-}" == "true" ]]; then
			echo "Debug: Source file does not exist, skipping backup: $source_file" >&2
		fi
		return 0
	fi

	mkdir -p "$backup_dir" || {
		echo "Error: Failed to create backup directory: $backup_dir" >&2
		return 1
	}

	local backup_file="$backup_dir/${backup_name}.backup.$(date +%Y%m%d_%H%M%S)"

	if cp "$source_file" "$backup_file"; then
		echo "Backup created: $backup_file"
		cleanup_old_backups "$backup_dir" "$backup_name" "$DEFAULT_BACKUP_COUNT"
		return 0
	else
		echo "Error: Failed to create backup: $backup_file" >&2
		return 1
	fi
}

cleanup_old_backups() {
	local backup_dir="$1"
	local file_prefix="$2"
	local max_backups="${3:-$DEFAULT_BACKUP_COUNT}"

	if [[ ! -d "$backup_dir" ]]; then
		return 0
	fi

	local -a backups=()
	while IFS= read -r -d '' backup; do
		backups+=("$backup")
	done < <(find "$backup_dir" -name "${file_prefix}.backup.*" -print0 2>/dev/null | sort -zr)

	[[ ${#backups[@]} -le $max_backups ]] && return 0

	local keep_count=0
	for backup in "${backups[@]}"; do
		if [[ $keep_count -lt $max_backups ]]; then
			((keep_count++))
			continue
		fi

		if rm -f "$backup"; then
			echo "Removed old backup: $(basename "$backup")"
		else
			echo "Warning: Failed to remove old backup: $backup" >&2
		fi
	done
}

detect_agentic_tool() {
	local detected_tools=()

	if command -v cursor &>/dev/null || [[ -d "/Applications/Cursor.app" ]]; then
		detected_tools+=("cursor")
	fi

	if [[ -d "$HOME/.claude" ]] || command -v claude &>/dev/null; then
		detected_tools+=("claude-code")
	fi

	if command -v windsurf &>/dev/null || [[ -d "/Applications/Windsurf.app" ]]; then
		detected_tools+=("windsurf")
	fi

	if [[ ${#detected_tools[@]} -eq 0 ]]; then
		echo "none"
	elif [[ ${#detected_tools[@]} -eq 1 ]]; then
		echo "${detected_tools[0]}"
	else
		echo "${detected_tools[0]}"
	fi
}

detect_all_agentic_tools() {
	local detected_tools=()

	if command -v cursor &>/dev/null; then
		detected_tools+=("cursor")
	fi

	if command -v claude &>/dev/null; then
		detected_tools+=("claude-code")
	fi

	if command -v windsurf &>/dev/null; then
		detected_tools+=("windsurf")
	fi

	printf '%s\n' "${detected_tools[@]}"
}

check_required_tools() {
	local -a required_tools=("git" "python3")
	local -a missing_tools=()

	for tool in "${required_tools[@]}"; do
		if ! command -v "$tool" &>/dev/null; then
			missing_tools+=("$tool")
		fi
	done

	if [[ ${#missing_tools[@]} -gt 0 ]]; then
		echo "Error: Missing required tools: ${missing_tools[*]}" >&2
		return 1
	fi

	return 0
}

check_gandalf_structure() {
	local -a required_dirs=("server" "tools")
	local -a required_files=("server/src/main.py" "gandalf")

	for dir in "${required_dirs[@]}"; do
		validate_directory "$GANDALF_ROOT/$dir" "Required directory $dir" || return 1
	done

	for file in "${required_files[@]}"; do
		validate_file "$GANDALF_ROOT/$file" "Required file $file" || return 1
	done

	return 0
}

verify_prerequisites() {
	echo "Verifying system requirements..."

	local -a checks=(
		"check_required_tools"
		"check_gandalf_structure"
	)

	for check in "${checks[@]}"; do
		if ! "$check"; then
			echo "Error: Prerequisite check failed: $check" >&2
			show_installation_help
			return 1
		fi
	done

	echo "Prerequisites verified successfully"
	return 0
}

show_installation_help() {
	cat <<EOF

System Requirements Check Failed!

Installation Options:

1. Full Development Environment (Recommended):
    Run the system setup script to install all development tools:
    ./gandalf setup

2. Minimal Installation:
    Install missing tools manually:
    - Python 3.12+: brew install python3 (macOS) or apt install python3 (Linux)
    - Git: brew install git (macOS) or apt install git (Linux)

3. Python Dependencies Only:
    pip install -r server/requirements.txt

EOF
}

update_json_config() {
	local config_file="$1"
	local server_name="$2"
	local command="$3"
	local -a args=("${@:4}")

	mkdir -p "$(dirname "$config_file")" || {
		echo "Error: Failed to create config directory: $(dirname "$config_file")" >&2
		return 1
	}

	local temp_file
	temp_file=$(mktemp) || {
		echo "Error: Failed to create temporary file" >&2
		return 1
	}

	# Create or update JSON configuration
	if [[ -f "$config_file" ]] && command -v jq &>/dev/null; then
		local args_json
		args_json=$(printf '%s\n' "${args[@]}" | jq -R . | jq -s .)

		jq --arg name "$server_name" \
			--arg cmd "$command" \
			--argjson args "$args_json" \
			'.mcpServers[$name] = {"command": $cmd, "args": $args}' \
			"$config_file" >"$temp_file" || {
			echo "Error: Failed to update JSON config with jq" >&2
			rm -f "$temp_file"
			return 1
		}
	else
		# Fallback JSON creation for when no jq
		local args_json=""
		if [[ ${#args[@]} -gt 0 ]]; then
			args_json=$(printf '"%s",' "${args[@]}")
			args_json="[${args_json%,}]"
		else
			args_json="[]"
		fi

		cat >"$temp_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
            "command": "$command",
            "args": $args_json
        }
    }
}
EOF
	fi

	if mv "$temp_file" "$config_file"; then
		echo "Updated configuration: $config_file"
		return 0
	else
		echo "Error: Failed to update configuration: $config_file" >&2
		rm -f "$temp_file"
		return 1
	fi
}

install_for_cursor() {
	local server_name="$1"
	local gandalf_root="$2"

	echo "Installing Gandalf MCP for Cursor..."

	local config_file="$HOME/.cursor/mcp.json"
	local mcp_script="$gandalf_root/gandalf"

	# Create backup if file exists
	if [[ -f "$config_file" ]]; then
		create_backup "$config_file" "cursor-mcp.json" || {
			echo "Warning: Failed to create backup, continuing..." >&2
		}
	fi

	local workspace_path="$(pwd -P)"
	if update_json_config "$config_file" "$server_name" "$mcp_script" "run" "--project-root" "$workspace_path"; then
		# Add environment variables for workspace detection and Python path
		if command -v jq &>/dev/null; then
			local temp_file
			temp_file=$(mktemp) || {
				echo "Warning: Failed to create temp file for env vars" >&2
				echo "Cursor MCP configuration installed successfully"
				echo "Configured with project root: $workspace_path"
				return 0
			}

			jq --arg workspace "$workspace_path" \
				--arg pythonpath "$gandalf_root/server" \
				'.mcpServers.gandalf.env = {"WORKSPACE_FOLDER_PATHS": $workspace, "PYTHONPATH": $pythonpath}' \
				"$config_file" >"$temp_file" && mv "$temp_file" "$config_file" || {
				echo "Warning: Failed to add environment variables" >&2
				rm -f "$temp_file"
			}
		fi

		echo "Cursor MCP configuration installed successfully"
		echo "Configured with project root: $workspace_path"
		return 0
	else
		echo "Error: Failed to install Cursor MCP configuration" >&2
		return 1
	fi
}

install_for_claude_code() {
	local server_name="$1"
	local gandalf_root="$2"

	echo "Installing Gandalf MCP for Claude Code..."

	if ! validate_executable "claude" "Claude CLI"; then
		echo "Error: Claude CLI not found. Please install Claude Code first." >&2
		return 1
	fi

	# Clean existing configurations
	claude mcp remove "$server_name" -s local 2>/dev/null || true
	claude mcp remove "$server_name" -s user 2>/dev/null || true

	# Install globally
	if claude mcp add "$server_name" "$gandalf_root/gandalf" -s user "run" \
		-e "PYTHONPATH=$gandalf_root/server" \
		-e "CLAUDECODE=1" \
		-e "CLAUDE_CODE_ENTRYPOINT=cli"; then
		echo "Claude Code MCP configuration installed successfully"
		return 0
	else
		echo "Error: Failed to install Claude Code MCP configuration" >&2
		return 1
	fi
}

install_for_windsurf() {
	local server_name="$1"
	local gandalf_root="$2"

	echo "Installing Gandalf MCP for Windsurf..."

	local config_file="$HOME/.codeium/windsurf/mcp_config.json"
	local mcp_script="$gandalf_root/gandalf"

	if update_json_config "$config_file" "$server_name" "$mcp_script" "run"; then
		# Add PYTHONPATH environment variable for module resolution
		if command -v jq &>/dev/null; then
			local temp_file
			temp_file=$(mktemp) || {
				echo "Warning: Failed to create temp file for env vars" >&2
				echo "Windsurf MCP configuration installed successfully"
				return 0
			}

			jq --arg pythonpath "$gandalf_root/server" \
				'.mcpServers.gandalf.env = {"PYTHONPATH": $pythonpath}' \
				"$config_file" >"$temp_file" && mv "$temp_file" "$config_file" || {
				echo "Warning: Failed to add environment variables" >&2
				rm -f "$temp_file"
			}
		fi

		echo "Windsurf MCP configuration installed successfully"
		return 0
	else
		echo "Error: Failed to install Windsurf MCP configuration" >&2
		return 1
	fi
}

install_for_all_tools() {
	local server_name="$1"
	local gandalf_root="$2"
	local primary_tool="$3"

	echo "Installing Gandalf MCP for all supported tools..."

	local cursor_success=false
	local claude_success=false
	local windsurf_success=false

	# Install for each tool
	local -a tools=("cursor" "claude-code" "windsurf")
	local -a install_functions=("install_for_cursor" "install_for_claude_code" "install_for_windsurf")
	local -a success_vars=("cursor_success" "claude_success" "windsurf_success")
	local -a tool_names=("Cursor IDE" "Claude Code" "Windsurf IDE")

	for i in "${!tools[@]}"; do
		local tool="${tools[$i]}"
		local install_func="${install_functions[$i]}"
		local success_var="${success_vars[$i]}"
		local tool_name="${tool_names[$i]}"

		echo "=== Installing for ${tool_name} ==="

		if "$install_func" "$server_name" "$gandalf_root"; then
			declare "$success_var=true"
			echo "PASS: ${tool_name} installation completed successfully"
		else
			echo "FAIL: ${tool_name} installation failed"
		fi
	done

	update_installation_state "$cursor_success" "$claude_success" "$windsurf_success"

	# Show summary
	echo "=== Installation Summary ==="
	echo "Cursor:     $([ "$cursor_success" = true ] && echo "PASS" || echo "FAIL")"
	echo "Claude Code: $([ "$claude_success" = true ] && echo "PASS" || echo "FAIL")"
	echo "Windsurf:   $([ "$windsurf_success" = true ] && echo "PASS" || echo "FAIL")"

	if [[ "$cursor_success" = true || "$claude_success" = true || "$windsurf_success" = true ]]; then
		echo "At least one tool was configured successfully"
		return 0
	else
		echo "Error: No tools were configured successfully" >&2
		return 1
	fi
}

create_rules_files() {
	echo "Creating global rules files using create-rules script..."

	local create_rules_script="$SCRIPTS_DIR/create-rules.sh"

	if [[ ! -f "$create_rules_script" ]]; then
		echo "Warning: create-rules script not found: $create_rules_script" >&2
		echo "Skipping rules file creation"
		return 0
	fi

	local force_flag=""
	if [[ "${FORCE:-false}" == "true" ]]; then
		force_flag="--force"
	fi

	if "$create_rules_script" $force_flag; then
		echo "Rules creation completed successfully"
		return 0
	else
		echo "Warning: Rules creation failed" >&2
		return 1
	fi
}

register_all_available_tools() {
	echo "Detecting and registering all available agentic tools..."

	local -a available_tools
	mapfile -t available_tools < <(detect_all_agentic_tools)

	if [[ ${#available_tools[@]} -eq 0 ]]; then
		echo "Warning: No agentic tools detected for registry" >&2
		return 1
	fi

	echo "Found ${#available_tools[@]} available tools: ${available_tools[*]}"

	local success_count=0
	local total_count=${#available_tools[@]}

	for tool in "${available_tools[@]}"; do
		echo "Registering $tool..."
		if "$SCRIPTS_DIR/registry.sh" auto-register "$tool"; then
			echo "Successfully registered $tool"
			((success_count++))
		else
			echo "Warning: Failed to register $tool" >&2
		fi
	done

	echo "Registry summary: $success_count/$total_count tools registered successfully"

	if [[ $success_count -gt 0 ]]; then
		echo "Registry contains:"
		"$SCRIPTS_DIR/registry.sh" list
		return 0
	else
		echo "Error: No tools were registered successfully" >&2
		return 1
	fi
}

check_server_connectivity() {
	local max_attempts="${1:-$DEFAULT_MAX_ATTEMPTS}"
	local wait_time="${2:-$DEFAULT_WAIT_TIME}"
	local tool="${3:-cursor}"

	echo "Testing server connectivity for $tool..."
	echo "Waiting ${wait_time}s for $tool to recognize MCP server..."

	sleep "$wait_time"

	local attempt=1
	while [[ $attempt -le $max_attempts ]]; do
		echo "Connectivity test attempt $attempt/$max_attempts..."

		if timeout 5 bash -c "cd '$GANDALF_ROOT/server' && PYTHONPATH=. python3 src/main.py --help" >/dev/null 2>&1; then
			echo "Server connectivity test: PASSED"
			return 0
		fi

		if [[ $attempt -lt $max_attempts ]]; then
			echo "Waiting 3s before retry..."
			sleep 3
		fi

		((attempt++))
	done

	echo "Warning: Server connectivity test failed after $max_attempts attempts" >&2
	return 1
}

usage() {
	cat <<EOF
Usage: ./gandalf install [OPTIONS]

Configure global MCP server for Cursor, Claude Code, and Windsurf.

Options:
    -f, --force             Force setup (overwrite existing config, clear cache)
    --tool <tool>           Force specific agentic tool (cursor|claude-code|windsurf)
    -h, --help              Show this help
    --skip-test             Skip connectivity testing
    --wait-time <seconds>   Wait time for tool recognition (default: 1)
    --debug                 Enable debug logging

Examples:   
    gandalf install                      # Install globally (auto-detect tools)
    gandalf install -f                   # Force overwrite existing config
    gandalf install --tool cursor        # Force Cursor installation only
    gandalf install --debug              # Enable debug output

EOF
}

parse_arguments() {
	FORCE_TOOL=""
	SKIP_TEST="false"
	DEBUG="false"
	WAIT_TIME="$DEFAULT_WAIT_TIME"

	while [[ $# -gt 0 ]]; do
		case "$1" in
		-f | --force)
			FORCE=true
			shift
			;;

		--tool)
			FORCE_TOOL="$2"
			if [[ "$FORCE_TOOL" != "cursor" && "$FORCE_TOOL" != "claude-code" && "$FORCE_TOOL" != "windsurf" ]]; then
				echo "Error: --tool must be 'cursor', 'claude-code', or 'windsurf'" >&2
				return 1
			fi
			shift 2
			;;
		--skip-test)
			SKIP_TEST="true"
			shift
			;;
		--wait-time)
			WAIT_TIME="$2"
			if ! [[ "$WAIT_TIME" =~ ^[0-9]+$ ]]; then
				echo "Error: --wait-time must be a positive integer" >&2
				return 1
			fi
			shift 2
			;;
		--debug)
			DEBUG="true"
			export MCP_DEBUG="true"
			shift
			;;
		-h | --help)
			usage
			return 0
			;;
		*)
			echo "Error: Unknown option: $1" >&2
			usage
			return 1
			;;
		esac
	done

	return 0
}

main() {
	if ! parse_arguments "$@"; then
		exit 1
	fi

	echo "Starting Gandalf MCP Server installation..."

	if ! verify_prerequisites; then
		exit 1
	fi

	if ! create_directory_structure "$GANDALF_HOME"; then
		exit 1
	fi

	if [[ "${FORCE:-false}" == "true" ]]; then
		if ! clear_cache "$GANDALF_HOME"; then
			echo "Warning: Cache clearing failed, but continuing..." >&2
		fi
	fi

	local detected_tool
	if [[ -n "$FORCE_TOOL" ]]; then
		detected_tool="$FORCE_TOOL"
		echo "Using forced tool: $detected_tool"
	else
		detected_tool=$(detect_agentic_tool)
		echo "Detected tool: $detected_tool"
	fi

	if ! create_installation_state "$GANDALF_ROOT" "unknown" "$detected_tool" "$FORCE_TOOL"; then
		echo "Error: Failed to create installation state" >&2
		exit 1
	fi

	if ! install_for_all_tools "$MCP_SERVER_NAME" "$GANDALF_ROOT" "$detected_tool"; then
		echo "Error: Installation failed for all tools" >&2
		exit 1
	fi

	if ! create_rules_files; then
		echo "Warning: Rules file creation failed, but continuing..." >&2
	fi

	# Initialize agentic tools registry with all available tools
	echo "Initializing agentic tools registry..."
	if register_all_available_tools; then
		echo "Registry initialization completed successfully"
	else
		echo "Warning: Registry initialization failed, but continuing..." >&2
		echo "You may need to run './gandalf registry auto-register' manually"
	fi

	if [[ "$SKIP_TEST" != "true" ]]; then
		if ! check_server_connectivity "$DEFAULT_MAX_ATTEMPTS" "$WAIT_TIME" "$detected_tool"; then
			echo "Warning: Server connectivity test failed, but installation completed" >&2
		fi
	else
		echo "Skipping connectivity tests"
	fi

	echo "Gandalf MCP Server installation completed successfully!"

	cat <<EOF

Global MCP Configuration Complete!

Configuration Summary:
    Primary tool: $detected_tool
    Server Name: $MCP_SERVER_NAME
    Installation Type: Global (works in all projects)
    Gandalf Home: $GANDALF_HOME

Next Steps:
    1. Restart your configured tools completely
    2. Wait a few moments after restart for MCP server initialization
    3. Test MCP integration by asking: "What files are in my project?"

Troubleshooting:
    - If MCP tools aren't available, restart your tool and wait 30 seconds
    - Run with --debug for detailed logging
    - Use --skip-test for faster installation without connectivity tests

EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
