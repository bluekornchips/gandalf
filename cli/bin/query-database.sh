#!/usr/bin/env bash
#
# Query database script for Gandalf
# Executes database queries from JSON files
#
set -eo pipefail

usage() {
	cat <<EOF
Usage: $(basename "$0") [OPTIONS] <query_file>

Execute database query from JSON file

ARGUMENTS:
  query_file    Path to JSON query file

OPTIONS:
  -o, --output FORMAT    	Output format: json (requires jq) or yaml (requires yq)
  -h, --help            	Show this help message

ENVIRONMENT VARIABLES:
  GANDALF_ROOT  Root directory of Gandalf installation

EOF
}

# Check if required formatting tool is available
#
# Inputs:
# - $1 format, Output format (json or yaml)
#
# Returns:
# - 0 if tool is available, 1 if not
check_format_tool() {
	local format="$1"

	if [[ -z "$format" ]]; then
		echo "check_format_tool:: format is required" >&2
		return 1
	fi

	case "$format" in
	json)
		if command -v jq >/dev/null 2>&1; then
			return 0
		else
			echo "check_format_tool:: jq is required for JSON formatting but not installed" >&2
			return 1
		fi
		;;
	yaml)
		if command -v yq >/dev/null 2>&1; then
			return 0
		else
			echo "check_format_tool:: yq is required for YAML formatting but not installed" >&2
			return 1
		fi
		;;
	*)
		echo "check_format_tool:: Invalid output format: $format. Supported formats: json, yaml" >&2
		return 1
		;;
	esac
}

# Format output using the specified tool
#
# Inputs:
# - $1 format, Output format (json or yaml)
# - stdin, Raw JSON data to format
#
# Side Effects:
# - Outputs formatted data to stdout
format_output() {
	local format="$1"

	case "$format" in
	json)
		jq .
		;;
	yaml)
		yq -P
		;;
	esac
}

# Execute database query from file
#
# Inputs:
# - $1 query_file, Path to JSON query file
# - $2 output_format, Optional output format (json or yaml)
#
# Side Effects:
# - Executes query and outputs results
execute_query_file() {
	local query_file="$1"
	local output_format="$2"
	local python_cmd
	local query_handler_script

	if [[ -z "$query_file" ]]; then
		echo "execute_query_file:: query_file is required" >&2
		return 1
	fi

	if [[ ! -f "$query_file" ]]; then
		echo "execute_query_file:: Query file not found: $query_file" >&2
		return 1
	fi

	python_cmd=""
	local python_versions=("python3.12" "python3.11" "python3.10" "python3.9" "python3.8" "python3")

	for version in "${python_versions[@]}"; do
		if command -v "$version" >/dev/null 2>&1; then
			python_cmd="$version"
			break
		fi
	done

	if [[ -z "$python_cmd" ]]; then
		echo "execute_query_file:: No suitable Python version found" >&2
		return 1
	fi

	# Use the console script entry point from virtual environment
	local gandalf_root="${GANDALF_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
	local gandalf_query_cmd="${gandalf_root}/.venv/bin/gandalf-query"

	if [[ ! -f "$gandalf_query_cmd" ]]; then
		echo "execute_query_file:: gandalf-query command not found: $gandalf_query_cmd" >&2
		return 1
	fi

	# Check if output formatting is requested
	if [[ -n "$output_format" ]]; then
		if ! check_format_tool "$output_format"; then
			return 1
		fi

		# Execute query and pipe through formatter
		if ! "$gandalf_query_cmd" "$query_file" | format_output "$output_format"; then
			echo "execute_query_file:: Query execution failed" >&2
			return 1
		fi
	else
		# Execute query without formatting
		if ! "$gandalf_query_cmd" "$query_file"; then
			echo "execute_query_file:: Query execution failed" >&2
			return 1
		fi
	fi

	return 0
}

main() {
	local output_format=""
	local query_file=""

	# Parse command line arguments
	while [[ $# -gt 0 ]]; do
		case $1 in
		-o | --output)
			if [[ $# -lt 2 ]]; then
				echo "--output requires a format argument" >&2
				usage
				return 1
			fi
			output_format="$2"
			shift 2
			;;
		-h | --help)
			usage
			return 0
			;;
		-*)
			echo "Unknown option $1" >&2
			usage
			return 1
			;;
		*)
			if [[ -n "$query_file" ]]; then
				echo "Multiple query files specified" >&2
				usage
				return 1
			fi
			query_file="$1"
			shift
			;;
		esac
	done

	if [[ -z "$query_file" ]]; then
		echo "Query file is required" >&2
		usage
		return 1
	fi

	execute_query_file "$query_file" "$output_format"
	return $?
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
	main "$@"
fi
