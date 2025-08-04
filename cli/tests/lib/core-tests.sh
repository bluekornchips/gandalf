#!/usr/bin/env bats

# Gandalf Core Library Tests
# Tests for centralized common functionality

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
  SCRIPT_DIR="${BATS_TEST_DIRNAME}"
  cd "$SCRIPT_DIR" || exit 1
  GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  export GANDALF_PROJECT_ROOT
fi

readonly CORE_SCRIPT="$GANDALF_PROJECT_ROOT/cli/lib/core.sh"
[[ -z "$CORE_SCRIPT" ]] && echo "'CORE_SCRIPT' is not set" >&2 && exit 1
[[ ! -f "$CORE_SCRIPT" ]] && echo "'CORE_SCRIPT' file does not exist" >&2 && exit 1

# Setup test environment before each test
setup() {
  unset GANDALF_PLATFORM
  unset CURSOR_DB_PATHS
  unset CLAUDE_CODE_DB_PATHS
  unset WINDSURF_DB_PATHS
  # shellcheck disable=SC1090,SC1091
  source "$CORE_SCRIPT"
}

@test "CORE_SCRIPT exists and is executable" {
  [[ -f "$CORE_SCRIPT" ]]
  [[ -x "$CORE_SCRIPT" ]]
}

@test "detect_platform::macos, mocked uname" {
  export MOCKED_UNAME_RETURN_VALUE="Darwin"
  uname() { echo "$MOCKED_UNAME_RETURN_VALUE"; }
  
  detect_platform
  [[ "$GANDALF_PLATFORM" == "macos" ]]
}

@test "detect_platform::linux, mocked uname" {
  export MOCKED_UNAME_RETURN_VALUE="Linux"
  uname() { echo "$MOCKED_UNAME_RETURN_VALUE"; }
  
  detect_platform
  [[ "$GANDALF_PLATFORM" == "linux" ]]
}

@test "detect_platform::unknown, mocked uname" {
  export MOCKED_UNAME_RETURN_VALUE="Unknown"
  uname() { echo "$MOCKED_UNAME_RETURN_VALUE"; }
  
  detect_platform
  [[ "$GANDALF_PLATFORM" == "unknown" ]]
}

@test "detect_platform::exports platform variable correctly" {
  detect_platform
  [[ -n "${GANDALF_PLATFORM:-}" ]]
}

@test "detect_platform::separate db path arrays are available" {
  detect_platform
  [[ -n "${CURSOR_DB_PATHS:-}" ]]
  [[ -n "${CLAUDE_CODE_DB_PATHS:-}" ]]
  [[ -n "${WINDSURF_DB_PATHS:-}" ]]
}

@test "detect_platform::db path arrays contain expected elements" {
  detect_platform
  local found_cursor=0
  local found_claude=0
  
  for path in "${CURSOR_DB_PATHS[@]}"; do
    if [[ "$path" == *"Cursor"* ]]; then
      found_cursor=$((found_cursor + 1))
    fi
  done
  
  for path in "${CLAUDE_CODE_DB_PATHS[@]}"; do
    if [[ "$path" == *"Claude"* ]]; then
      found_claude=$((found_claude + 1))
    fi
  done
  
  [[ $found_cursor -gt 0 ]]
  [[ $found_claude -gt 0 ]]
}