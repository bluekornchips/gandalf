#!/usr/bin/env bats

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required for load_generic_content tests" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required for load_generic_content tests" >&2
    exit 1
fi

GIT_ROOT=$(git rev-parse --show-toplevel)
GANDALF_ROOT="$GIT_ROOT/gandalf"
CONTENT_LOADER_PATH="$GANDALF_ROOT/server/src/content/load_generic_content.py"
TEST_HELPER="$GANDALF_ROOT/tests/helpers/test_load_generic_content.py"

ORIGINAL_HOME="$HOME"
TEST_HOME=""

create_test_json_conversation() {
    local title="$1"
    local message_count="${2:-2}"
    jq -nc \
        --arg title "$title" \
        --argjson count "$message_count" \
        '[{
            "conversation_id": "test-123",
            "title": $title,
            "message_count": $count,
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        }]'
}

create_test_json_data() {
    jq -nc '{
        "name": "test_data",
        "version": "1.0",
        "features": ["json", "loading", "testing"],
        "metadata": {
            "created": "2024-01-01",
            "author": "test_suite"
        }
    }'
}

create_test_text_content() {
    cat <<EOF
This is a test text file
with multiple lines
for testing the generic content loader.

Line 5
Line 6
Line 7
Line 8
Line 9
Line 10
Line 11 - this should be truncated in preview
Line 12 - this should also be truncated
EOF
}

load_content() {
    local data_path="$1"
    local context_name="${2:-test_context}"

    python3 "$TEST_HELPER" "$data_path" --context-name "$context_name"
}

create_large_json() {
    local output_file="$1"
    # Create large JSON with lots of nested data using shell/jq instead of python
    jq -nc \
        --argjson size 100 \
        '{
            large_array: [range($size) | {item: ., data: ("x" * 100)}],
            nested: {deep: {very: {much: {data: "here"}}}}
        }' >"$output_file"
}

check_import() {
    python3 "$TEST_HELPER" --check-import
}

check_class_import() {
    python3 "$TEST_HELPER" --check-class
}

setup() {
    TEST_HOME=$(mktemp -d)
    export HOME="$TEST_HOME"
}

teardown() {
    export HOME="$ORIGINAL_HOME"
    if [[ -n "$TEST_HOME" && -d "$TEST_HOME" ]]; then
        rm -rf "$TEST_HOME"
    fi
}

@test "load_generic_content.py module exists and is executable" {
    [ -f "$CONTENT_LOADER_PATH" ]
    [ -r "$CONTENT_LOADER_PATH" ]
}

@test "load_flat_context_data function is importable" {
    run check_import
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Import successful"
}

@test "GenericContentLoader class is importable" {
    run check_class_import
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Class import successful"
}

@test "Load non-existent file, should return None" {
    run load_content "/non/existent/path.txt"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "None"
}

@test "Load non-existent directory, should return None" {
    run load_content "/non/existent/directory"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "None"
}

@test "Load empty file, should pass" {
    test_file="$TEST_HOME/empty.txt"
    touch "$test_file"

    run load_content "$test_file" "empty_file"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: empty_file ==="
    echo "$output" | grep -q "Text file with 1 lines:"
}

@test "Load simple text file, should pass" {
    test_file="$TEST_HOME/test.txt"
    echo "Hello World" >"$test_file"

    run load_content "$test_file" "simple_text"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: simple_text ==="
    echo "$output" | grep -q "Text file with 2 lines:"
    echo "$output" | grep -q "Hello World"
}

@test "Load multi-line text file with truncation, should pass" {
    test_file="$TEST_HOME/multiline.txt"
    create_test_text_content >"$test_file"

    run load_content "$test_file" "multiline_text"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: multiline_text ==="
    echo "$output" | grep -q "Text file with 13 lines:"
    echo "$output" | grep -q "Line 10"
    echo "$output" | grep -q "... and 3 more lines"
    ! echo "$output" | grep -q "Line 11"
}

@test "Load valid JSON file, should pass" {
    test_file="$TEST_HOME/data.json"
    create_test_json_data >"$test_file"

    run load_content "$test_file" "json_data"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: json_data ==="
    echo "$output" | grep -q "JSON data:"
    echo "$output" | grep -q "test_data"
    echo "$output" | grep -q "features"
}

@test "Load conversation JSON file, should pass" {
    test_file="$TEST_HOME/conversation.json"
    create_test_json_conversation "Test Conversation" 2 >"$test_file"

    run load_content "$test_file" "conversation_data"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: conversation_data ==="
    echo "$output" | grep -q "Conversation data with 1 entries:"
    echo "$output" | grep -q "Test Conversation"
    echo "$output" | grep -q "(2 messages)"
}

@test "Load multiple conversation entries JSON, should pass" {
    test_file="$TEST_HOME/conversations.json"

    jq -nc '[
        {
            "conversation_id": "conv-1",
            "title": "First Chat",
            "message_count": 3,
            "messages": []
        },
        {
            "conversation_id": "conv-2", 
            "title": "Second Chat",
            "message_count": 5,
            "messages": []
        },
        {
            "conversation_id": "conv-3",
            "title": "Third Chat", 
            "message_count": 2,
            "messages": []
        },
        {
            "conversation_id": "conv-4",
            "title": "Fourth Chat",
            "message_count": 1,
            "messages": []
        },
        {
            "conversation_id": "conv-5",
            "title": "Fifth Chat",
            "message_count": 4,
            "messages": []
        },
        {
            "conversation_id": "conv-6",
            "title": "Sixth Chat",
            "message_count": 7,
            "messages": []
        }
    ]' >"$test_file"

    run load_content "$test_file" "multiple_conversations"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: multiple_conversations ==="
    echo "$output" | grep -q "Conversation data with 6 entries:"
    echo "$output" | grep -q "First Chat"
    echo "$output" | grep -q "Fifth Chat"
    echo "$output" | grep -q "... and 1 more"
    ! echo "$output" | grep -q "Sixth Chat"
}

@test "Load malformed JSON file, should handle gracefully" {
    test_file="$TEST_HOME/bad.json"
    echo '{"invalid": json missing quote}' >"$test_file"

    run load_content "$test_file" "bad_json"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: bad_json ==="
    echo "$output" | grep -q "Raw content:"
    echo "$output" | grep -q "invalid"
}

@test "Load binary-like file, should handle gracefully" {
    test_file="$TEST_HOME/binary.dat"
    # Create file with some binary-ish content: "legolas", but as bytes.
    printf '\x6c\x65\x67\x6f\x6c\x61\x73' >"$test_file"

    run load_content "$test_file" "binary_data"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: binary_data ==="
}

@test "Load empty directory, should pass" {
    test_dir="$TEST_HOME/empty_dir"
    mkdir -p "$test_dir"

    run load_content "$test_dir" "empty_directory"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: empty_directory ==="
    echo "$output" | grep -q "Directory with 0 loadable files:"
}

@test "Load directory with single file, should pass" {
    test_dir="$TEST_HOME/single_file_dir"
    mkdir -p "$test_dir"
    echo "Single file content" >"$test_dir/file.txt"

    run load_content "$test_dir" "single_file_directory"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: single_file_directory ==="
    echo "$output" | grep -q "Directory with 1 loadable files:"
    echo "$output" | grep -q "\-\-\- file.txt \-\-\-"
    echo "$output" | grep -q "Single file content"
}

@test "Load directory with multiple files, should pass" {
    test_dir="$TEST_HOME/multi_file_dir"
    mkdir -p "$test_dir"

    echo "First file" >"$test_dir/first.txt"
    echo "Second file" >"$test_dir/second.log"
    create_test_json_data >"$test_dir/data.json"
    echo "# Markdown content" >"$test_dir/readme.md"

    run load_content "$test_dir" "multi_file_directory"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: multi_file_directory ==="
    echo "$output" | grep -q "Directory with 4 loadable files:"
    echo "$output" | grep -q "\-\-\- first.txt \-\-\-"
    echo "$output" | grep -q "\-\-\- data.json \-\-\-"
    echo "$output" | grep -q "First file"
    echo "$output" | grep -q "JSON data:"
}

@test "Load directory with many files, should truncate at 5" {
    test_dir="$TEST_HOME/many_files_dir"
    mkdir -p "$test_dir"

    for i in {1..8}; do
        echo "File $i content" >"$test_dir/file$i.txt"
    done

    run load_content "$test_dir" "many_files_directory"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: many_files_directory ==="
    echo "$output" | grep -q "Directory with 8 loadable files:"
    echo "$output" | grep -q "\-\-\- file1.txt \-\-\-"
    echo "$output" | grep -q "\-\-\- file5.txt \-\-\-"
    echo "$output" | grep -q "... and 3 more files"
    ! echo "$output" | grep -q "\-\-\- file6.txt \-\-\-"
}

@test "Load directory with nested structure, should handle recursively" {
    test_dir="$TEST_HOME/nested_dir"
    mkdir -p "$test_dir/subdir1/subdir2"

    echo "Root file" >"$test_dir/root.txt"
    echo "Sub file 1" >"$test_dir/subdir1/sub1.txt"
    echo "Sub file 2" >"$test_dir/subdir1/subdir2/sub2.txt"

    run load_content "$test_dir" "nested_directory"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: nested_directory ==="
    echo "$output" | grep -q "Directory with 3 loadable files:"
    echo "$output" | grep -q "Root file"
    echo "$output" | grep -q "Sub file"
}

@test "Load directory with mixed file types, should filter correctly" {
    test_dir="$TEST_HOME/mixed_types_dir"
    mkdir -p "$test_dir"

    echo "Text content" >"$test_dir/text.txt"
    create_test_json_data >"$test_dir/data.json"
    echo "Log entry" >"$test_dir/app.log"
    echo "# Documentation" >"$test_dir/docs.md"
    echo "Binary content" >"$test_dir/binary.bin"
    echo "Python code" >"$test_dir/script.py"
    echo "Image data" >"$test_dir/image.jpg"

    run load_content "$test_dir" "mixed_types_directory"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: mixed_types_directory ==="
    echo "$output" | grep -q "Directory with 4 loadable files:"
    echo "$output" | grep -q "Text content"
    echo "$output" | grep -q "JSON data:"
    echo "$output" | grep -q "Log entry"
    echo "$output" | grep -q "Documentation"
    ! echo "$output" | grep -q "Binary content"
    ! echo "$output" | grep -q "Python code"
}

@test "Load with custom context name, should use provided name" {
    test_file="$TEST_HOME/custom.txt"
    echo "Custom content" >"$test_file"

    run load_content "$test_file" "my_custom_context_name"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: my_custom_context_name ==="
    echo "$output" | grep -q "=== End Context: my_custom_context_name ==="
}

@test "Load with default context name, should use default" {
    test_file="$TEST_HOME/default.txt"
    echo "Default content" >"$test_file"

    # Use the default by not specifying context name
    run python3 "$TEST_HELPER" "$test_file"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: external_data ==="
    echo "$output" | grep -q "=== End Context: external_data ==="
}

@test "Load large JSON content, should truncate appropriately" {
    test_file="$TEST_HOME/large.json"
    create_large_json "$test_file"

    run load_content "$test_file" "large_json"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: large_json ==="
    echo "$output" | grep -q "JSON data:"
    echo "$output" | grep -q "..."
}

@test "Load file with special characters, should handle encoding" {
    test_file="$TEST_HOME/special.txt"
    echo -e "Special chars: áéíóú\nUnicode: ñ ü ß" >"$test_file"

    run load_content "$test_file" "special_chars"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: special_chars ==="
    echo "$output" | grep -q "Special chars"
}

@test "Load symlink to file, should follow link" {
    test_file="$TEST_HOME/original.txt"
    test_link="$TEST_HOME/symlink.txt"
    echo "Original content" >"$test_file"
    ln -s "$test_file" "$test_link"

    run load_content "$test_link" "symlink_test"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: symlink_test ==="
    echo "$output" | grep -q "Original content"
}

@test "Load directory with hidden files, should include loadable hidden files" {
    test_dir="$TEST_HOME/hidden_files_dir"
    mkdir -p "$test_dir"

    echo "Visible content" >"$test_dir/visible.txt"
    echo "Hidden content" >"$test_dir/.hidden.txt"
    echo "Hidden log" >"$test_dir/.hidden.log"

    run load_content "$test_dir" "hidden_files"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "=== Loaded Context: hidden_files ==="
    echo "$output" | grep -q "Directory with 3 loadable files:"
    echo "$output" | grep -q "Visible content"
    echo "$output" | grep -q "Hidden content"
}

@test "Unicode and special characters, should pass" {
    local test_file="$TEST_HOME/unicode_test.txt"
    echo -e "Special chars: áéíóú\nUnicode: ñ ü ß" >"$test_file"

    run python3 "$TEST_HELPER" "$test_file"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Special chars"
    echo "$output" | grep -q "Unicode"
}
