#!/usr/bin/env bats

# Registry Management Tests
# Tests for registry file management and initialization

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
  SCRIPT_DIR="${BATS_TEST_DIRNAME}"
  cd "$SCRIPT_DIR" || exit 1
  GANDALF_PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  export GANDALF_PROJECT_ROOT
fi

readonly REGISTRY_SCRIPT="${GANDALF_PROJECT_ROOT}/cli/bin/registry.sh"
[[ -z "${REGISTRY_SCRIPT}" ]] && echo "'REGISTRY_SCRIPT' is not set" >&2 && exit 1
[[ ! -f "${REGISTRY_SCRIPT}" ]] && echo "'REGISTRY_SCRIPT' file does not exist" >&2 && exit 1

setup() {
  TEST_DIR="$(mktemp -d)"
  export TEST_DIR
  
  export HOME="${TEST_DIR}"
  
  # shellcheck disable=SC1090,SC1091
  source "${REGISTRY_SCRIPT}"
}

teardown() {
  if [[ -n "${TEST_DIR:-}" && -d "${TEST_DIR}" ]]; then
    rm -rf "${TEST_DIR}"
  fi
}

@test "REGISTRY_SCRIPT exists and is executable" {
  [[ -f "${REGISTRY_SCRIPT}" ]]
  [[ -x "${REGISTRY_SCRIPT}" ]]
}

@test "HOME not set, should exit with error" {
  unset HOME
  run init_registry
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Registry initialized"
}

@test "GANDALF_DB_PATHS not set, should source core.sh and init_registry" {
  unset GANDALF_DB_PATHS
  run init_registry
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Registry initialized"
}

@test "init_registry::creates registry file when it doesn't exist" {
  [[ ! -f "${REGISTRY_FILE}" ]]
  init_registry
  [[ -f "${REGISTRY_FILE}" ]]
}

@test "init_registry::creates directory structure when needed" {
  local registry_dir
  registry_dir="$(dirname "${REGISTRY_FILE}")"
  [[ ! -d "${registry_dir}" ]]
  init_registry
  [[ -d "${registry_dir}" ]]
}

@test "init_registry::initializes with empty JSON array" {
  init_registry
  [[ -f "${REGISTRY_FILE}" ]]
  [[ "$(cat "${REGISTRY_FILE}")" == "[]" ]]
}

@test "init_registry::does not overwrite existing registry file" {
  mkdir -p "$(dirname "${REGISTRY_FILE}")"
  echo '{"test": "data"}' > "${REGISTRY_FILE}"
  local original_content
  original_content="$(cat "${REGISTRY_FILE}")"
  init_registry >/dev/null
  [[ "$(cat "${REGISTRY_FILE}")" == "${original_content}" ]]
}

@test "'REGISTRY_FILE' constant is properly defined" {
  [[ -n "${REGISTRY_FILE:-}" ]]
  [[ "${REGISTRY_FILE}" == "${HOME}/.gandalf/registry.json" ]]
}

@test "check_available_tools::function exists and is callable" {
  run check_available_tools
  [[ "${status}" -eq 0 ]]
}

@test "check_available_tools::handles empty GANDALF_DB_PATHS" {
  GANDALF_DB_PATHS=()
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 0"
  echo "${output}" | grep -q "Claude database paths count: 0"
  echo "${output}" | grep -q "Windsurf database paths count: 0"
}

@test "check_available_tools::handles paths with no database files" {
  local test_path1="${TEST_DIR}/path1"
  local test_path2="${TEST_DIR}/path2"
  mkdir -p "${test_path1}" "${test_path2}"
  GANDALF_DB_PATHS=("${test_path1}" "${test_path2}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 0"
  echo "${output}" | grep -q "Claude database paths count: 0"
  echo "${output}" | grep -q "Windsurf database paths count: 0"
}

@test "check_available_tools::detects cursor.db files" {
  local test_path1="${TEST_DIR}/path1"
  local test_path2="${TEST_DIR}/path2"
  mkdir -p "${test_path1}" "${test_path2}"
  touch "${test_path1}/cursor.db"
  touch "${test_path2}/cursor.db"
  GANDALF_DB_PATHS=("${test_path1}" "${test_path2}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 2"
  echo "${output}" | grep -q "Claude database paths count: 0"
  echo "${output}" | grep -q "Windsurf database paths count: 0"
}

@test "check_available_tools::detects claude.db files" {
  local test_path1="${TEST_DIR}/path1"
  local test_path2="${TEST_DIR}/path2"
  mkdir -p "${test_path1}" "${test_path2}"
  touch "${test_path1}/claude.db"
  touch "${test_path2}/claude.db"
  GANDALF_DB_PATHS=("${test_path1}" "${test_path2}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 0"
  echo "${output}" | grep -q "Claude database paths count: 2"
  echo "${output}" | grep -q "Windsurf database paths count: 0"
}

@test "check_available_tools::detects windsurf.db files" {
  local test_path1="${TEST_DIR}/path1"
  local test_path2="${TEST_DIR}/path2"
  mkdir -p "${test_path1}" "${test_path2}"
  touch "${test_path1}/windsurf.db"
  touch "${test_path2}/windsurf.db"
  GANDALF_DB_PATHS=("${test_path1}" "${test_path2}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 0"
  echo "${output}" | grep -q "Claude database paths count: 0"
  echo "${output}" | grep -q "Windsurf database paths count: 2"
}

@test "check_available_tools::detects mixed database files in same path" {
  local test_path="${TEST_DIR}/mixed_path"
  mkdir -p "${test_path}"
  touch "${test_path}/cursor.db"
  touch "${test_path}/claude.db"
  touch "${test_path}/windsurf.db"
  GANDALF_DB_PATHS=("${test_path}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 1"
  echo "${output}" | grep -q "Claude database paths count: 1"
  echo "${output}" | grep -q "Windsurf database paths count: 1"
}

@test "check_available_tools::handles multiple paths with different databases" {
  local test_path1="${TEST_DIR}/path1"
  local test_path2="${TEST_DIR}/path2"
  local test_path3="${TEST_DIR}/path3"
  mkdir -p "${test_path1}" "${test_path2}" "${test_path3}"
  
  touch "${test_path1}/cursor.db"
  touch "${test_path2}/claude.db"
  touch "${test_path3}/windsurf.db"
  
  GANDALF_DB_PATHS=("${test_path1}" "${test_path2}" "${test_path3}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 1"
  echo "${output}" | grep -q "Claude database paths count: 1"
  echo "${output}" | grep -q "Windsurf database paths count: 1"
}

@test "check_available_tools::ignores non-database files" {
  local test_path="${TEST_DIR}/path_with_other_files"
  mkdir -p "${test_path}"
  touch "${test_path}/other_file.txt"
  touch "${test_path}/database.db"
  touch "${test_path}/cursor.db"
  GANDALF_DB_PATHS=("${test_path}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 1"
  echo "${output}" | grep -q "Claude database paths count: 0"
  echo "${output}" | grep -q "Windsurf database paths count: 0"
}

@test "check_available_tools::handles non-existent paths gracefully" {
  local test_path1="${TEST_DIR}/existing_path"
  local test_path2="${TEST_DIR}/non_existent_path"
  mkdir -p "${test_path1}"
  touch "${test_path1}/cursor.db"
  GANDALF_DB_PATHS=("${test_path1}" "${test_path2}")
  
  run check_available_tools
  [[ "${status}" -eq 0 ]]
  echo "${output}" | grep -q "Cursor database paths count: 1"
  echo "${output}" | grep -q "Claude database paths count: 0"
  echo "${output}" | grep -q "Windsurf database paths count: 0"
}