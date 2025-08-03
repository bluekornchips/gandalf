#!/usr/bin/env bash

# Dependencies Checker
# Validates that required shell dependencies are installed
# Provides helpful installation links when dependencies are missing

# Check if BATS testing framework is installed
check_bats() {
  local link="https://github.com/bats-core/bats-core"
  if which bats >/dev/null 2>&1; then
    return 0
  fi
  echo "BATS not installed, go to ${link} to install" >&2
  return 1
}

# Check if jq JSON processor is installed
check_jq() {
  local link="https://github.com/jqlang/jq"
  if which jq >/dev/null 2>&1; then
    return 0
  fi
  echo "JQ not installed, go to ${link} to install" >&2
  return 1
}

# Main function that checks all dependencies
main() {
  local bats_result
  local jq_result

  check_bats
  bats_result=$?
  check_jq
  jq_result=$?

  if [[ "${bats_result}" == "0" && "${jq_result}" == "0" ]]; then
    return 0
  fi
  return 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi