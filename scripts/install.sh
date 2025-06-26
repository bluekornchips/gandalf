#!/bin/bash
set -eo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

export PYTHONPATH="$GANDALF_ROOT:${PYTHONPATH:-}"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

SERVER_DIR="$GANDALF_ROOT/src"
SERVER_SCRIPT="$SERVER_DIR/main.py"
SCRIPTS_DIR="$GANDALF_ROOT/scripts"

usage() {
    cat <<EOF
Usage: gandalf.sh install [repo_path] [OPTIONS]

Configure MCP server for repository in Cursor.

Arguments:
    repo_path               Repository path (default: current directory)

Options:
    -f, --force            Force setup (overwrite existing config)
    -r, --reset            Reset/remove existing server before installing
    -h, --help             Show this help
    --skip-test           Skip connectivity testing (faster install)
    --wait-time <seconds> Wait time for Cursor recognition (default: 1)

Examples:
    gandalf.sh install                    # Configure current directory
    gandalf.sh install /path/to/repo      # Configure specific repository
    gandalf.sh install -f                 # Force overwrite existing config
    gandalf.sh install -r                 # Reset existing server and install fresh

What this does:
    1. Verifies system requirements (Python 3.10+, Git)
    2. (Optional) Resets existing server configuration if -r flag used
    3. Installs global $MCP_SERVER_NAME MCP server
    4. Configures single dynamic "$MCP_SERVER_NAME" server in Cursor
    5. Updates Cursor MCP configuration (~/.cursor/mcp.json)
    6. Creates $MCP_SERVER_NAME rules file (.cursor/rules/$MCP_SERVER_NAME-rules.mdc)
    7. Tests server connectivity with retry mechanism

EOF
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
        restart_server "$server_name"
    else
        rm -f "$temp_file"
        echo "Error removing $server_name server"
        return 1
    fi
}

restart_server() {
    local server_name="$1"

    echo "Restarting $server_name MCP server..."

    local MCP_PID=$(pgrep -f "$server_name.*main.py" | head -1 || echo "")
    if [[ -z "$MCP_PID" ]]; then
        echo "$server_name MCP server is not running"
        echo "Make sure Cursor is running and the MCP server was configured"
        return 0
    fi

    echo "Found $server_name MCP server: PID $MCP_PID"
    echo "Stopping $server_name MCP server..."
    kill "$MCP_PID" 2>/dev/null || true
    sleep 1

    if kill -0 "$MCP_PID" 2>/dev/null; then
        echo "Force stopping MCP server..."
        killall -9 python3 2>/dev/null || true
        sleep 1
    fi

    echo "$server_name MCP server stopped"
    echo "Cursor will automatically restart the MCP server with new configuration"
    sleep 2
}

perform_reset() {
    local config_file="$1"
    local server_name="$2"

    cat <<EOF
Performing reset before installation...
Config file: $config_file
Server name: $server_name

EOF

    if [[ -f "$config_file" ]]; then
        local backup_file="${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$config_file" "$backup_file"
        echo "Backup created: $backup_file"
    fi

    remove_server "$config_file" "$server_name"

    cat <<EOF

Reset completed successfully!
Proceeding with fresh installation...

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

verify_prerequisites() {
    echo "Verifying system requirements using shared dependency checker..."

    if ! "$SCRIPTS_DIR/check-dependencies.sh" --core-only --quiet; then
        cat <<EOF

MCP Server Prerequisites Check Failed!

The shared dependency checker found missing requirements.
Run for detailed information:
    $SCRIPTS_DIR/check-dependencies.sh

Quick fixes:
- Python 3.10+: $(python3 --version 2>/dev/null || echo "Not found")
- Git: $(git --version 2>/dev/null | head -1 || echo "Not found")

Optional: Add gandalf.sh to your PATH for global access:
    echo 'export PATH="$GANDALF_ROOT:\$PATH"' >> ~/.bashrc
    source ~/.bashrc
EOF
        exit 1
    fi

    if [[ ! -d "$SERVER_DIR" ]]; then
        echo "Error: Server directory not found: $SERVER_DIR"
        exit 1
    fi

    if [[ ! -f "$SERVER_SCRIPT" ]]; then
        echo "Error: MCP server script not found: $SERVER_SCRIPT"
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

Run dependency check for detailed information:
    $SCRIPTS_DIR/check-dependencies.sh

Try installing dependencies with:
    pip install -r $GANDALF_ROOT/requirements.txt
EOF
        exit 1
    fi
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

create_rules_file() {
    local repo_root="$1"
    local rules_dir="$repo_root/.cursor/rules"
    local rules_file="$rules_dir/$MCP_SERVER_NAME-rules.mdc"
    local source_rules_file="$GANDALF_ROOT/$MCP_SERVER_NAME-rules.md"

    mkdir -p "$rules_dir"

    if [[ -f "$rules_file" ]] && [[ "$FORCE" != "true" ]] && [[ "$RESET" != "true" ]]; then
        echo "$MCP_SERVER_NAME rules file already exists: $rules_file"
        echo "Use -f to force overwrite or -r to reset and reinstall"
        return 0
    fi

    if [[ ! -f "$source_rules_file" ]]; then
        echo "Source rules file not found: $source_rules_file"
        return 1
    fi

    cp "$source_rules_file" "$rules_file"
    echo "Created $MCP_SERVER_NAME rules file: $rules_file"
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

    echo "Testing server connectivity..."
    echo "Waiting ${wait_time}s for Cursor to recognize MCP server..."

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

wait_for_cursor_recognition() {
    local config_file="$1"
    local server_name="$2"
    local wait_time="${3:-1}"

    echo "Giving Cursor time to recognize new MCP configuration..."

    if pgrep -f "Cursor" >/dev/null 2>&1; then
        echo "   Cursor process detected - waiting ${wait_time}s for config reload"
        sleep "$wait_time"

        local mcp_process_count=$(pgrep -f "$server_name.*main.py" | wc -l | tr -d ' \n\r' || echo "0")
        [[ "$mcp_process_count" =~ ^[0-9]+$ ]] || mcp_process_count=0
        if [[ $mcp_process_count -gt 0 ]]; then
            echo "MCP server process started successfully (${mcp_process_count} process(es))"
        else
            echo "MCP server process not yet detected (may start on first use)"
        fi
    else
        echo "Cursor process not detected - configuration will be loaded on next start"
    fi

    return 0
}

# Parse arguments
REPO_ROOT=""
FORCE=false
RESET=false
SKIP_TEST=false
WAIT_TIME=1

if [[ $# -gt 0 && "${1:-}" != -* ]]; then
    REPO_ROOT="$1"
    shift
fi

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

echo "Configuring MCP for repository..."

if [[ -n "$REPO_ROOT" ]]; then
    if [[ ! -d "$REPO_ROOT" ]]; then
        echo "Specified repository root does not exist: $REPO_ROOT"
        exit 1
    fi
    REPO_ROOT="$(cd "$REPO_ROOT" && pwd -P)"
elif git rev-parse --git-dir >/dev/null 2>&1; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
else
    REPO_ROOT="$(pwd -P)"
fi

echo "Repository: $REPO_ROOT"

REPO_NAME="$(basename "$REPO_ROOT")"
SERVER_NAME="$MCP_SERVER_NAME"

echo "Server name: $SERVER_NAME"

CONFIG_DIR="$HOME/.cursor"
CONFIG_FILE="$CONFIG_DIR/mcp.json"

if [[ "$RESET" == "true" ]]; then
    perform_reset "$CONFIG_FILE" "$SERVER_NAME"
fi

echo "Configuring Cursor MCP settings..."

if [[ -f "$CONFIG_FILE" ]] && grep -q "\"$SERVER_NAME\"" "$CONFIG_FILE" 2>/dev/null; then
    if [[ "$FORCE" != "true" ]] && [[ "$RESET" != "true" ]]; then
        echo "Server '$SERVER_NAME' already configured. Use -f to force update or -r to reset and reinstall."
        exit 0
    else
        if [[ "$FORCE" == "true" ]]; then
            echo "Force updating existing server configuration"
        fi
    fi
fi

update_cursor_config "$CONFIG_FILE" "$SERVER_NAME" "$GANDALF_ROOT/gandalf.sh"

echo "Creating $MCP_SERVER_NAME rules file..."
create_rules_file "$REPO_ROOT"

wait_for_cursor_recognition "$CONFIG_FILE" "$SERVER_NAME" 1

if [[ "$SKIP_TEST" != "true" ]]; then
    if ! test_server_connectivity 3 "$WAIT_TIME" "$REPO_ROOT"; then
        echo "Warning: Server connectivity test failed, but installation completed"
        echo "The server may still work correctly in Cursor - try using MCP tools"
    fi
else
    echo "Skipping connectivity tests (--skip-test flag used)"
fi

cat <<EOF

MCP Repository Configuration Complete!

Configuration Summary:
    Server Name: $SERVER_NAME
    Repository:  $REPO_ROOT
    Server Path: $GANDALF_ROOT/gandalf.sh run
    Rules File:  $REPO_ROOT/.cursor/rules/$MCP_SERVER_NAME-rules.mdc
    Reset Mode:  $([[ "$RESET" == "true" ]] && echo "Yes - server was reset before installation" || echo "No")

Next Steps:
    1. Restart Cursor completely (recommended for best results)
    2. Wait a few moments after restart for MCP server initialization
    3. Test MCP integration by asking:
        - "What files are in my project?"
        - "Show me the git status"
    4. The $MCP_SERVER_NAME rules file guides AI interactions

Troubleshooting:
    - If MCP tools aren't available, restart Cursor and wait 30 seconds
    - Check Cursor's MCP logs: View -> Developer -> Toggle Developer Tools -> Console
    - Run 'gdlf test' to verify server functionality
    - Use 'gdlf install --skip-test' for faster installation without connectivity tests
    - Use 'gdlf install -r' to reset existing server and install fresh

EOF
