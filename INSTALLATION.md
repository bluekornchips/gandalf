# Installation Guide

Setup instructions for Gandalf MCP Server.

## Prerequisites

- Python 3.10+
- Git
- IDE: Cursor, Claude Code, or Windsurf with MCP support

## Quick Installation

```bash
# Clone repository
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf

# Auto-install
./gandalf.sh install

# Verify
./gandalf.sh test
```

The installer automatically detects your IDE and configures everything needed.

## Manual Configuration

If auto-installation fails, configure manually:

### Cursor IDE

Create or update `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/absolute/path/to/gandalf/gandalf.sh",
      "args": ["run"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/gandalf/server"
      }
    }
  }
}
```

### Claude Code

```bash
# Add MCP server
claude mcp add gandalf /absolute/path/to/gandalf/gandalf.sh \
  -s user run \
  -e "PYTHONPATH=/absolute/path/to/gandalf/server"

# Verify configuration
claude mcp list
```

### Windsurf

Create or update `~/.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/absolute/path/to/gandalf/gandalf.sh",
      "args": ["run"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/gandalf/server"
      }
    }
  }
}
```

## Verification

### Essential Tools Test

Test the 6 core tools in your IDE:

```bash
# Conversation recall
recall_conversations(fast_mode=true)

# Project context
get_project_info()

# File discovery
list_project_files(max_files=50, file_types=['.py', '.js'])

# Search functionality
search_conversations(search_query="authentication")

# Server status
get_server_version(random_string="test")

# Export capability
export_individual_conversations(format="json", limit=5)
```

### Validation Commands

```bash
# Quick validation
./gandalf.sh test

# Extended validation
./gandalf.sh lembas --all

# Check test count
./gandalf.sh test --count
# Should show: Total tests: {count}
```

### Debug Mode

Enable detailed logging:

```bash
# Run with debug output
GANDALF_DEBUG=true ./gandalf.sh run

# Or add to MCP config
"env": {
  "GANDALF_DEBUG": "true"
}
```

## Uninstallation

```bash
# Remove all configurations
./gandalf.sh uninstall

# Force removal without prompts
./gandalf.sh uninstall --force

# Keep cache files
./gandalf.sh uninstall --keep-cache
```

## Getting Help

- Documentation: [README](README.md) | [API](API.md) | [Troubleshooting](TROUBLESHOOTING.md)
- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Quick Help: `./gandalf.sh --help`
