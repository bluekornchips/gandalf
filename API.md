# API Reference

Complete tool documentation for Gandalf MCP Server.

## Core Tools

| Tool                              | Purpose                                     | Usage                 |
| --------------------------------- | ------------------------------------------- | --------------------- |
| `recall_conversations`            | Cross-platform conversation aggregation     | Always start here     |
| `get_project_info`                | Project metadata and Git status             | Unfamiliar projects   |
| `list_project_files`              | Smart file discovery with relevance scoring | Multi-file operations |
| `export_individual_conversations` | Export conversations to files               | Backup/documentation  |
| `get_server_version`              | Server version and protocol info            | Troubleshooting       |

## recall_conversations

Cross-platform conversation aggregation across all supported tools.

**Parameters:**

- `fast_mode` (boolean, default: true): Fast vs comprehensive analysis
- `days_lookback` (integer, default: 7): Days to look back (1-60)
- `limit` (integer, default: 20): Max conversations (1-100)
- `min_score` (number, default: 2.0): Relevance threshold
- `conversation_types` (array): ["debugging", "problem_solving", "technical", "general"]
- `tools` (array): ["cursor", "claude-code", "windsurf"]
- `search_query` (string): Filter for specific content
- `user_prompt` (string): Context for keyword extraction
- `tags` (array): Additional filter keywords

**Examples:**

```bash
recall_conversations(fast_mode=true)
recall_conversations(search_query="auth", limit=15)
recall_conversations(conversation_types=["debugging"])
```

## get_project_info

Project metadata, Git status, and file statistics.

**Parameters:**

- `include_stats` (boolean, default: true): Include file statistics

**Examples:**

```bash
get_project_info()
get_project_info(include_stats=false)
```

## list_project_files

Smart file discovery with relevance scoring.

**Parameters:**

- `file_types` (array): File extensions (e.g., [".py", ".js"])
- `max_files` (integer, default: 1000): Maximum files (1-10000)
- `use_relevance_scoring` (boolean, default: true): Enable prioritization

**Examples:**

```bash
list_project_files(file_types=[".py", ".js"], max_files=50)
list_project_files(max_files=100)
```

## export_individual_conversations

Export conversations to files.

**Parameters:**

- `format` (string, default: "json"): Format: "json", "md", "txt"
- `limit` (integer, default: 20): Max conversations (1-100)
- `output_dir` (string): Output directory (defaults to ~/.gandalf/exports)
- `conversation_filter` (string): Filter by name
- `workspace_filter` (string): Filter by workspace

**Examples:**

```bash
export_individual_conversations(format="md", limit=10)
export_individual_conversations(output_dir="/path/to/exports")
```

## get_server_version

Server version and protocol information.

**Parameters:**

- `random_string` (string, required): Any value

**Examples:**

```bash
get_server_version(random_string="test")
```

## Performance Guidelines

| Project Size          | Configuration | Example                                                |
| --------------------- | ------------- | ------------------------------------------------------ |
| Small (<50 files)     | Default       | `list_project_files(max_files=50)`                     |
| Medium (50-500 files) | Fast mode     | `recall_conversations(fast_mode=true)`                 |
| Large (500+ files)    | Limited scope | `list_project_files(max_files=50, file_types=[".py"])` |

## Cross-Platform Support

Automatically detects and aggregates from:

- **Cursor**: SQLite database (`~/.cursor/conversations.db`)
- **Claude Code**: JSONL sessions (`~/.claude/sessions/`)
- **Windsurf**: State database (App Support/Windsurf/state.vscdb)

For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
