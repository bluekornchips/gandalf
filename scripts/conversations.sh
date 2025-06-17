#!/bin/bash
set -eo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

JQ_AVAILABLE=true
if ! command -v jq >/dev/null 2>&1 || ! jq --version >/dev/null 2>&1; then
    JQ_AVAILABLE=false
fi

usage() {
    cat <<'EOF'
Usage: gandalf.sh conv [COMMAND] [OPTIONS]

Simple conversation storage.

Commands:
    store ID [OPTIONS]         Store conversation with ID (reads JSON from stdin)
    list [OPTIONS]             List stored conversations (shows most recent 20 by default)
    show ID [OPTIONS]          Show conversation details
    stats                      Show conversation statistics
    cleanup DAYS               Remove conversations older than DAYS
    clear                      Move all conversations to backup folder
    auto [OPTIONS]             Auto-capture current session and store it
    help                       Show this help

Options:
    -t TITLE                   Set conversation title
    -g TAGS                    Set comma-separated tags
    -f FORMAT                  Output format (roles, messages, json, text) - default: text
    -n LIMIT                   Limit number of results (default: 20 for list command)
    --test                     Skip storing (test mode)

Examples:
    echo '[{"role":"user","content":"Hello"}]' | gdlf conv store "test-conv" -t "Test"
    gdlf conv list                                    # Show most recent 20 conversations
    gdlf conv list -n 5                              # Show most recent 5 conversations
    gdlf conv show test-conv -f messages
    gdlf conv stats

EOF
}

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
CONV_DIR="${HOME}/.gandalf/conversations/${PROJECT_NAME}"
BACKUP_DIR="${HOME}/.gandalf/history/${PROJECT_NAME}"

DATE_ISO=$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)

IS_TEST=false
TITLE=""
TAGS=""
FORMAT="text"
LIMIT=""
ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
    --test) IS_TEST=true && shift ;;
    -t) TITLE="$2" && shift 2 ;;
    -g) TAGS="$2" && shift 2 ;;
    -f) FORMAT="$2" && shift 2 ;;
    -n) LIMIT="$2" && shift 2 ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        ARGS+=("$1")
        shift
        ;;
    esac
done

mkdir -p "$CONV_DIR"

if [[ ${#ARGS[@]} -eq 0 ]]; then
    usage
    exit 1
fi

COMMAND="${ARGS[0]}"
CONV_ID="${ARGS[1]}"

resolve_conv_id() {
    local pattern="$1"
    [[ ${#pattern} -eq 16 ]] && echo "$pattern" && return

    local matches=($(find "$CONV_DIR" -name "${pattern}*.json" 2>/dev/null))
    case ${#matches[@]} in
    0) return 1 ;;
    1) basename "${matches[0]}" .json ;;
    *)
        echo "Ambiguous ID '$pattern'" >&2
        return 1
        ;;
    esac
}

# Show conversation in different formats
show_conversation() {
    local file="$1"
    local format="$2"

    # Check if jq is available
    if [[ "$JQ_AVAILABLE" == "false" ]]; then
        cat <<EOF
=== Conversation File Contents ===
$(cat "$file")

Note: Install jq for formatted output

EOF
        return
    fi

    case "$format" in
    roles)
        jq -r '.messages[]?.role // empty' "$file"
        ;;
    messages)
        # Enhanced format for analytics conversations with metadata
        jq -r '.messages[]? | 
            if .metadata then
                if .metadata.full_result.content[0].text then
                    "[\(.role // "unknown")] \(.metadata.full_result.content[0].text)"
                elif .metadata.tool_name then
                    # Analytics conversation with tool metadata
                    if .role == "user" then
                        "[\(.role)] Called \(.metadata.tool_name)" + 
                        (if .metadata.arguments then " with args: \(.metadata.arguments | tostring)" else "" end) +
                        (if .timestamp then " at \(.timestamp)" else "" end)
                    else
                        "[\(.role)] Tool \(.metadata.tool_name) executed successfully" +
                        (if .timestamp then " at \(.timestamp)" else "" end)
                    end
                else
                    "[\(.role // "unknown")] \(.content // "")"
                end
            else
                "[\(.role // "unknown")] \(.content // "")"
            end' "$file"
        ;;
    json)
        jq . "$file"
        ;;
    text | *)
        # Text format for compatibility with tests
        local conv_id=$(jq -r '.conversation_id' "$file")
        local title=$(jq -r '.title // ""' "$file")
        cat <<EOF
# Conversation: $conv_id
Title: $title
## Messages
EOF
        # Check for metadata with full content
        jq -r '.messages[]? | 
            if .metadata then
                if .metadata.full_result.content[0].text then
                    "[\(.role // "unknown")] \(.metadata.full_result.content[0].text)"
                elif .metadata.tool_name then
                    # Analytics conversation with tool metadata
                    if .role == "user" then
                        "[\(.role)] Called \(.metadata.tool_name)" + 
                        (if .metadata.arguments then " with args: \(.metadata.arguments | tostring)" else "" end) +
                        (if .timestamp then " at \(.timestamp)" else "" end)
                    else
                        "[\(.role)] Tool \(.metadata.tool_name) executed successfully" +
                        (if .timestamp then " at \(.timestamp)" else "" end)
                    end
                else
                    "[\(.role // "unknown")] \(.content // "")"
                end
            else
                "[\(.role // "unknown")] \(.content // "")"
            end' "$file"
        ;;
    esac
}

store_conversation() {
    [[ -z "$CONV_ID" ]] && {
        echo "Conversation ID required" >&2
        exit 1
    }
    [[ "$IS_TEST" == "true" ]] && {
        cat >/dev/null
        echo "Test mode - not stored"
        exit 0
    }

    local messages=$(cat)

    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        echo "$messages" | jq . >/dev/null || {
            echo "Invalid JSON" >&2
            exit 1
        }
    fi

    # Generate hash-based ID if not 16 chars
    local actual_id
    if [[ ${#CONV_ID} -ne 16 ]]; then
        if [[ "$JQ_AVAILABLE" == "true" ]]; then
            local content_hash=$(echo "$messages" | jq -cS . | openssl dgst -sha256 | cut -d' ' -f2)
        else
            local content_hash=$(echo "$messages" | openssl dgst -sha256 | cut -d' ' -f2)
        fi
        actual_id="${content_hash:0:16}"
    else
        actual_id="$CONV_ID"
    fi

    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        local tags_json
        if [[ -n "$TAGS" ]]; then
            tags_json=$(echo "$TAGS" | tr ',' '\n' | jq -Rs 'split("\n") | map(select(. != ""))')
        else
            tags_json="[]"
        fi

        local message_count=$(echo "$messages" | jq 'length')

        # Create conversation file
        jq -n \
            --arg id "$actual_id" \
            --arg title "$TITLE" \
            --arg project "$PROJECT_NAME" \
            --arg created "$DATE_ISO" \
            --argjson tags "$tags_json" \
            --argjson messages "$messages" \
            --argjson count "$message_count" \
            '{
                conversation_id: $id,
                title: $title,
                project_name: $project,
                created_at: $created,
                tags: $tags,
                messages: $messages,
                message_count: $count
            }' >"$CONV_DIR/$actual_id.json"
    else
        # Fallback: create a simple JSON structure manually
        cat >"$CONV_DIR/$actual_id.json" <<EOF
{
    "conversation_id": "$actual_id",
    "title": "$TITLE",
    "project_name": "$PROJECT_NAME",
    "created_at": "$DATE_ISO",
    "tags": [],
    "messages": $messages,
    "message_count": 1
}
EOF
    fi

    cat <<EOF
Stored conversation: ${actual_id:0:9} ($TITLE)
Full ID: $actual_id

EOF
}

list_conversations() {
    [[ ! -d "$CONV_DIR" ]] && {
        echo "No conversations found."
        exit 0
    }

    # Check if there are any JSON files
    local json_files=($(find "$CONV_DIR" -name "*.json" 2>/dev/null))
    [[ ${#json_files[@]} -eq 0 ]] && {
        echo "No conversations found."
        exit 0
    }

    if [[ "$JQ_AVAILABLE" == "false" ]]; then
        echo "=== Conversation Files ==="
        for file in "${json_files[@]}"; do
            cat <<EOF
File: $(basename "$file")
---
$(cat "$file")

EOF
        done
        echo "Note: Install jq for formatted output"
        return
    fi

    local display_limit="${LIMIT:-20}"

    # Sort by file modification time first (much faster than parsing JSON)
    local sorted_files=($(ls -t "${json_files[@]}" 2>/dev/null | head -n "$display_limit"))

    if [[ "$FORMAT" == "json" ]]; then
        local temp_file=$(mktemp)
        echo "[" >"$temp_file"
        local first=true

        for file in "${sorted_files[@]}"; do
            if jq . "$file" >/dev/null 2>&1; then
                [[ "$first" == "false" ]] && echo "," >>"$temp_file"
                jq -c . "$file" >>"$temp_file"
                first=false
            fi
        done
        echo "]" >>"$temp_file"
        cat "$temp_file"
        rm -f "$temp_file"
    else
        printf "%-12s %-16s %-8s %s\n" "ID" "Created" "Messages" "Title"
        printf "%s\n" "$(printf '%.0s-' {1..60})"

        # Only parse JSON for the files we're actually displaying
        for file in "${sorted_files[@]}"; do
            if jq . "$file" >/dev/null 2>&1; then
                local json_data=$(jq -r '[.conversation_id[:9], .created_at[:16], .message_count, (.title // "<no title>")] | @tsv' "$file" 2>/dev/null)
                if [[ -n "$json_data" ]]; then
                    # Parse the tab-separated values properly
                    IFS=$'\t' read -r id created count title <<<"$json_data"
                    printf "%-12s %-16s %-8s %s\n" "$id" "$created" "$count" "$title"
                fi
            fi
        done
    fi
}

show_conversation_details() {
    [[ -z "$CONV_ID" ]] && {
        echo "Conversation ID required" >&2
        exit 1
    }

    local full_id=$(resolve_conv_id "$CONV_ID") || {
        echo "Conversation not found: $CONV_ID" >&2
        exit 1
    }
    local file="$CONV_DIR/$full_id.json"
    [[ ! -f "$file" ]] && {
        echo "Conversation not found: $CONV_ID" >&2
        exit 1
    }

    show_conversation "$file" "$FORMAT"
}

show_conversation_stats() {
    [[ ! -d "$CONV_DIR" ]] && {
        echo "No conversations found."
        exit 0
    }

    local json_files=($(find "$CONV_DIR" -name "*.json" 2>/dev/null))
    [[ ${#json_files[@]} -eq 0 ]] && {
        echo "No conversations found."
        exit 0
    }

    local total_convs=${#json_files[@]}
    local total_msgs=0

    if [[ "$JQ_AVAILABLE" == "true" ]]; then
        for file in "${json_files[@]}"; do
            if jq . "$file" >/dev/null 2>&1; then
                local count=$(jq '.message_count // 0' "$file" 2>/dev/null || echo "0")
                total_msgs=$((total_msgs + count))
            fi
        done
    else
        # Fallback: estimate message count
        total_msgs="unknown (jq not available)"
    fi

    cat <<EOF
Total Conversations: $total_convs
Total Messages: $total_msgs
Storage Location: $CONV_DIR

EOF
}

cleanup_old_conversations() {
    local days="${ARGS[1]}"
    [[ -z "$days" || ! "$days" =~ ^[0-9]+$ ]] && {
        echo "Days must be a positive number" >&2
        exit 1
    }
    [[ ! -d "$CONV_DIR" ]] && {
        echo "No conversations to clean up."
        exit 0
    }

    local cutoff_time=$(($(date +%s) - (days * 86400)))
    local cleaned=0
    local json_files=($(find "$CONV_DIR" -name "*.json" 2>/dev/null))

    for file in "${json_files[@]}"; do
        # Check both file modification time and created_at in JSON
        local file_time=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null || echo "0")
        local json_time=0

        if jq . "$file" >/dev/null 2>&1; then
            local created_at=$(jq -r '.created_at // ""' "$file" 2>/dev/null)
            if [[ -n "$created_at" ]]; then
                json_time=$(date -d "$created_at" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${created_at%.*}" +%s 2>/dev/null || echo "0")
            fi
        fi

        # Use the older of the two times
        local check_time=$file_time
        [[ $json_time -gt 0 && $json_time -lt $file_time ]] && check_time=$json_time

        if [[ $check_time -lt $cutoff_time ]]; then
            rm -f "$file"
            ((cleaned++))
        fi
    done

    echo "Cleaned up $cleaned conversations older than $days days."
}

clear_all_conversations() {
    [[ ! -d "$CONV_DIR" ]] && {
        echo "No conversations to clear."
        exit 0
    }

    local backup_dir="$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"

    local conv_count=$(find "$CONV_DIR" -name "*.json" 2>/dev/null | wc -l)
    find "$CONV_DIR" -name "*.json" -exec mv {} "$backup_dir/" \; 2>/dev/null

    echo "Cleared $conv_count conversations to: $backup_dir"
}

auto_capture_conversation() {
    local test_messages=$(cat)
    echo "$test_messages" | jq . >/dev/null || {
        echo "Invalid JSON input for auto-capture" >&2
        exit 1
    }

    # Generate auto ID
    local content_hash=$(echo "$test_messages" | jq -cS . | openssl dgst -sha256 | cut -d' ' -f2)
    local auto_id="${content_hash:0:16}"

    local tags_json
    if [[ -n "$TAGS" ]]; then
        tags_json=$(echo "$TAGS" | tr ',' '\n' | jq -Rs 'split("\n") | map(select(. != ""))')
    else
        tags_json='["auto"]'
    fi

    local message_count=$(echo "$test_messages" | jq 'length')
    local title="${TITLE:-Auto-captured Session}"

    # Create conversation file
    jq -n \
        --arg id "$auto_id" \
        --arg title "$title" \
        --arg project "$PROJECT_NAME" \
        --arg created "$DATE_ISO" \
        --argjson tags "$tags_json" \
        --argjson messages "$test_messages" \
        --argjson count "$message_count" \
        '{
            conversation_id: $id,
            title: $title,
            project_name: $project,
            created_at: $created,
            tags: $tags,
            messages: $messages,
            message_count: $count
        }' >"$CONV_DIR/$auto_id.json"

    echo "Auto-captured conversation successfully: ${auto_id:0:9} ($title)"
    echo "View with: gdlf conv show ${auto_id:0:8}"
}

case "$COMMAND" in
store) store_conversation ;;
list) list_conversations ;;
show) show_conversation_details ;;
stats) show_conversation_stats ;;
cleanup) cleanup_old_conversations ;;
auto) auto_capture_conversation ;;
clear) clear_all_conversations ;;
help | -h | --help)
    usage
    ;;
*)
    echo "Unknown command: $COMMAND" >&2
    usage
    exit 1
    ;;
esac
