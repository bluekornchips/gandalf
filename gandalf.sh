#!/usr/bin/env bash
#
# Gandalf main CLI entry point
# Provides command-line interface for the Gandalf project
#
set -euo pipefail

# Display help information for the CLI
#
# Inputs:
# - None
#
# Side Effects:
# - Outputs help text to stdout
show_help() {
  cat <<EOF
Usage: $(basename "$0") COMMAND [OPTIONS]

Commands:
  test                Run test suites (shell, python, or specific test categories)
  help                Show this help message

Options:
  --help, -h          Show help for specific command

Examples:
  $0 test [name]                # Run a specific test file, by name
  $0 help                       # Show this help message

For more information, see: ${GANDALF_PROJECT_ROOT}/README.md

EOF
}

# Set up project root and home directory
SCRIPT_PATH="$(realpath "${BASH_SOURCE:-$0}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

GANDALF_PROJECT_ROOT="${SCRIPT_DIR}"
GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"
GANDALF_VERSION=$(cat "${GANDALF_PROJECT_ROOT}/VERSION" 2>/dev/null || echo "unknown")
export GANDALF_VERSION

# Main CLI function that handles command routing
#
# Inputs:
# - $1, command, the command to execute
# - $@, args, arguments for the command
#
# Side Effects:
# - Executes commands or shows help
main() {
  local command="${1:-help}"
  shift || true

  case "$command" in
    test)
      "${GANDALF_PROJECT_ROOT}/cli/bin/fellowship.sh" "$@"
      ;;
    help|--help|-h)
      show_help
      ;;
    *)
      echo "Error: Unknown command: $command" >&2
      echo "Run '$0 help' for usage information" >&2
      exit 1
      ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi