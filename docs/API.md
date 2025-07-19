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
recall_conversations(min_score=0.5, tags=["api", "auth"])
```

**Response Structure:**

```json
{
  "conversations": [...],
  "total_conversations": 25,
  "available_tools": ["cursor", "claude-code"],
  "context_keywords": ["auth", "api"],
  "processing_time": 0.045,
  "tool_results": {
    "cursor": {"total_conversations": 15},
    "claude-code": {"total_conversations": 10}
  }
}
```

## get_project_info

Project metadata, Git status, and file statistics.

**Parameters:**

- `include_stats` (boolean, default: true): Include file statistics

**Response Structure:**

```json
{
  "project_root": "/path/to/project",
  "project_name": "my-project",
  "valid_path": true,
  "git": {
    "is_git_repo": true,
    "current_branch": "main",
    "repo_root": "/path/to/project"
  },
  "file_stats": {
    "total_files": 150,
    "total_directories": 25
  }
}
```

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

**Response Structure:**

```json
{
  "files": [
    {
      "path": "src/main.py",
      "score": 0.95,
      "priority": "high",
      "size": 2048
    }
  ],
  "total_files": 150,
  "processing_time": 0.123
}
```

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

**Response Structure:**

```json
{
  "exported_files": 15,
  "output_directory": "/Users/user/.gandalf/exports",
  "export_format": "json",
  "processing_time": 0.234
}
```

**Examples:**

```bash
export_individual_conversations()
export_individual_conversations(format="md", limit=10)
export_individual_conversations(output_dir="/path/to/exports", conversation_filter="auth")
```

## get_server_version

Server version and protocol information.

**Parameters:**

- None required

**Response Structure:**

```json
{
  "server_version": "2.3.0",
  "protocol_version": "2024-11-05",
  "server_name": "gandalf-mcp"
}
```

**Examples:**

```bash
get_server_version()
```

## Performance Guidelines

| Project Size          | Configuration    | Example                                                |
| --------------------- | ---------------- | ------------------------------------------------------ |
| Small (<50 files)     | Default settings | `list_project_files()`                                 |
| Medium (50-500 files) | Enable fast mode | `recall_conversations(fast_mode=true)`                 |
| Large (500+ files)    | Limit scope      | `list_project_files(file_types=[".py"], max_files=50)` |

## Cross-Platform Support

Automatically detects and aggregates from:

- **Cursor**: SQLite database conversations
- **Claude Code**: JSONL session files
- **Windsurf**: State database integration

## Error Handling

All tools return consistent error responses:

```json
{
  "error": {
    "code": "INVALID_PARAMS",
    "message": "Description of the error"
  }
}
```

Common error codes:

- `INVALID_PARAMS`: Invalid or missing parameters
- `ACCESS_DENIED`: Security restrictions
- `NOT_FOUND`: Resource not found
- `TIMEOUT`: Operation timed out

For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
