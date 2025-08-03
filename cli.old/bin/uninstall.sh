#!/usr/bin/env bash
# Gandalf MCP Server Uninstall Script

set -euo pipefail

SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
GANDALF_ROOT="$(dirname "$(dirname "$SCRIPT_PATH")")"

export MCP_SERVER_NAME="${MCP_SERVER_NAME:-gandalf}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

usage() {
	cat <<EOF
Usage: ./gandalf uninstall [OPTIONS]

Remove Gandalf MCP server configurations and setup files.

IMPORTANT: This removes configuration files but preserves conversation history.

Options:
    -f, --force            Skip confirmation prompts
    -h, --help             Show this help
    --backup-dir <path>    Custom backup directory (default: ~/.gandalf_backups)
    --keep-cache           Keep cache files (default: remove cache)
    --dry-run              Show what would be removed without actually removing

What this removes:
    - Gandalf MCP server files and binaries
    - Python virtual environment and dependencies
    - Global ~/.gandalf directory and all contents
    - MCP server configurations from all agentic tools (Cursor, Claude Code, Windsurf)
    - Gandalf CLI aliases and shortcuts

What this preserves:
    - Conversation history (agentic tool databases remain untouched)
    - Project files and code
    - Git repositories and history
    - Python installation
    - Agentic tool installations themselves

Examples:
    gandalf uninstall                    # Interactive uninstall with prompts
    gandalf uninstall -f                 # Force uninstall without prompts
    gandalf uninstall --dry-run          # Show what would be removed
    gandalf uninstall --keep-cache       # Keep cache files

EOF
}

# Parse arguments
FORCE_MODE=false
DRY_RUN=false
KEEP_CACHE=false
BACKUP_DIR="$HOME/.gandalf_backups"

while [[ $# -gt 0 ]]; do
	case $1 in
	-f | --force)
		FORCE_MODE=true
		shift
		;;
	--dry-run)
		DRY_RUN=true
		shift
		;;
	--keep-cache)
		KEEP_CACHE=true
		shift
		;;
	--backup-dir)
		BACKUP_DIR="$2"
		shift 2
		;;
	-h | --help)
		usage
		exit 0
		;;
	*)
		echo "Unknown option $1"
		usage
		exit 1
		;;
	esac
done

BACKUP_PATH="$BACKUP_DIR/gandalf_backup_$TIMESTAMP"

if [[ "$DRY_RUN" == "true" ]]; then
	echo "DRY RUN MODE - No changes will be made"
fi

# Create backup directory
if [[ "$DRY_RUN" == "false" ]]; then
	mkdir -p "$BACKUP_PATH"
	echo "Created backup directory: $BACKUP_PATH"
fi

# Confirmation prompt
if [[ "$FORCE_MODE" == "false" && "$DRY_RUN" == "false" ]]; then
	echo "This will remove all Gandalf MCP server configurations"
	echo "Backup location: $BACKUP_PATH"
	read -p "Continue? (y/N): " -n 1 -r
	echo
	if [[ ! $REPLY =~ ^[Yy]$ ]]; then
		echo "Uninstall cancelled"
		exit 0
	fi
fi

# Stop MCP server processes
echo "Stopping Gandalf MCP server processes..."

# In test mode, don't kill processes to avoid interfering with running servers
if [[ "${TEST_MODE:-false}" == "true" ]]; then
	echo "TEST_MODE detected - skipping process termination to avoid interfering with running servers"
else
	PIDS=$(pgrep -f "$MCP_SERVER_NAME.*main.py" 2>/dev/null || echo "")
	if [[ -n "$PIDS" ]]; then
		if [[ "$DRY_RUN" == "false" ]]; then
			echo "$PIDS" | xargs kill 2>/dev/null || true
			sleep 2
			# Force kill if still running
			REMAINING=$(pgrep -f "$MCP_SERVER_NAME.*main.py" 2>/dev/null || echo "")
			if [[ -n "$REMAINING" ]]; then
				echo "$REMAINING" | xargs kill -9 2>/dev/null || true
			fi
			echo "Stopped MCP server processes"
		else
			echo "[DRY RUN] Would stop processes: $PIDS"
		fi
	else
		echo "No running MCP server processes found"
	fi
fi

# Remove Cursor configuration
CURSOR_CONFIG="$HOME/.cursor/mcp.json"
CURSOR_RULES_DIR="$HOME/.cursor/rules"
CURSOR_RULES="$CURSOR_RULES_DIR/gandalf-rules.mdc"

if [[ -f "$CURSOR_CONFIG" ]]; then
	echo "Removing Cursor MCP configuration..."
	if [[ "$DRY_RUN" == "false" ]]; then
		cp "$CURSOR_CONFIG" "$BACKUP_PATH/" 2>/dev/null || true
		if command -v jq &>/dev/null; then
			TEMP_FILE=$(mktemp)
			jq --arg name "$MCP_SERVER_NAME" 'del(.mcpServers[$name])' "$CURSOR_CONFIG" >"$TEMP_FILE" && mv "$TEMP_FILE" "$CURSOR_CONFIG"
			echo "Removed $MCP_SERVER_NAME from Cursor MCP config"
		else
			rm -f "$CURSOR_CONFIG"
			echo "jq not available, removed entire Cursor MCP config"
		fi
	else
		echo "[DRY RUN] Would remove Cursor MCP configuration"
	fi
fi

if [[ -f "$CURSOR_RULES" ]]; then
	if [[ "$DRY_RUN" == "false" ]]; then
		cp "$CURSOR_RULES" "$BACKUP_PATH/" 2>/dev/null || true
		rm -f "$CURSOR_RULES"
		echo "Removed Cursor rules file"
	else
		echo "[DRY RUN] Would remove Cursor rules file"
	fi
fi

# Clean up empty Cursor rules directory
if [[ -d "$CURSOR_RULES_DIR" ]] && [[ -z "$(ls -A "$CURSOR_RULES_DIR" 2>/dev/null)" ]]; then
	if [[ "$DRY_RUN" == "false" ]]; then
		rmdir "$CURSOR_RULES_DIR" 2>/dev/null || true
		echo "Removed empty Cursor rules directory"
	else
		echo "[DRY RUN] Would remove empty Cursor rules directory"
	fi
fi

# Remove Claude Code configuration
echo "Removing Claude Code configuration..."
CLAUDE_CONFIG="$HOME/.claude/mcp.json"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"

if command -v claude >/dev/null 2>&1; then
	if [[ "$DRY_RUN" == "false" ]]; then
		claude mcp remove "$MCP_SERVER_NAME" -s user 2>/dev/null || true
		claude mcp remove "$MCP_SERVER_NAME" -s local 2>/dev/null || true
		echo "Removed Claude Code MCP configuration"
	else
		echo "[DRY RUN] Would remove Claude Code MCP configuration"
	fi
else
	echo "Claude CLI not available - checking manual config files"

	if [[ -f "$CLAUDE_CONFIG" ]]; then
		if [[ "$DRY_RUN" == "false" ]]; then
			cp "$CLAUDE_CONFIG" "$BACKUP_PATH/" 2>/dev/null || true
			if command -v jq &>/dev/null; then
				TEMP_FILE=$(mktemp)
				jq --arg name "$MCP_SERVER_NAME" 'del(.mcpServers[$name])' "$CLAUDE_CONFIG" >"$TEMP_FILE" && mv "$TEMP_FILE" "$CLAUDE_CONFIG"
				echo "Removed $MCP_SERVER_NAME from Claude Code MCP config"
			else
				rm -f "$CLAUDE_CONFIG"
				echo "jq not available, removed entire Claude Code MCP config"
			fi
		else
			echo "[DRY RUN] Would remove Claude Code MCP configuration"
		fi
	fi
fi

# Remove Claude Code project settings with Gandalf rules
if [[ -f "$CLAUDE_SETTINGS" ]]; then
	if [[ "$DRY_RUN" == "false" ]]; then
		cp "$CLAUDE_SETTINGS" "$BACKUP_PATH/" 2>/dev/null || true
		if command -v jq &>/dev/null; then
			TEMP_FILE=$(mktemp)
			jq 'del(.gandalfRules)' "$CLAUDE_SETTINGS" >"$TEMP_FILE" && mv "$TEMP_FILE" "$CLAUDE_SETTINGS"
			echo "Removed Gandalf rules from Claude Code settings"
		else
			echo "jq not available - Claude Code settings may contain Gandalf rules"
		fi
	else
		echo "[DRY RUN] Would remove Gandalf rules from Claude Code settings"
	fi
fi

# Remove Windsurf configuration
echo "Removing Windsurf configuration..."
WINDSURF_CONFIG="$HOME/.windsurf/mcp.json"
WINDSURF_GLOBAL_RULES="$HOME/.windsurf/global_rules.md"

if [[ -f "$WINDSURF_CONFIG" ]]; then
	if [[ "$DRY_RUN" == "false" ]]; then
		cp "$WINDSURF_CONFIG" "$BACKUP_PATH/" 2>/dev/null || true
		if command -v jq &>/dev/null; then
			TEMP_FILE=$(mktemp)
			jq --arg name "$MCP_SERVER_NAME" 'del(.mcpServers[$name])' "$WINDSURF_CONFIG" >"$TEMP_FILE" && mv "$TEMP_FILE" "$WINDSURF_CONFIG"
			echo "Removed $MCP_SERVER_NAME from Windsurf MCP config"
		else
			rm -f "$WINDSURF_CONFIG"
			echo "jq not available, removed entire Windsurf MCP config"
		fi
	else
		echo "[DRY RUN] Would remove Windsurf MCP configuration"
	fi
fi

if [[ -f "$WINDSURF_GLOBAL_RULES" ]]; then
	if [[ "$DRY_RUN" == "false" ]]; then
		cp "$WINDSURF_GLOBAL_RULES" "$BACKUP_PATH/" 2>/dev/null || true
		rm -f "$WINDSURF_GLOBAL_RULES"
		echo "Removed Windsurf global rules file"
	else
		echo "[DRY RUN] Would remove Windsurf global rules file"
	fi
fi

# Note about project-specific Windsurf rules
echo "Note: Project-specific .windsurfrules files remain in individual project directories"
echo "These can be safely removed manually if no longer needed"

# Remove ~/.gandalf directory
GANDALF_HOME="$HOME/.gandalf"
if [[ -d "$GANDALF_HOME" ]]; then
	echo "Removing ~/.gandalf directory..."
	if [[ "$DRY_RUN" == "false" ]]; then
		cp -r "$GANDALF_HOME" "$BACKUP_PATH/" 2>/dev/null || true
		if [[ "$KEEP_CACHE" == "false" ]]; then
			rm -rf "$GANDALF_HOME"
			echo "Removed ~/.gandalf directory"
		else
			rm -rf "$GANDALF_HOME"/{exports,backups,config,installation-state} 2>/dev/null || true
			echo "Removed ~/.gandalf directory (kept cache)"
		fi
	else
		echo "[DRY RUN] Would remove ~/.gandalf directory"
	fi
fi

# Remove shell aliases
SHELL_FILES=("$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc" "$HOME/.profile")
for SHELL_FILE in "${SHELL_FILES[@]}"; do
	if [[ -f "$SHELL_FILE" ]] && grep -q "gandalf\|gdlf" "$SHELL_FILE" 2>/dev/null; then
		if [[ "$DRY_RUN" == "false" ]]; then
			cp "$SHELL_FILE" "$BACKUP_PATH/" 2>/dev/null || true
			TEMP_FILE=$(mktemp)
			grep -v "gandalf\|gdlf" "$SHELL_FILE" >"$TEMP_FILE" || true
			mv "$TEMP_FILE" "$SHELL_FILE"
			echo "Removed Gandalf references from: $SHELL_FILE"
		else
			echo "[DRY RUN] Would remove Gandalf references from: $SHELL_FILE"
		fi
	fi
done

if [[ "$DRY_RUN" == "false" ]]; then
	cat <<EOF
Uninstall completed successfully!
Backup location: $BACKUP_PATH

Next steps:
1. Restart your agentic tools to reload configurations
2. Backup files are available at: $BACKUP_PATH

To reinstall: ./gandalf install
EOF
else
	echo "DRY RUN completed - no changes were made"
fi
