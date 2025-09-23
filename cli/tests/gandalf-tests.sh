#!/usr/bin/env bats

# Gandalf CLI Tests
# Tests for the main CLI entry point (gandalf.sh)

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
  SCRIPT_DIR="${BATS_TEST_DIRNAME}"
  cd "$SCRIPT_DIR" || exit 1
  GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  export GANDALF_PROJECT_ROOT
fi

readonly GANDALF_SCRIPT="${GANDALF_PROJECT_ROOT}/gandalf.sh"
[[ -z "${GANDALF_SCRIPT}" ]] && echo "'GANDALF_SCRIPT' is not set" >&2 && exit 1
[[ ! -f "${GANDALF_SCRIPT}" ]] && echo "'GANDALF_SCRIPT' file does not exist" >&2 && exit 1

setup_file() {
  return 0
}

setup() {
  TEST_DIR="$(mktemp -d)"
  export TEST_DIR

  VERSION_FILE="${TEST_DIR}/VERSION"
  echo "1.0.0" >"${VERSION_FILE}"

  export GANDALF_PROJECT_ROOT="${TEST_DIR}"
  export GANDALF_HOME="${TEST_DIR}/.gandalf"

  cp "${GANDALF_SCRIPT}" "${TEST_DIR}/gandalf.sh"
  chmod +x "${TEST_DIR}/gandalf.sh"

  mkdir -p "${TEST_DIR}/cli/bin"
  cat >"${TEST_DIR}/cli/bin/fellowship.sh" <<'EOF'
#!/usr/bin/env bash
echo "Mock fellowship script executed with args: $*"
EOF
  chmod +x "${TEST_DIR}/cli/bin/fellowship.sh"

  return 0
}

teardown() {
  if [[ -n "${TEST_DIR:-}" && -d "${TEST_DIR}" ]]; then
    rm -rf "${TEST_DIR}"
  fi
}

@test "GANDALF_SCRIPT exists and is executable" {
  [[ -f "${GANDALF_SCRIPT}" ]]
  [[ -x "${GANDALF_SCRIPT}" ]]
}

@test "main::function exists and is callable" {
  # Source the script to make main function available
  # shellcheck disable=SC1090
  source "${GANDALF_SCRIPT}"
  run main "help"
  [[ "${status}" -eq 0 ]]
}

@test "main::shows help with help command" {
  run bash "${TEST_DIR}/gandalf.sh" help
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Usage:"
  echo "${output}" | grep -q "Commands:"
  echo "${output}" | grep -q "test"
  echo "${output}" | grep -q "help"
}

@test "main::shows help with --help flag" {
  run bash "${TEST_DIR}/gandalf.sh" --help
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Usage:"
  echo "${output}" | grep -q "Commands:"
}

@test "main::shows help with -h flag" {
  run bash "${TEST_DIR}/gandalf.sh" -h
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Usage:"
  echo "${output}" | grep -q "Commands:"
}

@test "main::shows help when no command provided" {
  run bash "${TEST_DIR}/gandalf.sh"
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Usage:"
  echo "${output}" | grep -q "Commands:"
}

@test "main::routes test command to fellowship" {
  run bash "${TEST_DIR}/gandalf.sh" test
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Mock fellowship script executed with args:"
}

@test "main::passes arguments to fellowship" {
  run bash "${TEST_DIR}/gandalf.sh" test --some-arg value
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Mock fellowship script executed with args: --some-arg value"
}

@test "main::handles unknown command" {
  run bash "${TEST_DIR}/gandalf.sh" unknown-command
  [[ "${status}" -eq 1 ]]
  echo "${output}" | grep -q "Error: Unknown command: unknown-command"
  echo "${output}" | grep -q "Run '.*help' for usage information"
}

@test "main::handles empty command" {
  run bash "${TEST_DIR}/gandalf.sh" ""
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Usage:"
}

@test "script::sets up environment variables" {
  # Source the script to check environment setup
  # shellcheck disable=SC1090
  source "${GANDALF_SCRIPT}"
  [[ -n "${GANDALF_PROJECT_ROOT:-}" ]]
  [[ -n "${GANDALF_HOME:-}" ]]
  [[ -n "${GANDALF_VERSION:-}" ]]
}

@test "script::reads version from VERSION file" {
  run bash "${TEST_DIR}/gandalf.sh" help
  [[ "${status}" -eq 0 ]]
  source "${TEST_DIR}/gandalf.sh"
  [[ "${GANDALF_VERSION}" == "1.0.0" ]]
}

@test "script::handles missing VERSION file gracefully" {
  # Remove VERSION file
  rm -f "${TEST_DIR}/VERSION"

  source "${TEST_DIR}/gandalf.sh"
  # Version should be "unknown" when VERSION file is missing
  [[ "${GANDALF_VERSION}" == "unknown" ]]
}

@test "script::only executes main when run directly" {
  # Test that the script doesn't execute main when sourced
  run source "${GANDALF_SCRIPT}"
  [[ "${status}" -eq 0 ]]
  # The script should source without error and not execute main
}

@test "script::executes main when run as script" {
  run bash "${TEST_DIR}/gandalf.sh" help
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Usage:"
}

@test "main::handles multiple arguments correctly" {
  run bash "${TEST_DIR}/gandalf.sh" test arg1 arg2 arg3
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Mock fellowship script executed with args: arg1 arg2 arg3"
}

@test "main::handles special characters in arguments" {
  run bash "${TEST_DIR}/gandalf.sh" test "arg with spaces" "arg-with-dashes" "arg_with_underscores"
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Mock fellowship script executed with args: arg with spaces arg-with-dashes arg_with_underscores"
}

@test "script::sets correct project root" {
  source "${TEST_DIR}/gandalf.sh"
  [[ "${GANDALF_PROJECT_ROOT}" == "${TEST_DIR}" ]]
}

@test "script::sets correct home directory" {
  # Source the script and check home directory
  # shellcheck disable=SC1090
  source "${GANDALF_SCRIPT}"
  [[ "${GANDALF_HOME}" == "${TEST_DIR}/.gandalf" ]]
}

@test "script::exports version variable" {
  # Source the script and check version export
  # shellcheck disable=SC1090
  source "${GANDALF_SCRIPT}"
  [[ -n "${GANDALF_VERSION:-}" ]]
}
