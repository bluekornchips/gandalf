# Installation Guide

Setup instructions for Gandalf MCP Server.

## Requirements

- Python 3.10+
- Git
- Cursor IDE, Claude Code, or Windsurf with MCP support

## Quick Install

```bash
# Clone and install
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf
./gandalf.sh install

# Verify
./gandalf.sh test
```

The installer auto-detects your IDE and sets up everything.

## Manual Setup

If auto-install fails:

### Cursor IDE

Create `~/.cursor/mcp.json`:

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
claude mcp add gandalf /absolute/path/to/gandalf/gandalf.sh \
  -s user run \
  -e "PYTHONPATH=/absolute/path/to/gandalf/server"
```

### Windsurf

Create `~/.windsurf/mcp.json`:

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

Test in your IDE:

```bash
# Try these commands
recall_conversations(fast_mode=true)
get_project_info()
```

## Performance Tuning

For large projects, add to your MCP config:

```json
"env": {
  "GANDALF_CACHE_TTL": "600",
  "GANDALF_MAX_FILES": "500"
}
```

## Multi-Tool Setup

The installer detects all supported tools automatically. No additional setup needed.

## Getting Help

- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
