# Installation Guide

Setup instructions for Gandalf MCP Server.

## Prerequisites

- Python 3.12+
- Git
- IDE: Cursor, Claude Code, or Windsurf with MCP support

## Quick Installation

```bash
# Clone repository
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf

# Auto-install and configure
./gandalf install

# Verify installation
./gandalf test
```

The installer automatically:

- Detects your IDE and configures MCP settings
- Initializes the agentic tools registry
- Sets up conversation database detection
- Creates global rules files for each tool

## Manual Configuration

If auto-installation fails, configure manually:

### Cursor IDE

Create or update `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/absolute/path/to/gandalf/gandalf",
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
claude mcp add gandalf /absolute/path/to/gandalf/gandalf \
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
      "command": "/absolute/path/to/gandalf/gandalf",
      "args": ["run"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/gandalf/server"
      }
    }
  }
}
```

## Registry System

Gandalf uses an automated registry system to detect and manage agentic tools:

### Automatic Registry Setup

The registry is automatically initialized during:

- First server startup (self-healing)
- Installation (`./gandalf install`)
- Manual registration

### Manual Registry Commands

```bash
# Auto-detect and register all tools
./gandalf registry auto-register

# List registered tools
./gandalf registry list

# Register specific tool
./gandalf registry register cursor ~/.cursor

# Remove tool registration
./gandalf registry unregister cursor

# Check current registrations
cat ~/.gandalf/registry.json
```

### Registry Troubleshooting

If conversation recall returns empty results:

```bash
# Check registry status
./gandalf registry list

# Re-initialize if empty
./gandalf registry auto-register

# Verify detection
./gandalf test --quick
```

## Verification

### Test Core Tools

Test the essential tools in your IDE:

```bash
# Conversation recall
recall_conversations()

# Project context
get_project_info()

# File discovery
list_project_files()

# Server status
get_server_version()

# Export capability
export_individual_conversations()
```

### Validation Commands

```bash
# Quick validation
./gandalf test

# Extended validation
./gandalf lembas

# Installation status
cat ~/.gandalf/installation-state
```

### Debug Mode

Enable detailed logging:

```bash
# Run with debug output
GANDALF_DEBUG=true ./gandalf run

# Or add to MCP config
"env": {
  "GANDALF_DEBUG": "true",
  "PYTHONPATH": "/absolute/path/to/gandalf/server"
}
```

## Troubleshooting

### Common Issues

1. Tools not appearing: Restart IDE completely (Cmd/Ctrl + Q)
2. Server not responding: Check Python version and dependencies
3. Permission errors: Ensure execute permissions on `./gandalf`

### Reset Installation

```bash
# Force reinstall
./gandalf install --force

# Check dependencies
cd gandalf/server && pip install -e .
```

## Uninstallation

```bash
# Remove all configurations
./gandalf uninstall

# Force removal without prompts
./gandalf uninstall --force
```

## Getting Help

- Documentation: [README](../README.md) | [API](API.md) | [Troubleshooting](TROUBLESHOOTING.md)
- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Quick Help: `./gandalf --help`
