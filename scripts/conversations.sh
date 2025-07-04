#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
GANDALF_ROOT="$(dirname "$SCRIPT_DIR")"
export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

SERVER_SCRIPT="$GANDALF_ROOT/server/src/main.py"

usage() {
    cat <<'EOF'
Usage: gandalf.sh conv [COMMAND] [OPTIONS]

Real-time conversation access via MCP tools.

Commands:
    recall [OPTIONS]           Analyze recent conversations with context intelligence
    query [OPTIONS]            Search conversations for specific topics
    export [OPTIONS]           Export individual conversations to specified directory
    workspaces                 List available Cursor workspace databases
    help                       Show this help

Options:
    --fast_mode=BOOL           Use fast extraction (default: true)
    --days_lookback=N          Days to look back (default: 7)
    --limit=N                  Maximum results (default: 20)
    --query="TEXT"             Search query text
    --include_content=BOOL     Include content snippets (default: false)
    --format=FORMAT            Export format: json, md, txt (default: json)
    --output_dir=PATH          Export directory (defaults to ~/.gandalf/exports)
    --workspace_filter=HASH    Filter by specific workspace hash
    --conversation_filter=TEXT Filter conversations by name (partial match)
    --summary=BOOL             Summary mode (default: false)
    --file=FILENAME            Output to file in current directory (optional)

Examples:
    gdlf conv recall --fast_mode=true --days_lookback=7
    gdlf conv query --query="debugging authentication" --include_content=true
    gdlf conv export --format=json --limit=10
    gdlf conv export --format=md --conversation_filter="debugging" --output_dir=./exports
    gdlf conv workspaces

EOF
}

# Simple MCP tool execution
call_mcp_tool() {
    local tool_name="$1"
    local args="$2"

    # Ensure args is a single line JSON
    local args_oneline=$(echo "$args" | jq -c .)

    local temp_input=$(mktemp)
    cat >"$temp_input" <<EOFMCP
{"jsonrpc": "2.0", "method": "initialize", "id": 1, "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "gandalf-cli", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
{"jsonrpc": "2.0", "method": "tools/call", "id": 2, "params": {"name": "$tool_name", "arguments": $args_oneline}}
EOFMCP

    # Get the raw response and extract the content
    local response=$(python3 "$SERVER_SCRIPT" --project-root "$(pwd -P)" <"$temp_input" 2>&1)

    # Check if server execution failed
    if [[ $? -ne 0 ]]; then
        echo "Error running server:" >&2
        echo "$response" >&2
        rm "$temp_input"
        return 1
    fi

    # Filter and process each JSON line separately, looking for the response
    local content=""
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            # Try to parse each line as JSON and look for the result
            local parsed_line=$(echo "$line" | jq 'select(.id == 2 and has("result")) | .result.content[0].text' -r 2>/dev/null)
            if [[ -n "$parsed_line" && "$parsed_line" != "null" ]]; then
                content="$parsed_line"
                break
            fi
        fi
    done <<<"$response"

    # Check if content extraction failed
    if [[ -z "$content" || "$content" == "null" ]]; then
        echo "Failed to extract content from response" >&2
        rm "$temp_input"
        return 1
    fi

    # Check if content is JSON and parse it if so, otherwise return as-is
    if echo "$content" | jq . >/dev/null 2>&1; then
        echo "$content" | jq .
    else
        echo "$content"
    fi

    rm "$temp_input"
}

# Parse arguments to JSON
parse_args() {
    local args_json="{}"
    local output_file=""

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
        --output_dir=*)
            args_json=$(echo "$args_json" | jq --arg val "${1#*=}" '. + {output_dir: $val}')
            ;;
        --workspace_filter=*)
            args_json=$(echo "$args_json" | jq --arg val "${1#*=}" '. + {workspace_filter: $val}')
            ;;
        --conversation_filter=*)
            args_json=$(echo "$args_json" | jq --arg val "${1#*=}" '. + {conversation_filter: $val}')
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

    # Return JSON as single line
    echo "$args_json" | jq -c .
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

COMMAND="$1"
shift

# Parse arguments and extract JSON args
PARSE_RESULT=$(parse_args "$@")
ARGS_JSON="$PARSE_RESULT"

case "$COMMAND" in
recall)
    call_mcp_tool "recall_cursor_conversations" "$ARGS_JSON"
    ;;
query)
    call_mcp_tool "search_cursor_conversations" "$ARGS_JSON"
    ;;
export)
    call_mcp_tool "export_individual_conversations" "$ARGS_JSON"
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
