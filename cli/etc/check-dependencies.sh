#!/usr/bin/env bash
#
# Dependencies Checker
# Validates that required shell dependencies are installed
# Provides helpful installation links when dependencies are missing
#
set -eo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Dependencies Checker
Validates that required shell dependencies are installed
Provides helpful installation links when dependencies are missing

OPTIONS:
  -h, --help  Show this help message
EOF
}
# Return repo root using git; falls back to current directory
#
# Inputs:
# - None
#
# Returns:
# - The repository root directory
# - 1 if the repository root directory cannot be determined
#
# Side Effects:
# - None
get_repo_root() {
	if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
		git rev-parse --show-toplevel
		return 0
	fi
	pwd
}

# Check presence of a local virtual environment directory at repo root
#
# Inputs:
# - None
#
# Returns 0 if .venv directory exists in repo root
check_venv_dir() {
	local repo_root
	repo_root="$(get_repo_root)"
	local venv_dir="${repo_root}/.venv"

	if [[ -d "${venv_dir}" ]]; then
		echo "Virtual environment directory found at ${venv_dir}" >&2
		return 0
	fi

	echo ".venv not found at ${repo_root}. Create it with: python3 -m venv .venv" >&2
	return 1
}

# Check that the current shell has the repo's .venv activated
#
# Inputs:
# - None
#
# Returns 0 if VIRTUAL_ENV points to repo_root/.venv
check_venv_active() {
	local repo_root
	repo_root="$(get_repo_root)"
	local expected_venv="${repo_root}/.venv"

	if [[ -n "${VIRTUAL_ENV:-}" && "${VIRTUAL_ENV}" == "${expected_venv}" ]]; then
		echo "Virtual environment activated (${VIRTUAL_ENV})" >&2
		return 0
	fi

	echo "Virtual environment not active. Activate with: . .venv/bin/activate" >&2
	return 1
}

# Check if a command is available in PATH
#
# Inputs:
# - $1, command, name of the command to check
#
# Side Effects:
# - None
check_command() {
	local command="$1"
	local link="$2"
	local description="$3"

	if command -v "${command}" >/dev/null 2>&1; then
		echo "${description} found" >&2
		return 0
	fi

	echo "${description} not installed, go to ${link} to install" >&2
	return 1
}

# Check if BATS testing framework is installed
#
# Inputs:
# - None
#
# Side Effects:
# - None
check_bats() {
	check_command "bats" "https://github.com/bats-core/bats-core" "BATS testing framework"
}

# Check if jq JSON processor is installed
#
# Inputs:
# - None
#
# Side Effects:
# - None
check_jq() {
	check_command "jq" "https://github.com/jqlang/jq" "jq JSON processor"
}

# Check if git is installed
#
# Inputs:
# - None
#
# Side Effects:
# - None
check_git() {
	check_command "git" "https://git-scm.com/downloads" "Git version control"
}

# Check if shellcheck is installed
#
# Inputs:
# - None
#
# Side Effects:
# - None
check_shellcheck() {
	check_command "shellcheck" "https://github.com/koalaman/shellcheck" "ShellCheck linter"
}

# Main function that checks all dependencies
#
# Inputs:
# - None
#
# Side Effects:
# - None
main() {
	while [[ $# -gt 0 ]]; do
		case $1 in
		-h | --help)
			usage
			return 0
			;;
		*)
			echo "Unknown option '$1'" >&2
			echo "Use '$(basename "$0") --help' for usage information" >&2
			return 1
			;;
		esac
	done

	local failed_checks=0

	# Environment checks
	check_venv_dir || ((failed_checks++))
	check_venv_active || ((failed_checks++))

	check_bats || ((failed_checks++))
	check_jq || ((failed_checks++))
	check_git || ((failed_checks++))
	check_shellcheck || ((failed_checks++))

	if [[ "${failed_checks}" -ne 0 ]]; then
		echo "Missing ${failed_checks} dependencies" >&2
		return 1
	fi

	return 0
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	main "$@"
fi
