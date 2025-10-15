#!/usr/bin/env bats
#
# Install Script Tests
#

GIT_ROOT="$(git rev-parse --show-toplevel)"
SCRIPT="${GIT_ROOT}/cli/bin/install.sh"
[[ ! -f "${SCRIPT}" ]] && echo "Script not found: ${SCRIPT}" >&2 && exit 1

setup() {
	source "${SCRIPT}"

	GANDALF_ROOT="$(mktemp -d)"

	CORE_SCRIPT="${GIT_ROOT}/cli/lib/core.sh"

	# Set up common test environment for MCP tests
	GANDALF_HOME="$(mktemp -d)"
	CURSOR_DIR="$GANDALF_HOME/.cursor"
	CLAUDE_DIR="$GANDALF_HOME/.claude"
	mkdir -p "$CURSOR_DIR"
	mkdir -p "$CLAUDE_DIR"

	CURSOR_CONFIG="$CURSOR_DIR/mcp.json"
	CLAUDE_CONFIG="$CLAUDE_DIR/claude_desktop_config"

	create_server_file

	echo "0.1.0" >"$GANDALF_ROOT/VERSION"

	mkdir -p "$GANDALF_ROOT/spec"
	cat >"$GANDALF_ROOT/spec/gandalf-rules.md" <<EOF
# Gandalf MCP Server Usage Rules
EOF

	GANDALF_RULES_FILE="$GANDALF_ROOT/spec/gandalf-rules.md"
	export GANDALF_RULES_FILE

	FORCE_INSTALL="true"

	export GANDALF_ROOT
	export FORCE_INSTALL
	export CORE_SCRIPT
	export HOME="$GANDALF_HOME"
	export CURSOR_CONFIG
	export CLAUDE_CONFIG
}

########################################################
# Mocks
########################################################
mock_git_rev_parse() {
	git() {
		if [[ "$1" == "rev-parse" && "$2" == "--show-toplevel" ]]; then
			echo "$GANDALF_ROOT"
		else
			command git "$@"
		fi
	}
	export -f git
}

mock_git_rev_parse_fail() {
	git() {
		if [[ "$1" == "rev-parse" && "$2" == "--show-toplevel" ]]; then
			return 1
		else
			command git "$@"
		fi
	}
	export -f git
}

mock_claude_command_available() {
	claude() {
		case "$1 $2" in
		"mcp remove")
			echo "Removed MCP server \"$3\" from local config"
			return 0
			;;
		"mcp add-json")
			echo "Added stdio MCP server $3 to local config"
			return 0
			;;
		*)
			echo "Unknown claude command"
			return 1
			;;
		esac
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

mock_claude_add_json_fail() {
	claude() {
		case "$1 $2" in
		"mcp remove")
			echo "Removed MCP server \"$3\" from local config"
			return 0
			;;
		"mcp add-json")
			echo "Failed to add MCP server"
			return 1
			;;
		*)
			echo "Unknown claude command"
			return 1
			;;
		esac
	}
	export -f claude
}
mock_check_dependencies() {
	CHECK_DEPENDENCIES_SCRIPT="$(mktemp -d)/check-dependencies.sh"
	cat <<EOF >"${CHECK_DEPENDENCIES_SCRIPT}"
#!/usr/bin/env bash
exit 0
EOF
	chmod +x "${CHECK_DEPENDENCIES_SCRIPT}"

	export CHECK_DEPENDENCIES_SCRIPT
}

mock_check_dependencies_fail() {
	# shellcheck disable=SC2329
	CHECK_DEPENDENCIES_SCRIPT="$(mktemp -d)/check-dependencies.sh"
	cat <<EOF >"${CHECK_DEPENDENCIES_SCRIPT}"
#!/usr/bin/env bash
exit 1
EOF
	chmod +x "${CHECK_DEPENDENCIES_SCRIPT}"

	export CHECK_DEPENDENCIES_SCRIPT
}

mock_registry() {
	REGISTRY_SCRIPT="$(mktemp -d)/registry.sh"
	cat <<EOF >"${REGISTRY_SCRIPT}"
#!/usr/bin/env bash
registry() {
	# Set up DB_PATH_DATA with cursor and claude entries for testing
	export DB_PATH_DATA='{"cursor":["/test/cursor"],"claude":["/test/claude"]}'
	return 0
}
EOF
	chmod +x "${REGISTRY_SCRIPT}"

	export REGISTRY_SCRIPT
}

mock_registry_fail() {
	REGISTRY_SCRIPT="$(mktemp -d)/registry.sh"
	cat <<EOF >"${REGISTRY_SCRIPT}"
#!/usr/bin/env bash
exit 1
EOF
	chmod +x "${REGISTRY_SCRIPT}"

	export REGISTRY_SCRIPT
}

create_server_file() {
	SERVER_PATH="$GANDALF_ROOT/server/main.py"
	mkdir -p "$GANDALF_ROOT/server/src"
	cat <<EOF >"$SERVER_PATH"
#!/usr/bin/env python
print("Running Gandalf MCP Server")
EOF
	chmod +x "$SERVER_PATH"
	export SERVER_PATH
}

create_rules_file() {
	# Create minimal rules file
	mkdir -p "$GANDALF_ROOT/spec"
	cat >"$GANDALF_ROOT/spec/gandalf-rules.md" <<EOF
# Gandalf MCP Server Usage Rules
EOF
	export GANDALF_RULES_FILE="$GANDALF_ROOT/spec/gandalf-rules.md"
}

########################################################
# install
########################################################
@test "install:: runs successfully when dependencies are available" {
	mock_check_dependencies
	mock_registry
	mock_git_rev_parse

	run install
	[[ "$status" -eq 0 ]]
}

@test "install:: installs rules when running complete installation" {
	mock_check_dependencies
	mock_registry
	mock_git_rev_parse

	run install
	[[ "$status" -eq 0 ]]

	# Check that rules were installed in the test directory
	[[ -d "$GANDALF_ROOT/.cursor/rules" ]]
	[[ -f "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc" ]]
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc"
}

@test "install:: fails when dependencies are not available" {
	mock_check_dependencies_fail

	run install
	[[ "$status" -eq 1 ]]
}

########################################################
# setup_gandalf_home
########################################################
@test "setup_gandalf_home:: creates directory structure" {
	run setup_gandalf_home
	[[ "$status" -eq 0 ]]
	[[ -d "$GANDALF_HOME/logs" ]]
	[[ -d "$GANDALF_HOME/registry" ]]
}

@test "setup_gandalf_home:: removes existing directory when force is true" {
	FORCE_INSTALL="true"

	mkdir -p "$GANDALF_HOME/old_content"
	echo "test" >"$GANDALF_HOME/old_file"

	run setup_gandalf_home
	[[ "$status" -eq 0 ]]
	[[ -d "$GANDALF_HOME/logs" ]]
	[[ -d "$GANDALF_HOME/registry" ]]
	[[ ! -d "$GANDALF_HOME/old_content" ]]
	[[ ! -f "$GANDALF_HOME/old_file" ]]
}

@test "setup_gandalf_home:: preserves existing directory when force is false" {
	unset FORCE_INSTALL

	mkdir -p "$GANDALF_HOME/existing"
	echo "test" >"$GANDALF_HOME/existing_file"

	run setup_gandalf_home
	[[ "$status" -eq 0 ]]
	[[ -d "$GANDALF_HOME/logs" ]]
	[[ -d "$GANDALF_HOME/registry" ]]
	[[ -d "$GANDALF_HOME/existing" ]]
	[[ -f "$GANDALF_HOME/existing_file" ]]
}

########################################################
# setup_mcp_connections
########################################################
@test "setup_mcp_connections:: creates Cursor MCP configuration when file doesn't exist" {
	run setup_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CURSOR_DIR/mcp.json" ]]
	grep -q "gandalf" "$CURSOR_DIR/mcp.json"
	grep -q "python" "$CURSOR_DIR/mcp.json"
	grep -q "server/main.py" "$CURSOR_DIR/mcp.json"
}

@test "setup_mcp_connections:: creates Claude Desktop configuration when file doesn't exist" {

	run setup_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CLAUDE_DIR/claude_desktop_config" ]]
	grep -q "gandalf" "$CLAUDE_DIR/claude_desktop_config"
	grep -q "python" "$CLAUDE_DIR/claude_desktop_config"
	grep -q "server/main.py" "$CLAUDE_DIR/claude_desktop_config"
}

@test "setup_mcp_connections:: updates existing configuration when gandalf key doesn't exist" {
	jq -n '{
		"mcpServers": {
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$CURSOR_DIR/mcp.json"

	run setup_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CURSOR_DIR/mcp.json" ]]
	grep -q "gandalf" "$CURSOR_DIR/mcp.json"
	grep -q "other-server" "$CURSOR_DIR/mcp.json"
	grep -q "python" "$CURSOR_DIR/mcp.json"
	grep -q "server/main.py" "$CURSOR_DIR/mcp.json"
}

@test "setup_mcp_connections:: skips existing configuration when gandalf key exists and force not set" {
	unset FORCE_INSTALL
	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/old/path"]
			},
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$CURSOR_DIR/mcp.json"

	run setup_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CURSOR_DIR/mcp.json" ]]
	# Should keep the old gandalf config
	grep -q "/old/path" "$CURSOR_DIR/mcp.json"
	grep -q "other-server" "$CURSOR_DIR/mcp.json"
	# Should not contain the new server path
	! grep -q "server/main.py" "$CURSOR_DIR/mcp.json"
}

@test "setup_mcp_connections:: forces update when gandalf key exists and force is set" {
	FORCE_INSTALL="true"

	# Create existing config with gandalf
	jq -n '{
		"mcpServers": {
			"gandalf": {
				"command": "python",
				"args": ["/old/path"]
			},
			"other-server": {
				"command": "node",
				"args": ["/path/to/other"]
			}
		}
	}' >"$CURSOR_DIR/mcp.json"

	run setup_mcp_connections
	[[ "$status" -eq 0 ]]

	[[ -f "$CURSOR_DIR/mcp.json" ]]
	# Should update to new gandalf config
	grep -q "server/main.py" "$CURSOR_DIR/mcp.json"
	grep -q "other-server" "$CURSOR_DIR/mcp.json"
	# Should not contain the old path
	! grep -q "/old/path" "$CURSOR_DIR/mcp.json"
}

########################################################
# setup_claude_code_mcp
########################################################
@test "setup_claude_code_mcp:: configures successfully when claude command is available" {
	create_server_file
	mock_claude_command_available

	run setup_claude_code_mcp
	[[ "$status" -eq 0 ]]

	echo "$output" | grep -q "Claude Code MCP configuration added successfully"
}

@test "setup_claude_code_mcp:: skips when claude command is not available" {
	create_server_file
	mock_claude_command_unavailable

	run setup_claude_code_mcp
	[[ "$status" -eq 0 ]]

	echo "$output" | grep -q "Claude Code CLI not found, skipping Claude Code MCP configuration"
}

@test "setup_claude_code_mcp:: fails when claude mcp add-json fails" {
	create_server_file
	mock_claude_add_json_fail

	run setup_claude_code_mcp
	[[ "$status" -eq 1 ]]

	echo "$output" | grep -q "Failed to configure Claude Code MCP"
}

########################################################
# setup_editor_config
########################################################
@test "setup_editor_config:: creates config file when it doesn't exist" {

	create_server_file

	local config_file="$GANDALF_HOME/.cursor/mcp.json"

	# Ensure config file doesn't exist
	rm -f "$config_file"

	run setup_editor_config "Cursor" "$config_file"
	[[ "$status" -eq 0 ]]

	[[ -f "$config_file" ]]
	grep -q "gandalf" "$config_file"
	grep -q "python" "$config_file"
	grep -q "$SERVER_PATH" "$config_file"
}

@test "setup_editor_config:: updates config when gandalf key doesn't exist" {

	create_server_file

	local config_file="$GANDALF_HOME/.cursor/mcp.json"

	# Create existing config without gandalf
	mkdir -p "$(dirname "$config_file")"
	cat >"$config_file" <<EOF
{
  "mcpServers": {
    "other-server": {
      "command": "node",
      "args": ["/path/to/other"]
    }
  }
}
EOF

	run setup_editor_config "Cursor" "$config_file"
	[[ "$status" -eq 0 ]]

	[[ -f "$config_file" ]]
	grep -q "gandalf" "$config_file"
	grep -q "other-server" "$config_file"
	grep -q "python" "$config_file"
	grep -q "$SERVER_PATH" "$config_file"
}

@test "setup_editor_config:: skips when gandalf exists and force not set" {
	unset FORCE_INSTALL

	create_server_file

	local config_file="$GANDALF_HOME/.cursor/mcp.json"

	# Create existing config with gandalf
	mkdir -p "$(dirname "$config_file")"
	cat >"$config_file" <<EOF
{
  "mcpServers": {
    "gandalf": {
      "command": "python",
      "args": ["/old/path"]
    },
    "other-server": {
      "command": "node",
      "args": ["/path/to/other"]
    }
  }
}
EOF

	run setup_editor_config "Cursor" "$config_file"
	[[ "$status" -eq 0 ]]

	[[ -f "$config_file" ]]
	# Should keep the old gandalf config
	grep -q "/old/path" "$config_file"
	grep -q "other-server" "$config_file"
	# Should not contain the new server path
	! grep -q "$SERVER_PATH" "$config_file"
}

@test "setup_editor_config:: forces update when gandalf exists and force is set" {
	export FORCE_INSTALL="true"

	create_server_file

	local config_file="$GANDALF_HOME/.cursor/mcp.json"

	# Create existing config with gandalf
	mkdir -p "$(dirname "$config_file")"
	cat >"$config_file" <<EOF
{
  "mcpServers": {
    "gandalf": {
      "command": "python",
      "args": ["/old/path"]
    },
    "other-server": {
      "command": "node",
      "args": ["/path/to/other"]
    }
  }
}
EOF

	run setup_editor_config "Cursor" "$config_file"
	[[ "$status" -eq 0 ]]

	[[ -f "$config_file" ]]
	# Should update to new gandalf config
	grep -q "$SERVER_PATH" "$config_file"
	grep -q "other-server" "$config_file"
	# Should not contain the old path
	! grep -q "/old/path" "$config_file"
}

########################################################
# gandalf.sh integration tests
########################################################
@test "gandalf.sh:: --server command works" {
	cd "$GIT_ROOT"
	run ./gandalf.sh --server --help
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "Usage:"
}

@test "gandalf.sh:: --server status works" {
	cd "$GIT_ROOT"
	run ./gandalf.sh --server status
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "Server is not running"
}

@test "gandalf.sh:: --server version works" {
	cd "$GIT_ROOT"
	GANDALF_ROOT="$GANDALF_ROOT" run ./gandalf.sh --server version
	[[ "$status" -eq 0 ]]
	echo "$output" | grep -q "0.1.0"
}

@test "gandalf.sh:: --server pid works" {
	cd "$GIT_ROOT"
	run ./gandalf.sh --server pid
	[[ "$status" -eq 1 ]]
	echo "$output" | grep -q "No PID file found"
}

########################################################
# setup_cursor_rules
########################################################
@test "setup_cursor_rules:: creates rules directory and copies file" {
	mock_git_rev_parse
	create_rules_file

	run setup_cursor_rules "$GANDALF_ROOT" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	# Rules should be installed in the specified directory
	[[ -d "$GANDALF_ROOT/.cursor/rules" ]]
	[[ -f "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc" ]]
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc"
}

@test "setup_cursor_rules:: uses git root when available" {
	cd "$GANDALF_HOME"
	git init
	git config user.email "test@example.com"
	git config user.name "Test User"
	touch README.md
	git add README.md
	git commit -m "Initial commit"

	run setup_cursor_rules "$GANDALF_HOME" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	# Should use the new git root (GANDALF_HOME)
	[[ -d "$GANDALF_HOME/.cursor/rules" ]]
	[[ -f "$GANDALF_HOME/.cursor/rules/gandalf-rules.mdc" ]]
}

@test "setup_cursor_rules:: falls back to current directory when not in git repo" {
	# Create a non-git directory
	local non_git_dir
	non_git_dir="$(mktemp -d)"
	cd "$non_git_dir"

	# Mock git to fail
	mock_git_rev_parse_fail

	export GANDALF_ROOT

	run setup_cursor_rules "$non_git_dir" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	[[ -d "$non_git_dir/.cursor/rules" ]]
	[[ -f "$non_git_dir/.cursor/rules/gandalf-rules.mdc" ]]

	# Cleanup
	rm -rf "$non_git_dir"
}

@test "setup_cursor_rules:: fails when source file doesn't exist" {
	# Set invalid rules source
	RULES_SOURCE=""
	export RULES_SOURCE

	run setup_cursor_rules "$GANDALF_ROOT" "/nonexistent/rules.md"
	[[ "$status" -eq 0 ]]
	# Should still create the rules file with empty content
	[[ -f "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc" ]]
}

@test "setup_cursor_rules:: overwrites existing rules file" {
	mock_git_rev_parse
	create_rules_file

	# Create existing rules file
	mkdir -p "$GANDALF_ROOT/.cursor/rules"
	echo "old content" >"$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc"

	run setup_cursor_rules "$GANDALF_ROOT" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	[[ -f "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc" ]]
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc"
	! grep -q "old content" "$GANDALF_ROOT/.cursor/rules/gandalf-rules.mdc"
}

########################################################
# setup_claude_rules
########################################################
@test "setup_claude_rules:: creates CLAUDE.md when it doesn't exist" {
	create_rules_file

	run setup_claude_rules "$GANDALF_ROOT" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	[[ -f "$GANDALF_ROOT/CLAUDE.md" ]]
	grep -q "###GANDALFRULES###" "$GANDALF_ROOT/CLAUDE.md"
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/CLAUDE.md"
}

@test "setup_claude_rules:: appends rules when no markers exist" {
	create_rules_file

	# Create existing CLAUDE.md without markers
	echo "Existing content" >"$GANDALF_ROOT/CLAUDE.md"

	run setup_claude_rules "$GANDALF_ROOT" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	[[ -f "$GANDALF_ROOT/CLAUDE.md" ]]
	grep -q "Existing content" "$GANDALF_ROOT/CLAUDE.md"
	grep -q "###GANDALFRULES###" "$GANDALF_ROOT/CLAUDE.md"
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/CLAUDE.md"
}

@test "setup_claude_rules:: replaces content between existing markers" {
	create_rules_file

	# Create CLAUDE.md with existing rules section
	cat >"$GANDALF_ROOT/CLAUDE.md" <<EOF
# Project Documentation

###GANDALFRULES###
Old rules content
###GANDALFRULES###

More documentation
EOF

	run setup_claude_rules "$GANDALF_ROOT" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	[[ -f "$GANDALF_ROOT/CLAUDE.md" ]]
	grep -q "# Project Documentation" "$GANDALF_ROOT/CLAUDE.md"
	grep -q "More documentation" "$GANDALF_ROOT/CLAUDE.md"
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/CLAUDE.md"
	! grep -q "Old rules content" "$GANDALF_ROOT/CLAUDE.md"
}

@test "setup_claude_rules:: handles single marker by appending" {
	create_rules_file

	# Create CLAUDE.md with only one marker
	echo "###GANDALFRULES###" >"$GANDALF_ROOT/CLAUDE.md"
	echo "Incomplete rules" >>"$GANDALF_ROOT/CLAUDE.md"

	run setup_claude_rules "$GANDALF_ROOT" "$GANDALF_ROOT/spec/gandalf-rules.md"
	[[ "$status" -eq 0 ]]

	[[ -f "$GANDALF_ROOT/CLAUDE.md" ]]
	grep -q "Incomplete rules" "$GANDALF_ROOT/CLAUDE.md"
	grep -q "Gandalf MCP Server Usage Rules" "$GANDALF_ROOT/CLAUDE.md"
	# Should have 3 markers now (1 original + 2 new)
	[[ $(grep -c "###GANDALFRULES###" "$GANDALF_ROOT/CLAUDE.md") -eq 3 ]]
}
