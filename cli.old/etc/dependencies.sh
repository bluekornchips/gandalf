#!/usr/bin/env bash
#
# Check if shell dependencies are installed
# If not, print a message to the user to install them

check_bats() {
  local link="https://github.com/bats-core/bats-core"
  if which bats >/dev/null 2>&1; then
    return 0
  fi
  echo "BATS not installed, go to ${link} to install" >&2
  return 1
}

check_jq() {
  local link="https://github.com/jqlang/jq"
  if which jq >/dev/null 2>&1; then
    return 0
  fi
  echo "JQ not installed, go to ${link} to install" >&2
  return 1
}

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