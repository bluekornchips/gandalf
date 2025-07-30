#!/usr/bin/env bash
set -euo pipefail

# Docker Test Runner for Gandalf MCP Server

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly GANDALF_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
readonly PROJECT_ROOT="$(cd "$GANDALF_ROOT/.." && pwd -P)"
readonly IMAGE_NAME="gandalf-shell:latest"

check_docker_available() {
	if ! command -v docker >/dev/null; then
		echo "Error: Docker not found. Please install Docker first." >&2
		return 1
	fi
}

build_image_if_needed() {
	if ! docker images "$IMAGE_NAME" | grep -q gandalf-shell; then
		echo "Building Docker image: $IMAGE_NAME"
		if ! docker build -f "$GANDALF_ROOT/Docker/Dockerfile" -t "$IMAGE_NAME" "$PROJECT_ROOT"; then
			echo "Error: Failed to build Docker image" >&2
			return 1
		fi
	fi
}

run_tests_in_container() {
	local test_command="gdlf test"

	# Build test command with passed arguments
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--shell | --python)
			test_command="$test_command $1"
			;;
		*)
			echo "Error: Unknown option: $1" >&2
			return 1
			;;
		esac
		shift
	done

    cat <<EOF
Running tests in Docker container...
Command: $test_command

EOF

	docker run --rm "$IMAGE_NAME" "$test_command"
	local exit_code=$?
	
	echo ""
	if [[ $exit_code -eq 0 ]]; then
		echo "Docker tests completed successfully!"
		return 0
	else
		echo "Docker tests failed!"
		return $exit_code
	fi
}

show_usage() {
	cat <<EOF
Docker Test Runner for Gandalf MCP Server

USAGE:
    docker-test [OPTIONS]

OPTIONS:
    --shell             Run shell tests only in container
    --python            Run Python tests only in container
    --help, -h          Show this help

EXAMPLES:
    docker-test                     # Run all tests in Docker
    docker-test --shell             # Run shell tests in Docker
    docker-test --python            # Run Python tests in Docker

EOF
}

main() {
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--help | -h)
			show_usage
			exit 0
			;;
		--shell | --python)
			break
			;;
		*)
			echo "Error: Unknown option: $1" >&2
			show_usage
			exit 1
			;;
		esac
		shift
	done

	check_docker_available
	build_image_if_needed
	run_tests_in_container "$@"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi
