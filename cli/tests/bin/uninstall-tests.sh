#!/usr/bin/env bats
#
# Uninstall Script Tests
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/cli/bin/uninstall.sh"
[[ ! -f "${SCRIPT}" ]] && echo "Script not found: ${SCRIPT}" >&2 && exit 1

setup() {
	source "${SCRIPT}"

	GANDALF_ROOT="$(mktemp -d)"

	# Set up common test environment for MCP tests
	GANDALF_HOME="$(mktemp -d)"
	CURSOR_DIR="$GANDALF_HOME/.cursor"
	CLAUDE_DIR="$GANDALF_HOME/.claude"
	mkdir -p "$CURSOR_DIR"
	mkdir -p "$CLAUDE_DIR"

	FORCE_UNINSTALL="true"

	export GANDALF_ROOT
	export FORCE_UNINSTALL
	export HOME="$GANDALF_HOME"
}

########################################################
# Mocks
########################################################
mock_claude_command_available() {
	claude() {
		case "$1" in
		"mcp")
			case "$2" in
			"remove")
				echo "Removed server: $3"
				return 0
				;;
			esac
			;;
		esac
		return 1
	}
	export -f claude
}

mock_claude_command_unavailable() {
	command() {
		if [[ "$1" == "-v" && "$2" == "claude" ]]; then
			return 1
		else
			builtin command "$@"
		fi
	}
	export -f command
}

mock_claude_remove_fail() {
	claude() {
		case "$1" in
		"mcp")
			case "$2" in
			"remove")
				return 1
				;;
			esac
			;;
		esac
		return 1
	}
	export -f claude
}

# ########################################################
# remove_claude_code_mcp
# ########################################################
@test "remove_claude_code_mcp:: removes configuration when claude command is available" {
	mock_claude_command_available

	run remove_claude_code_mcp
	[[ "$status" -eq 0 ]]

	echo "$output" | grep -q "Claude Code MCP configuration removed successfully"
}

@test "remove_claude_code_mcp:: skips when claude command is not available" {
	mock_claude_command_unavailable

	run remove_claude_code_mcp
	[[ "$status" -eq 0 ]]

	echo "$output" | grep -q "Claude Code CLI not found, skipping Claude Code MCP removal"
}

@test "remove_claude_code_mcp:: continues when claude mcp remove fails" {
	mock_claude_remove_fail

	run remove_claude_code_mcp
	[[ "$status" -eq 0 ]]

	echo "$output" | grep -q "Failed to remove Claude Code MCP configuration"
}

########################################################
# uninstall
########################################################
@test "uninstall:: runs successfully with force flag" {
	# Create test MCP config files
	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/path/to/server"]
			},
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$CURSOR_DIR/mcp.json"

	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/path/to/server"]
			}
		}
	}' >"$CLAUDE_DIR/claude_desktop_config"

	run uninstall
	[[ "$status" -eq 0 ]]
}

@test "uninstall:: handles missing MCP config files" {
	run uninstall
	[[ "$status" -eq 0 ]]
}

@test "uninstall:: handles missing Gandalf home directory" {
	rm -rf "$GANDALF_HOME"

	run uninstall
	[[ "$status" -eq 0 ]]
}

########################################################
# remove_mcp_connections
########################################################
@test "remove_mcp_connections:: removes gandalf config from Cursor" {
	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/path/to/server"]
			},
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$CURSOR_DIR/mcp.json"

	run remove_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CURSOR_DIR/mcp.json" ]]
	! grep -q "gandalf" "$CURSOR_DIR/mcp.json"
	grep -q "other-server" "$CURSOR_DIR/mcp.json"
}

@test "remove_mcp_connections:: removes gandalf config from Claude" {
	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/path/to/server"]
			}
		}
	}' >"$CLAUDE_DIR/claude_desktop_config"

	run remove_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CLAUDE_DIR/claude_desktop_config" ]]
	! grep -q "gandalf" "$CLAUDE_DIR/claude_desktop_config"
}

@test "remove_mcp_connections:: handles missing config files" {
	rm -f "$CURSOR_DIR/mcp.json"
	rm -f "$CLAUDE_DIR/claude_desktop_config"

	run remove_mcp_connections
	[[ "$status" -eq 0 ]]
}

@test "remove_mcp_connections:: handles config files without gandalf" {
	jq -n '{
		"mcpServers": {
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$CURSOR_DIR/mcp.json"

	run remove_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CURSOR_DIR/mcp.json" ]]
	grep -q "other-server" "$CURSOR_DIR/mcp.json"
}

########################################################
# remove_editor_config
########################################################
@test "remove_editor_config:: removes gandalf config from existing file" {
	local config_file="$GANDALF_HOME/.cursor/mcp.json"
	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/path/to/server"]
			},
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$config_file"

	run remove_editor_config "$config_file" "Cursor"
	[[ "$status" -eq 0 ]]

	[[ -f "$config_file" ]]
	! grep -q "gandalf" "$config_file"
	grep -q "other-server" "$config_file"
}

@test "remove_editor_config:: handles missing config file" {
	local config_file="$GANDALF_HOME/.cursor/mcp.json"

	run remove_editor_config "$config_file" "Cursor"
	[[ "$status" -eq 0 ]]
}

@test "remove_editor_config:: handles config file without gandalf" {
	local config_file="$GANDALF_HOME/.cursor/mcp.json"
	jq -n '{
		"mcpServers": {
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$config_file"

	run remove_editor_config "$config_file" "Cursor"
	[[ "$status" -eq 0 ]]

	[[ -f "$config_file" ]]
	grep -q "other-server" "$config_file"
}

########################################################
# remove_gandalf_home
########################################################
@test "remove_gandalf_home:: removes existing directory" {
	mkdir -p "$GANDALF_HOME/logs"
	mkdir -p "$GANDALF_HOME/registry"
	echo "test" >"$GANDALF_HOME/test_file"

	run remove_gandalf_home
	[[ "$status" -eq 0 ]]

	[[ ! -d "$GANDALF_HOME" ]]
}

@test "remove_gandalf_home:: handles missing directory" {
	rm -rf "$GANDALF_HOME"

	run remove_gandalf_home
	[[ "$status" -eq 0 ]]
}

########################################################
# remove_python_env
########################################################
@test "remove_python_env:: removes existing venv directory" {
	local venv_dir
	venv_dir="${GANDALF_ROOT}/.venv"
	mkdir -p "$venv_dir/bin"
	touch "$venv_dir/bin/python3"

	run remove_python_env
	[[ "$status" -eq 0 ]]

	[[ ! -d "$venv_dir" ]]
	echo "$output" | grep -q "Removed Python virtual environment"
}

@test "remove_python_env:: handles missing venv directory" {
	run remove_python_env
	[[ "$status" -eq 0 ]]

	echo "$output" | grep -q "Python virtual environment not found"
}
