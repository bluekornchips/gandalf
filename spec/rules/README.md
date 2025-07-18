# Gandalf Rules

Agent behavior rules for development tools using Gandalf MCP Server.

## Quick Start

```bash
# Edit rules
spec/rules/core.md             # Core workflows
spec/rules/troubleshooting.md  # Error recovery

# Deploy rules
./gandalf install --force

# Test
./gandalf test install
```

## Rule Files

| File                 | Purpose                              | Activation         |
| -------------------- | ------------------------------------ | ------------------ |
| `core.md`            | Primary workflows and decision trees | Always active      |
| `troubleshooting.md` | Error recovery and diagnostics       | Smart activation   |
| `README.md`          | Documentation (this file)            | Documentation only |

## Deployment

Rules are deployed differently per tool:

| Tool            | Location                            | Format                     |
| --------------- | ----------------------------------- | -------------------------- |
| Cursor      | `~/.cursor/rules/gandalf-rules.mdc` | Smart activation           |
| Claude Code | `~/.claude/global_settings.json`    | `gandalfRules` property    |
| Windsurf    | `~/.windsurf/global_rules.md`       | Combined (6000 char limit) |

## Rule Structure

### Core Workflows, [core.md](./core.md)

- Always active, across all tools
- Defines primary decision trees
- Performance optimization guidelines
- Best practices for tool usage

### Troubleshooting, [troubleshooting.md](./troubleshooting.md)

- Smart activation on error conditions
- Error recovery procedures
- Common issue resolution
- Diagnostic workflows

## Management Commands

```bash
# Edit
vim spec/rules/core.md
vim spec/rules/troubleshooting.md

# Deploy to all tools
./gandalf install --force

# Test
./gandalf test install
```
