#!/bin/bash
################################################################################
# Gandalf MCP Server Installation Script
#
# This script configures the Gandalf MCP server for agentic tool integration.
# It handles MCP-specific setup, agentic tool detection, and server configuration.
#
# Prerequisites: Run system setup first if needed:
#   - For development environment: ../../scripts/setup.sh
#   - For minimal requirements: Python 3.10+, Git
#
# Usage: ./install.sh [repo_path] [OPTIONS]
################################################################################

set -eo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
export GANDALF_HOME="${GANDALF_HOME:-$HOME/.${MCP_SERVER_NAME}}"

SERVER_DIR="$GANDALF_ROOT/server/src"
SERVER_SCRIPT="$SERVER_DIR/main.py"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"

ensure_gandalf_directory() {
    local gandalf_home="$GANDALF_HOME"

    if [[ ! -d "$gandalf_home" ]]; then
        echo "Setting up $gandalf_home directory structure..."
        mkdir -p "$gandalf_home"/{cache,exports,backups,config}
        chmod 755 "$gandalf_home"
        find "$gandalf_home" -type d -exec chmod 755 {} \;
        echo "Created $gandalf_home directory structure"
    else
        mkdir -p "$gandalf_home"/{cache,exports,backups,config}
        echo "Verified $gandalf_home directory structure"
    fi

    return 0
}

create_installation_state() {
    local gandalf_home="$GANDALF_HOME"
    local gandalf_root="${1:-}"
    local gandalf_version="${2:-}"
    local detected_tool="${3:-}"
    local force_tool="${4:-}"
    local repo_root="${5:-}"
    local server_name="${6:-$MCP_SERVER_NAME}"

    local state_file="$gandalf_home/installation-state"

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
GANDALF_HOME="$gandalf_home"
EOF

    chmod 644 "$state_file"
    echo "Installation state saved to: $state_file"
    return 0
}

update_installation_state() {
    local gandalf_home="$GANDALF_HOME"
    local cursor_success="${1:-false}"
    local claude_success="${2:-false}"
    local windsurf_success="${3:-false}"

    local state_file="$gandalf_home/installation-state"

    if [[ ! -f "$state_file" ]]; then
        echo "Warning: Installation state file not found: $state_file"
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

    echo "Updated installation state: $state_file"

    # Update the simple registry
    update_registry "$cursor_success" "$claude_success" "$windsurf_success"

    return 0
}

update_registry() {
    local cursor_success="${1:-false}"
    local claude_success="${2:-false}"
    local windsurf_success="${3:-false}"

    echo "Updating agentic tool registry..."

    # Register Cursor if successful
    if [[ "$cursor_success" == "true" ]]; then
        "$SCRIPTS_DIR/registry.sh" auto-register cursor
    fi

    # Register Claude Code if successful
    if [[ "$claude_success" == "true" ]]; then
        "$SCRIPTS_DIR/registry.sh" auto-register claude-code
    fi

    # Register Windsurf if successful
    if [[ "$windsurf_success" == "true" ]]; then
        "$SCRIPTS_DIR/registry.sh" auto-register windsurf
    fi
}

detect_agentic_tool() {
    "$SCRIPTS_DIR/registry.sh" detect
}

usage() {
    cat <<EOF
Usage: gandalf.sh install [OPTIONS]

Configure global MCP server for Cursor, Claude Code, and Windsurf (auto-detected).

Prerequisites:
    For full development environment: ../../scripts/setup.sh
    For minimal requirements: Python 3.10+, Git

Options:
    -f, --force             Force setup (overwrite existing config)
    -r, --reset             Reset/remove existing server before installing
    --tool <tool>           Force specific agentic tool (cursor|claude-code|windsurf)
    -h, --help              Show this help
    --skip-test             Skip connectivity testing (faster install)
    --wait-time <seconds>   Wait time for agentic tool recognition (default: 1)

Examples:   
    gandalf.sh install                      # Install globally (auto-detect agentic tools)
    gandalf.sh install -f                   # Force overwrite existing global config
    gandalf.sh install -r                   # Reset ALL agentic tool configs and install fresh
    gandalf.sh install --tool cursor        # Force Cursor installation only
    gandalf.sh install --tool claude-code   # Force Claude Code installation only
    gandalf.sh install --tool windsurf      # Force Windsurf installation only

Reset Behavior:
-r, --reset             Resets configurations for ALL agentic tools (Cursor, Claude Code, and Windsurf)
                        This ensures a truly clean restart across all environments

What this does:
    1. Verifies system requirements (Python 3.10+, Git, project structure)
    2. Detects your agentic tool environment (Cursor, Claude Code, or Windsurf)
    3. (Optional) Resets existing server configuration if reset flag used
    4. Installs global $MCP_SERVER_NAME MCP server for all detected agentic tools
    5. Configures dynamic "$MCP_SERVER_NAME" server in each agentic tool
    6. Updates agentic tool MCP configuration globally
    7. Creates global $MCP_SERVER_NAME rules files for each tool
    8. Tests server connectivity with retry mechanism

Global Installation:
    - Gandalf is installed once and works everywhere
    - No per-project configuration needed
    - Rules are applied globally across all projects
    - MCP server configuration is shared across all workspaces

For system-wide development setup, run: ../../scripts/setup.sh

EOF
}

detect_agentic_tool_by_database() {
    # Check for Cursor databases (more reliable indicator)
    local cursor_workspace_storage="$HOME/Library/Application Support/Cursor/workspaceStorage"
    if [[ -d "$cursor_workspace_storage" ]] && [[ -n "$(find "$cursor_workspace_storage" -name "*.vscdb" -o -name "*.db" 2>/dev/null | head -1)" ]]; then
        echo "cursor"
        return 0
    fi

    # Check for Claude Code storage
    local claude_storage_paths=("$HOME/.claude" "$HOME/.config/claude")
    for claude_path in "${claude_storage_paths[@]}"; do
        if [[ -d "$claude_path" ]] && [[ -n "$(find "$claude_path" -type f 2>/dev/null | head -1)" ]]; then
            echo "claude-code"
            return 0
        fi
    done

    # Fallback to environment-based detection
    detect_agentic_tool
}

check_config_exists() {
    local config_file="$1"
    if [[ ! -f "$config_file" ]]; then
        echo "MCP config file not found: $config_file"
        return 1
    fi
    return 0
}

remove_server() {
    local config_file="$1"
    local server_name="$2"
    local tool="${3:-}"

    if ! check_config_exists "$config_file"; then
        echo "Cannot remove server: config file not found"
        return 1
    fi

    echo "Removing $server_name server..."

    if ! jq -e --arg name "$server_name" '.mcpServers | has($name)' "$config_file" >/dev/null 2>&1; then
        echo "$server_name server not found in configuration"
        echo "No action needed; server was already removed or never configured"
        return 0
    fi

    local temp_file=$(mktemp)
    if jq --arg name "$server_name" 'del(.mcpServers[$name])' "$config_file" >"$temp_file"; then
        mv "$temp_file" "$config_file"
        echo "Successfully removed $server_name server"
        restart_server "$server_name" "$tool"
    else
        rm -f "$temp_file"
        echo "Error removing $server_name server"
        return 1
    fi
}

restart_server() {
    local server_name="$1"
    local tool="${2:-}"

    echo "Restarting $server_name MCP server..."

    # Kill gandalf MCP server processes
    local MCP_PIDS=$(pgrep -f "$server_name.*main.py" || echo "")
    if [[ -n "$MCP_PIDS" ]]; then
        echo "Found $server_name MCP server processes: $MCP_PIDS"
        echo "Stopping $server_name MCP server..."
        echo "$MCP_PIDS" | xargs kill 2>/dev/null || true
        sleep 1

        # Check if any processes are still running and force kill if needed
        local remaining_pids=$(pgrep -f "$server_name.*main.py" || echo "")
        if [[ -n "$remaining_pids" ]]; then
            echo "Force stopping remaining MCP server processes..."
            echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
        echo "$server_name MCP server processes stopped"
    else
        echo "$server_name MCP server is not running"
    fi

    # Tool-specific restart handling
    if [[ -n "$tool" ]]; then
        case "$tool" in
        "cursor")
            echo "Cursor will automatically restart the MCP server with new configuration"
            if pgrep -f "Cursor" >/dev/null 2>&1; then
                echo "Note: For immediate effect, consider restarting Cursor completely"
            fi
            ;;
        "claude-code")
            echo "Claude Code will automatically restart the MCP server with new configuration"
            if pgrep -f "claude" >/dev/null 2>&1; then
                echo "Note: For immediate effect, consider restarting Claude Code completely"
            fi
            ;;
        *)
            echo "$tool will automatically restart the MCP server with new configuration"
            ;;
        esac
    else
        echo "Tool will automatically restart the MCP server with new configuration" # This sounds weird
        echo "Make sure your agentic tool is running and the MCP server was configured"
    fi

    sleep 2
}

perform_comprehensive_reset() {
    local server_name="$1"
    local detected_tool="${2:-}"

    echo "Performing comprehensive reset for all agentic tool environments..."
    echo "Server name: $server_name"
    echo ""

    # Reset for Cursor
    local cursor_config_file="$HOME/.cursor/mcp.json"
    if [[ -f "$cursor_config_file" ]]; then
        echo "Resetting Cursor configuration..."
        if [[ -f "$cursor_config_file" ]]; then
            local backup_file="${cursor_config_file}.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$cursor_config_file" "$backup_file"
            echo "Cursor backup created: $backup_file"
        fi
        remove_server "$cursor_config_file" "$server_name" "cursor"
        cat <<EOF
Cursor reset completed

EOF
    else
        cat <<EOF
No Cursor configuration found to reset

EOF
    fi

    local claude_config_file="$HOME/.claude/mcp.json"
    if [[ -f "$claude_config_file" ]]; then
        echo "Resetting Claude Code configuration..."
        if [[ -f "$claude_config_file" ]]; then
            local backup_file="${claude_config_file}.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$claude_config_file" "$backup_file"
            echo "Claude Code backup created: $backup_file"
        fi
        remove_server "$claude_config_file" "$server_name" "claude-code"
        cat <<EOF
Claude Code reset completed

EOF
    else
        cat <<EOF
No Claude Code configuration found to reset

EOF
    fi

    # Kill any remaining MCP server processes
    echo "Ensuring all $server_name MCP server processes are stopped..."
    restart_server "$server_name" "$detected_tool"

    cat <<EOF

Comprehensive reset completed successfully!
- All agentic tool configurations have been reset
- All MCP server processes have been stopped
- Configuration backups have been created

Proceeding with fresh installation for $detected_tool...

EOF
}

get_python_executable() {
    local venv_python="$GANDALF_ROOT/.venv/bin/python3"
    if [[ -f "$venv_python" ]]; then
        echo "$venv_python"
    else
        echo "python3"
    fi
}

check_python_version() {
    local min_version="3.10"

    if ! command -v python3 &>/dev/null; then
        echo "Error: Python 3 not found"
        return 1
    fi

    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)

    if [[ -z "$python_version" ]]; then
        echo "Error: Could not determine Python version"
        return 1
    fi

    if printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1 | grep -q "^$min_version$"; then
        echo "Python $python_version found"
        return 0
    else
        echo "Error: Python $python_version found, but $min_version+ required"
        return 1
    fi
}

check_python_requirements() {
    local requirements_file="$GANDALF_ROOT/server/requirements.txt"

    if [[ ! -f "$requirements_file" ]]; then
        echo "No requirements.txt found"
        return 0
    fi

    local python_cmd
    python_cmd=$(get_python_executable)

    local missing_packages=""

    while IFS= read -r line; do
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

        local package_name
        package_name=$(echo "$line" | sed 's/[><=!].*//' | tr -d '[:space:]')

        # Map pip package names to Python import names
        local import_name="$package_name"
        case "$package_name" in
        "PyYAML") import_name="yaml" ;;
        esac

        local is_optional=false
        if echo "$line" | grep -q "# optional" || [[ "$package_name" =~ ^pytest ]]; then
            is_optional=true
        fi

        if ! "$python_cmd" -c "import $import_name" &>/dev/null; then
            if [[ "$is_optional" != "true" ]]; then
                if [[ -z "$missing_packages" ]]; then
                    missing_packages="$package_name"
                else
                    missing_packages="$missing_packages $package_name"
                fi
            fi
        fi
    done <"$requirements_file"

    if [[ -n "$missing_packages" ]]; then
        echo "Error: Missing required Python packages: $missing_packages"
        return 1
    fi

    return 0
}

check_git() {
    if ! command -v git &>/dev/null; then
        echo "Error: Git not found"
        return 1
    fi
    return 0
}

check_pip() {
    if ! command -v pip3.10 &>/dev/null; then
        echo "Error: pip3.10 not found"
        return 1
    fi
    return 0
}

check_gandalf_structure() {
    local required_dirs=("server" "scripts")
    local required_files=("server/src/main.py" "gandalf.sh")

    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$GANDALF_ROOT/$dir" ]]; then
            echo "Error: Missing required directory: $dir/"
            return 1
        fi
    done

    for file in "${required_files[@]}"; do
        if [[ ! -f "$GANDALF_ROOT/$file" ]]; then
            echo "Error: Missing required file: $file"
            return 1
        fi
    done

    return 0
}

verify_prerequisites() {
    echo "Verifying system requirements..."

    local failed=false

    # Check core dependencies
    if ! check_python_version; then
        failed=true
    fi

    if ! check_git; then
        failed=true
    fi

    if ! check_pip; then
        failed=true
    fi

    # Check Gandalf project structure
    if ! check_gandalf_structure; then
        failed=true
    fi

    # Check Python requirements
    if ! check_python_requirements; then
        echo "Install with: pip install -r $GANDALF_ROOT/server/requirements.txt"
        failed=true
    fi

    # Check optional tools
    if ! command -v jq &>/dev/null; then
        echo "Warning: jq not found (optional, but recommended for JSON processing)"
    fi

    if [[ "$failed" == "true" ]]; then
        cat <<EOF

System Requirements Check Failed!

System Requirements:
    - Python 3.10+: $(python3 --version 2>/dev/null || echo "Not found")
    - pip3.10: $(pip3.10 --version 2>/dev/null || echo "Not found")
    - Git: $(git --version 2>/dev/null | head -1 || echo "Not found")

Installation Options:

1. Full Development Environment (Recommended):
    Run the system setup script to install all development tools:
    ../../scripts/setup.sh

2. Minimal Installation:
    Install missing tools manually:
    - Python 3.10+: brew install python3 (macOS) or apt install python3 (Linux)
    - pip3.10: python3 -m ensurepip --upgrade
    - Git: brew install git (macOS) or apt install git (Linux)

3. Python Dependencies Only:
    pip3.10 install -r $GANDALF_ROOT/server/requirements.txt

Optional: Add gandalf.sh to your PATH for global access:
    echo 'export PATH="$GANDALF_ROOT:\$PATH"' >> ~/.bashrc
    source ~/.bashrc
EOF
        cat <<EOF

Suggestion: Run '../../scripts/setup.sh' for complete development environment setup
EOF
        exit 1
    fi

    chmod +x "$GANDALF_ROOT/gandalf.sh" "$GANDALF_ROOT/scripts"/* "$SERVER_SCRIPT" 2>/dev/null || true

    # Test MCP server using the correct Python executable
    local python_exec
    python_exec=$(get_python_executable)
    echo "Testing MCP server with Python: $python_exec"

    if ! "$python_exec" "$SERVER_SCRIPT" --help >/dev/null 2>&1; then
        cat <<EOF
Error: MCP server test failed
This may be due to missing Python dependencies.

Troubleshooting Steps:

1. Install missing dependencies:
    pip3.10 install -r $GANDALF_ROOT/server/requirements.txt

2. If using virtual environment:
    source $GANDALF_ROOT/.venv/bin/activate
    pip3.10 install -r $GANDALF_ROOT/server/requirements.txt

3. For complete environment setup:
    ../../scripts/setup.sh
EOF
        exit 1
    fi

    echo "Prerequisites verified successfully!"
}

update_cursor_config() {
    local config_file="$1"
    local server_name="$2"
    local mcp_script="$3"

    mkdir -p "$(dirname "$config_file")"

    if [[ -f "$config_file" ]]; then
        cp "$config_file" "$config_file.backup.$(date +%s)"
        temp_file=$(mktemp)

        if command -v jq &>/dev/null; then
            jq --arg name "$server_name" \
                --arg cmd "$mcp_script" \
                '.mcpServers[$name] = {
                    "command": $cmd,
                    "args": ["run"]
                }' "$config_file" >"$temp_file"
            mv "$temp_file" "$config_file"
        else
            # Fallback for no jq, most people probably won't have it
            cat >"$config_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
            "command": "$mcp_script",
            "args": ["run"]
        }
    }
}
EOF
        fi
    else
        cat >"$config_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
            "command": "$mcp_script",
            "args": ["run"]
        }
    }
}
EOF
    fi

    echo "Updated Cursor configuration: $server_name"
}

update_claude_code_config() {
    local config_file="$1"
    local server_name="$2"
    local gandalf_root="$3"

    # Claude CLI is required for proper MCP management
    if ! command -v claude >/dev/null 2>&1; then
        echo "Error: claude CLI not found. Please install Claude Code first."
        return 1
    fi

    # Clean slate; remove any existing configurations
    claude mcp remove "$server_name" -s local 2>/dev/null || true
    claude mcp remove "$server_name" -s user 2>/dev/null || true

    # Install globally so it works everywhere; no need to reinstall per project
    echo "Adding $server_name MCP server with global scope..."
    # Use the shell script wrapper like Cursor does
    if claude mcp add "$server_name" "$gandalf_root/gandalf.sh" -s user "run" \
        -e "PYTHONPATH=$gandalf_root/server" \
        -e "CLAUDECODE=1" \
        -e "CLAUDE_CODE_ENTRYPOINT=cli"; then
        echo "Updated Claude Code configuration: $server_name (global scope)"
        return 0
    else
        echo "Failed to add $server_name MCP server via Claude CLI"
        return 1
    fi
}

update_windsurf_config() {
    local config_file="$1"
    local server_name="$2"
    local mcp_script="$3"

    mkdir -p "$(dirname "$config_file")"

    # Always create/replace with correct Windsurf format
    # Windsurf uses "mcpServers" as the top-level key
    cat >"$config_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
            "command": "$mcp_script",
            "args": ["run"]
        }
    }
}
EOF

    echo "Updated Windsurf MCP config: $config_file"
}

install_for_claude_code() {
    local server_name="$1"
    local gandalf_root="$2"

    echo "Installing Gandalf MCP for Claude Code..."

    # One-time global installation; works in all projects after this
    if update_claude_code_config "" "$server_name" "$gandalf_root"; then
        echo "PASS: Claude Code MCP configuration installed successfully!"
        echo "Server configured with global scope; available in all projects"
        return 0
    else
        echo "FAIL: Failed to install Claude Code MCP configuration"
        echo "Make sure Claude Code is installed and the 'claude' CLI is available"
        return 1
    fi
}

install_for_cursor() {
    local server_name="$1"
    local gandalf_root="$2"

    echo "Installing Gandalf MCP for Cursor..."

    local config_file="$HOME/.cursor/mcp.json"
    local mcp_script="$gandalf_root/gandalf.sh"

    update_cursor_config "$config_file" "$server_name" "$mcp_script"

    echo "Cursor MCP configuration installed successfully!"
    return 0
}

install_for_windsurf() {
    local server_name="$1"
    local gandalf_root="$2"

    echo "Installing Gandalf MCP for Windsurf..."

    local config_file="$HOME/.codeium/windsurf/mcp_config.json"
    local mcp_script="$gandalf_root/gandalf.sh"
    local config_dir="$(dirname "$config_file")"

    # Create config directory if it doesn't exist
    mkdir -p "$config_dir"

    # Create or update Windsurf MCP configuration
    update_windsurf_config "$config_file" "$server_name" "$mcp_script"

    echo "Windsurf MCP configuration installed successfully!"
    return 0
}

create_rules_file() {
    echo "Creating global rules files for all supported tools..."

    # Always create the necessary directories
    mkdir -p "$HOME/.cursor/rules"
    mkdir -p "$HOME/.claude"
    mkdir -p "$HOME/.windsurf"

    # Allow tests to override the spec directory location
    local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"
    local source_rules_file="$spec_dir/$MCP_SERVER_NAME-rules.md"

    if [[ ! -f "$source_rules_file" ]]; then
        echo "Warning: Source rules file not found: $source_rules_file"
        echo "Skipping rules file creation. Install will continue without rules files."
        echo "Rules files can be created later by running: ./gandalf.sh install -f"
        echo "Created directory structure for future rules files"
        return 0
    fi

    # Create global Cursor rules
    if ! create_global_cursor_rules; then
        echo "Warning: Failed to create Cursor rules, continuing..."
    fi

    # Create global Claude Code rules
    if ! create_global_claude_code_rules; then
        echo "Warning: Failed to create Claude Code rules, continuing..."
    fi

    # Create global Windsurf rules
    if ! create_global_windsurf_rules; then
        echo "Warning: Failed to create Windsurf rules, continuing..."
    fi
}

create_global_cursor_rules() {
    local global_rules_dir="$HOME/.cursor/rules"
    local rules_file="$global_rules_dir/$MCP_SERVER_NAME-rules.mdc"

    # Allow tests to override the spec directory location
    local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"
    local source_rules_file="$spec_dir/$MCP_SERVER_NAME-rules.md"

    mkdir -p "$global_rules_dir"

    if [[ -f "$rules_file" ]] && [[ "$FORCE" != "true" ]] && [[ "$RESET" != "true" ]]; then
        echo "Global Cursor rules file already exists: $rules_file"
        echo "Use -f to force overwrite or -r to reset and reinstall"
        return 0
    fi

    if [[ ! -f "$source_rules_file" ]]; then
        echo "Source rules file not found: $source_rules_file"
        return 1
    fi

    cp "$source_rules_file" "$rules_file"
    echo "Created global Cursor rules file: $rules_file"
    echo "Note: Cursor will use these rules globally across all projects"
}

create_global_claude_code_rules() {
    local global_claude_dir="$HOME/.claude"
    local rules_file="$global_claude_dir/global_settings.json"

    # Allow tests to override the spec directory location
    local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"
    local source_rules_file="$spec_dir/$MCP_SERVER_NAME-rules.md"

    mkdir -p "$global_claude_dir"

    if [[ ! -f "$source_rules_file" ]]; then
        echo "Source rules file not found: $source_rules_file"
        return 1
    fi

    # Read the source rules content and escape for JSON properly
    local rules_content
    rules_content=$(cat "$source_rules_file")

    # Use Python to properly escape JSON content if available, otherwise use sed
    if command -v python3 >/dev/null 2>&1; then
        rules_content=$(python3 -c "
import json
import sys
content = '''$rules_content'''
print(json.dumps(content))
")
    else
        # Fallback to sed-based escaping
        rules_content=$(echo "$rules_content" |
            sed 's/\\/\\\\/g' |
            sed 's/"/\\"/g' |
            sed ':a;N;$!ba;s/\n/\\n/g' |
            sed 's/\t/\\t/g' |
            sed 's/\r/\\r/g')
        rules_content="\"$rules_content\""
    fi

    # Create or update global Claude Code settings
    if [[ -f "$rules_file" ]]; then
        # File exists, check if we should overwrite
        if [[ "$FORCE" != "true" ]] && [[ "$RESET" != "true" ]]; then
            echo "Global Claude Code settings file already exists: $rules_file"
            echo "Use -f to force overwrite or -r to reset and reinstall"
            return 0
        fi

        # Backup existing settings
        cp "$rules_file" "$rules_file.backup.$(date +%s)"
        echo "Backed up existing global Claude Code settings"
    fi

    # Create new global settings.json with gandalf rules using proper JSON formatting
    cat >"$rules_file" <<EOF
{
    "permissions": {
        "allow": [
            "Bash(*)",
            "Edit(*)",
            "Read(*)",
            "Write(*)"
        ]
    },
    "gandalfRules": $rules_content
}
EOF

    echo "Created global Claude Code rules in settings: $rules_file"
    echo "Note: Claude Code will use these rules globally across all projects"
}

create_global_windsurf_rules() {
    local windsurf_global_rules="$HOME/.windsurf/global_rules.md"

    # Allow tests to override the spec directory location
    local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"
    local source_rules_file="$spec_dir/$MCP_SERVER_NAME-rules.md"

    mkdir -p "$HOME/.windsurf"

    if [[ ! -f "$source_rules_file" ]]; then
        echo "Source rules file not found: $source_rules_file"
        return 1
    fi

    # Create/update global rules for Windsurf
    if [[ -f "$windsurf_global_rules" ]] && [[ "$FORCE" != "true" ]] && [[ "$RESET" != "true" ]]; then
        echo "Windsurf global rules file already exists: $windsurf_global_rules"
        echo "Use -f to force overwrite or -r to reset and reinstall"
        return 0
    fi

    # For Windsurf, we'll create a comprehensive global rules file
    # Windsurf has a 6000 character limit, so we need to truncate if necessary
    local rules_content
    rules_content=$(cat "$source_rules_file")
    local char_count=${#rules_content}

    if [[ $char_count -gt 6000 ]]; then
        echo "Warning: Rules content ($char_count chars) exceeds Windsurf limit (6000 chars)"
        echo "Truncating rules content for Windsurf compatibility..."

        # Reserve space for the truncation message (be more conservative)
        local truncation_message="

# Note: Content truncated to fit Windsurf 6000 character limit
# Full rules available in Cursor global rules and Claude Code global settings"
        local message_length=${#truncation_message}
        local max_content_length=$((6000 - message_length - 5)) # Extra buffer for safety

        rules_content=$(echo "$rules_content" | head -c "$max_content_length")
        rules_content="$rules_content$truncation_message"

        # Double-check the final size and trim more if needed
        local final_length=${#rules_content}
        if [[ $final_length -gt 6000 ]]; then
            local excess=$((final_length - 6000))
            local adjusted_content_length=$((max_content_length - excess))
            rules_content=$(echo "$rules_content" | head -c "$adjusted_content_length")
            rules_content="$rules_content$truncation_message"
        fi
    fi

    echo "$rules_content" >"$windsurf_global_rules"
    echo "Created Windsurf global rules: $windsurf_global_rules"
    echo "Character count: ${#rules_content}/6000"
    echo "Note: Windsurf will use these rules globally across all projects"
}

show_test_results() {
    local attempt="$1"
    local script_test="$2"
    local process_test="$3"
    local init_test="$4"

    echo "  Attempt $attempt: Script $([ "$script_test" = true ] && echo "PASS" || echo "FAIL") | Process $([ "$process_test" = true ] && echo "PASS" || echo "FAIL") | Server $([ "$init_test" = true ] && echo "PASS" || echo "FAIL")"
}

show_connectivity_failure() {
    local max_attempts="$1"

    cat <<EOF
Server connectivity test failed after $max_attempts attempts.
This may be normal if Cursor hasn't fully loaded the MCP configuration yet.
The server should work correctly once Cursor recognizes the configuration.
If you are using Cursor, you can try restarting Cursor to see if that fixes the issue.
EOF
}

show_installation_warning() {
    cat <<EOF
Installation completed with warnings:
    MCP server configuration has been updated
    Connectivity test failed, but this is often temporary
    Restart Cursor completely for best results
    Wait 30 seconds after restart before testing MCP tools
EOF
}

test_server_connectivity() {
    local max_attempts="${1:-3}"
    local wait_time="${2:-1}"
    local repo_root="$3"
    local tool="${4:-cursor}"

    echo "Testing server connectivity for $tool..."
    echo "Waiting ${wait_time}s for $tool to recognize MCP server..."

    sleep "$wait_time"

    local server_working=false
    local attempt=1
    local python_exec
    python_exec=$(get_python_executable)

    pushd "$repo_root" >/dev/null || return 1

    while [[ $attempt -le $max_attempts ]]; do
        echo "Connectivity test attempt $attempt/$max_attempts..."

        local script_test=false
        local process_test=false
        local init_test=false
        local tools_test=false

        local mcp_process_count=$(pgrep -f "$MCP_SERVER_NAME.*main.py" | wc -l | tr -d ' \n\r' || echo "0")
        [[ "$mcp_process_count" =~ ^[0-9]+$ ]] || mcp_process_count=0
        if [[ $mcp_process_count -gt 0 ]]; then
            process_test=true
            echo "Found $mcp_process_count MCP server process(es) running"
        fi

        if timeout 3 "$python_exec" "$SERVER_SCRIPT" --help >/dev/null 2>&1; then
            script_test=true
        fi

        # Set environment variables based on tool
        local env_vars=""
        if [[ "$tool" == "claude-code" ]]; then
            export CLAUDECODE=1
            export CLAUDE_CODE_ENTRYPOINT=cli
        fi

        if init_response=$(echo '{"jsonrpc": "2.0", "method": "initialize", "id": 1}' | timeout 5 "$python_exec" "$SERVER_SCRIPT" 2>/dev/null); then
            if echo "$init_response" | grep -q '"protocolVersion"'; then
                init_test=true
            fi
        fi

        if tools_response=$(echo '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}' | timeout 5 "$python_exec" "$SERVER_SCRIPT" 2>/dev/null); then
            if echo "$tools_response" | grep -q '"tools"'; then
                tools_test=true
            fi
        fi

        show_test_results "$attempt" "$script_test" "$process_test" "$init_test"

        if [[ "$script_test" == true ]] && ([[ "$init_test" == true ]] || [[ "$tools_test" == true ]]); then
            server_working=true
            echo "Server connectivity test: PASSED"
            break
        fi

        if [[ $attempt -lt $max_attempts ]]; then
            echo "Waiting 3s before retry..."
            sleep 3
        fi

        ((attempt++))
    done

    popd >/dev/null

    if [[ "$server_working" == false ]]; then
        show_connectivity_failure "$max_attempts"
        echo ""
        show_installation_warning
        echo ""
        return 1
    fi

    return 0
}

wait_for_tool_recognition() {
    local config_file="$1"
    local server_name="$2"
    local wait_time="${3:-1}"
    local tool="${4:-cursor}"

    echo "Giving $tool time to recognize new MCP configuration..."

    local tool_process_name
    case "$tool" in
    "cursor")
        tool_process_name="Cursor"
        ;;
    "claude-code")
        tool_process_name="claude"
        ;;
    *)
        tool_process_name="$tool"
        ;;
    esac

    if pgrep -f "$tool_process_name" >/dev/null 2>&1; then
        echo "   $tool process detected - waiting ${wait_time}s for config reload"
        sleep "$wait_time"

        # Wait for MCP server to actually start with retries
        local max_attempts=5
        local attempt=1
        local mcp_server_started=false

        while [[ $attempt -le $max_attempts ]]; do
            local mcp_process_count=$(pgrep -f "$server_name.*main.py" | wc -l | tr -d ' \n\r' || echo "0")
            [[ "$mcp_process_count" =~ ^[0-9]+$ ]] || mcp_process_count=0

            if [[ $mcp_process_count -gt 0 ]]; then
                echo "MCP server process started successfully (${mcp_process_count} process(es))"
                mcp_server_started=true
                break
            else
                echo "Attempt $attempt/$max_attempts: MCP server not yet detected, waiting 3s..."
                sleep 3
                ((attempt++))
            fi
        done

        if [[ "$mcp_server_started" == "false" ]]; then
            echo "Warning: MCP server process not detected after ${max_attempts} attempts"
            echo "This is normal - server will start on first MCP tool use"
        fi
    else
        echo "$tool process not detected - configuration will be loaded on next start"
    fi

    return 0
}

# Parse arguments
FORCE=false
RESET=false
SKIP_TEST=false
WAIT_TIME=1
FORCE_TOOL=""

while [[ $# -gt 0 ]]; do
    case $1 in
    -f | --force)
        FORCE=true
        shift
        ;;
    -r | --reset)
        RESET=true
        shift
        ;;
    --tool)
        FORCE_TOOL="$2"
        if [[ "$FORCE_TOOL" != "cursor" && "$FORCE_TOOL" != "claude-code" && "$FORCE_TOOL" != "windsurf" ]]; then
            echo "Error: --tool must be 'cursor', 'claude-code', or 'windsurf'"
            exit 1
        fi
        shift 2
        ;;
    --skip-test)
        SKIP_TEST=true
        shift
        ;;
    --wait-time)
        WAIT_TIME="$2"
        shift 2
        ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        echo "Unknown option $1"
        usage
        exit 1
        ;;
    esac
done

# Verify prerequisites first
echo "Verifying system requirements..."
verify_prerequisites
echo "Prerequisites verified successfully!"

# Detect or use forced tool
if [[ -n "$FORCE_TOOL" ]]; then
    DETECTED_TOOL="$FORCE_TOOL"
    echo "Using forced tool: $DETECTED_TOOL"
else
    DETECTED_TOOL=$(detect_agentic_tool_by_database)

    # If no databases found, fall back to environment detection
    if [[ "$DETECTED_TOOL" == "${GANDALF_FALLBACK_TOOL:-cursor}" ]]; then
        echo "No conversation databases found, checking environment..."
        ENV_TOOL=$(detect_agentic_tool)
        if [[ "$ENV_TOOL" != "${GANDALF_FALLBACK_TOOL:-cursor}" ]]; then
            DETECTED_TOOL="$ENV_TOOL"
            echo "Environment detection found: $DETECTED_TOOL"
        else
            echo "Using database detection result: $DETECTED_TOOL"
        fi
    else
        echo "Database detection found: $DETECTED_TOOL"
    fi
fi

setup_gandalf_directory() {
    echo "Setting up ~/.gandalf directory structure..."
    ensure_gandalf_directory
    create_installation_state "$GANDALF_ROOT" "$GANDALF_SERVER_VERSION" "$DETECTED_TOOL" "$FORCE_TOOL" "$REPO_ROOT" "$SERVER_NAME"
}

# Install for all supported tools, not just detected one
install_for_all_tools() {
    local server_name="$1"
    local gandalf_root="$2"
    local primary_tool="$3"

    echo "Installing Gandalf MCP for all supported tools..."
    echo "Primary tool (detected): $primary_tool"
    echo ""

    local cursor_success=false
    local claude_success=false
    local windsurf_success=false

    # Always try to install for Cursor
    echo "=== Installing for Cursor IDE ==="
    if install_for_cursor "$server_name" "$gandalf_root"; then
        cursor_success=true
        echo "PASS: Cursor installation completed successfully"
    else
        echo "FAIL: Cursor installation failed or skipped"
    fi
    echo ""

    # Always try to install for Claude Code
    echo "=== Installing for Claude Code ==="
    if install_for_claude_code "$server_name" "$gandalf_root"; then
        claude_success=true
        echo "PASS: Claude Code installation completed successfully"
    else
        echo "FAIL: Claude Code installation failed or skipped"
    fi
    echo ""

    # Always try to install for Windsurf
    echo "=== Installing for Windsurf IDE ==="
    if install_for_windsurf "$server_name" "$gandalf_root"; then
        windsurf_success=true
        echo "PASS: Windsurf installation completed successfully"
    else
        echo "FAIL: Windsurf installation failed or skipped"
    fi
    echo ""

    # Update installation state using directory manager
    update_installation_state "$cursor_success" "$claude_success" "$windsurf_success"

    # Summary
    echo "=== Installation Summary ==="
    echo "Cursor tool:    $([ "$cursor_success" = true ] && echo "PASS: Configured" || echo "FAIL: Failed/Skipped")"
    echo "Claude Code tool:   $([ "$claude_success" = true ] && echo "PASS: Configured" || echo "FAIL: Failed/Skipped")"
    echo "Windsurf tool:      $([ "$windsurf_success" = true ] && echo "PASS: Configured" || echo "FAIL: Failed/Skipped")"
    echo "Primary tool:   $primary_tool"
    echo ""

    if [[ "$cursor_success" = true || "$claude_success" = true || "$windsurf_success" = true ]]; then
        echo "At least one tool was configured successfully!"
        return 0
    else
        echo "Warning: No tools were configured successfully"
        return 1
    fi
}

echo "Configuring global MCP installation..."

SERVER_NAME="$MCP_SERVER_NAME"
echo "Server name: $SERVER_NAME"

# Setup ~/.gandalf directory
setup_gandalf_directory

# Set config file and directory based on detected tool (for testing purposes)
case "$DETECTED_TOOL" in
"cursor")
    CONFIG_DIR="$HOME/.cursor"
    CONFIG_FILE="$CONFIG_DIR/mcp.json"
    ;;
"claude-code")
    CONFIG_DIR="$HOME/.claude"
    CONFIG_FILE="$CONFIG_DIR/mcp.json"
    ;;
"windsurf")
    CONFIG_DIR="$HOME/.codeium/windsurf"
    CONFIG_FILE="$CONFIG_DIR/mcp_config.json"
    ;;
*)
    echo "Error: Unsupported tool: $DETECTED_TOOL"
    exit 1
    ;;
esac

if [[ "$RESET" == "true" ]]; then
    perform_comprehensive_reset "$SERVER_NAME" "$DETECTED_TOOL"
fi

echo "Configuring global MCP settings for all supported tools..."

# Check if server already exists in primary tool
if [[ -f "$CONFIG_FILE" ]] && grep -q "\"$SERVER_NAME\"" "$CONFIG_FILE" 2>/dev/null; then
    if [[ "$FORCE" != "true" ]] && [[ "$RESET" != "true" ]]; then
        echo "Server '$SERVER_NAME' already configured in $DETECTED_TOOL. Use -f to force update or -r to reset and reinstall."
        echo "Note: This will still attempt to configure other tools."
    else
        if [[ "$FORCE" == "true" ]]; then
            echo "Force updating existing server configuration"
        fi
    fi
fi

# Install for all tools instead of just the detected one
if ! install_for_all_tools "$SERVER_NAME" "$GANDALF_ROOT" "$DETECTED_TOOL"; then
    echo "Warning: Some tool installations failed, but continuing..."
fi

echo "Creating global $MCP_SERVER_NAME rules files..."
create_rules_file

wait_for_tool_recognition "$CONFIG_FILE" "$SERVER_NAME" "$WAIT_TIME" "$DETECTED_TOOL"

if [[ "$SKIP_TEST" != "true" ]]; then
    # For testing, we'll use the current directory but this doesn't affect the global installation
    TEST_DIR="$(pwd -P)"
    if ! test_server_connectivity 3 "$WAIT_TIME" "$TEST_DIR" "$DETECTED_TOOL"; then
        echo "Warning: Server connectivity test failed, but installation completed"
        echo "The server may still work correctly in $DETECTED_TOOL - try using MCP tools"
    fi
else
    echo "Skipping connectivity tests (--skip-test flag used)"
fi

cat <<EOF

Global MCP Configuration Complete!

Configuration Summary:
    Primary tool: $DETECTED_TOOL
    Server Name: $SERVER_NAME
    Installation Type: Global (works in all projects)
    Gandalf Home: $HOME/.gandalf
    Global Rules Files Created:
        Cursor: $HOME/.cursor/rules/$SERVER_NAME-rules.mdc
        Claude Code: $HOME/.claude/global_settings.json
        Windsurf: $HOME/.windsurf/global_rules.md
    Reset Mode: $([[ "$RESET" == "true" ]] && echo "Comprehensive - ALL tool configurations reset" || echo "No reset performed")
    Installation: Multi-tool (attempts to configure all supported tools)

Tool Configuration Status:
$(
    # Read installation state to show results
    if [[ -f "$HOME/.gandalf/installation-state" ]]; then
        source "$HOME/.gandalf/installation-state" 2>/dev/null || true
        echo "    Cursor tool:      $([ "${CURSOR_INSTALLED:-false}" = "true" ] && echo "PASS: Configured Globally" || echo "FAIL: Failed/Not Available")"
        echo "    Claude Code tool:     $([ "${CLAUDE_CODE_INSTALLED:-false}" = "true" ] && echo "PASS: Configured Globally" || echo "FAIL: Failed/Not Available")"
        echo "    Windsurf tool:        $([ "${WIND_SURF_INSTALLED:-false}" = "true" ] && echo "PASS: Configured Globally" || echo "FAIL: Failed/Not Available")"
    else
        echo "    Status:          Installation state file not found"
    fi
)

Gandalf Directory Structure:
    ~/.gandalf/cache/              # MCP server cache files
    ~/.gandalf/exports/            # Conversation exports
    ~/.gandalf/backups/            # Configuration backups  
    ~/.gandalf/config/             # Custom configurations
    ~/.gandalf/installation-state  # Installation tracking

Global Rules Integration:
    Each tool uses its native global rules format:
    - Cursor: Uses ~/.cursor/rules/*.mdc files for global IDE rules
    - Claude Code: Uses ~/.claude/global_settings.json for global context
    - Windsurf: Uses ~/.windsurf/global_rules.md for global rules
    - All tools receive the same core Gandalf MCP guidance adapted to their format
    - Rules apply automatically to ALL projects and workspaces

Next Steps:
    1. Restart ALL configured tools completely (recommended for best results)
    2. Wait a few moments after restart for MCP server initialization
    3. Test MCP integration in any configured tool by asking:
        - "What files are in my project?"
        - "Show me the git status"
        - "List recent conversations"
    4. The global $MCP_SERVER_NAME rules guide AI interactions across all tools and projects
    5. Gandalf works globally - no reinstallation needed for any projects

Troubleshooting:
    - If MCP tools aren't available, restart your tool and wait 30 seconds
    - Check tool-specific MCP logs for connection issues
    - Run 'gdlf test' to verify server functionality
    - Use 'gdlf install --skip-test' for faster installation without connectivity tests
    - Use 'gdlf install -r' to reset ALL tool configurations and install fresh
    - Use 'gdlf uninstall' to completely remove all configurations

Global Access:
    - Gandalf is now configured to work from any directory
    - Use 'gdlf' or 'gandalf' commands from anywhere
    - Configuration and cache managed in ~/.gandalf directory
    - Rules apply automatically to all projects and workspaces

EOF
