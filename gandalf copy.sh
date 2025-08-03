#!/usr/bin/env bash

set -euo pipefail

# Gandalf main cli entry point

readonly GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly GANDALF_HOME="${GANDALF_HOME:-$HOME/.gandalf}"

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

# #!/usr/bin/env bash
# # Gandalf MCP Server - Main CLI Entry Point

# set -euo pipefail

# readonly GANDALF_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# show_help() {
# 	cat <<EOF
# Gandalf MCP Server - AI conversation history analysis and intelligent project context

# Usage: $0 COMMAND [OPTIONS]

# Commands:
#     run                 Start the MCP server
#     install             Install MCP server globally for all supported tools
#     uninstall           Remove MCP server configurations
#     test                Run test suites (shell, python, or specific test categories)
#     docker-test         Run test suites in Docker container
#     lembas              Run comprehensive test suite and validation
#     conv                Conversation management commands
#     status              Server status monitoring and health checking
#     help                Show this help message

# Options:
#     --help, -h          Show help for specific command
#     --debug             Enable debug mode with verbose output
#     --project-root DIR  Set project root directory (for run command)

# Examples:
#     $0 install                    # Install for all detected tools
#     $0 run --project-root /path   # Start server for specific project
#     $0 test --all                 # Run all tests
#     $0 test --shell               # Run shell tests only
#     $0 docker-test                # Run all tests in Docker container
#     $0 docker-test --shell        # Run shell tests in Docker
#     $0 lembas                     # Run full test suite
#     $0 status                     # Check installation status

# For more information, see: $GANDALF_ROOT/README.md

# EOF
# }

# # Handle run command with special argument parsing
# handle_run() {
# 	local project_root="$PWD"
# 	local debug_mode="false"

# 	while [[ $# -gt 0 ]]; do
# 		case "$1" in
# 		--debug)
# 			debug_mode="true"
# 			shift
# 			;;
# 		--project-root)
# 			project_root="$2"
# 			shift 2
# 			;;
# 		--help | -h)
# 			echo "Usage: $0 run [--debug] [--project-root DIR]"
# 			echo "Start the Gandalf MCP server"
# 			exit 0
# 			;;
# 		*)
# 			echo "Error: Unknown option for run command: $1" >&2
# 			exit 1
# 			;;
# 		esac
# 	done

# 	if [[ "$debug_mode" == "true" ]]; then
# 		export MCP_DEBUG="true"
# 	fi

# 	# Set Python path for module resolution, cross platform hopefully
# 	export PYTHONPATH="$GANDALF_ROOT/server:${PYTHONPATH:-}"

# 	cd "$GANDALF_ROOT/server"
# 	exec python3 -m src.main --project-root "$project_root"
# }

# # Main command dispatcher
# main() {
# 	case "${1:-help}" in
# 	run)
# 		shift
# 		handle_run "$@"
# 		;;
# 	install)
# 		exec "$GANDALF_ROOT/tools/bin/install.sh" "${@:2}"
# 		;;
# 	setup)
# 		exec "$GANDALF_ROOT/tools/bin/setup.sh" "${@:2}"
# 		;;
# 	uninstall)
# 		exec "$GANDALF_ROOT/tools/bin/uninstall.sh" "${@:2}"
# 		;;
# 	test)
# 		exec "$GANDALF_ROOT/tools/bin/test-runner.sh" "${@:2}"
# 		;;
# 	docker-test)
# 		exec "$GANDALF_ROOT/tools/bin/docker-test.sh" "${@:2}"
# 		;;
# 	conv)
# 		exec "$GANDALF_ROOT/tools/bin/conversations.sh" "${@:2}"
# 		;;
# 	lembas)
# 		exec "$GANDALF_ROOT/tools/bin/lembas.sh" "${@:2}"
# 		;;
# 	status)
# 		exec "$GANDALF_ROOT/tools/bin/status.sh" "${@:2}"
# 		;;
# 	help | --help | -h)
# 		show_help
# 		;;
# 	*)
# 		echo "Error: Unknown command: $1" >&2
# 		echo "Run '$0 help' for usage information" >&2
# 		exit 1
# 		;;
# 	esac
# }

# if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
# 	main "$@"
# fi
