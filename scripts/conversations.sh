#!/bin/bash
set -euo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

SERVER_SCRIPT="$GANDALF_ROOT/server/main.py"

usage() {
    cat <<'EOF'
Usage: gandalf.sh conv [COMMAND] [OPTIONS]

Real-time conversation access via MCP tools.

Commands:
    ingest [OPTIONS]           Analyze recent conversations with context intelligence
    query [OPTIONS]            Search conversations for specific topics
    export [OPTIONS]           Export conversations to file
    workspaces                 List available Cursor workspace databases
    help                       Show this help

Options:
    --fast_mode=BOOL           Use fast extraction (default: true)
    --days_lookback=N          Days to look back (default: 7)
    --limit=N                  Maximum results (default: 20)
    --query="TEXT"             Search query text
    --include_content=BOOL     Include content snippets (default: false)
    --format=FORMAT            Output format: json, markdown, cursor (default: json)
    --summary=BOOL             Summary mode (default: false)

Examples:
    gdlf conv ingest --fast_mode=true --days_lookback=7
    gdlf conv query --query="debugging authentication" --include_content=true
    gdlf conv export --format=markdown
    gdlf conv workspaces

EOF
}

# Simple MCP tool execution
call_mcp_tool() {
    local tool_name="$1"
    local args="$2"

    python3 "$SERVER_SCRIPT" --project-root "$(pwd)" <<EOF | jq -s '.[] | select(.id == 2 and has("result")) | .result.content[0].text' | jq -r
{"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "gandalf-cli", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
{"jsonrpc": "2.0", "method": "tools/call", "id": 2, "params": {"name": "$tool_name", "arguments": $args}}
EOF
}

# Parse arguments to JSON
parse_args() {
    local args_json="{}"

    while [[ $# -gt 0 ]]; do
        case $1 in
        --fast_mode=*)
            args_json=$(echo "$args_json" | jq --argjson val "${1#*=}" '. + {fast_mode: $val}')
            ;;
        --days_lookback=*)
            args_json=$(echo "$args_json" | jq --argjson val "${1#*=}" '. + {days_lookback: $val}')
            ;;
        --limit=*)
            args_json=$(echo "$args_json" | jq --argjson val "${1#*=}" '. + {limit: $val}')
            ;;
        --query=*)
            args_json=$(echo "$args_json" | jq --arg val "${1#*=}" '. + {query: $val}')
            ;;
        --include_content=*)
            args_json=$(echo "$args_json" | jq --argjson val "${1#*=}" '. + {include_content: $val}')
            ;;
        --format=*)
            args_json=$(echo "$args_json" | jq --arg val "${1#*=}" '. + {format: $val}')
            ;;
        --summary=*)
            args_json=$(echo "$args_json" | jq --argjson val "${1#*=}" '. + {summary: $val}')
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
        esac
        shift
    done

    echo "$args_json"
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

COMMAND="$1"
shift

ARGS_JSON=$(parse_args "$@")

case "$COMMAND" in
ingest)
    call_mcp_tool "ingest_conversations" "$ARGS_JSON"
    ;;
query)
    call_mcp_tool "query_conversation_context" "$ARGS_JSON"
    ;;
export)
    call_mcp_tool "query_cursor_conversations" "$ARGS_JSON"
    ;;
workspaces)
    call_mcp_tool "list_cursor_workspaces" '{"random_string": "dummy"}'
    ;;
help | -h | --help)
    usage
    ;;
*)
    echo "Unknown command: $COMMAND" >&2
    usage
    exit 1
    ;;
esac
