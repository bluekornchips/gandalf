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
./gandalf run --debug

# Reset everything
./gandalf uninstall --force
./gandalf install --force

# Clear cache
rm -rf ~/.gandalf/cache/*
./gandalf test
```

## Advanced Troubleshooting

### Diagnostic Commands

```bash
# Full system check
./gandalf lembas --all

# Basic connectivity
./gandalf test

# Cache inspection
ls -la ~/.gandalf/cache/*/

# Basic connectivity test
./gandalf test
```

### Recovery Strategies

| Issue Type            | Quick Fix                         | Deep Fix                    |
| --------------------- | --------------------------------- | --------------------------- |
| **No Results**        | `min_score=0.1, days_lookback=30` | Clear cache + reinstall     |
| **Slow Performance**  | `fast_mode=true, limit=20`        | Optimize database indexes   |
| **Connection Errors** | Restart IDE                       | `./gandalf install --force` |
| **Cache Issues**      | `rm -rf ~/.gandalf/cache/*`       | Reset all configurations    |

### Performance Monitoring

```bash
# Monitor response times
time recall_conversations(fast_mode=true)

# Basic performance test
./gandalf test
```
