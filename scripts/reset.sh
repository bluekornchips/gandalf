#!/bin/bash
set -eo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

# Define the MCP configuration file path
CONFIG_FILE="$HOME/.cursor/mcp.json"

usage() {
    cat <<EOF
MCP Configuration Reset Tool

This script helps reset or clean up MCP (Model Context Protocol) server configurations.

USAGE:
    ./reset.sh [OPTIONS] [SERVER_NAME]

ARGUMENTS:
    SERVER_NAME                 Specific server to remove (optional)

OPTIONS:
    -h, --help                 Show this help message
    -a, --all                  Remove all MCP servers from config
    -l, --list                 List current MCP server configurations
    -b, --backup               Create backup before making changes
    -r, --reinstall            Reinstall after removal (requires server path)
    -v, --verbose              Enable verbose output

EXAMPLES:
    ./reset.sh --list                    # Show current servers
    ./reset.sh gandalf                   # Remove specific server by name
    ./reset.sh --all --backup            # Remove all servers with backup
    ./reset.sh --reinstall gandalf       # Remove and reinstall server
EOF
}

check_config_exists() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "MCP config file not found: $CONFIG_FILE"
        return 1
    fi
    return 0
}

create_backup() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "No config file to backup"
        return 0
    fi

    local backup_file="${CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_FILE" "$backup_file"
    echo "Backup created: $backup_file"
    return 0
}

list_servers() {
    echo "Current MCP server configurations:"

    if ! check_config_exists; then
        echo "No MCP servers configured"
        return 0
    fi

    local server_count=$(jq -r '.mcpServers | length' "$CONFIG_FILE" 2>/dev/null || echo "0")

    if [[ "$server_count" -eq 0 ]]; then
        echo "No MCP servers configured"
        return 0
    fi

    echo -e "Found $server_count server(s):\n"

    jq -r '.mcpServers | keys[]' "$CONFIG_FILE" 2>/dev/null | while read -r name; do
        echo "Server: $name"

        local command=$(jq -r --arg name "$name" '.mcpServers[$name].command // ""' "$CONFIG_FILE" 2>/dev/null)
        [[ -n "$command" ]] && echo "   Command: $command"

        local args=$(jq -r --arg name "$name" '.mcpServers[$name].args // [] | join(" ")' "$CONFIG_FILE" 2>/dev/null)
        [[ -n "$args" ]] && echo "   Args: $args"

        local cwd=$(jq -r --arg name "$name" '.mcpServers[$name].cwd // ""' "$CONFIG_FILE" 2>/dev/null)
        [[ -n "$cwd" ]] && echo "   Working Dir: $cwd"

        echo
    done
}

remove_server() {
    local server_name="$1"

    if ! check_config_exists; then
        echo "Cannot remove server: config file not found"
        return 1
    fi

    echo "Removing server: $server_name"

    if ! jq -e --arg name "$server_name" '.mcpServers | has($name)' "$CONFIG_FILE" >/dev/null 2>&1; then
        echo "Server '$server_name' not found in configuration"
        return 1
    fi

    local temp_file=$(mktemp)

    if jq --arg name "$server_name" 'del(.mcpServers[$name])' "$CONFIG_FILE" >"$temp_file"; then
        mv "$temp_file" "$CONFIG_FILE"
        echo "Successfully removed server: $server_name"
    else
        rm -f "$temp_file"
        echo "Error removing server: $server_name"
        return 1
    fi
}

remove_all_servers() {
    if ! check_config_exists; then
        echo "No config file found, nothing to remove"
        return 0
    fi

    echo "Removing all MCP servers..."

    temp_file=$(mktemp)

    if jq '.mcpServers = {}' "$CONFIG_FILE" >"$temp_file"; then
        mv "$temp_file" "$CONFIG_FILE"
        echo "Successfully removed all MCP servers"
    else
        rm -f "$temp_file"
        echo "Error removing servers"
        return 1
    fi
}

parse_arguments() {
    BACKUP=false
    LIST_ONLY=false
    REMOVE_ALL=false
    REINSTALL=false
    SERVER_NAME=""

    while [[ $# -gt 0 ]]; do
        case $1 in
        -h | --help)
            usage
            exit 0
            ;;
        -b | --backup)
            BACKUP=true
            shift
            ;;
        -l | --list)
            LIST_ONLY=true
            shift
            ;;
        -a | --all)
            REMOVE_ALL=true
            shift
            ;;
        -r | --reinstall)
            REINSTALL=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            if [[ -n "$SERVER_NAME" ]]; then
                echo "Multiple server names specified"
                exit 1
            fi
            SERVER_NAME="$1"
            shift
            ;;
        esac
    done
}

main() {
    parse_arguments "$@"

    cat <<EOF
Starting MCP configuration reset...
Config file: $CONFIG_FILE
Backup mode: $BACKUP
List only: $LIST_ONLY
Remove all: $REMOVE_ALL
Server name: ${SERVER_NAME:-<none>}
EOF

    [[ "$BACKUP" == "true" ]] && create_backup
    [[ "$LIST_ONLY" == "true" ]] && list_servers && exit 0

    if [[ "$REMOVE_ALL" == "true" ]]; then
        if [[ -n "$SERVER_NAME" ]]; then
            echo "Cannot specify server name with --all option"
            exit 1
        fi
        remove_all_servers
        exit 0
    fi

    if [[ -n "$SERVER_NAME" ]]; then
        remove_server "$SERVER_NAME"

        if [[ "$REINSTALL" == "true" ]]; then
            echo "Reinstallation not yet implemented"
            echo "Please use the install_to_repo script manually"
        fi

        exit 0
    fi

    echo "No specific action requested, showing current configuration:"
    list_servers
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
