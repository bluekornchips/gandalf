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

- `fast_mode` (boolean, default: true): Enable optimizations
- `days_lookback` (integer, default: 30): Days to look back (1-60)
- `limit` (integer, default: 60): Max conversations (1-100)
- `min_score` (number, default: 1.0): Relevance threshold
- `conversation_types` (array): Filter by type: "architecture", "debugging", "problem_solving", "technical", "code_discussion", "general"
- `tools` (array): Filter by tool: "cursor", "claude-code", "windsurf"
- `search_query` (string): Filter for specific content
- `user_prompt` (string): Context for keyword extraction
- `tags` (array): Additional filter keywords

**Examples:**

```bash
recall_conversations()
recall_conversations(search_query="authentication", limit=15)
recall_conversations(conversation_types=["debugging", "problem_solving"])
recall_conversations(tools=["cursor"], fast_mode=true)
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

Smart file discovery with relevance scoring and filtering.

**Parameters:**

- `file_types` (array): File extensions (e.g., [".py", ".js"]) - max 20 types
- `max_files` (integer, default: 1000): Maximum files (1-10000)
- `use_relevance_scoring` (boolean, default: true): Enable prioritization

**Examples:**

```bash
list_project_files()
list_project_files(file_types=[".py", ".js"], max_files=50)
list_project_files(use_relevance_scoring=false)
```

## export_individual_conversations

Export conversations to separate files.

**Parameters:**

- `format` (string, default: "json"): Export format: "json", "md", "markdown", "txt"
- `limit` (integer, default: 20): Max conversations (1-100)
- `output_dir` (string): Output directory (defaults to ~/.gandalf/exports)
- `conversation_filter` (string): Filter by conversation name (partial match)
- `workspace_filter` (string): Filter by workspace hash

**Examples:**

```bash
export_individual_conversations()
export_individual_conversations(format="md", limit=10)
export_individual_conversations(output_dir="/path/to/exports")
```

## get_server_version

Server version and protocol information.

**Parameters:**

- None required

**Examples:**

```bash
get_server_version()
```

## Usage Guidelines

| Project Size          | Configuration    | Example                                                |
| --------------------- | ---------------- | ------------------------------------------------------ |
| Small (<50 files)     | Default settings | `list_project_files()`                                 |
| Medium (50-500 files) | Enable fast mode | `recall_conversations(fast_mode=true)`                 |
| Large (500+ files)    | Limit scope      | `list_project_files(file_types=[".py"], max_files=50)` |

## Cross-Platform Support

Automatically detects and aggregates from:

- Cursor: SQLite database conversations with workspace detection
- Claude Code: JSONL session files with project-specific context
- Windsurf: State database integration with session tracking

## Error Handling

The server implements **two-tier error handling** according to MCP 2025-06-18:

### Protocol Errors

Standard JSON-RPC errors for structural issues:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "Invalid params: missing required parameter 'name'"
  }
}
```

### Tool Execution Errors

Business logic errors returned in tool results:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Failed to access conversation database: Permission denied"
    }
  ],
  "isError": true
}
```

Common error codes:

- `INVALID_PARAMS`: Invalid or missing parameters
- `ACCESS_DENIED`: Security restrictions
- `NOT_FOUND`: Resource not found
- `TIMEOUT`: Operation timed out
- `INTERNAL_ERROR`: Server processing error

For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
