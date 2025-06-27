# Troubleshooting Guide

Quick solutions for common Gandalf MCP server issues in **Cursor IDE** and **Claude Code**.

## Quick Fixes

### Hard Reset

```bash
./gandalf.sh install -r
# Restart your IDE completely
```

### Basic Diagnostics

1. **Check MCP Status**:

   - **Claude Code**: Use `/mcp` command or `claude mcp list`
   - **Cursor IDE**: View → Output → MCP Logs (set to DEBUG level)

2. **Test Components**: `./gandalf.sh test`
3. **Check Dependencies**: `./gandalf.sh deps --verbose`

## Common Issues

### Gandalf Not Available in Different Directories

**Problem**: Gandalf MCP tools don't work when you're in a different project directory

**Symptoms**:

- Gandalf tools work in the original project but not elsewhere
- "No MCP servers configured" when using `claude mcp list` from different directories
- Tools show as unavailable in Claude Code when working in other projects

**Cause**: Gandalf is configured with local scope (project-specific) instead of user scope (global)

**Solutions**:

1. **Convert to Global Configuration** (recommended):

```bash
# From the gandalf directory
cd /path/to/gandalf
claude mcp remove gandalf -s local  # Remove local config
claude mcp add gandalf python3 -s user src/main.py -e PYTHONPATH=/path/to/gandalf -e CLAUDECODE=1 -e CLAUDE_CODE_ENTRYPOINT=cli
```

2. **Check Current Configuration Scope**:

```bash
claude mcp get gandalf  # Look for "Scope: Local" vs "Scope: User"
```

3. **Use Absolute Paths for Global Access**:

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

**Note**: Use `-s user` for global access across all projects, or `-s local` for project-specific access.

### MCP Server Not Recognized

**Problem**: IDE doesn't recognize Gandalf MCP server

**Claude Code Solutions**:

```bash
# Check server status
claude mcp list

# Verify server configuration
claude mcp get gandalf

# Re-add server if missing
claude mcp remove gandalf
./gandalf.sh install --ide claude-code

# Restart Claude Code completely
```

**Cursor IDE Solutions**:

```bash
# Check configuration file
cat ~/.cursor/mcp.json

# Reset and reinstall
./gandalf.sh install -r

# Restart Cursor completely
```

### Tools Not Working

**Problem**: MCP tools unavailable or not responding

**Claude Code Solutions**:

```bash
# Check authentication status
/mcp  # In Claude Code interface

# Verify server is running
claude mcp get gandalf

# Test basic functionality
# Ask: "What files are in my project?"

# Reset if needed
./gandalf.sh install -r
```

**Cursor IDE Solutions**:

```bash
# Check MCP logs for errors
# View → Output → MCP Logs (DEBUG level)

# Verify server process
ps aux | grep gandalf

# Test connectivity
./gandalf.sh test

# Reset if failing
./gandalf.sh install -r
```

### Can't See Tool Activity

**Problem**: Only see connection messages, not tool execution details

**Claude Code Solutions**:

- Use `/mcp` command to check server status
- Look for MCP-related output in Claude Code interface
- Check server logs if available

**Cursor IDE Solutions**:

- Go to View → Output → MCP Logs
- Set level to DEBUG (not ERROR)
- Click cogwheel → "Set as Default"

### Configuration Changes Not Working

**Problem**: Rules or settings changes ignored

**Solution**:

```bash
./gandalf.sh install -r
# Restart your IDE completely
```

## Installation Issues

### IDE Detection Problems

**Problem**: Gandalf detects wrong IDE or fails to detect

**Solutions**:

```bash
# Force specific IDE
./gandalf.sh install --ide claude-code
./gandalf.sh install --ide cursor

# Check environment variables
echo $CLAUDECODE
echo $CLAUDE_CODE_ENTRYPOINT
echo $CURSOR_TRACE_ID

# Set fallback IDE
export GANDALF_FALLBACK_IDE="claude-code"
./gandalf.sh install
```

### Python Problems

```bash
python3 --version  # Should be 3.10+

# macOS
brew install python@3.10

# Ubuntu/Debian
sudo apt install python3.10 python3.10-pip

# CentOS/RHEL/Fedora
sudo dnf install python3.10 python3.10-pip
```

### Missing Dependencies

```bash
./gandalf.sh deps --verbose

# macOS
brew install bats-core jq

# Ubuntu/Debian
sudo apt install bats jq

# CentOS/RHEL/Fedora
sudo dnf install jq
```

### Permission Issues

```bash
chmod +x gandalf.sh
chmod +x scripts/*
chmod +x src/main.py
```

### Not a Git Repository

```bash
git init
git add .
git commit -m "Initial commit"

# Or install to specific path
./gandalf.sh install /path/to/project
```

## Claude Code Specific Issues

### Session Data Not Found

**Problem**: Conversation tools return empty results

**Solutions**:

```bash
# Check Claude Code data directories
ls -la ~/.claude/
ls -la ~/.config/claude/

# Verify session files exist
find ~/.claude -name "*.jsonl" -type f

# Check environment variables
echo $CLAUDE_HOME
echo $CLAUDE_WORKSPACE

# Force Claude Code mode
export CLAUDECODE=1
export CLAUDE_CODE_ENTRYPOINT=cli
./gandalf.sh install --ide claude-code
```

### MCP Configuration Issues

**Problem**: Claude Code doesn't recognize MCP server

**Solutions**:

```bash
# Check MCP configuration
claude mcp list

# Verify server configuration
claude mcp get gandalf

# Remove and re-add server
claude mcp remove gandalf
claude mcp add gandalf python3 -m src.main \
  --cwd /path/to/gandalf \
  --env PYTHONPATH=/path/to/gandalf \
  --env CLAUDECODE=1

# Restart Claude Code
```

### Authentication Issues

**Problem**: MCP server requires authentication

**Solutions**:

```bash
# Use interactive authentication
/mcp  # In Claude Code interface

# Check authentication status
claude mcp get gandalf

# Clear and re-authenticate if needed
# Use /mcp command to manage authentication
```

## Cursor IDE Specific Issues

### Workspace Detection Problems

**Problem**: Cursor workspace not detected properly

**Solutions**:

```bash
# Check Cursor data directories
ls -la ~/Library/Application\ Support/Cursor/

# Verify workspace databases
find ~/Library/Application\ Support/Cursor/workspaceStorage -name "*.vscdb"

# Reset workspace detection
./gandalf.sh install -r
```

### Database Access Issues

**Problem**: Cannot access Cursor conversation database

**Solutions**:

```bash
# Check database permissions
ls -la ~/Library/Application\ Support/Cursor/workspaceStorage/

# Verify Cursor is not running (for database access)
ps aux | grep Cursor

# Reset database connections
./gandalf.sh install -r
```

## Performance Issues

### Slow Startup

```bash
# Faster installation
./gandalf.sh install --skip-test

# Optimize Git
git gc --aggressive

# Check for large files
find . -size +10M -type f
```

### High Memory Usage

- Reduce `max_files` in tool calls
- Clear cache: `./gandalf.sh install -r`
- Check for large binary files
- Limit conversation recall with smaller `days_lookback`

### Cache Problems

```bash
./gandalf.sh install -r
# Restart your IDE
# Let cache rebuild
```

## Testing Issues

### Test Failures

```bash
# Check dependencies first
./gandalf.sh deps

# Run tests individually
./gandalf.sh test --shell
./gandalf.sh test --python

# Verbose output
./gandalf.sh test --verbose

# Full validation
./gandalf.sh lembas
```

### BATS Not Found

```bash
# macOS
brew install bats-core

# Ubuntu/Debian
sudo apt install bats

# Manual installation
git clone https://github.com/bats-core/bats-core.git
cd bats-core
sudo ./install.sh /usr/local
```

## Environment Variables

### Debugging Variables

```bash
# Enable debug logging
export MCP_DEBUG=true

# Set specific IDE
export GANDALF_FALLBACK_IDE="claude-code"

# Claude Code specific
export CLAUDECODE=1
export CLAUDE_CODE_ENTRYPOINT=cli

# Custom server name
export MCP_SERVER_NAME=gandalf
```

### Path Variables

```bash
# Custom Python path
export PYTHONPATH="/path/to/gandalf:$PYTHONPATH"

# Custom Claude home
export CLAUDE_HOME="$HOME/.claude"
```

## When to Get Help

If issues persist after trying these solutions:

1. **Run full diagnostics**: `./gandalf.sh lembas`
2. **Collect logs**:
   - **Claude Code**: Use `/mcp` command output
   - **Cursor IDE**: MCP Logs (DEBUG level)
3. **Document environment**: OS, Python version, IDE version
4. **Provide reproduction steps**: Exact commands and error messages

## Known Issues

### IDE-Specific Limitations

- **Claude Code**: Session data location varies by installation
- **Cursor IDE**: Database access requires Cursor to be closed
- **Remote Development**: Limited conversation access in remote environments

### General Issues

- Opening `.mdc` files slows down Cursor (known bug)
- Agent behavior sensitive to rules in `gandalf-rules.md`
- Context loss after hitting `stop` (use `./gandalf.sh install -r`)
- Agent changes behavior if rules modified (restart server)

### Workarounds

- Use `./gandalf.sh lembas` for comprehensive validation
- Keep IDE-specific logs for debugging
- Test with minimal configuration first, then add complexity
- Use `--skip-test` flag for faster installation during development
