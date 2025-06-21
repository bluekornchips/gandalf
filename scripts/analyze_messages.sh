#!/bin/bash

set -euo pipefail

readonly SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly GANDALF_ROOT="$(dirname "$SCRIPT_PATH")"
readonly MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
readonly LOG_DIR="$HOME/.$MCP_SERVER_NAME/conversation_logs"

export MCP_SERVER_NAME

check_log_directory() {
    [[ -d "$LOG_DIR" ]] || {
        echo "No message logs directory found at: $LOG_DIR" >&2
        exit 1
    }
}

require_jq() {
    command -v jq &>/dev/null || {
        cat >&2 <<EOF
Error: jq is required for this operation

Installation options:
    macOS:    brew install jq
    Ubuntu:   sudo apt-get install jq

EOF
        exit 1
    }
}

get_file_size() {
    local file="$1"
    if command -v du >/dev/null 2>&1; then
        du -h "$file" 2>/dev/null | cut -f1 || echo "unknown"
    elif [[ -f "$file" ]]; then
        echo "$(wc -c <"$file" 2>/dev/null || echo "0") bytes"
    else
        echo "unknown"
    fi
}

get_file_date() {
    local file="$1"
    if command -v stat >/dev/null 2>&1; then
        stat -c '%y' "$file" 2>/dev/null ||
            stat -f '%Sm' "$file" 2>/dev/null ||
            echo "unknown"
    elif command -v ls >/dev/null 2>&1; then
        ls -l "$file" 2>/dev/null | awk '{print $6, $7, $8}' || echo "unknown"
    else
        echo "unknown"
    fi
}

# Safe JSON extraction with fallbacks
safe_jq() {
    local query="$1" input="$2" default="${3:-unknown}"

    if command -v jq >/dev/null 2>&1; then
        echo "$input" | jq -r "$query" 2>/dev/null || echo "$default"
    else
        echo "$default"
    fi
}

has_error() {
    local line="$1"
    if command -v jq >/dev/null 2>&1; then
        echo "$line" | jq -e '.data.error' >/dev/null 2>&1
    else
        # uncomplicated grep fallback
        echo "$line" | grep -q '"error"' 2>/dev/null
    fi
}

# File handling utilities
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

get_latest_log() {
    check_log_directory
    find "$LOG_DIR" -name "*.jsonl" -type f | xargs ls -t | head -1
}

# Display utilities
show_header() {
    local title="$1"
    cat <<EOF
$title
"================================"
EOF
}

show_log_header() {
    local logfile="$1"
    show_header "Message Log: ${logfile##*/}"
}

show_error_header() {
    show_header "Error Messages"
}

process_log_line() {
    local line="$1"
    local type timestamp

    type=$(safe_jq '.type' "$line" "unknown")
    timestamp=$(safe_jq '.timestamp' "$line" "unknown")

    case "$type" in
    "session_start")
        local project_root pid
        project_root=$(safe_jq '.project_root' "$line" "unknown")
        pid=$(safe_jq '.pid' "$line" "unknown")
        cat <<EOF
SESSION START - $timestamp
    Project: $project_root
    PID: $pid
EOF
        ;;
    "session_end")
        local total_messages
        total_messages=$(safe_jq '.total_messages' "$line" "unknown")
        cat <<EOF
SESSION END - $timestamp
    Total Messages: $total_messages
EOF
        ;;
    "request")
        local method
        method=$(safe_jq '.data.method' "$line" "unknown")
        echo "REQUEST - $timestamp - $method"

        case "$method" in
        "tools/call")
            local tool_name
            tool_name=$(safe_jq '.data.params.name' "$line" "unknown")
            echo "   Tool: $tool_name"
            ;;
        esac
        ;;
    "response")
        echo "RESPONSE - $timestamp"

        if has_error "$line"; then
            local error_msg
            error_msg=$(safe_jq '.data.error.message' "$line" "unknown error")
            echo "   Error: $error_msg"
        else
            echo "   Success"
        fi
        ;;
    "notification")
        local method level message
        method=$(safe_jq '.data.method' "$line" "unknown")
        level=$(safe_jq '.data.params.level' "$line" "unknown")
        message=$(safe_jq '.data.params.message' "$line" "unknown")
        echo "NOTIFICATION - $timestamp - $method ($level)"
        echo "   $message"
        ;;
    *)
        echo "UNKNOWN - $timestamp - $type"
        ;;
    esac
    echo
}

format_tail_line() {
    local line="$1"

    command -v jq &>/dev/null || {
        echo "$line"
        return
    }

    local type timestamp
    type=$(safe_jq '.type' "$line" "")
    timestamp=$(safe_jq '.timestamp' "$line" "")

    case "$type" in
    "request")
        local method
        method=$(safe_jq '.data.method' "$line" "")
        case "$method" in
        "tools/call")
            local tool_name
            tool_name=$(safe_jq '.data.params.name' "$line" "unknown")
            echo "REQUEST $timestamp: $tool_name"
            ;;
        *)
            echo "REQUEST $timestamp: $method"
            ;;
        esac
        ;;
    "response")
        if has_error "$line"; then
            local error_msg
            error_msg=$(safe_jq '.data.error.message' "$line" "unknown error")
            echo "ERROR $timestamp: $error_msg"
        else
            echo "RESPONSE $timestamp: Success"
        fi
        ;;
    "notification")
        local level
        level=$(safe_jq '.data.params.level' "$line" "")
        case "$level" in
        "error")
            local message
            message=$(safe_jq '.data.params.message' "$line" "unknown")
            echo "ALERT $timestamp: $message"
            ;;
        *)
            echo "NOTIFICATION $timestamp: $level"
            ;;
        esac
        ;;
    "")
        echo "$line"
        ;;
    *)
        echo "${type^^} $timestamp"
        ;;
    esac
}

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
    check_log_directory

    show_header "Available message log files:"

    find "$LOG_DIR" -name "*.jsonl" -type f | while read -r logfile; do
        local filename="${logfile##*/}"
        local session_id size
        session_id=$(echo "$filename" | grep -o '[a-f0-9]\{16\}' | head -1)
        size=$(du -h "$logfile" | cut -f1)
        printf "%-60s %s (%s)\n" "$filename" "$session_id" "$size"
    done | sort
}

show_session() {
    require_jq
    local logfile
    logfile=$(get_logfile "$1")
    validate_logfile "$logfile"

    show_log_header "$logfile"

    while IFS= read -r line; do
        process_log_line "$line"
    done <"$logfile"
}

show_stats() {
    require_jq
    local logfile
    logfile=$(get_logfile "$1")
    validate_logfile "$logfile"

    show_header "Statistics for Session: ${logfile##*/%.jsonl}"

    local total_count=0 request_count=0 response_count=0
    local notification_count=0 error_count=0
    local start_time="unknown" end_time="unknown"

    while IFS= read -r line; do
        ((total_count++))

        local type
        type=$(safe_jq '.type' "$line" "")

        case "$type" in
        "request") ((request_count++)) ;;
        "response")
            ((response_count++))
            has_error "$line" && ((error_count++))
            ;;
        "notification") ((notification_count++)) ;;
        "session_start") start_time=$(safe_jq '.timestamp' "$line" "unknown") ;;
        "session_end") end_time=$(safe_jq '.timestamp' "$line" "unknown") ;;
        esac
    done <"$logfile"

    cat <<EOF
Total Messages: $total_count
Requests: $request_count
Responses: $response_count
Notifications: $notification_count
Errors: $error_count

Timeline:
Start: $start_time
End: $end_time

Tool Usage:
EOF

    if command -v grep >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
        grep -h '"tools/call"' "$logfile" 2>/dev/null |
            jq -r '.data.params.name // "unknown"' 2>/dev/null |
            sort | uniq -c | sort -nr |
            sed 's/^/   /'
    else
        echo "jq or grep not available for tool analysis"
    fi
}

show_summary() {
    require_jq
    local logfile
    logfile=$(get_logfile "$1")
    validate_logfile "$logfile"

    local session_id="unknown" project_root="unknown"
    local start_time="unknown" end_time="ongoing"
    local total_messages=0 error_count=0
    local -a tools_used=()

    while IFS= read -r line; do
        ((total_messages++))

        local type
        type=$(safe_jq '.type' "$line" "")

        case "$type" in
        "session_start")
            session_id=$(safe_jq '.session_id' "$line" "unknown")
            project_root=$(safe_jq '.project_root' "$line" "unknown")
            start_time=$(safe_jq '.timestamp' "$line" "unknown")
            ;;
        "session_end")
            end_time=$(safe_jq '.timestamp' "$line" "unknown")
            ;;
        "request")
            local method
            method=$(safe_jq '.data.method' "$line" "")
            if [[ "$method" == "tools/call" ]]; then
                local tool_name
                tool_name=$(safe_jq '.data.params.name' "$line" "")
                [[ -n "$tool_name" && "$tool_name" != "unknown" ]] && tools_used+=("$tool_name")
            fi
            ;;
        "response")
            has_error "$line" && ((error_count++))
            ;;
        esac
    done <"$logfile"

    local unique_tools="none"
    if [[ ${#tools_used[@]} -gt 0 ]]; then
        local -A unique_tools_map
        for tool in "${tools_used[@]}"; do
            unique_tools_map["$tool"]=1
        done
        unique_tools=$(printf '%s, ' "${!unique_tools_map[@]}" | sed 's/, $//')
    fi

    cat <<EOF
Session Summary: $session_id
Project: $project_root
Duration: $start_time to $end_time
Tools Used: $unique_tools
Total Messages: $total_messages
Errors: $error_count
EOF
}

show_errors() {
    require_jq
    local logfile_pattern="${1:-*}"

    show_error_header

    find "$LOG_DIR" -name "${logfile_pattern}*.jsonl" -type f | while read -r logfile; do
        local filename="${logfile##*/}"
        local error_count=0
        local -a errors_found=()

        while IFS= read -r line; do
            local type
            type=$(safe_jq '.type' "$line" "")

            if [[ "$type" == "response" ]] && has_error "$line"; then
                ((error_count++))
                local timestamp error_msg
                timestamp=$(safe_jq '.timestamp' "$line" "unknown")
                error_msg=$(safe_jq '.data.error.message' "$line" "unknown error")
                errors_found+=("   Error $timestamp: $error_msg")
            fi
        done <"$logfile"

        if [[ $error_count -gt 0 ]]; then
            echo "$filename ($error_count errors)"
            printf '%s\n' "${errors_found[@]}"
            echo
        fi
    done
}

show_tools() {
    require_jq
    local logfile_pattern="${1:-*}"

    show_header "Tool Usage Analysis"

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

    show_header "Tailing: ${logfile##*/}"
    echo -e "Press Ctrl+C to stop\n"

    tail -f "$logfile" | while read -r line; do
        format_tail_line "$line"
    done
}

export_session() {
    require_jq
    local logfile output_file
    logfile=$(get_logfile "$1")
    output_file="$2"
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

show_latest_log_info() {
    local latest_log="$1"
    cat <<EOF
Latest log: ${latest_log##*/}
File size: $(get_file_size "$latest_log")
Modified: $(get_file_date "$latest_log")
EOF
}

start_tail() {
    local latest_log="$1"
    show_header "Tailing latest log: ${latest_log##*/}"
    echo -e "Press Ctrl+C to stop\n"
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
        show_summary "$2"
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
