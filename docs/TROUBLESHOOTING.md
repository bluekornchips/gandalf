# Troubleshooting Guide

Quick solutions for common Gandalf MCP Server issues.

## Quick Diagnosis

```bash
./gandalf test
./gandalf lembas --all
cat ~/.gandalf/installation-state
```

## Common Issues

### Tools Not Appearing in IDE

**Solutions:**

1. Restart IDE completely (Cmd/Ctrl + Q)
2. `./gandalf install --force`
3. Check MCP logs:
   - Cursor: View > Output > MCP Logs
   - Claude Code: Check terminal output
   - Windsurf: View > Output > MCP Logs

### Empty Conversation Results

**Solutions:**

1. **Registry Auto-Initialization (Automatic)** - System self-repairs on startup
2. **Manual Registry Setup:**
   ```bash
   ./gandalf registry auto-register
   ./gandalf registry list
   ```
3. **Check Registry Status:**
   ```bash
   cat ~/.gandalf/registry.json
   ```

### Server Not Responding

**Solutions:**

1. Check dependencies:
   ```bash
   cd gandalf/server && pip install -e .
   ```
2. Verify Python version:
   ```bash
   python3 --version  # Should be 3.12+
   ```
3. Registry issues:
   ```bash
   rm ~/.gandalf/registry.json
   ./gandalf registry auto-register
   ```

### No Cursor Conversations Found

**Solutions:**

1. Check database location:
   ```bash
   ls -la "$HOME/Library/Application Support/Cursor"
   ```
2. Verify workspace database:
   ```bash
   find "$HOME/Library/Application Support/Cursor" -name "*.vscdb"
   ```
3. Restart Cursor
4. Check project info: `get_project_info()`

### Command Execution Failures

**Solutions:**

1. Fix permissions: `chmod +x gandalf`
2. Kill hanging processes: `pkill -f gandalf`
3. Clear cache: `rm -rf ~/.gandalf/cache/*`

### Slow Response Times

**Solutions:**

1. `recall_conversations(fast_mode=true)`
2. `list_project_files(file_types=[".py"], max_files=50)`
3. `recall_conversations(days_lookback=7, limit=10)`
4. `rm -rf ~/.gandalf/cache/*`

## IDE-Specific Issues

### Cursor IDE

```bash
cat ~/.cursor/mcp.json
./gandalf install --force
ps aux | grep -i cursor
```

### Claude Code

```bash
claude mcp list
./gandalf install --force
```

### Windsurf

```bash
cat ~/.windsurf/mcp.json
./gandalf install --force
```

## Reset Everything

```bash
./gandalf uninstall --force
./gandalf install --force
rm -rf ~/.gandalf/cache/*
```

## Getting Help

Run diagnostics: `./gandalf lembas --all`

Create GitHub issue with:

- OS and Python version
- IDE name and version
- Error messages
- Output of `./gandalf test`
- MCP configuration (remove sensitive paths)

[GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
