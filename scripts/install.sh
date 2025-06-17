#!/bin/bash
set -eo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

usage() {
    cat <<EOF
Usage: gandalf.sh install [repo_path] [OPTIONS]

Configure MCP server for repository in Cursor.

Arguments:
    repo_path               Repository path (default: current directory)

Options:
    -f, --force            Force setup (overwrite existing config)
    -h, --help             Show this help

Examples:
    gandalf.sh install                    # Configure current directory
    gandalf.sh install /path/to/repo      # Configure specific repository
    gandalf.sh install -f                 # Force overwrite existing config

What this does:
    1. Detects repository root
    2. Configures single dynamic "gandalf" server
    3. Updates Cursor MCP configuration (~/.cursor/mcp.json)
    4. Creates Gandalf rules file (.cursor/rules/gandalf-rules.mdc)
    5. Tests server connectivity

Note: Gandalf automatically detects your current project directory, so you only need to install it once.
It will work across all your repositories.

Prerequisites:
    Run 'gandalf.sh setup' first

EOF
}

update_cursor_config() {
    local config_file="$1"
    local server_name="$2"
    local mcp_script="$3"

    mkdir -p "$(dirname "$config_file")"

    if [[ -f "$config_file" ]]; then
        cp "$config_file" "$config_file.backup.$(date +%s)"

        temp_file=$(mktemp)

        if command -v jq >/dev/null 2>&1; then
            jq --arg name "$server_name" \
                --arg cmd "$mcp_script" \
                '.mcpServers[$name] = {
                    "command": $cmd,
                    "args": ["run"],
                    "env": {}
                }' "$config_file" >"$temp_file"
            mv "$temp_file" "$config_file"
        else
            # Fallback for no jq - most people probably won't have it
            cat >"$config_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
            "command": "$mcp_script",
            "args": ["run"],
            "env": {}
        }
    }
}
EOF
        fi
    else
        # Create new config file
        cat >"$config_file" <<EOF
{
    "mcpServers": {
        "$server_name": {
        "command": "$mcp_script",
        "args": ["run"],
        "env": {}
        }
    }
}
EOF
    fi

    echo "Updated Cursor configuration: $server_name"
}

create_gandalf_rules() {
    local repo_root="$1"
    local rules_dir="$repo_root/.cursor/rules"
    local rules_file="$rules_dir/gandalf-rules.mdc"
    local source_rules_file="$GANDALF_ROOT/gandalf-rules.txt"

    mkdir -p "$rules_dir"

    if [[ -f "$rules_file" ]] && [[ "$FORCE" != "true" ]]; then
        echo "Gandalf rules file already exists: $rules_file"
        echo "Use -f to force overwrite"
        return 0
    fi

    if [[ ! -f "$source_rules_file" ]]; then
        echo "Source rules file not found: $source_rules_file"
        return 1
    fi

    # Copy the gandalf-rules.txt file from the source as .mdc
    cp "$source_rules_file" "$rules_file"

    echo "Created Gandalf rules file: $rules_file"
}

REPO_ROOT=""
FORCE=false

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

SERVER_DIR="$GANDALF_ROOT/server"

echo "Configuring MCP for repository..."

if [[ ! -d "$SERVER_DIR" ]]; then
    echo "MCP server not found. Run 'gandalf.sh setup' first."
    exit 1
fi

if [[ -n "$REPO_ROOT" ]]; then
    if [[ ! -d "$REPO_ROOT" ]]; then
        echo "Specified repository root does not exist: $REPO_ROOT"
        exit 1
    fi
    REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
elif git rev-parse --git-dir >/dev/null 2>&1; then
    REPO_ROOT="$(git rev-parse --show-toplevel)"
else
    REPO_ROOT="$(pwd)"
fi

echo "Repository: $REPO_ROOT"

REPO_NAME="$(basename "$REPO_ROOT")"
SERVER_NAME="$MCP_SERVER_NAME"

echo "Server name: $SERVER_NAME"

CONFIG_DIR="$HOME/.cursor"
CONFIG_FILE="$CONFIG_DIR/mcp.json"

echo "Configuring Cursor MCP settings..."

if [[ -f "$CONFIG_FILE" ]] && grep -q "\"$SERVER_NAME\"" "$CONFIG_FILE" 2>/dev/null; then
    if [[ "$FORCE" != "true" ]]; then
        echo "Server '$SERVER_NAME' already configured. Use -f to force update."
        exit 0
    else
        echo "Force updating existing server configuration"
    fi
fi

update_cursor_config "$CONFIG_FILE" "$SERVER_NAME" "$GANDALF_ROOT/gandalf.sh"

echo "Creating Gandalf rules file..."
create_gandalf_rules "$REPO_ROOT"

echo "Testing server connectivity..."

pushd "$REPO_ROOT" >/dev/null

if echo '{"method": "initialize", "id": 1}' | "$GANDALF_ROOT/gandalf.sh" run 2>/dev/null | grep -q "protocolVersion"; then
    echo "Server initialization test passed"
else
    echo "Server initialization test failed"
fi

if echo '{"method": "tools/list", "id": 2}' | "$GANDALF_ROOT/gandalf.sh" run 2>/dev/null | grep -q "tools"; then
    echo "Tools list test passed"
else
    echo "Tools list test failed"
fi

popd >/dev/null

cat <<EOF

MCP Repository Configuration Complete!

Configuration:
    Server Name: $SERVER_NAME
    Repository:  $REPO_ROOT
    Server:      $GANDALF_ROOT/gandalf.sh run
    Rules File:  $REPO_ROOT/.cursor/rules/gandalf-rules.mdc

Next Steps:
    1. Restart Cursor completely
    2. Test MCP integration by asking:
        - "What files are in my project?"
        - "Show me the git status"
    3. The Gandalf rules file has been created to help guide AI interactions

EOF
