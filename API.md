# API Reference

## Quick Start

Always start with `recall_conversations()`, then use other tools as needed.

## Tools

| Tool                              | Purpose                         | When to Use             |
| --------------------------------- | ------------------------------- | ----------------------- |
| `recall_conversations`            | Get recent conversations        | Always start here       |
| `search_conversations`            | Search conversation history     | Finding specific topics |
| `get_project_info`                | Project metadata and Git status | Unfamiliar projects     |
| `list_project_files`              | Smart file discovery            | Multi-file operations   |
| `get_server_version`              | Server version info             | Troubleshooting         |
| `export_individual_conversations` | Export conversations            | Backup/analysis         |

---

## recall_conversations

Get recent relevant conversations across all tools.

**Parameters**

- `fast_mode` (boolean, default: true): Quick extraction
- `days_lookback` (integer, default: 7): Days to search back (1-60)
- `limit` (integer, default: 20): Max conversations per tool (1-100)
- `min_score` (number, default: 2.0): Minimum relevance score

**Examples**

```bash
# Basic usage
recall_conversations(fast_mode=true)

# Extended search
recall_conversations(days_lookback=14, limit=30)
```

---

## search_conversations

Search conversation history for specific topics.

**Parameters**

- `query` (string, required): Search query
- `days_lookback` (integer, default: 30): Search timeframe (0 = all time)
- `limit` (integer, default: 20): Max results per tool
- `include_content` (boolean, default: false): Include full content

**Examples**

```bash
# Search for patterns
search_conversations(query="authentication bug fix")

# Include full content
search_conversations(query="database performance", include_content=true)
```

---

## get_project_info

Get project metadata, Git status, and statistics.

**Parameters**

- `include_stats` (boolean, default: true): Include file counts

**Examples**

```bash
# Full project analysis
get_project_info()

# Basic info only
get_project_info(include_stats=false)
```

---

## list_project_files

Smart file discovery with relevance scoring.

**Parameters**

- `file_types` (array, optional) - Filter by extensions (e.g., [".py", ".js"])
- `max_files` (integer, default: 1000) - Max files to return (1-10000)
- `use_relevance_scoring` (boolean, default: true) - Enable smart prioritization

**Examples**

```bash
# Python and JavaScript files
list_project_files(file_types=[".py", ".js"], max_files=50)

# All files with smart prioritization
list_project_files(max_files=100)
```

---

## get_server_version

Get server version and protocol information.

**Parameters**

- `random_string` (string, required): Dummy parameter (any value)

**Examples**

```bash
get_server_version(random_string="check")
```

---

## export_individual_conversations

Export conversations to files.

**Parameters**

- `format` (string, default: "json"): Export format: "json", "md", "txt"
- `limit` (integer, default: 20): Max conversations (1-100)
- `output_dir` (string, optional): Output directory
- `conversation_filter` (string, optional): Filter by name

**Examples**

```bash
# Export as Markdown
export_individual_conversations(format="md", limit=10)

# Export to specific directory
export_individual_conversations(format="json", output_dir="/path/to/exports")
```

---

## Performance Guidelines

| Project Size          | Configuration        | Example                                                |
| --------------------- | -------------------- | ------------------------------------------------------ |
| Small (<50 files)     | Default settings     | `list_project_files(max_files=50)`                     |
| Medium (50-500 files) | Use `fast_mode=true` | `recall_conversations(fast_mode=true)`                 |
| Large (500+ files)    | Limit scope          | `list_project_files(max_files=50, file_types=[".py"])` |

## Best Practices

- Always use `fast_mode=true` for recall
- Limit `max_files` based on need
- Use specific `file_types` to reduce noise
- Start broad, then narrow searches

## Common Workflows

**Starting new work**

```bash
recall_conversations(fast_mode=true)
get_project_info()
list_project_files(max_files=50)
```

**Finding solutions**

```bash
recall_conversations(days_lookback=14)
search_conversations(query="your topic")
```

**Troubleshooting**

```bash
get_server_version(random_string="debug")
recall_conversations(limit=5)
```

## Error Handling

Common errors:

- `TOOL_EXECUTION_ERROR`: Check parameters and resources
- `TIMEOUT_ERROR`: Use `fast_mode=true`, reduce scope
- `DATABASE_ACCESS_ERROR`: Check permissions

## Cross-Platform Support

Gandalf automatically detects:

- **Cursor IDE**: SQLite database (~/.cursor/conversations.db)
- **Claude Code**: JSONL sessions (~/.claude/sessions/)
- **Windsurf**: State database (App Support/Windsurf/state.vscdb)

Note: Windsurf conversations may be empty due to flow-based architecture.
