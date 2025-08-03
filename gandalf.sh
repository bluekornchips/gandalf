#!/usr/bin/env bash

set -euo pipefail

# Gandalf main cli entry point

show_help() {
	cat <<EOF

Usage: $0 COMMAND [OPTIONS]

Commands:
    test                Run test suites (shell, python, or specific test categories)
    help                Show this help message

Options:
    --help, -h          Show help for specific command

Examples:
    $0 test [name]                # Run a specific test file, by name
    $0 help                       # Show this help message

For more information, see: $GANDALF_ROOT/README.md

EOF
}

GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"
GANDALF_VERSION=$(cat "$GANDALF_ROOT/VERSION")

main() {
	local command="${1:-help}"
	shift || true

	case "$command" in
		test)
			"$GANDALF_ROOT/cli/bin/fellowship.sh" "$@"
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