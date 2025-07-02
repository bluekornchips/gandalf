# Troubleshooting Guide

Comprehensive troubleshooting guide for Gandalf, a conversation aggregator and MCP Server, with support for Cursor IDE, Claude Code, and Windsurf.

## Quick Diagnosis

Run these commands to quickly identify issues:

```bash
# Check system dependencies
./gandalf.sh deps

# Test server functionality
./gandalf.sh test

# Full validation workflow
./gandalf.sh lembas

# Check installation status
cat ~/.gandalf/installation-state
```

## Common Issues

### 1. MCP Tools Not Appearing

**Symptoms**: Development tool doesn't show Gandalf tools or capabilities

**Diagnosis**:

```bash
# Check if server is configured
./gandalf.sh test

# Verify MCP configuration
cat ~/.cursor/mcp.json    # For Cursor
cat ~/.claude/mcp.json    # For Claude Code
cat ~/.windsurf/mcp.json  # For Windsurf
```

**Problem**:

1. **Restart development tool completely**:

   - Exit completely (⌘/Ctrl + Q)
   - Wait 5 seconds
   - Reopen development tool

2. **Verify configuration**:

   ```bash
   # Reset and reinstall
   ./gandalf.sh install -r
   ```

3. **Check MCP logs** (tool specific):
   - **Cursor**: View > Output > MCP Logs
   - **Claude Code**: Check terminal output or logs
   - **Windsurf**: View > Output > MCP Logs

### 2. "Server Not Responding" Errors

**Symptoms**: Error messages about server connectivity or timeouts

**Diagnosis**:

```bash
# Test server directly
cd gandalf
./gandalf.sh run --help

# Check Python dependencies
python3 -c "import yaml; print('Dependencies OK')"
```

**Problem**:

1. **Install missing dependencies**:

   ```bash
   cd gandalf/server
   pip install -r requirements.txt
   ```

2. **Check Python version**:

   ```bash
   python3 --version  # Should be 3.10+
   ```

3. **Verify permissions**:
   ```bash
   ls -la gandalf/server/src/main.py
   chmod +x gandalf/server/src/main.py
   ```

### 3. Conversation History Not Available

**Symptoms**: Can't recall conversations or get empty results

**Diagnosis**:

```bash
# Test conversation tools
./gandalf.sh test
```

**Problem**:

1. **Check conversation database permissions**:

   ```bash
   # For Cursor
   ls -la "$HOME/Library/Application Support/Cursor"

   # For Claude Code
   ls -la ~/.claude
   ls -la ~/.config/claude

   # For Windsurf
   ls -la ~/.windsurf
   ```

2. Restart development tool to reinitialize database connections

**Note**: Windsurf conversations may appear empty by design due to its flow-based Cascade AI architecture. This is normal behavior.

### 4. Import Errors

**Symptoms**: Python import errors when starting server

**Diagnosis**:

```bash
cd gandalf
./gandalf.sh run --help
```

**Problem**:

1. **Install server dependencies**:

   ```bash
   cd gandalf/server
   pip install -r requirements.txt
   ```

2. **Check PYTHONPATH**:

   ```bash
   cd gandalf
   ./gandalf.sh run --help
   ```

3. **Use virtual environment**:
   ```bash
   python3 -m venv ~/.gandalf/venv
   source ~/.gandalf/venv/bin/activate
   pip install -r requirements.txt
   ```

## Tool-Specific Issues

### Cursor Issues

#### Cursor Can't Find MCP Configuration

**Symptoms**: Cursor doesn't load Gandalf tools

**Check**:

```bash
# Verify configuration file exists and is valid
cat ~/.cursor/mcp.json
jq . ~/.cursor/mcp.json  # Should validate JSON
```

**Fix**:

```bash
# Reset Cursor configuration
./gandalf.sh install --tool cursor -r
```

#### Cursor MCP Logs Show Errors

**Check logs**: View > Output > MCP Logs (set to DEBUG level)

**Common errors**:

- "Command not found": Check absolute paths in configuration
- "Permission denied": Check file permissions with `chmod +x`
- "Module not found": Install dependencies with `pip install -r requirements.txt`

### Claude Code Issues

#### Claude Code Can't Connect to MCP

**Symptoms**: `/mcp` command shows no servers or connection errors

**Check**:

```bash
# Verify Claude Code MCP configuration
claude mcp list
claude mcp get gandalf
```

**Fix**:

```bash
# Reset Claude Code configuration
./gandalf.sh install --tool claude-code -r
```

#### Claude Code MCP Commands Fail

**Check status**:

```bash
# Check MCP server status
claude mcp status gandalf

# Test server directly
cd gandalf
./gandalf.sh run --help
```

### Windsurf Issues

#### Windsurf Shows Empty Conversations

**Symptoms**: Windsurf conversations appear empty in Gandalf results

**This is expected behavior**: Windsurf uses Cascade AI with flow-based interactions rather than traditional chat conversations.

**For Windsurf context, check instead**:

```bash
# Check Cascade Memories and Rules
ls -la ~/.windsurf
ls -la .windsurfrules
ls -la .windsurf/workflows/
```

#### Windsurf Can't Find MCP Configuration

**Symptoms**: Windsurf doesn't load Gandalf tools

**Check**:

```bash
# Verify configuration file exists and is valid
cat ~/.windsurf/mcp.json
jq . ~/.windsurf/mcp.json  # Should validate JSON
```

**Fix**:

```bash
# Reset Windsurf configuration
./gandalf.sh install --tool windsurf -r
```

## Performance Issues

### Slow Response Times

**Symptoms**: Tools take a long time to respond

**Problem**:

1. **Enable fast mode**:

   ```bash
   # Use fast_mode=true for recall_conversations
   recall_conversations(fast_mode=true)
   ```

2. **Limit file analysis**:

   ```bash
   # Reduce max_files for large projects
   list_project_files(max_files=50, file_types=["py", "js"])
   ```

3. **Tune cache settings**:
   ```bash
   # Add to MCP configuration
   "env": {
     "GANDALF_CACHE_TTL": "600",
     "GANDALF_MAX_FILES": "500"
   }
   ```

### High Memory Usage

**Symptoms**: System becomes slow when using Gandalf

**Problem**:

1. **Reduce conversation lookback**:

   ```bash
   recall_conversations(days_lookback=7, limit=10)
   ```

2. **Use specific file types**:

   ```bash
   list_project_files(file_types=["py"], max_files=100)
   ```

3. **Clear cache**:
   ```bash
   rm -rf ~/.gandalf/cache/*
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
# Cursor: View > Output > MCP Logs
# Claude Code: Check ~/.claude/logs/
# Windsurf: View > Output > MCP Logs

# Restart completely
# Don't just reload - fully quit and restart your development tool
```

## Advanced Debugging

### Enable Debug Logging

Add to your MCP configuration:

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
# Verify all dependencies are installed
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

If you're still having issues:

1. **Run full diagnostics**:

   ```bash
   ./gandalf.sh lembas
   ```

2. **Check the logs** in your IDE's MCP output, if available

3. **Create an issue** with:

   - Your operating system
   - Python version (`python3 --version`)
   - IDE and version
   - Error messages from logs
   - Output of `./gandalf.sh test`

4. **Include your configuration** (remove sensitive paths):
   ```bash
   # Sanitize and include your MCP config
   cat ~/.cursor/mcp.json | jq 'del(.mcpServers.gandalf.cwd)'
   ```
