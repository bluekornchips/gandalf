#!/bin/bash
################################################################################
# Gandalf MCP Server Setup Script
#
# Sets up Gandalf MCP configurations for available agentic tools and manages
# the ~/.gandalf directory structure.
#
# Usage: ./setup.sh [OPTIONS]
################################################################################

set -euo pipefail

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GANDALF_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load platform utilities
source "$SCRIPT_DIR/platform-utils.sh"

# Default configurations
MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
GANDALF_SERVER_VERSION="${GANDALF_SERVER_VERSION:-2.0.1}"
ENV_FILE="$GANDALF_ROOT/.env"

# Load common utilities - create a minimal shared.sh if it doesn't exist
if [[ ! -f "$SCRIPT_DIR/shared.sh" ]]; then
    # Create minimal shared utilities
    cat >"$SCRIPT_DIR/shared.sh" <<'EOF'
#!/bin/bash
# Minimal shared utilities for Gandalf scripts

export GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"

load_env_variables() {
    local env_file="${1:-$GANDALF_ROOT/.env}"
    if [[ -f "$env_file" ]]; then
        source "$env_file"
    fi
}
EOF
fi

source "$SCRIPT_DIR/shared.sh"

load_env_variables() {
    if [[ -f "$ENV_FILE" ]]; then
        source "$ENV_FILE"
    fi
}

# Global state variables
GANDALF_INSTALLED=false
CURSOR_AVAILABLE=false
CLAUDE_CODE_AVAILABLE=false
CURSOR_SETUP_SUCCESS=false
CLAUDE_CODE_SETUP_SUCCESS=false

################################################################################
# Gandalf Directory Management Functions
################################################################################

# Create ~/.gandalf directory structure
create_gandalf_directory() {
    local gandalf_home="$GANDALF_HOME"

    echo "Setting up $gandalf_home directory structure..."

    # Create main directory structure
    mkdir -p "$gandalf_home"/{cache,exports,backups,config}

    # Set proper permissions
    chmod 755 "$gandalf_home"

    # Create subdirectory permissions
    find "$gandalf_home" -type d -exec chmod 755 {} \;

    echo "Created $gandalf_home directory structure"
    return 0
}

# Create installation state file
create_installation_state() {
    local gandalf_root="${1:-}"
    local gandalf_version="${2:-}"
    local detected_tool="${3:-}"
    local force_tool="${4:-}"
    local repo_root="${5:-}"
    local server_name="${6:-$MCP_SERVER_NAME}"
    local cursor_success="${7:-false}"
    local claude_success="${8:-false}"

    local state_dir="$HOME/.gandalf"
    local state_file="$state_dir/installation-state"

    mkdir -p "$state_dir"

    cat >"$state_file" <<EOF
# Gandalf Installation State
# This file tracks installation configuration and metadata

# Core Configuration
GANDALF_ROOT="$gandalf_root"
GANDALF_VERSION="$gandalf_version"
INSTALLATION_DATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
DETECTED_TOOL="$detected_tool"
FORCE_TOOL="$force_tool"
REPO_ROOT="$repo_root"
SERVER_NAME="$server_name"

# Installation Results
CURSOR_INSTALLED=$cursor_success
CLAUDE_CODE_INSTALLED=$claude_success
INSTALL_ALL_TOOLS=true
LAST_UPDATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
EOF

    echo "Installation state saved to: $state_file"
}

# Update installation state with results
update_installation_state() {
    local gandalf_home="$GANDALF_HOME"
    local cursor_success="${1:-false}"
    local claude_success="${2:-false}"

    local state_file="$gandalf_home/installation-state"

    if [[ ! -f "$state_file" ]]; then
        echo "Warning: Installation state file not found: $state_file"
        return 1
    fi

    cat >>"$state_file" <<EOF

# Installation Results ($(date -u +"%Y-%m-%dT%H:%M:%SZ"))
CURSOR_INSTALLED=$cursor_success
CLAUDE_CODE_INSTALLED=$claude_success
INSTALL_ALL_TOOLS=true
LAST_UPDATE="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
EOF

    echo "Updated installation state: $state_file"
    return 0
}

# Load installation state
load_installation_state() {
    local gandalf_home="$GANDALF_HOME"
    local state_file="$gandalf_home/installation-state"

    if [[ -f "$state_file" ]]; then
        # Source the state file to load variables
        source "$state_file" 2>/dev/null || true

        # Check if Gandalf is installed based on state
        if [[ -n "${GANDALF_ROOT:-}" && -d "${GANDALF_ROOT:-}" ]]; then
            GANDALF_INSTALLED=true
            echo "Gandalf installation found: ${GANDALF_ROOT}"
        fi
    else
        echo "No installation state found"
    fi
}

ensure_gandalf_directory() {
    local gandalf_home="$GANDALF_HOME"

    if [[ ! -d "$gandalf_home" ]]; then
        create_gandalf_directory
    else
        mkdir -p "$gandalf_home"/{cache,exports,backups,config}
        echo "Verified $gandalf_home directory structure"
    fi

    return 0
}

# Show gandalf directory info
show_gandalf_directory_info() {
    local gandalf_home="$GANDALF_HOME"

    echo "Gandalf Directory Information:"
    echo "  Location: $gandalf_home"
    echo "  Exists: $([ -d "$gandalf_home" ] && echo "Yes" || echo "No")"

    if [[ -d "$gandalf_home" ]]; then
        echo "  Size: $(du -sh "$gandalf_home" 2>/dev/null | cut -f1 || echo "Unknown")"
        echo "  Subdirectories:"
        for subdir in cache exports backups config; do
            local dir_path="$gandalf_home/$subdir"
            if [[ -d "$dir_path" ]]; then
                local size=$(du -sh "$dir_path" 2>/dev/null | cut -f1 || echo "Unknown")
                local count=$(find "$dir_path" -type f 2>/dev/null | wc -l | tr -d ' ')
                echo "    $subdir/: $size ($count files)"
            else
                echo "    $subdir/: Not found"
            fi
        done
    fi

    # Show installation state if available
    local state_file="$gandalf_home/installation-state"
    if [[ -f "$state_file" ]]; then
        echo "  Installation State: Available"
        if load_installation_state; then
            cat <<EOF

Last Updated: ${LAST_UPDATE:-${INSTALLATION_DATE:-Unknown}}
Cursor Installed: ${CURSOR_INSTALLED:-Unknown}
Claude Code Installed: ${CLAUDE_CODE_INSTALLED:-Unknown}

EOF
        fi
    else
        echo "  Installation State: Not found"
    fi
}

################################################################################
# Agentic Tool Setup Functions
################################################################################

# Function to detect agentic tool availability
detect_agentic_tool_availability() {
    # Check for Cursor agentic tool using platform-aware detection
    local cursor_config_dir
    cursor_config_dir=$(get_cursor_config_dir)
    local cursor_app_support_dir
    cursor_app_support_dir=$(get_cursor_app_support_dir)

    if [[ -d "$cursor_config_dir" ]] || [[ -d "$cursor_app_support_dir" ]]; then
        CURSOR_AVAILABLE=true
        echo "Cursor IDE detected (config: $cursor_config_dir)"
    else
        echo "Cursor IDE not detected"
        CURSOR_AVAILABLE=false
    fi

    # Check for Claude Code
    if [[ -d "$HOME/.claude" ]] || [[ -d "$HOME/.config/claude" ]]; then
        CLAUDE_CODE_AVAILABLE=true
        echo "Claude Code detected"
    else
        echo "Claude Code not detected"
        CLAUDE_CODE_AVAILABLE=false
    fi
}

# Function to setup Cursor agentic tool configuration
setup_cursor() {
    local server_name="$1"
    local gandalf_root="$2"

    if [[ "$CURSOR_AVAILABLE" != "true" ]]; then
        echo "Skipping Cursor setup - IDE not available"
        return 1
    fi

    echo "Setting up Cursor IDE configuration..."

    local cursor_config_dir="$HOME/.cursor"
    local cursor_config_file="$cursor_config_dir/mcp.json"

    # Create config directory if it doesn't exist
    mkdir -p "$cursor_config_dir"

    # Create or update mcp.json
    if [[ ! -f "$cursor_config_file" ]]; then
        echo '{"mcpServers": {}}' >"$cursor_config_file"
    fi

    # Add or update the server configuration
    local temp_file=$(mktemp)
    jq --arg name "$server_name" --arg cmd "$gandalf_root/gandalf.sh" \
        '.mcpServers[$name] = {
            "command": $cmd,
            "args": ["run"]
        }' "$cursor_config_file" >"$temp_file"

    mv "$temp_file" "$cursor_config_file"
    echo "Cursor IDE setup completed"
    return 0
}

# Function to setup Claude Code configuration
setup_claude_code() {
    local server_name="$1"
    local gandalf_root="$2"

    if [[ "$CLAUDE_CODE_AVAILABLE" != "true" ]]; then
        echo "Skipping Claude Code setup - not available"
        return 1
    fi

    echo "Setting up Claude Code configuration..."

    # Claude Code can use either ~/.claude or ~/.config/claude
    local claude_config_dir=""
    if [[ -d "$HOME/.claude" ]]; then
        claude_config_dir="$HOME/.claude"
    elif [[ -d "$HOME/.config/claude" ]]; then
        claude_config_dir="$HOME/.config/claude"
    else
        # Create the standard location
        claude_config_dir="$HOME/.claude"
        mkdir -p "$claude_config_dir"
    fi

    local claude_config_file="$claude_config_dir/mcp.json"

    # Create config directory if it doesn't exist
    mkdir -p "$claude_config_dir"

    # Create or update mcp.json
    if [[ ! -f "$claude_config_file" ]]; then
        echo '{"mcpServers": {}}' >"$claude_config_file"
    fi

    # Add or update the server configuration
    local temp_file=$(mktemp)
    jq --arg name "$server_name" --arg cmd "$gandalf_root/gandalf.sh" \
        '.mcpServers[$name] = {
            "command": $cmd,
            "args": ["run"],
            "env": {
                "PYTHONPATH": "'$gandalf_root'/server",
                "CLAUDECODE": "1",
                "CLAUDE_CODE_ENTRYPOINT": "cli"
            }
        }' "$claude_config_file" >"$temp_file"

    mv "$temp_file" "$claude_config_file"
    echo "Claude Code setup completed"
    return 0
}

# Function to verify Gandalf MCP server
verify_gandalf() {
    if [[ "$GANDALF_INSTALLED" != true ]]; then
        echo "WARNING: Gandalf MCP server not installed"
        echo "Please run ./install.sh first"
        return 1
    fi

    echo "Verifying Gandalf MCP server..."

    if command -v gandalf &>/dev/null; then
        echo "Gandalf MCP server is available"
        gandalf --version 2>/dev/null || echo "Version check failed"
        return 0
    else
        echo "WARNING: Gandalf command not found in PATH"
        return 1
    fi
}

# Function to update state file
update_state_file() {
    local state_file="$GANDALF_HOME/installation-state"

    # Ensure directory exists
    ensure_gandalf_directory

    # Append setup results
    cat <<EOF >>"$state_file"

# Setup Results ($(date))
CURSOR_SETUP_SUCCESS=$CURSOR_SETUP_SUCCESS
CLAUDE_CODE_SETUP_SUCCESS=$CLAUDE_CODE_SETUP_SUCCESS
SETUP_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

    echo "Setup state updated: $state_file"
}

# Function to show setup summary
show_setup_summary() {
    cat <<EOF

Setup Summary:

Gandalf MCP Server: $([ "$GANDALF_INSTALLED" == true ] && echo "Available" || echo "Not available")
Cursor IDE Setup: $([ "$CURSOR_SETUP_SUCCESS" == true ] && echo "Completed" || echo "Skipped/Failed")
Claude Code Setup: $([ "$CLAUDE_CODE_SETUP_SUCCESS" == true ] && echo "Completed" || echo "Skipped/Failed")

Configuration Files:
EOF

    # Show what was configured
    if [[ "$CURSOR_SETUP_SUCCESS" == true ]]; then
        echo "- Cursor rules: $HOME/.cursor/rules/gandalf-rules.mdc"
    fi

    if [[ "$CLAUDE_CODE_SETUP_SUCCESS" == true ]]; then
        echo "- Claude Code project: ./CLAUDE.md"
        echo "- Claude Code user: $HOME/.claude/CLAUDE.md"
        echo "- Claude Code settings: ./.claude/settings.json (with Gandalf rules)"
    fi

    # Note: Windsurf rules are created during install, not setup
    echo "- Windsurf rules: Created during install (.windsurfrules + global_rules.md)"

    # Show gandalf directory info
    echo ""
    show_gandalf_directory_info

    cat <<EOF

Next Steps:
EOF

    if [[ "$CURSOR_SETUP_SUCCESS" == true || "$CLAUDE_CODE_SETUP_SUCCESS" == true ]]; then
        cat <<EOF
1. Restart your IDE or tool to load new configurations
2. Test MCP integration with your IDE or tool
3. Use /memory command in Claude Code to verify memory loading
EOF
    else
        cat <<EOF
1. Install a supported IDE or tool if needed
2. Ensure required template files are present
3. Run this setup script again
EOF
    fi
}

# Function to show usage
show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Setup Gandalf MCP configurations for available agentic tools and manage ~/.gandalf directory

OPTIONS:
    -d, --directory DIR  Specify project directory (default: current directory)
    -h, --help          Show this help message
    --info              Show ~/.gandalf directory information and exit

EXAMPLES:
    $0                      # Setup in current directory
    $0 -d /path/to/project  # Setup in specific directory
    $0 --info               # Show directory information

REQUIRED FILES:
    - gandalf-rules.md      # For Cursor setup
    - CLAUDE.md             # For Claude Code project memory
    - claude-user-memory.md # For Claude Code user memory
EOF
}

# Main function
main() {
    local project_dir="$(pwd)"
    local show_info_only=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
        -d | --directory)
            project_dir="$2"
            shift 2
            ;;
        --info)
            show_info_only=true
            shift
            ;;
        -h | --help)
            show_usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            show_usage
            exit 1
            ;;
        esac
    done

    # If just showing info, do that and exit
    if [[ "$show_info_only" == true ]]; then
        show_gandalf_directory_info
        exit 0
    fi

    # Validate project directory
    if [[ ! -d "$project_dir" ]]; then
        echo "ERROR: Project directory does not exist: $project_dir"
        exit 1
    fi

    echo "Gandalf MCP Server Setup"
    echo "========================"
    echo "Project directory: $project_dir"
    echo

    # Ensure gandalf directory exists
    ensure_gandalf_directory
    echo

    # Detect agentic tool availability
    detect_agentic_tool_availability
    echo

    # Load installation state
    load_installation_state
    echo

    # Verify Gandalf server
    verify_gandalf || echo "Continuing with available agentic tools..."
    echo

    # Setup agentic tools
    echo "Setting up agentic tool configurations..."

    # Setup Cursor (non-fatal if it fails)
    setup_cursor "$MCP_SERVER_NAME" "$GANDALF_ROOT" || echo "Cursor setup encountered issues"
    echo

    # Setup Claude Code (non-fatal if it fails)
    setup_claude_code "$MCP_SERVER_NAME" "$GANDALF_ROOT" || echo "Claude Code setup encountered issues"
    echo

    # Update state file
    update_state_file
    echo

    # Show summary
    show_setup_summary
}

# Run main function with all arguments
main "$@"
