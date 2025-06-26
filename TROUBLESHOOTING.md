# Troubleshooting Guide

Quick solutions for common Gandalf MCP server issues.

## Quick Fixes

### Hard Reset

```bash
./gandalf.sh install -r
# Restart Cursor completely
```

### Basic Diagnostics

1. **MCP Logs**: View → Output → MCP Logs (set to DEBUG level)
2. **Test Components**: `./gandalf.sh test`
3. **Check Dependencies**: `./gandalf.sh deps --verbose`

## Common Issues

### Can't See Tool Activity in Cursor

**Problem**: Only see connection messages, not tool execution details

**Solution**:

- Go to View → Output → MCP Logs
- Set level to DEBUG (not ERROR)
- Click cogwheel → "Set as Default"

### Configuration Changes Not Working

**Problem**: Rules or settings changes ignored

**Solution**:

```bash
./gandalf.sh install -r
# Restart Cursor completely
```

### MCP Server Not Starting

**Problem**: Server not recognized in Cursor

**Quick Fix**:

```bash
./gandalf.sh install -r
sleep 5
# Restart Cursor
```

**Check**:

- `~/.cursor/mcp.json` exists
- MCP Logs show server startup
- `ps aux | grep gandalf`

### Tools Not Working

**Problem**: MCP tools unavailable or not responding

**Solution**:

1. Restart Cursor completely
2. Wait 30 seconds
3. Try: "What files are in my project?"
4. If still failing: `./gandalf.sh install -r`

## Installation Issues

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

## Performance Issues

### Slow Startup

```bash
# Faster installation
./gandalf.sh install --skip-test

# Optimize Git
git gc --aggressive
```

### High Memory Usage

- Reduce `max_files` in tool calls
- Clear cache: `./gandalf.sh install -r`
- Check for large binary files

### Cache Problems

```bash
./gandalf.sh install -r
# Restart Cursor
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

## When to Get Help

If issues persist after trying these solutions:

1. Run: `./gandalf.sh lembas`
2. Collect MCP Logs (DEBUG level)
3. Note: OS, Python version, Cursor version
4. Document exact reproduction steps

## Known Issues

- Opening `.mdc` files slows down Cursor (known bug)
- Agent behavior sensitive to rules in `rules.md`
- Context loss after hitting `stop` (use `./gandalf.sh install -r`)
- Agent changes behavior if rules modified (restart server)
