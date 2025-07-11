# Troubleshooting Guide

Quick solutions for common Gandalf MCP Server issues.

## Quick Diagnosis

```bash
# Check system dependencies
./gandalf.sh deps

# Test server functionality
./gandalf.sh test

# Full validation
./gandalf.sh lembas

# Check installation status
cat ~/.gandalf/installation-state
```

## Common Issues

### Tools Not Appearing in IDE

Symptoms: Development tool doesn't show Gandalf tools or capabilities

Solutions:

1. Restart IDE completely: Exit fully (Cmd/Ctrl + Q), wait 5 seconds, reopen
2. Reset configuration: `./gandalf.sh install --force`
3. Check MCP logs:
   - Cursor: View > Output > MCP Logs
   - Claude Code: Check terminal output
   - Windsurf: View > Output > MCP Logs

### Server Not Responding

Symptoms: Error messages about server connectivity or timeouts

Solutions:

1. Check dependencies:

   ```bash
   cd gandalf/server
   pip install -r requirements.txt
   ```

2. Verify Python version:

   ```bash
   python3 --version  # Should be 3.10+
   ```

3. Test server directly:
   ```bash
   ./gandalf.sh run --help
   ```

### Empty Conversation Results

Symptoms: Can't recall conversations or get empty results

Solutions:

1. Check database permissions:

   ```bash
   # Cursor
   ls -la "$HOME/Library/Application Support/Cursor"

   # Claude Code
   ls -la ~/.claude

   # Windsurf (normal behavior due to flow-based architecture)
   ls -la ~/.windsurf
   ```

2. Restart development tool to reinitialize database connections

### Slow Performance

Symptoms: Tools take a long time to respond

Solutions:

1. Enable fast mode: `recall_conversations(fast_mode=true)`
2. Limit scope: `list_project_files(max_files=50, file_types=[".py"])`
3. Reduce lookback: `recall_conversations(days_lookback=7, limit=10)`

## Tool-Specific Issues

### Cursor Issues

Configuration problems:

```bash
# Check configuration
cat ~/.cursor/mcp.json
jq . ~/.cursor/mcp.json

# Reset configuration
./gandalf.sh install --tool cursor --force
```

Common MCP log errors:

- "Command not found": Check absolute paths in configuration
- "Permission denied": `chmod +x gandalf.sh`
- "Module not found": `pip install -r requirements.txt`

### Claude Code Issues

Connection problems:

```bash
# Check MCP server status
claude mcp list
claude mcp get gandalf

# Reset configuration
./gandalf.sh install --tool claude-code --force
```

### Windsurf Issues

Empty conversations: Expected behavior due to flow-based Cascade architecture

Configuration issues:

```bash
# Check configuration
cat ~/.windsurf/mcp.json
jq . ~/.windsurf/mcp.json

# Reset configuration
./gandalf.sh install --tool windsurf --force
```

## Performance Optimization

### Memory Usage

Reduce memory consumption:

```bash
# Limit conversations
recall_conversations(days_lookback=7, limit=10)

# Filter file types
list_project_files(file_types=[".py"], max_files=100)

# Clear cache
rm -rf ~/.gandalf/cache/*
```

### Response Time

Improve performance:

```bash
# Enable fast mode
recall_conversations(fast_mode=true)

# Limit file analysis
list_project_files(max_files=50, file_types=[".py", ".js"])
```

## Installation Problems

### Permission Errors

```bash
# Fix permissions
chmod +x gandalf.sh
sudo chown -R $(whoami) ~/.gandalf
```

### MCP Configuration Issues

```bash
# Check development tool logs
# Restart completely (don't just reload)
```

## Advanced Debugging

### Enable Debug Logging

Add to MCP configuration:

```json
{
  "gandalf": {
    "env": {
      "GANDALF_DEBUG": "true"
    }
  }
}
```

### Test Server Manually

```bash
# Test basic functionality
cd gandalf
echo '{"method": "tools/list"}' | ./gandalf.sh run

# Test specific tool
echo '{"method": "tools/call", "params": {"name": "get_server_version", "arguments": {}}}' | ./gandalf.sh run
```

### Check Dependencies

```bash
cd gandalf/server
python3 -c "
import sys
try:
    import yaml, sqlite3, json, pathlib
    print('All dependencies available')
except ImportError as e:
    print(f'Missing dependency: {e}')
"
```

## Getting Help

If issues persist:

1. Run diagnostics: `./gandalf.sh lembas`
2. Check IDE MCP logs
3. Create issue with:
   - Operating system
   - Python version (`python3 --version`)
   - IDE and version
   - Error messages from logs
   - Output of `./gandalf.sh test`
   - MCP configuration (sanitized)

Documentation: [README](README.md) | [Installation](INSTALLATION.md) | [API](API.md)
Support: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
