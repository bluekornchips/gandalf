---
description:
globs:
alwaysApply: true
---

# Gandalf MCP Rules

## Core Principle

**Context before action.** Always gather relevant context before making changes or providing solutions.

## Essential Workflow

### 1. Start with History

**ALWAYS** begin with conversation recall:

```bash
recall_conversations(fast_mode=true, days_lookback=7)
```

### 2. Assess Context Needs

Ask yourself:

- Is this a familiar project or codebase?
- Do I need to understand file structure?
- Are there past solutions to similar problems?
- What specific information do I need?

### 3. Gather Targeted Context

Only gather what you need:

- **Project overview**: `get_project_info()` for unfamiliar projects
- **File discovery**: `list_project_files()` for multi-file work
- **Past solutions**: `search_conversations()` for specific topics
- **System status**: `get_server_version()` for MCP issues

## The 6 Tools - When to Use

| Tool                              | Primary Use                       | Secondary Use                  | Skip When                   |
| --------------------------------- | --------------------------------- | ------------------------------ | --------------------------- |
| `recall_conversations`            | **Always start here**             | Finding recent context         | Never skip                  |
| `search_conversations`            | Finding specific past solutions   | Understanding project patterns | No relevant history exists  |
| `get_project_info`                | Understanding unfamiliar projects | Checking Git status            | Project is already familiar |
| `list_project_files`              | Multi-file operations             | Finding specific files         | Working with single files   |
| `get_server_version`              | Troubleshooting MCP issues        | Checking compatibility         | No MCP problems             |
| `export_individual_conversations` | Backup/documentation needs        | Sharing context                | Not requested by user       |

## Decision Trees

### New Project/Codebase

1. `recall_conversations()` - Check if you've worked on this before
2. `get_project_info()` - Understand structure and Git status
3. `list_project_files()` - Discover relevant files
4. Proceed with targeted file reading

### Debugging/Problem Solving

1. `recall_conversations()` - Look for similar past issues
2. `search_conversations()` - Find specific error patterns or solutions
3. `get_project_info()` - Check for recent changes or Git status
4. Apply solutions or gather more specific context

### Code Changes/Refactoring

1. `recall_conversations()` - Check for past discussions about this code
2. `list_project_files()` - Find all related files
3. Read relevant files and understand dependencies
4. Make changes with full context

## Performance Guidelines

### Optimize Tool Usage

- Use `fast_mode=true` for conversation recall (default)
- Limit `max_files` based on project size:
  - Small projects (< 100 files): `max_files=50`
  - Medium projects (100-1000 files): `max_files=100`
  - Large projects (> 1000 files): `max_files=50` with specific `file_types`

### Avoid Context Overload

- Don't gather information you won't use
- Focus on the specific problem or task
- Use targeted file type filters when possible
- Prefer multiple small, focused queries over one large query

## Common Mistakes to Avoid

### Context Gathering

- **Don't skip conversation history** - Always start with `recall_conversations()`
- **Don't over-gather** - Only get context you'll actually use
- **Don't assume** - Check project structure before making assumptions
- **Don't ignore past solutions** - Search conversations for similar problems

### Tool Usage

- **Don't use all tools by default** - Be selective based on the task
- **Don't execute Git commands that alter state** - Unless explicitly requested
- **Don't make changes without context** - Understand the codebase first
- **Don't repeat failed approaches** - Learn from conversation history

## Quality Checks

Before providing solutions:

- [ ] Have I checked conversation history for similar problems?
- [ ] Do I understand the project structure and context?
- [ ] Have I identified all relevant files and dependencies?
- [ ] Am I building on past solutions rather than starting from scratch?
- [ ] Is my approach consistent with established patterns in this project?

## Error Recovery

### When Tools Fail

1. **Try alternative approaches**: Use `list_project_files()` if `get_project_info()` fails
2. **Reduce scope**: Use `fast_mode=true`, smaller `max_files`, shorter `days_lookback`
3. **Check system status**: Use `get_server_version()` to diagnose MCP issues
4. **Fallback gracefully**: Work with available context rather than failing completely

### When Context is Insufficient

1. **Ask targeted questions** - Be specific about what you need to know
2. **Start with smaller changes** - Make incremental progress
3. **Document assumptions** - Be clear about what you're assuming
4. **Verify understanding** - Confirm your interpretation with the user

## Integration Patterns

### With Standard Development Tools

- Use Gandalf for **context and history**, standard tools for **implementation**
- **Don't duplicate work** - If you have context, use it; don't re-gather
- **Coordinate approaches** - Build on existing solutions rather than replacing them

### Cross-Tool Conversation Aggregation

- Gandalf automatically aggregates conversations from Cursor and Claude Code
- No special configuration needed - just use the tools normally
- Results include relevance scoring across all conversation sources
- Processing is typically under 0.05 seconds

## Environment Information

### Supported Environments

- **Cursor IDE**: Full conversation history, workspace detection
- **Claude Code**: Session history, project analysis
- **Auto-detection**: Based on environment variables and running processes

### Version Requirements

- **Current Architecture**: 6 streamlined tools
- **Expected Version**: 2.0.0+
- **Reset Command**: `gandalf install -r` to clear cache and reinstall

## Troubleshooting Quick Reference

| Problem                    | Quick Fix                                        |
| -------------------------- | ------------------------------------------------ |
| Tools not appearing        | Restart IDE completely; run `gandalf install -r` |
| Server not responding      | Check `gandalf test`; verify Python dependencies |
| Slow performance           | Use `fast_mode=true`; limit `max_files`          |
| Empty conversation results | Restart IDE; check database permissions          |
| Import errors              | Install dependencies; check Python version 3.10+ |

For detailed troubleshooting, see `gandalf/docs/troubleshooting.md`
