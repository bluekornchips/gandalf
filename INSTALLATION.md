# Installation Guide

Gandalf MCP server supports both **Cursor IDE** and **Claude Code** with automatic environment detection. The installation process adapts based on your IDE environment.

## Requirements

- **Python 3.10+** - Required for MCP server
- **Git** - Required for repository operations
- **IDE**: Cursor IDE or Claude Code with MCP support
- **Optional**: BATS for running shell tests

## Quick Install

```bash
# 1. Check dependencies
./gandalf.sh deps

# 2. Install (auto-detects your IDE)
./gandalf.sh install

# 3. Restart your IDE completely

# 4. Test installation
./gandalf.sh test
```

## IDE-Specific Installation

### Claude Code Installation

For **Claude Code**, Gandalf uses the standard MCP configuration format. The installer automatically detects Claude Code and configures the appropriate settings.

**Configuration Locations** (automatically handled):

- `~/.config/claude/mcp_settings.json`
- `~/.claude/mcp_settings.json`
- `~/.claude/mcp.json`

**Manual Claude Code Setup** (if needed):

```bash
# Add Gandalf MCP server with global scope (from the gandalf directory)
cd /path/to/gandalf
claude mcp add gandalf python3 -s user src/main.py -e PYTHONPATH=/path/to/gandalf -e CLAUDECODE=1 -e CLAUDE_CODE_ENTRYPOINT=cli

# INCORRECT: This will fail with "unknown option '-m'"
# claude mcp add gandalf python3 -m src.main --cwd /path/to/gandalf --env PYTHONPATH=/path/to/gandalf --env CLAUDECODE=1

# Alternative: Add from JSON configuration with global scope
claude mcp add-json gandalf '{
  "type": "stdio",
  "command": "python3",
  "args": ["src/main.py"],
  "cwd": "/path/to/gandalf",
  "env": {
    "PYTHONPATH": "/path/to/gandalf",
    "CLAUDECODE": "1",
    "CLAUDE_CODE_ENTRYPOINT": "cli"
  }
}' -s user

# Verify installation
claude mcp list
claude mcp get gandalf
```

**IMPORTANT**: Use `-s user` for global access across all projects (recommended) or `-s local` for project-specific access.

### Cursor IDE Installation

For **Cursor IDE**, Gandalf configures the traditional MCP setup using the shell wrapper.

**Configuration**: `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/path/to/gandalf/gandalf.sh",
      "args": ["run"]
    }
  }
}
```

## Installation Options

### Standard Installation

```bash
# Install to current repository
./gandalf.sh install

# Install to specific repository
./gandalf.sh install /path/to/project
```

### Advanced Options

```bash
# Force overwrite existing configuration
./gandalf.sh install -f

# Reset existing server and install fresh
./gandalf.sh install -r

# Force specific IDE (bypass auto-detection)
./gandalf.sh install --ide cursor
./gandalf.sh install --ide claude-code

# Skip connectivity testing (faster)
./gandalf.sh install --skip-test
```

## Verification

### Test Installation

```bash
# Run comprehensive test suite
./gandalf.sh test

# Quick validation workflow
./gandalf.sh lembas
```

### Verify in IDE

**In your IDE, test these commands:**

```
What files are in my project?
```

```
Get project information and statistics
```

### Check MCP Status

**Claude Code:**

```bash
# Check server status
claude mcp list

# View server details
claude mcp get gandalf

# Use /mcp command in Claude Code for interactive status
```

**Cursor IDE:**

- View → Output → MCP Logs (set to DEBUG level)
- Look for "gandalf" server startup messages

## Troubleshooting

### Installation Fails

```bash
# Check all dependencies
./gandalf.sh deps --verbose

# Reset and reinstall
./gandalf.sh install -r

# Manual dependency check
python3 --version  # Should be 3.10+
git --version
```

### Server Not Recognized

**Claude Code:**

```bash
# Restart Claude Code completely
# Check configuration
claude mcp get gandalf

# Re-add if needed
claude mcp remove gandalf
./gandalf.sh install --ide claude-code
```

**Cursor IDE:**

```bash
# Restart Cursor completely
# Check MCP logs for errors
# Reset if needed
./gandalf.sh install -r
```

### Tools Not Working

```bash
# Verify server is running
./gandalf.sh test

# Check for errors
./gandalf.sh deps --verbose

# Full reset
./gandalf.sh install -r
```

### Gandalf Not Available in Different Directories

**Problem**: Gandalf MCP tools don't work when you're in a different directory (e.g., `/Users/user/other-project`)

**Cause**: Gandalf is configured with local scope (project-specific) instead of user scope (global)

**Solutions**:

1. **Convert to Global Configuration** (recommended):

```bash
# From the gandalf directory
cd /path/to/gandalf
claude mcp remove gandalf -s local  # Remove local config
claude mcp add gandalf python3 -s user src/main.py -e PYTHONPATH=/path/to/gandalf -e CLAUDECODE=1 -e CLAUDE_CODE_ENTRYPOINT=cli
```

2. **Use absolute paths in configuration**:

```bash
claude mcp add-json gandalf '{
  "type": "stdio",
  "command": "python3",
  "args": ["/absolute/path/to/gandalf/src/main.py"],
  "cwd": "/absolute/path/to/gandalf",
  "env": {
    "PYTHONPATH": "/absolute/path/to/gandalf",
    "CLAUDECODE": "1",
    "CLAUDE_CODE_ENTRYPOINT": "cli"
  }
}' -s user
```

3. **Check current configuration scope**:

```bash
claude mcp get gandalf  # Shows if it's local/user/project scoped
```

**Note**: Use `-s user` for global access or `-s local` for project-specific access.

## Environment Variables

Optional environment variables for customization:

```bash
# Override IDE detection
export GANDALF_FALLBACK_IDE="claude-code"  # or "cursor"

# Enable debug logging
export MCP_DEBUG="true"

# Custom server name
export MCP_SERVER_NAME="gandalf"

# Claude Code specific
export CLAUDECODE="1"
export CLAUDE_CODE_ENTRYPOINT="cli"
```

## Global Access

Add Gandalf to your PATH for global access:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
export PATH="/path/to/gandalf:$PATH"

# Then use globally
gdlf install
gdlf test
gdlf lembas
```

## Next Steps

After successful installation:

1. **Restart your IDE completely**
2. **Test basic functionality**: "What files are in my project?"
3. **Review documentation**: [API.md](API.md) for available tools
4. **Check troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

## Support

- **Logs**: Check MCP logs in your IDE for detailed error information
- **Reset**: Use `./gandalf.sh install -r` for clean reinstall
- **Test**: Run `./gandalf.sh lembas` for comprehensive validation
