#!/usr/bin/env bash
# Gandalf MCP Server Rules Creation Script

set -euo pipefail

readonly SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
readonly GANDALF_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_PATH")")")"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"

# Define section markers
readonly START_MARKER="##__GANDALF_RULES_START__##"
readonly END_MARKER="##__GANDALF_RULES_END__##"

usage() {
	cat <<EOF
Usage: $0 [OPTIONS]

Create global and local rules files for Cursor, Claude Code, and Windsurf.

OPTIONS:
    -f, --force      Overwrite existing rules without prompting
    -l, --local      Create rules in current directory only (default: both global and local)
    -g, --global     Create global rules only (default: both global and local)  
    -h, --help       Show this help message
    --debug          Enable debug logging

EXAMPLES:
    $0                     # Create both global and local rules
    $0 --local             # Create local rules only (./.cursor/rules/, ./CLAUDE.md)
    $0 --global            # Create global rules only (~/.cursor/rules/, etc.)
    $0 --force             # Force overwrite existing rules (both global and local)
    $0 --debug             # Enable debug output

EOF
}

parse_arguments() {
	FORCE="false"
	DEBUG="false"
	LOCAL_ONLY="false"
	GLOBAL_ONLY="false"

	while [[ $# -gt 0 ]]; do
		case "$1" in
		-f | --force)
			FORCE="true"
			shift
			;;
		-l | --local)
			LOCAL_ONLY="true"
			shift
			;;
		-g | --global)
			GLOBAL_ONLY="true"
			shift
			;;
		--debug)
			DEBUG="true"
			export MCP_DEBUG="true"
			shift
			;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			echo "Error: Unknown option: $1" >&2
			usage
			exit 1
			;;
		esac
	done

	if [[ "$LOCAL_ONLY" == "true" && "$GLOBAL_ONLY" == "true" ]]; then
		echo "Error: Cannot specify both --local and --global options" >&2
		exit 1
	fi
}

create_cursor_rules() {
	local rules_content="$1"
	local rules_dir="$2"

	local rules_file="$rules_dir/$MCP_SERVER_NAME-rules.mdc"

	if [[ -f "$rules_file" ]] && [[ "${FORCE:-false}" != "true" ]]; then
		echo "Cursor rules file already exists: $rules_file"
		return 0
	fi

	# Create rules directory if it doesn't exist
	mkdir -p "$rules_dir" || {
		echo "Error: Failed to create rules directory: $rules_dir" >&2
		return 1
	}

	# Remove any existing frontmatter from rules_content and add proper Cursor frontmatter
	local clean_content
	clean_content=$(echo "$rules_content" | sed '/^---$/,/^---$/d')
	
	cat >"$rules_file" <<EOF
---
description: Enhanced Gandalf MCP Server Rules with Performance Optimization and Advanced Workflows
globs:
alwaysApply: true
---

$clean_content
EOF

	if [[ $? -eq 0 ]]; then
		echo "Created Cursor rules file: $rules_file"
		return 0
	else
		echo "Error: Failed to create Cursor rules file" >&2
		return 1
	fi
}

create_claude_rules() {
	local rules_content="$1"
	local rules_dir="${GANDALF_HOME_OVERRIDE:-$HOME}/.claude"
	local claude_file="$rules_dir/CLAUDE.md"

	# Check if file exists and force is not enabled
	if [[ -f "$claude_file" ]] && [[ "${FORCE:-false}" != "true" ]]; then
		echo "Claude Code CLAUDE.md already exists: $claude_file"
		return 0
	fi



	# Check if file exists and has Gandalf section
	if [[ -f "$claude_file" ]] && grep -q "$START_MARKER" "$claude_file"; then
		echo "Updating Gandalf rules section in existing CLAUDE.md"
		
		local temp_file
		temp_file=$(mktemp) || {
			echo "Error: Failed to create temporary file" >&2
			return 1
		}
		
		local in_gandalf_rules=false
		local found_start_marker=false
		
		while IFS= read -r line; do
			if [[ "$line" == "$START_MARKER" ]]; then
				if [[ "$found_start_marker" == "false" ]]; then
					# First marker - write it and our new content
					echo "$line" >> "$temp_file"
					echo "" >> "$temp_file"
					echo "$rules_content" >> "$temp_file"
					echo "" >> "$temp_file"
					found_start_marker=true
					in_gandalf_rules=true
				fi
			elif [[ "$line" == "$END_MARKER" ]]; then
				if [[ "$in_gandalf_rules" == "true" ]]; then
					# End marker - write it and continue
					echo "$line" >> "$temp_file"
					in_gandalf_rules=false
				fi
			elif [[ "$in_gandalf_rules" == "false" ]]; then
				# Outside Gandalf rules section, preserve content
				echo "$line" >> "$temp_file"
			fi
			# Inside Gandalf rules section, skip content (it gets replaced)
		done < "$claude_file"
		
		# Replace original file
		if mv "$temp_file" "$claude_file"; then
			echo "Updated Gandalf rules section in CLAUDE.md"
		else
			echo "Error: Failed to update CLAUDE.md" >&2
			rm -f "$temp_file"
			return 1
		fi
		
	else
		# File doesn't exist or doesn't have Gandalf section
		if [[ -f "$claude_file" ]]; then
			echo "Adding Gandalf rules section to existing CLAUDE.md"
			# Append to existing file
			cat >> "$claude_file" <<EOF

$START_MARKER

$rules_content

$END_MARKER
EOF
		else
			echo "Creating new CLAUDE.md with Gandalf rules"
			# Create new file with just Gandalf section
			cat > "$claude_file" <<EOF
$START_MARKER

$rules_content

$END_MARKER
EOF
		fi
		
		echo "Created/updated Claude Code CLAUDE.md: $claude_file"
	fi

	return 0
}

create_windsurf_rules() {
	local rules_content="$1"
	local rules_dir="$2"

	local rules_file="$rules_dir/global_rules.md"

	if [[ -f "$rules_file" ]] && [[ "${FORCE:-false}" != "true" ]]; then
		echo "Windsurf rules file already exists: $rules_file"
		return 0
	fi

	# Create rules directory if it doesn't exist
	mkdir -p "$rules_dir" || {
		echo "Error: Failed to create rules directory: $rules_dir" >&2
		return 1
	}

	# Check Windsurf character limit
	local char_count=${#rules_content}
	local max_chars=6000

	if [[ $char_count -gt $max_chars ]]; then
		echo "Warning: Rules content ($char_count chars) exceeds Windsurf limit ($max_chars chars)" >&2
		echo "Truncating content for Windsurf compatibility"

		local truncation_message=$'\n\n# Note: Content truncated to fit Windsurf 6000 character limit\n# Full rules available in Cursor and Claude Code configurations\n# See spec/rules/core.md for complete documentation'
		local message_length=${#truncation_message}
		local max_content_length=$((max_chars - message_length - 10))

		rules_content=$(printf '%s' "$rules_content" | head -c "$max_content_length")
		rules_content="$rules_content$truncation_message"
	fi

	if printf '%s' "$rules_content" >"$rules_file"; then
		echo "Created Windsurf rules file: $rules_file (${#rules_content}/$max_chars chars)"
		return 0
	else
		echo "Error: Failed to create Windsurf rules file" >&2
		return 1
	fi
}

create_local_cursor_rules() {
	local rules_content="$1"
	create_cursor_rules "$rules_content" "./.cursor/rules"
}

create_local_claude_rules() {
	local rules_content="$1"
	local claude_file="./CLAUDE.md"

	# Check if file exists and force is not enabled
	if [[ -f "$claude_file" ]] && [[ "${FORCE:-false}" != "true" ]]; then
		echo "Local Claude Code CLAUDE.md already exists: $claude_file"
		return 0
	fi

	# Check if file exists and has Gandalf section
	if [[ -f "$claude_file" ]] && grep -q "$START_MARKER" "$claude_file"; then
		echo "Updating Gandalf rules section in local CLAUDE.md"
		
		local temp_file
		temp_file=$(mktemp) || {
			echo "Error: Failed to create temporary file" >&2
			return 1
		}
		
		local in_gandalf_rules=false
		local found_start_marker=false
		
		while IFS= read -r line; do
			if [[ "$line" == "$START_MARKER" ]]; then
				if [[ "$found_start_marker" == "false" ]]; then
					# First marker - write it and our new content
					echo "$line" >> "$temp_file"
					echo "" >> "$temp_file"
					echo "$rules_content" >> "$temp_file"
					echo "" >> "$temp_file"
					found_start_marker=true
					in_gandalf_rules=true
				fi
			elif [[ "$line" == "$END_MARKER" ]]; then
				if [[ "$in_gandalf_rules" == "true" ]]; then
					# End marker - write it and continue
					echo "$line" >> "$temp_file"
					in_gandalf_rules=false
				fi
			elif [[ "$in_gandalf_rules" == "false" ]]; then
				# Outside Gandalf rules section, preserve content
				echo "$line" >> "$temp_file"
			fi
			# Inside Gandalf rules section, skip content (it gets replaced)
		done < "$claude_file"
		
		# Replace original file
		if mv "$temp_file" "$claude_file"; then
			echo "Updated local Gandalf rules section in CLAUDE.md"
		else
			echo "Error: Failed to update local CLAUDE.md" >&2
			rm -f "$temp_file"
			return 1
		fi
		
	else
		# File doesn't exist or doesn't have Gandalf section
		if [[ -f "$claude_file" ]]; then
			echo "Adding Gandalf rules section to existing local CLAUDE.md"
			# Append to existing file
			cat >> "$claude_file" <<EOF

$START_MARKER

$rules_content

$END_MARKER
EOF
		else
			echo "Creating new local CLAUDE.md with Gandalf rules"
			# Create new file with just Gandalf section
			cat > "$claude_file" <<EOF
$START_MARKER

$rules_content

$END_MARKER
EOF
		fi
		
		echo "Created/updated local Claude Code CLAUDE.md: $claude_file"
	fi

	return 0
}

create_local_windsurf_rules() {
	local rules_content="$1"
	create_windsurf_rules "$rules_content" "./.windsurf"
}

create_global_rules_files() {
	local rules_content="$1"
	
	echo "Creating global rules files for all supported tools..."

	# Create necessary directories
	local home_dir="${GANDALF_HOME_OVERRIDE:-$HOME}"
	local -a rule_dirs=("$home_dir/.cursor/rules" "$home_dir/.claude" "$home_dir/.windsurf")
	for dir in "${rule_dirs[@]}"; do
		mkdir -p "$dir" || {
			echo "Warning: Failed to create rules directory: $dir" >&2
		}
	done

	local cursor_success=false
	local claude_success=false
	local windsurf_success=false

	# Create rules for each tool using the combined content
	if create_cursor_rules "$rules_content" "$home_dir/.cursor/rules"; then
		cursor_success=true
		echo "Installing global rules for Cursor IDE"
	fi

	if create_claude_rules "$rules_content"; then
		claude_success=true
		echo "Installing global rules for Claude Code"
	fi

	if create_windsurf_rules "$rules_content" "$home_dir/.windsurf"; then
		windsurf_success=true
		echo "Installing global rules for Windsurf IDE"
	fi

	if [[ "$cursor_success" = true || "$claude_success" = true || "$windsurf_success" = true ]]; then
		echo "Global Rules Files Created:"
		[[ "$cursor_success" = true ]] && echo "Cursor: $home_dir/.cursor/rules/$MCP_SERVER_NAME-rules.mdc"
		[[ "$claude_success" = true ]] && echo "Claude Code: $home_dir/.claude/CLAUDE.md"
		[[ "$windsurf_success" = true ]] && echo "Windsurf: $home_dir/.windsurf/global_rules.md"
	fi

	return 0
}

create_local_rules_files() {
	local rules_content="$1"
	
	echo "Creating local workspace rules files..."

	local cursor_success=false
	local claude_success=false
	local windsurf_success=false

	# Create local rules for each tool
	if create_local_cursor_rules "$rules_content"; then
		cursor_success=true
		echo "Installing local rules for Cursor IDE"
	fi

	if create_local_claude_rules "$rules_content"; then
		claude_success=true
		echo "Installing local rules for Claude Code"
	fi

	if create_local_windsurf_rules "$rules_content"; then
		windsurf_success=true
		echo "Installing local rules for Windsurf IDE"
	fi

	if [[ "$cursor_success" = true || "$claude_success" = true || "$windsurf_success" = true ]]; then
		echo "Local Rules Files Created:"
		[[ "$cursor_success" = true ]] && echo "Cursor: ./.cursor/rules/$MCP_SERVER_NAME-rules.mdc"
		[[ "$claude_success" = true ]] && echo "Claude Code: ./CLAUDE.md"
		[[ "$windsurf_success" = true ]] && echo "Windsurf: ./.windsurf/global_rules.md"
	fi

	return 0
}

create_rules_files() {
	local spec_dir="${GANDALF_SPEC_OVERRIDE:-$GANDALF_ROOT/spec}"

	local workflows_file="$spec_dir/rules/core.md"
	local troubleshooting_file="$spec_dir/rules/troubleshooting.md"

	# Check if any rules files exist
	if [[ ! -f "$workflows_file" && ! -f "$troubleshooting_file" ]]; then
		echo "Warning: No rules files found in $spec_dir" >&2
		echo "Skipping rules file creation"
		return 0
	fi

	echo "Found rules files in $spec_dir"

	# Combine the rule files into a single file
	local combined_rules=""
	if [[ -f "$workflows_file" ]]; then
		combined_rules="$(cat "$workflows_file")"
	fi
	if [[ -f "$troubleshooting_file" ]]; then
		if [[ -n "$combined_rules" ]]; then
			combined_rules="$combined_rules"$'\n\n'"$(cat "$troubleshooting_file")"
		else
			combined_rules="$(cat "$troubleshooting_file")"
		fi
	fi

	# Create rules based on options
	if [[ "$LOCAL_ONLY" == "true" ]]; then
		create_local_rules_files "$combined_rules"
	elif [[ "$GLOBAL_ONLY" == "true" ]]; then
		create_global_rules_files "$combined_rules"
	else
		# Default: create both global and local rules
		create_global_rules_files "$combined_rules"
		create_local_rules_files "$combined_rules"
	fi

	echo "See spec/rules/core.md and spec/rules/troubleshooting.md for complete documentation"

	return 0
}

main() {
	if ! parse_arguments "$@"; then
		exit 1
	fi

	echo "Starting Gandalf Rules Creation..."

	if ! create_rules_files; then
		echo "Error: Rules file creation failed" >&2
		exit 1
	fi

	echo "Gandalf Rules Creation completed successfully!"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main "$@"
fi 