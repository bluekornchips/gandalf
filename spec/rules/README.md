# Enhanced Gandalf Rules

Agent behavior rules for development tools using Gandalf MCP Server.

## Quick Start

```bash
# Edit rules
spec/rules/gandalf-rules.md    # All workflows and recovery

# Deploy rules
./gandalf install --force

# Test
./gandalf test install
```

## Rule Files

| File               | Purpose                                 | Activation         |
| ------------------ | --------------------------------------- | ------------------ |
| `gandalf-rules.md` | Complete rule system with all workflows | Always active      |
| `README.md`        | Documentation (this file)               | Documentation only |

## Deployment

Rules are deployed differently per tool:

| Tool        | Location                            | Format                     |
| ----------- | ----------------------------------- | -------------------------- |
| Cursor      | `~/.cursor/rule./gandalf-rules.mdc` | Smart activation           |
| Claude Code | `~/.claude/global_settings.json`    | `gandalfRules` property    |
| Windsurf    | `~/.windsurf/global_rules.md`       | Combined (6000 char limit) |

## Rule Structure

### Complete Rule System, [gandalf-rules.md](./gandalf-rules.md)

The single rule file contains:

- **Section 1**: Core workflows (always active)
- **Section 2**: Advanced operations for multi-tool coordination
- **Section 3**: Performance optimization with auto-scaling parameters
- **Section 4**: Error recovery with smart activation triggers
- **Section 5**: Best practices integration
- **Section 6**: Troubleshooting reference

## Management Commands

```bash
# Edit rules
vim spec/rules/gandalf-rules.md

# Deploy to all tools
./gandalf install --force

# Test deployment
./gandalf test install

# Verify functionality
get_project_info(include_stats=true)
recall_conversations(fast_mode=true, limit=5)
```
