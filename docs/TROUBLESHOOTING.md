# Troubleshooting Guide

Quick solutions for common Gandalf MCP Server issues.

## Quick Diagnosis

```bash
# Test server functionality
./gandalf test

# Full validation
./gandalf lembas --all

# Check installation status
cat ~/.gandalf/installation-state
```

## Common Issues

### Tools Not Appearing in IDE

Symptoms: Development tool doesn't show Gandalf tools or capabilities

Solutions:

1. Restart IDE completely: Exit fully (Cmd/Ctrl + Q), wait 5 seconds, reopen
2. Reset configuration: `./gandalf install --force`
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
   ./gandalf run --help
   ```

### Empty or No Conversation Results

Symptoms: Can't recall conversations or get empty results

Solutions:

1. Check database permissions:

   ```bash
   # Check access to IDE databases
   ls -la "$HOME/Library/Application Support/Cursor"
   ls -la ~/.claude
   ```

2. Restart development tool to reinitialize database connections

3. Use broader search parameters:
   ```bash
   recall_conversations(min_score=0.5, days_lookback=60)
   ```

### No Cursor Conversations Found

Symptoms: `recall_conversations()` returns 0 cursor conversations despite having used Cursor

Solutions:

1. Check Cursor database location:

   ```bash
   # macOS
   ls -la "$HOME/Library/Application Support/Cursor"

   # Linux
   ls -la "$HOME/.config/Cursor"
   ```

2. Verify Cursor workspace database exists:

   ```bash
   find "$HOME/Library/Application Support/Cursor" -name "*.vscdb" 2>/dev/null
   ```

3. Restart Cursor to ensure database is properly closed and accessible

4. Check if conversations exist in current workspace:
   ```bash
   # Should show recent conversation data
   get_project_info()
   ```

### Command Execution Failures

Symptoms: `./gandalf test` or `./gandalf lembas` commands fail or hang

Solutions:

1. Check execute permissions:

   ```bash
   chmod +x gandalf
   ls -la gandalf
   ```

2. Run with explicit shell:

   ```bash
   bash ./gandalf test
   ```

3. Check for background processes:

   ```bash
   # Kill any hanging gandalf processes
   pkill -f gandalf
   ```

4. Clear test cache:
   ```bash
   rm -rf ~/.gandalf/cache/test-*
   ```

### Validation Test Failures

Symptoms: `./gandalf lembas --all` reports test failures

Solutions:

1. Run specific test suites to isolate issues:

   ```bash
   # Python tests only
   cd gandalf/server && pytest

   # Shell tests only
   cd gandalf/tools/tests && bash shell-tests-manager.sh
   ```

2. Check for missing dependencies:

   ```bash
   cd gandalf/server
   pip install -r requirements.txt
   ```

3. Verify all required tools are installed:
   ```bash
   which python3 shellcheck bats
   ```

### Slow Performance

Symptoms: Tools take a long time to respond

Solutions:

1. Enable fast mode: `recall_conversations(fast_mode=true)`
2. Limit scope: `list_project_files(file_types=[".py"], max_files=50)`
3. Reduce lookback: `recall_conversations(days_lookback=7, limit=10)`
4. Clear cache: `rm -rf ~/.gandalf/cache/*`

## IDE-Specific Issues

### Cursor IDE

Configuration problems:

```bash
# Check configuration
cat ~/.cursor/mcp.json

# Reset configuration
./gandalf install --force
```

Common MCP log errors:

- "Command not found": Check absolute paths in configuration
- "Permission denied": `chmod +x gandalf`
- "Module not found": `pip install -r gandalf/server/requirements.txt`

Database access issues:

```bash
# Check if Cursor is running (may lock database)
ps aux | grep -i cursor

# Verify database permissions
ls -la "$HOME/Library/Application Support/Cursor/workspaceStorage"
```

### Claude Code

Connection problems:

```bash
# Check MCP server status
claude mcp list

# Reset configuration
./gandalf install --force
```

### Windsurf

Empty conversations: Normal behavior due to flow-based architecture

Configuration issues:

```bash
# Check configuration
cat ~/.windsurf/mcp.json

# Reset configuration
./gandalf install --force
```

## Installation Problems

### Permission Errors

```bash
# Fix file permissions
chmod +x gandalf

# Fix directory permissions
sudo chown -R $(whoami) ~/.gandalf
```

### Python Dependencies

```bash
# Check Python version
python3 --version

# Install dependencies
cd gandalf/server
pip install -r requirements.txt

# Test dependencies
python3 -c "import yaml, sqlite3, json, pathlib; print('Dependencies OK')"
```

## Advanced Debugging

### Enable Debug Logging

Add to MCP configuration:

```json
{
  "mcpServers": {
    "gandalf": {
      "env": {
        "GANDALF_DEBUG": "true",
        "PYTHONPATH": "/absolute/path/to/gandalf/server"
      }
    }
  }
}
```

### Test Server Manually

```bash
# Test server startup
cd gandalf
echo '{"method": "tools/list"}' | ./gandalf run

# Test specific tool
echo '{"method": "tools/call", "params": {"name": "get_server_version", "arguments": {}}}' | ./gandalf run
```

### Reset Everything

```bash
# Complete reset
./gandalf uninstall --force
./gandalf install --force

# Clear all cache
rm -rf ~/.gandalf/cache/*
```

## Performance Optimization

### Memory Usage

```bash
# Limit conversations
recall_conversations(limit=10, days_lookback=7)

# Filter file types
list_project_files(file_types=[".py"], max_files=50)
```

### Response Time

```bash
# Enable fast mode
recall_conversations(fast_mode=true)

# Use specific filters
recall_conversations(tools=["cursor"], conversation_types=["debugging"])
```

## Getting Help

If issues persist:

1. Run diagnostics: `./gandalf lembas --all`
2. Check IDE MCP logs for specific error messages
3. Create GitHub issue with:
   - Operating system and version
   - Python version (`python3 --version`)
   - IDE name and version
   - Error messages from logs
   - Output of `./gandalf test`
   - MCP configuration (remove sensitive paths)

Documentation: [README](../README.md) | [Installation](INSTALLATION.md) | [API](API.md)

Support: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
