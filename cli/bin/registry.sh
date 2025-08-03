#!/usr/bin/env bash

# Registry Management for Gandalf
# Manages tool registrations and database paths for the Gandalf system

set -eo pipefail

if [[ -z "${GANDALF_PROJECT_ROOT:-}" ]]; then
  SCRIPT_PATH="$(realpath "${BASH_SOURCE:-$0}")"
  SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
  GANDALF_PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
  
fi

if [[ -z "$HOME" ]]; then
  echo "'HOME' is not set. Not sure how you ended up here dude." >&2
  exit 1
fi

if [[ -z "${GANDALF_DB_PATHS}" ]]; then
  # shellcheck disable=SC1091
  source "${GANDALF_PROJECT_ROOT}/cli/lib/core.sh"
fi

readonly REGISTRY_FILE="${HOME}/.gandalf/registry.json"

# Registry Schema:
# [
#     {
#         "tool": "tool-name",
#         "tool_paths": []
#     }
# ]

init_registry() {
  if [[ ! -f "${REGISTRY_FILE}" ]]; then
    mkdir -p "$(dirname "${REGISTRY_FILE}")"
    echo "[]" > "${REGISTRY_FILE}"
    echo "Registry initialized"
  fi
}

check_available_tools(){
  # For each path in 'GANDALF_DB_PATHS', check for the presence of the database files
  cursor_db_paths=()
  claude_db_paths=()
  windsurf_db_paths=()

  echo "'GANDALF_DB_PATHS' count: ${#GANDALF_DB_PATHS[@]}"

  for path in "${GANDALF_DB_PATHS[@]}"; do
    [[ -f "${path}/cursor.db" ]] && cursor_db_paths+=("${path}")
    [[ -f "${path}/claude.db" ]] && claude_db_paths+=("${path}")
    [[ -f "${path}/windsurf.db" ]] && windsurf_db_paths+=("${path}")
  done

  echo "Cursor database paths count: ${#cursor_db_paths[@]}"
  echo "Claude database paths count: ${#claude_db_paths[@]}"
  echo "Windsurf database paths count: ${#windsurf_db_paths[@]}"
}

main() {
  if [[ ! -f "${REGISTRY_FILE}" ]]; then
    init_registry
  fi
  check_available_tools
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi