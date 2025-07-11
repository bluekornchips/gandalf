#!/bin/bash
# Gandalf MCP Server Installation Script
# Configures MCP servers for Cursor, Claude Code, and Windsurf

set -euo pipefail

readonly SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
readonly GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"
readonly SCRIPTS_DIR="$GANDALF_ROOT/scripts"
readonly SERVER_DIR="$GANDALF_ROOT/server/src"
readonly SERVER_SCRIPT="$SERVER_DIR/main.py"
readonly DEFAULT_WAIT_TIME=1
readonly DEFAULT_MAX_ATTEMPTS=3
readonly DEFAULT_BACKUP_COUNT=5

export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export GANDALF_HOME="${GANDALF_HOME:-$HOME/.${MCP_SERVER_NAME}}"

source "$SCRIPTS_DIR/platform-utils.sh"
source "$SCRIPTS_DIR/install/cursor"
source "$SCRIPTS_DIR/install/claude-code"
source "$SCRIPTS_DIR/install/windsurf"

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

check_python_version() {
    local python_cmd="python3"

    if ! command -v "$python_cmd" &>/dev/null; then
        echo "Error: Python 3 not found" >&2
        return 1
    fi

    local version_info
    version_info=$("$python_cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)

    if ! printf '%s\n' "3.10" "$version_info" | sort -V | head -n1 | grep -q "^3.10$"; then
        echo "Error: Python 3.10+ required, found $version_info" >&2
        return 1
    fi

    echo "Python $version_info found"
    return 0
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
    local -a required_dirs=("server" "scripts")
    local -a required_files=("server/src/main.py" "gandalf.sh")

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
        "check_python_version"
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
    cat <<'EOF'

System Requirements Check Failed!

Installation Options:

1. Full Development Environment (Recommended):
    Run the system setup script to install all development tools:
    ../../scripts/setup.sh

2. Minimal Installation:
    Install missing tools manually:
    - Python 3.10+: brew install python3 (macOS) or apt install python3 (Linux)
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

update_json_config_with_env() {
    local config_file="$1"
    local server_name="$2"
    local command="$3"
    local env_vars="$4"
    local -a args=("${@:5}")

    mkdir -p "$(dirname "$config_file")" || {
        echo "Error: Failed to create config directory: $(dirname "$config_file")" >&2
        return 1
    }

    local temp_file
    temp_file=$(mktemp) || {
        echo "Error: Failed to create temporary file" >&2
        return 1
    }
    if [[ -f "$config_file" ]] && command -v jq &>/dev/null; then
        local args_json
        args_json=$(printf '%s\n' "${args[@]}" | jq -R . | jq -s .)
        
        if [[ -n "$env_vars" ]]; then
            local env_object
            env_object=$(echo "$env_vars" | sed 's/^"env": *//; s/, *$//')
            
            jq --arg name "$server_name" \
                --arg cmd "$command" \
                --argjson args "$args_json" \
                --argjson env "$env_object" \
                '.mcpServers[$name] = {"command": $cmd, "args": $args, "env": $env}' \
                "$config_file" >"$temp_file" || {
                echo "Error: Failed to update JSON config with jq" >&2
                rm -f "$temp_file"
                return 1
            }
        else
            jq --arg name "$server_name" \
                --arg cmd "$command" \
                --argjson args "$args_json" \
                '.mcpServers[$name] = {"command": $cmd, "args": $args}' \
                "$config_file" >"$temp_file" || {
                echo "Error: Failed to update JSON config with jq" >&2
                rm -f "$temp_file"
                return 1
            }
        fi
    else
        # Fallback JSON creation for when no jq
        local args_json=""
        if [[ ${#args[@]} -gt 0 ]]; then
            args_json=$(printf '"%s",' "${args[@]}")
            args_json="[${args_json%,}]"
        else
            args_json="[]"
        fi
        
        if [[ -n "$env_vars" ]]; then
            local env_object
            env_object=$(echo "$env_vars" | sed 's/^"env": *//; s/, *$//') # Remove trailing comma and parse env vars
            
            cat >"$temp_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
            "command": "$command",
            "args": $args_json,
            "env": $env_object
        }
    }
}
EOF
        else
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

        if "$install_func" "$server_name" "$gandalf_root" "$scope" "$install_dir"; then
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
    echo "Creating global rules files for all supported tools..."

    local -a rule_dirs=("$HOME/.cursor/rules" "$HOME/.claude" "$HOME/.windsurf")
    for dir in "${rule_dirs[@]}"; do
        mkdir -p "$dir" || {
            echo "Warning: Failed to create rules directory: $dir" >&2
        }
    done

    local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"

    local workflows_file="$spec_dir/rules/core.md"
    local troubleshooting_file="$spec_dir/rules/troubleshooting.md"

    # Check if any rules files exist
    if [[ ! -f "$workflows_file" && ! -f "$troubleshooting_file" ]]; then
        echo "Warning: No rules files found in $spec_dir" >&2
        echo "Skipping rules file creation"
        return 0
    fi

    echo "Found rules files in $spec_dir"

    # Combine the rule files into a single file
    local combined_rules=""
    if [[ -f "$workflows_file" ]]; then
        combined_rules="$(cat "$workflows_file")"
    fi
    if [[ -f "$troubleshooting_file" ]]; then
        if [[ -n "$combined_rules" ]]; then
            combined_rules="$combined_rules"$'\n\n'"$(cat "$troubleshooting_file")"
        else
            combined_rules="$(cat "$troubleshooting_file")"
        fi
    fi

    local cursor_success=false
    local claude_success=false  
    local windsurf_success=false

    # Create rules for each tool using the combined content
    if create_cursor_rules "$combined_rules"; then
        cursor_success=true
        echo "Installing for Cursor IDE"
    fi

    if create_claude_rules "$combined_rules"; then
        claude_success=true
        echo "Installing for Claude Code"
    fi

    if create_windsurf_rules "$combined_rules"; then
        windsurf_success=true
        echo "Installing for Windsurf IDE"
    fi

    if [[ "$cursor_success" = true || "$claude_success" = true || "$windsurf_success" = true ]]; then
        echo "Global Rules Files Created:"
        [[ "$cursor_success" = true ]] && echo "Cursor: $HOME/.cursor/rules/$MCP_SERVER_NAME-rules.mdc"
        [[ "$claude_success" = true ]] && echo "Claude Code: $HOME/.claude/global_settings.json"
        [[ "$windsurf_success" = true ]] && echo "Windsurf: $HOME/.windsurf/global_rules.md"
        echo "See spec/rules/core.md and spec/rules/troubleshooting.md for complete documentation"
    fi

    return 0
}

create_local_rules_files() {
    local install_dir="$1"
    echo "Creating local rules files for project: $install_dir"

    local -a rule_dirs=("$install_dir/.cursor/rules" "$install_dir/.claude" "$install_dir/.windsurf")
    for dir in "${rule_dirs[@]}"; do
        mkdir -p "$dir" || {
            echo "Warning: Failed to create local rules directory: $dir" >&2
        }
    done

    local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"
    local workflows_file="$spec_dir/rules/core.md"
    local troubleshooting_file="$spec_dir/rules/troubleshooting.md"

    # Check if any rules files exist
    if [[ ! -f "$workflows_file" && ! -f "$troubleshooting_file" ]]; then
        echo "Warning: No rules files found in $spec_dir" >&2
        echo "Skipping local rules file creation"
        return 0
    fi

    echo "Found rules files in $spec_dir"

    # Combine the rule files into a single file
    local combined_rules=""
    if [[ -f "$workflows_file" ]]; then
        combined_rules="$(cat "$workflows_file")"
    fi
    if [[ -f "$troubleshooting_file" ]]; then
        if [[ -n "$combined_rules" ]]; then
            combined_rules="$combined_rules"$'\n\n'"$(cat "$troubleshooting_file")"
        else
            combined_rules="$(cat "$troubleshooting_file")"
        fi
    fi

    local cursor_success=false
    local claude_success=false  
    local windsurf_success=false

    # Create local rules for each tool using the combined content
    if create_local_cursor_rules "$install_dir" "$combined_rules"; then
        cursor_success=true
    fi

    if create_local_claude_rules "$install_dir" "$combined_rules"; then
        claude_success=true
    fi

    if create_local_windsurf_rules "$install_dir" "$combined_rules"; then
        windsurf_success=true
    fi

    if [[ "$cursor_success" = true || "$claude_success" = true || "$windsurf_success" = true ]]; then
        echo "Local Rules Files Created:"
        [[ "$cursor_success" = true ]] && echo "Cursor: $install_dir/.cursor/rules/gandalf-rules.mdc"
        [[ "$claude_success" = true ]] && echo "Claude Code: $install_dir/.claude/local_settings.json"
        [[ "$windsurf_success" = true ]] && echo "Windsurf: $install_dir/.windsurf/rules.md"
        echo "See spec/rules/core.md and spec/rules/troubleshooting.md for complete documentation"
    fi

    return 0
}







check_server_connectivity() {
    local max_attempts="${1:-$DEFAULT_MAX_ATTEMPTS}"
    local wait_time="${2:-$DEFAULT_WAIT_TIME}"
    local tool="${3:-cursor}"

    echo "Testing server connectivity for $tool..."
    echo "Waiting ${wait_time}s for $tool to recognize MCP server..."

    sleep "$wait_time"

    local python_exec
    python_exec=$(get_python_executable) || {
        echo "Error: Failed to get Python executable" >&2
        return 1
    }

    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        echo "Connectivity test attempt $attempt/$max_attempts..."

        if timeout 5 bash -c "cd '$GANDALF_ROOT/server' && PYTHONPATH=. '$python_exec' src/main.py --help" >/dev/null 2>&1; then
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

get_python_executable() {
    local venv_python="$GANDALF_ROOT/.venv/bin/python3"
    if [[ -f "$venv_python" ]]; then
        echo "$venv_python"
    else
        echo "python3"
    fi
}

get_git_repo_name() {
    local install_dir="$1"
    
    # Check if we're in a git repository
    if ! git -C "$install_dir" rev-parse --git-dir >/dev/null 2>&1; then
        return 1
    fi
    
    # Try to get repo name from remote origin URL
    local repo_url
    if repo_url=$(git -C "$install_dir" config --get remote.origin.url 2>/dev/null); then
        # Extract repo name from various URL formats
        # git@github.com:user/repo.git -> repo
        # https://github.com/user/repo.git -> repo  
        # https://github.com/user/repo -> repo
        local repo_name
        repo_name=$(basename "$repo_url" .git)
        if [[ -n "$repo_name" && "$repo_name" != "." ]]; then
            echo "$repo_name"
            return 0
        fi
    fi
    
    # Fallback: try to get from git directory name
    local git_root
    if git_root=$(git -C "$install_dir" rev-parse --show-toplevel 2>/dev/null); then
        local repo_name
        repo_name=$(basename "$git_root")
        if [[ -n "$repo_name" && "$repo_name" != "." ]]; then
            echo "$repo_name"
            return 0
        fi
    fi
    
    return 1
}

# Replace non-alphanumeric characters with hyphens, remove leading/trailing hyphens
sanitize_name() {
    local name="$1"
    echo "$name" | sed 's/[^a-zA-Z0-9]/-/g' | sed 's/^-*//; s/-*$//' | tr '[:upper:]' '[:lower:]'
}

generate_server_name() {
    local scope="$1"
    local install_dir="$2"
    local custom_name="$3"
    
    if [[ -n "$custom_name" ]]; then
        echo "$custom_name"
        return 0
    fi
    
    if [[ "$scope" == "global" ]]; then
        echo "$MCP_SERVER_NAME"
    else
        # For local installations, use priority system:
        # 1. Git repository name
        # 2. Folder name
        local project_name=""
        
        # Try git repo name first
        if project_name=$(get_git_repo_name "$install_dir"); then
            project_name=$(sanitize_name "$project_name")
            echo "${MCP_SERVER_NAME}-${project_name}"
            return 0
        fi
        
        # Fallback to folder name
        project_name=$(basename "$install_dir")
        project_name=$(sanitize_name "$project_name")
        
        if [[ -n "$project_name" && "$project_name" != "." ]]; then
            echo "${MCP_SERVER_NAME}-${project_name}"
        else
            # Last resort: use hash like before
            local dir_hash
            dir_hash=$(echo "$install_dir" | sha256sum | cut -c1-8)
            echo "${MCP_SERVER_NAME}-local-${dir_hash}"
        fi
    fi
}

find_available_port() {
    local start_port="${1:-8765}"
    local max_attempts=100
    local port=$start_port
    
    for ((i=0; i<max_attempts; i++)); do
        if ! netstat -tuln 2>/dev/null | grep -q ":$port "; then
            echo "$port"
            return 0
        fi
        ((port++))
    done
    
    echo "Error: Could not find available port starting from $start_port" >&2
    return 1
}

get_local_config_path() {
    local tool="$1"
    local install_dir="$2"
    
    case "$tool" in
        "cursor")
            echo "$install_dir/.cursor/mcp.json"
            ;;
        "windsurf")
            echo "$install_dir/.windsurf/mcp_config.json"
            ;;
        "claude-code")
            # Claude Code uses scope, not file path for local
            echo "local-scope"
            ;;
        *)
            echo "Error: Unknown tool: $tool" >&2
            return 1
            ;;
    esac
}

create_local_gandalf_script() {
    local install_dir="$1"
    local port="$2"
    local server_name="$3"
    
    local local_script="$install_dir/.gandalf/gandalf-local.sh"
    local local_dir="$install_dir/.gandalf"
    
    mkdir -p "$local_dir"
    
    cat > "$local_script" <<EOF
#!/bin/bash
# Local Gandalf MCP Server Script
# Generated for directory: $install_dir
# Server name: $server_name
# Port: $port

export GANDALF_ROOT="$GANDALF_ROOT"
export GANDALF_LOCAL_DIR="$install_dir"
export GANDALF_LOCAL_PORT="$port"
export GANDALF_SERVER_NAME="$server_name"
export PYTHONPATH="\$GANDALF_ROOT/server:\${PYTHONPATH:-}"

exec "\$GANDALF_ROOT/gandalf.sh" "\$@"
EOF
    
    chmod +x "$local_script"
    echo "$local_script"
}

update_local_registry() {
    local install_dir="$1"
    local server_name="$2"
    local port="$3"
    local tools="$4"
    
    local registry_file="$install_dir/.gandalf/registry.json"
    local registry_dir="$(dirname "$registry_file")"
    
    mkdir -p "$registry_dir"
    
    local temp_file
    temp_file=$(mktemp)
    
    # Create or update local registry
    if [[ -f "$registry_file" ]] && command -v jq &>/dev/null; then
        jq --arg name "$server_name" \
           --arg dir "$install_dir" \
           --arg port "$port" \
           --arg tools "$tools" \
           --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
           '.installations[$name] = {
               "install_dir": $dir,
               "port": $port,
               "tools": $tools,
               "installed_at": $timestamp,
               "gandalf_root": "'$GANDALF_ROOT'",
               "status": "active"
           }' "$registry_file" > "$temp_file"
    else
        cat > "$temp_file" <<EOF
{
    "installations": {
        "$server_name": {
            "install_dir": "$install_dir",
            "port": "$port",
            "tools": "$tools",
            "installed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
            "gandalf_root": "$GANDALF_ROOT",
            "status": "active"
        }
    }
}
EOF
    fi
    
    mv "$temp_file" "$registry_file"
    echo "Updated local registry: $registry_file"
}

# Command line parsing
usage() {
    cat <<'EOF'
Usage: gandalf.sh install [OPTIONS]

Configure MCP server for Cursor, Claude Code, and Windsurf.

Options:
    -f, --force             Force setup (overwrite existing config)
    --tool <tool>           Force specific agentic tool (cursor|claude-code|windsurf)
    --local                 Install to current directory (default: global)
    --server-name <name>    Custom server name (default: gandalf or gandalf-{project})
    --port <port>           Custom port for local server (default: auto-assigned)
    -h, --help              Show this help
    --skip-test             Skip connectivity testing
    --wait-time <seconds>   Wait time for tool recognition (default: 1)
    --debug                 Enable debug logging

Examples:   
    gandalf.sh install                      # Install globally (auto-detect tools)
    gandalf.sh install --local              # Install to current directory
    gandalf.sh install -f                   # Force overwrite existing config
    gandalf.sh install --tool cursor        # Force Cursor installation only
    gandalf.sh install --debug              # Enable debug output

EOF
}

parse_arguments() {
    FORCE_TOOL=""
    SKIP_TEST="false"
    DEBUG="false"
    WAIT_TIME="$DEFAULT_WAIT_TIME"
    LOCAL_INSTALL="false"
    CUSTOM_SERVER_NAME=""
    CUSTOM_PORT=""

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
        --local)
            LOCAL_INSTALL="true"
            shift
            ;;
        --server-name)
            CUSTOM_SERVER_NAME="$2"
            if [[ -z "$CUSTOM_SERVER_NAME" ]]; then
                echo "Error: --server-name cannot be empty" >&2
                return 1
            fi
            shift 2
            ;;
        --port)
            CUSTOM_PORT="$2"
            if ! [[ "$CUSTOM_PORT" =~ ^[0-9]+$ ]] || [[ "$CUSTOM_PORT" -lt 1024 ]] || [[ "$CUSTOM_PORT" -gt 65535 ]]; then
                echo "Error: --port must be a number between 1024 and 65535" >&2
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

    local scope="global"
    local install_dir=""
    
    if [[ "$LOCAL_INSTALL" == "true" ]]; then
        scope="local"
        install_dir="$(pwd)"
    fi
    
    echo "Starting Gandalf MCP Server installation..."
    echo "Scope: $scope"
    [[ "$scope" == "local" ]] && echo "Install directory: $install_dir"

    if ! verify_prerequisites; then
        exit 1
    fi

    local gandalf_home
    if [[ "$scope" == "local" ]]; then
        gandalf_home="$install_dir/.gandalf"
        mkdir -p "$gandalf_home"/{logs,cache,config,exports,backups}
        echo "Created local Gandalf directory: $gandalf_home"
    else
        gandalf_home="$GANDALF_HOME"
        if ! create_directory_structure "$gandalf_home"; then
            exit 1
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

    local server_name
    server_name=$(generate_server_name "$scope" "$install_dir" "$CUSTOM_SERVER_NAME")
    echo "Server name: $server_name"

    local port=""
    if [[ "$scope" == "local" ]]; then
        port="${CUSTOM_PORT:-$(find_available_port)}"
        echo "Assigned port: $port"
    fi

    if [[ "$scope" == "global" ]]; then
        if ! create_installation_state "$GANDALF_ROOT" "unknown" "$detected_tool" "$FORCE_TOOL"; then
            echo "Error: Failed to create installation state" >&2
            exit 1
        fi
    fi

    if ! install_for_all_tools "$server_name" "$GANDALF_ROOT" "$detected_tool"; then
        echo "Error: Installation failed for all tools" >&2
        exit 1
    fi

    if [[ "$scope" == "local" ]]; then
        local tool_list="cursor,claude-code,windsurf"
        update_local_registry "$install_dir" "$server_name" "$port" "$tool_list"
        
        if ! create_local_rules_files "$install_dir"; then
            echo "Warning: Local rules file creation failed, but continuing..." >&2
        fi
    fi

    if [[ "$scope" == "global" ]]; then
        if ! create_rules_files; then
            echo "Warning: Rules file creation failed, but continuing..." >&2
        fi
    fi

    # Connectivity testing
    if [[ "$SKIP_TEST" != "true" ]]; then
        if ! check_server_connectivity "$DEFAULT_MAX_ATTEMPTS" "$WAIT_TIME" "$detected_tool"; then
            echo "Warning: Server connectivity test failed, but installation completed" >&2
        fi
    else
        echo "Skipping connectivity tests"
    fi

    echo "Gandalf MCP Server installation completed successfully!"

    # Show appropriate summary based on scope
    if [[ "$scope" == "global" ]]; then
        cat <<EOF

Global MCP Configuration Complete!

Configuration Summary:
    Primary tool: $detected_tool
    Server Name: $server_name
    Installation Type: Global (works in all projects)
    Gandalf Home: $gandalf_home

Next Steps:
    1. Restart your configured tools completely
    2. Wait a few moments after restart for MCP server initialization
    3. Test MCP integration by asking: "What files are in my project?"

EOF
    else
        cat <<EOF

Local MCP Configuration Complete!

Configuration Summary:
    Primary tool: $detected_tool
    Server Name: $server_name
    Installation Type: Local (directory-specific)
    Install Directory: $install_dir
    Local Port: $port
    Gandalf Home: $gandalf_home

Local Configuration Files Created:
    - Cursor: $install_dir/.cursor/mcp.json
    - Windsurf: $install_dir/.windsurf/mcp_config.json
    - Claude Code: Local scope configuration
    - Registry: $install_dir/.gandalf/registry.json

Local Rules Files Created:
    - Cursor: $install_dir/.cursor/rules/gandalf-rules.mdc
    - Claude Code: $install_dir/.claude/local_settings.json
    - Windsurf: $install_dir/.windsurf/rules.md

Next Steps:
    1. Open your IDE in the project directory: $install_dir
    2. Restart your configured tools completely
    3. Wait a few moments after restart for MCP server initialization
    4. Test MCP integration by asking: "What files are in my project?"

Note: This installation only works when your IDE is opened in this specific directory.

EOF
    fi

    cat <<EOF
Troubleshooting:
    - If MCP tools aren't available, restart your tool and wait 30 seconds
    - Run with --debug for detailed logging
    - Use --skip-test for faster installation without connectivity tests

EOF
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
