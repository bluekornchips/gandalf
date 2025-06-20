#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

LOG_DIR="$HOME/.$MCP_SERVER_NAME/conversation_logs"

# Show usage information
show_usage() {
    cat <<EOF
Usage: $0 [options] [logfile]

Analyze Gandalf message logs for patterns and performance

Options:
    -h, --help      Show this help message
    -s, --stats     Show detailed statistics
    -e, --errors    Show error messages only
    -t, --tail      Tail the latest log file
    -l, --latest    Show info about the latest log file

If no logfile is specified, uses the most recent log file.
EOF
}

require_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        cat <<EOF
Error: jq is required for this operation
Install: brew install jq (macOS) or apt-get install jq (Linux)
EOF
        exit 1
    fi
}

get_logfile() {
    local input="$1"
    if [[ -f "$input" ]]; then
        echo "$input"
    elif [[ -f "$LOG_DIR/${input}.jsonl" ]]; then
        echo "$LOG_DIR/${input}.jsonl"
    else
        find "$LOG_DIR" -name "*${input}*.jsonl" -type f | head -1
    fi
}

validate_logfile() {
    local logfile="$1"
    [[ -f "$logfile" ]] || {
        echo "Error: Log file not found: $1" >&2
        exit 1
    }
}

usage() {
    cat <<EOF
Message Log Analyzer for $MCP_SERVER_NAME MCP Server

USAGE:
    gandalf.sh analyze_messages <command> [options]

COMMANDS:
    list                        List all available log sessions
    latest                      Show latest session and summary  
    show <session_id>           Show session activity
    stats <session_id>          Show detailed session statistics
    summary <session_id>        Show brief session summary
    errors [pattern]            Show error messages (optionally filtered)
    tools [pattern]             Show tool usage statistics
    tail [session_id]           Follow log in real-time (latest if no ID)
    export <session_id> <file>  Export session to JSON file

EXAMPLES:
    analyze_messages.sh list
    analyze_messages.sh latest
    analyze_messages.sh stats abc123def456
    analyze_messages.sh summary abc123def456
    analyze_messages.sh errors  # All errors
    analyze_messages.sh tools abc123def456  # Tools for specific session

EOF
}

list_logs() {
    [[ -d "$LOG_DIR" ]] || {
        echo "No message logs directory found at: $LOG_DIR" >&2
        exit 1
    }

    cat <<'EOF'
Available message log files:
============================

EOF

    if stat -f "%m %N" /dev/null >/dev/null 2>&1; then
        find "$LOG_DIR" -name "*.jsonl" -type f -exec stat -f "%m %N" {} \; | sort -nr | cut -d' ' -f2-
    else
        find "$LOG_DIR" -name "*.jsonl" -type f -printf "%T@ %p\n" | sort -nr | cut -d' ' -f2-
    fi | while read -r logfile; do
        local basename=$(basename "$logfile")
        local session_id=$(echo "$basename" | grep -o '[a-f0-9]\{16\}' | head -1)
        local size=$(du -h "$logfile" | cut -f1)
        local modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$logfile" 2>/dev/null ||
            stat -c "%y" "$logfile" 2>/dev/null | cut -d. -f1)

        printf "%-60s %s (%s)\n" "$basename" "$session_id" "$size"
    done
}

get_latest_log() {
    [[ -d "$LOG_DIR" ]] || {
        echo "No message logs directory found" >&2
        exit 1
    }

    find "$LOG_DIR" -name "*.jsonl" -type f -exec stat -f "%m %N" {} \; 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2- ||
        find "$LOG_DIR" -name "*.jsonl" -type f -printf "%T@ %p\n" 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-
}

# Show log file header
show_log_header() {
    local logfile="$1"
    cat <<EOF
Message Log: $(basename "$logfile")
================================

EOF
}

show_session() {
    require_jq
    local logfile=$(get_logfile "$1")
    validate_logfile "$logfile"

    show_log_header "$logfile"

    # Use jq to process and format in one pass
    jq -r '
        if .type == "session_start" then
            "SESSION START - \(.timestamp)\n   Project: \(.project_root)\n   PID: \(.pid)"
        elif .type == "session_end" then
            "SESSION END - \(.timestamp)\n   Total Messages: \(.total_messages)"
        elif .type == "request" then
            if .data.method == "tools/call" then
                "REQUEST - \(.timestamp) - \(.data.method)\n   Tool: \(.data.params.name)"
            else
                "REQUEST - \(.timestamp) - \(.data.method)"
            end
        elif .type == "response" then
            if .data.error then
                "RESPONSE - \(.timestamp)\n   Error: \(.data.error.message)"
            else
                "RESPONSE - \(.timestamp)\n   Success"
            end
        elif .type == "notification" then
            "NOTIFICATION - \(.timestamp) - \(.data.method) (\(.data.params.level))\n   \(.data.params.message)"
        else
            "UNKNOWN - \(.timestamp) - \(.type)"
        end + "\n"
    ' "$logfile"
}

show_stats() {
    require_jq
    local logfile=$(get_logfile "$1")
    validate_logfile "$logfile"

    cat <<EOF
Statistics for Session: $(basename "$logfile" .jsonl)
=====================================

EOF

    # Single jq pass to generate all statistics using slurp mode
    jq -sr '
        (. | length) as $total |
        (. | map(select(.type == "request")) | length) as $requests |
        (. | map(select(.type == "response")) | length) as $responses |
        (. | map(select(.type == "notification")) | length) as $notifications |
        (. | map(select(.type == "response" and .data.error)) | length) as $errors |
        (. | map(select(.type == "session_start")) | .[0].timestamp // "unknown") as $start |
        (. | map(select(.type == "session_end")) | .[0].timestamp // "unknown") as $end |
        
        "Total Messages: \($total)",
        "Requests: \($requests)",
        "Responses: \($responses)", 
        "Notifications: \($notifications)",
        "Errors: \($errors)",
        "",
        "Timeline:",
        "Start: \($start)",
        "End: \($end)",
        "",
        "Tool Usage:"
    ' "$logfile"

    # Tool usage frequency
    jq -r 'select(.type == "request" and .data.method == "tools/call") | .data.params.name' "$logfile" |
        sort | uniq -c | sort -nr | sed 's/^/   /'
}

summary() {
    require_jq
    local logfile=$(get_logfile "$1")
    validate_logfile "$logfile"

    jq -sr '
        (. | map(select(.type == "session_start")) | .[0]) as $session |
        (. | map(select(.type == "request" and .data.method == "tools/call")) | map(.data.params.name)) as $tools |
        (. | map(select(.type == "response" and .data.error)) | length) as $errors |
        (. | map(select(.type == "session_end")) | .[0].timestamp // "ongoing") as $end |
        
        "Session Summary: \($session.session_id)",
        "Project: \($session.project_root)",
        "Duration: \($session.timestamp) to \($end)",
        "Tools Used: \($tools | unique | join(", "))",
        "Total Messages: \(. | length)",
        "Errors: \($errors)"
    ' "$logfile"
}

# Show error section header
show_error_header() {
    cat <<EOF
Error Messages
=================

EOF
}

show_errors() {
    require_jq
    local logfile_pattern="${1:-*}"

    show_error_header

    find "$LOG_DIR" -name "${logfile_pattern}*.jsonl" -type f | while read -r logfile; do
        local basename=$(basename "$logfile")
        local error_count=$(jq -r 'select(.type == "response" and .data.error)' "$logfile" 2>/dev/null | wc -l)

        if [[ "$error_count" -gt 0 ]]; then
            echo "$basename ($error_count errors)"
            jq -r 'select(.type == "response" and .data.error) | 
                "   Error \(.timestamp): \(.data.error.message)"' "$logfile"
            echo
        fi
    done
}

show_tools() {
    require_jq
    local logfile_pattern="${1:-*}"

    cat <<EOF
Tool Usage Analysis
====================="
EOF

    # Aggregate tool usage across sessions
    find "$LOG_DIR" -name "${logfile_pattern}*.jsonl" -type f -exec cat {} \; |
        jq -r 'select(.type == "request" and .data.method == "tools/call") | .data.params.name' |
        sort | uniq -c | sort -nr |
        awk '{printf "   %3d  %s\n", $1, $2}'
}

tail_log() {
    local session_id="${1:-}"
    local logfile

    if [[ -n "$session_id" ]]; then
        logfile=$(get_logfile "$session_id")
    else
        logfile=$(get_latest_log)
    fi

    validate_logfile "$logfile"

    cat <<EOF
Tailing: $(basename "$logfile")
Press Ctrl+C to stop

EOF

    tail -f "$logfile" | while read -r line; do
        if command -v jq >/dev/null 2>&1; then
            echo "$line" | jq -r '
                if .type == "request" and .data.method == "tools/call" then
                    "REQUEST \(.timestamp): \(.data.params.name)"
                elif .type == "response" and .data.error then
                    "ERROR \(.timestamp): \(.data.error.message)"
                elif .type == "notification" and .data.params.level == "error" then
                    "ALERT \(.timestamp): \(.data.params.message)"
                else
                    "\(.type | ascii_upcase) \(.timestamp)"
                end
            ' 2>/dev/null || echo "$line"
        else
            echo "$line"
        fi
    done
}

export_session() {
    require_jq
    local logfile=$(get_logfile "$1")
    local output_file="$2"
    validate_logfile "$logfile"

    echo "Exporting session to: $output_file"

    jq -s '{
        session_id: (.[0].session_id // "unknown"),
        export_timestamp: now | strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_file: "'"$logfile"'",
        summary: {
            total_messages: length,
            requests: [.[] | select(.type == "request")] | length,
            responses: [.[] | select(.type == "response")] | length,
            notifications: [.[] | select(.type == "notification")] | length,
            errors: [.[] | select(.type == "response" and .data.error)] | length,
            tools_used: [.[] | select(.type == "request" and .data.method == "tools/call") | .data.params.name] | unique
        },
        messages: .
    }' "$logfile" >"$output_file"

    echo "Export complete: $output_file"
}

# Show latest log info
show_latest_log_info() {
    local latest_log="$1"
    cat <<EOF
Latest log: $(basename "$latest_log")
File size: $(du -h "$latest_log" | cut -f1)
Modified: $(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$latest_log" 2>/dev/null || stat -c "%y" "$latest_log" 2>/dev/null | cut -d. -f1)
EOF
}

# Start tailing log
start_tail() {
    local latest_log="$1"
    cat <<EOF
Tailing latest log: $(basename "$latest_log")
Press Ctrl+C to stop

EOF
    tail -f "$latest_log"
}

# Main execution with improved error handling
main() {
    case "${1:-help}" in
    list) list_logs ;;
    latest)
        latest_log=$(get_latest_log)
        if [[ -n "$latest_log" ]] && [[ -f "$latest_log" ]]; then
            show_latest_log_info "$latest_log"
            show_session "$latest_log"
        else
            echo "No log files found"
            exit 1
        fi
        ;;
    show)
        [[ $# -ge 2 ]] || {
            echo "Usage: $0 show <session_id>" >&2
            exit 1
        }
        show_session "$2"
        ;;
    stats)
        [[ $# -ge 2 ]] || {
            echo "Usage: $0 stats <session_id>" >&2
            exit 1
        }
        show_stats "$2"
        ;;
    summary)
        [[ $# -ge 2 ]] || {
            echo "Usage: $0 summary <session_id>" >&2
            exit 1
        }
        summary "$2"
        ;;
    errors) show_errors "${2:-}" ;;
    tools) show_tools "${2:-}" ;;
    tail)
        if [[ $# -ge 2 ]]; then
            tail_log "$2"
        else
            # If no session ID provided, tail the latest log
            latest_log=$(get_latest_log)
            if [[ -n "$latest_log" ]] && [[ -f "$latest_log" ]]; then
                start_tail "$latest_log"
            else
                echo "No log files found to tail"
                exit 1
            fi
        fi
        ;;
    export)
        [[ $# -ge 3 ]] || {
            echo "Usage: $0 export <session_id> <output_file>" >&2
            exit 1
        }
        export_session "$2" "$3"
        ;;
    help | -h | --help) usage ;;
    *)
        echo "Unknown command: $1" >&2
        usage
        exit 1
        ;;
    esac
}

main "$@"
