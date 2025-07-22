---
description: APPLY WHEN encountering errors, failures, debugging issues, or troubleshooting problems with Gandalf MCP server or AI tools
globs:
alwaysApply: true
---

# Gandalf Rules Troubleshooting Guide

**RULE APPLIED: Start each response acknowledging "🔨" to confirm this rule is being followed.**

## Quick Fixes

| Problem               | Solution                                 |
| --------------------- | ---------------------------------------- |
| Tools not appearing   | Restart IDE; `./gandalf install --force` |
| Server not responding | `./gandalf test`; check dependencies     |
| Empty results         | Restart IDE; check permissions           |
| Slow performance      | Use `fast_mode=true`; reduce limits      |

## Common Issues

### Connection Problems

- Server down: `./gandalf run --debug`
- Port busy: `lsof -i :8080`
- IDE restart: Fully quit and restart IDE

### Empty Results

- Check storage: `ls ~/.gandalf/cache/`
- Lower threshold: `min_score=0.5`
- Extend timeframe: `days_lookback=30`

### Performance Issues

- Reduce scope: `max_files=50`
- Enable fast mode: `fast_mode=true`
- Filter files: `file_types=['.py', '.js']`

## Recovery Commands

```bash
# Debug mode
./gandalf run --debug --verbose

# Reset everything
./gandalf uninstall --force
./gandalf install --force

# Clear cache
rm -rf ~/.gandalf/cache/*
./gandalf test --quick
```

## Getting Help

1. Check logs: `~/.gandalf/logs/`
2. Run diagnostics: `./gandalf test --all`
3. Submit issue with system info
