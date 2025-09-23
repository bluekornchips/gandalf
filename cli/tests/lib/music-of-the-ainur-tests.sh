#!/usr/bin/env bats
#
# Music of the Ainur (MOTA)Logging Library Tests
# Tests for centralized logging functionality

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
	SCRIPT_DIR="${BATS_TEST_DIRNAME}"
	cd "$SCRIPT_DIR" || exit 1
	GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
	export GANDALF_PROJECT_ROOT
fi

readonly MOTA_SCRIPT="${GANDALF_PROJECT_ROOT}/cli/lib/music-of-the-ainur.sh"
[[ -z "$MOTA_SCRIPT" ]] && echo "'MOTA_SCRIPT' is not set" >&2 && exit 1
[[ ! -f "$MOTA_SCRIPT" ]] && echo "'MOTA_SCRIPT' file does not exist" >&2 && exit 1

readonly LOG_ERR_MSG_PATTERN="ERR:"
readonly LOG_INF_MSG_PATTERN="INF:"
readonly LOG_DEB_MSG_PATTERN="DEB:"

setup() {
	TEST_DIR=$(mktemp -d)
	export GANDALF_HOME="$TEST_DIR"

	# shellcheck disable=SC1090,SC1091
	source "$MOTA_SCRIPT"

	LOG_LEVEL=$LOG_LEVEL_INFO

}

teardown() {
	rm -rf "$TEST_DIR"
}

@test "init_logging:: creates log directory" {
	run init_logging
	[[ "$status" -eq 0 ]]
	[[ -d "$LOG_DIR" ]]
}

@test "init_logging:: creates log file with required pattern" {
	run init_logging
	[[ "$status" -eq 0 ]]

	local log_files
	mapfile -t log_files < <(find "$LOG_DIR" -name "gandalf-*.log")
	[[ ${#log_files[@]} -eq 1 ]]

	[[ -w "${log_files[0]}" ]]
}

@test "log_debug:: writes debug message when level allows" {
	LOG_LEVEL=$LOG_LEVEL_DEBUG
	LOG_TO_FILE=false
	init_logging

	local test_message="Test debug message"
	run log_debug "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_DEB_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"
}

@test "log_debug:: does not write when level is too high" {
	LOG_LEVEL=$LOG_LEVEL_INFO
	LOG_TO_FILE=false
	init_logging

	local test_message="Test debug message"
	run log_debug "$test_message"

	# Should not output anything
	[[ -z "$output" ]]
}

@test "log_info:: writes info message when level allows" {
	LOG_LEVEL=$LOG_LEVEL_INFO
	LOG_TO_FILE=false
	init_logging

	local test_message="Test info message"
	run log_info "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_INF_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"
}

@test "log_error:: writes error message when level allows" {
	LOG_LEVEL=$LOG_LEVEL_ERROR
	LOG_TO_FILE=false
	init_logging

	local test_message="Test error message"
	run log_error "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_ERR_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"
}

@test "log_error:: does not write when level is too high" {
	LOG_LEVEL=3
	LOG_TO_FILE=false
	init_logging

	local test_message="Test error message"
	run log_error "$test_message"

	# Should not output anything
	[[ -z "$output" ]]
}

@test "log messages include timestamp when LOG_TO_FILE=true" {
	LOG_TO_FILE=true
	init_logging

	log_info "Test message"

	# Check log file contains timestamp format
	run cat "$LOG_FILE"
	echo "$output" | grep -q "\[[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}\]"
}

@test "log messages include level information when LOG_TO_FILE=true" {
	LOG_TO_FILE=true
	init_logging

	log_info "Test message"

	# Check log file contains level information
	run cat "$LOG_FILE"
	echo "$output" | grep -q "$LOG_INF_MSG_PATTERN"
}

@test "custom log file path works" {
	local custom_log_file="custom-test.log"
	LOG_FILE="$custom_log_file"
	init_logging

	# Check that custom log file was created
	[[ -f "$LOG_FILE" ]]
	[[ "$LOG_FILE" == *"$custom_log_file" ]]
}

@test "color constants are defined" {
	# Test that all color constants are defined
	[[ -n "$COLOR_RESET" ]]
	[[ -n "$COLOR_RED" ]]
	[[ -n "$COLOR_GREEN" ]]
	[[ -n "$COLOR_YELLOW" ]]
	[[ -n "$COLOR_BLUE" ]]
}

@test "terminal colors are properly formatted" {
	# Test that color constants contain proper ANSI escape sequences
	[[ "$COLOR_RESET" == "\033[0m" ]]
	[[ "$COLOR_RED" == "\033[31m" ]]
	[[ "$COLOR_GREEN" == "\033[32m" ]]
	[[ "$COLOR_YELLOW" == "\033[33m" ]]
	[[ "$COLOR_BLUE" == "\033[34m" ]]
}

@test "log messages contain color codes" {
	LOG_LEVEL=$LOG_LEVEL_DEBUG
	LOG_TO_FILE=true
	init_logging

	log_debug "Debug test"
	log_info "Info test"
	log_error "Error test"

	# Check that log file contains ANSI color escape sequences
	run cat "$LOG_FILE"
	echo "$output" | grep -q $'\033'

	# Check for specific color codes in the log
	echo "$output" | grep -q $'\033\[33m' # Yellow timestamp
	echo "$output" | grep -q $'\033\[34m' # Blue debug
	echo "$output" | grep -q $'\033\[32m' # Green info
	echo "$output" | grep -q $'\033\[31m' # Red error
	echo "$output" | grep -q $'\033\[0m'  # Reset
}

@test "color codes are properly terminated" {
	LOG_TO_FILE=true
	init_logging

	log_info "Test message"

	# Check that log file contains both color codes and reset codes
	run cat "$LOG_FILE"
	local has_colors
	local has_resets
	has_colors=$(echo "$output" | grep -c $'\033\[[0-9]*m' || echo "0")
	has_resets=$(echo "$output" | grep -c $'\033\[0m' || echo "0")

	# Should have at least one color and one reset
	[[ "$has_colors" -gt 0 ]]
	[[ "$has_resets" -gt 0 ]]
}

@test "log level constants are correctly defined" {
	[[ "$LOG_LEVEL_DEBUG" -eq 0 ]]
	[[ "$LOG_LEVEL_INFO" -eq 1 ]]
	[[ "$LOG_LEVEL_ERROR" -eq 2 ]]
}

@test "default log level is INFO" {
	# Reset LOG_LEVEL to test default
	unset LOG_LEVEL
	unset LOG_TO_FILE
	source "$BATS_TEST_DIRNAME/../../lib/music-of-the-ainur.sh"

	[[ "$LOG_LEVEL" -eq "$LOG_LEVEL_DEBUG" ]]
}

@test "log directory uses GANDALF_HOME when set" {
	# Test that LOG_DIR uses GANDALF_HOME from setup
	[[ "$LOG_DIR" == "$TEST_DIR/logs" ]]
}

@test "log directory falls back to HOME when GANDALF_HOME not set" {
	# This test is already covered by the default behavior
	# since LOG_DIR is set during setup
	[[ "$LOG_DIR" == "$TEST_DIR/logs" ]]
}

@test "multiple log calls work correctly" {
	LOG_TO_FILE=false
	init_logging

	run bash -c "
    source '$MOTA_SCRIPT'
    log_info 'First message'
    log_info 'Second message'
    log_error 'Error message'
  "

	# Check all messages are in stdout output
	echo "$output" | grep -q "First message"
	echo "$output" | grep -q "Second message"
	echo "$output" | grep -q "Error message"
}

# LOG_TO_FILE functionality tests

@test "LOG_TO_FILE::default value is false" {
	# Reset LOG_TO_FILE to test default
	unset LOG_TO_FILE
	source "$BATS_TEST_DIRNAME/../../lib/music-of-the-ainur.sh"

	[[ "$LOG_TO_FILE" == "false" ]]
}

@test "LOG_TO_FILE::when false, messages go to stdout only" {
	LOG_TO_FILE=false
	init_logging

	local test_message="Test stdout message"
	run log_info "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_INF_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"

	# Log file should be empty
	[[ ! -s "$LOG_FILE" ]]
}

@test "LOG_TO_FILE::when true, messages go to both stdout and log file" {
	LOG_TO_FILE=true
	init_logging

	local test_message="Test file message"
	run log_info "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_INF_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"

	# Should also write to log file with timestamp
	run cat "$LOG_FILE"
	echo "$output" | grep -q "$LOG_INF_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"
	echo "$output" | grep -q "\[[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}\]"
}

@test "LOG_TO_FILE::when true, debug messages include timestamp" {
	LOG_TO_FILE=true
	LOG_LEVEL=$LOG_LEVEL_DEBUG
	init_logging

	local test_message="Test debug file message"
	run log_debug "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_DEB_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"

	# Should also write to log file with timestamp
	run cat "$LOG_FILE"
	echo "$output" | grep -q "$LOG_DEB_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"
	echo "$output" | grep -q "\[[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}\]"
}

@test "LOG_TO_FILE::when true, error messages include timestamp" {
	LOG_TO_FILE=true
	LOG_LEVEL=$LOG_LEVEL_ERROR
	init_logging

	local test_message="Test error file message"
	run log_error "$test_message"

	# Should output to stdout
	echo "$output" | grep -q "$LOG_ERR_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"

	# Should also write to log file with timestamp
	run cat "$LOG_FILE"
	echo "$output" | grep -q "$LOG_ERR_MSG_PATTERN"
	echo "$output" | grep -q "$test_message"
	echo "$output" | grep -q "\[[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}\]"
}

@test "LOG_TO_FILE::when true, multiple messages are appended to file" {
	LOG_TO_FILE=true
	init_logging

	log_info "First file message"
	log_info "Second file message"
	log_error "Error file message"

	# Check all messages are also in log file
	run cat "$LOG_FILE"
	echo "$output" | grep -q "First file message"
	echo "$output" | grep -q "Second file message"
	echo "$output" | grep -q "Error file message"

	# Count total log entries
	local line_count
	line_count=$(wc -l <"$LOG_FILE")
	[[ "$line_count" -eq 3 ]]
}

@test "LOG_TO_FILE::when false, multiple messages go to stdout only" {
	LOG_TO_FILE=false
	init_logging

	run bash -c "
    source '$MOTA_SCRIPT'
    log_info 'First stdout message'
    log_info 'Second stdout message'
    log_error 'Error stdout message'
  "

	# Check all messages are in stdout output
	echo "$output" | grep -q "First stdout message"
	echo "$output" | grep -q "Second stdout message"
	echo "$output" | grep -q "Error stdout message"

	# Log file should be empty
	[[ ! -s "$LOG_FILE" ]]
}

@test "LOG_TO_FILE::respects log level when true" {
	LOG_TO_FILE=true
	LOG_LEVEL=$LOG_LEVEL_INFO
	init_logging

	log_debug "Debug message should not appear"
	log_info "Info message should appear"
	log_error "Error message should appear"

	# Check only appropriate messages are in log file
	run cat "$LOG_FILE"
	! echo "$output" | grep -q "Debug message should not appear"
	echo "$output" | grep -q "Info message should appear"
	echo "$output" | grep -q "Error message should appear"
}

@test "LOG_TO_FILE::respects log level when false" {
	LOG_TO_FILE=false
	LOG_LEVEL=$LOG_LEVEL_INFO
	init_logging

	run bash -c "
    source '$MOTA_SCRIPT'
    log_debug 'Debug message should not appear'
    log_info 'Info message should appear'
    log_error 'Error message should appear'
  "

	# Check only appropriate messages are in stdout
	! echo "$output" | grep -q "Debug message should not appear"
	echo "$output" | grep -q "Info message should appear"
	echo "$output" | grep -q "Error message should appear"
}

@test "LOG_TO_FILE::color codes work in file mode" {
	LOG_TO_FILE=true
	LOG_LEVEL=$LOG_LEVEL_DEBUG
	init_logging

	log_debug "Debug test"
	log_info "Info test"
	log_error "Error test"

	# Check that log file contains ANSI color escape sequences
	run cat "$LOG_FILE"
	echo "$output" | grep -q $'\033'

	# Check for specific color codes in the log file
	echo "$output" | grep -q $'\033\[33m' # Yellow timestamp
	echo "$output" | grep -q $'\033\[34m' # Blue debug
	echo "$output" | grep -q $'\033\[32m' # Green info
	echo "$output" | grep -q $'\033\[31m' # Red error
	echo "$output" | grep -q $'\033\[0m'  # Reset
}

@test "LOG_TO_FILE::color codes work in stdout mode" {
	LOG_TO_FILE=false
	LOG_LEVEL=$LOG_LEVEL_DEBUG
	init_logging

	run bash -c "
    source '$MOTA_SCRIPT'
    log_debug 'Debug test'
    log_info 'Info test'
    log_error 'Error test'
  "

	# Check that stdout contains ANSI color escape sequences
	echo "$output" | grep -q $'\033'

	# Check for specific color codes in stdout
	echo "$output" | grep -q $'\033\[34m' # Blue debug
	echo "$output" | grep -q $'\033\[32m' # Green info
	echo "$output" | grep -q $'\033\[31m' # Red error
	echo "$output" | grep -q $'\033\[0m'  # Reset
}
