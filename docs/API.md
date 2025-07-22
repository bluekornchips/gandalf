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

**Response Structure (MCP 2025-06-18 Format):**

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"conversations\": [...], \"total_conversations\": 25, ...}",
      "annotations": {
        "audience": ["assistant"],
        "priority": 0.8
      }
    }
  ],
  "structuredContent": {
    "summary": {
      "total_conversations": 25,
      "available_tools": ["cursor", "claude-code"],
      "processing_time": 0.045
    },
    "conversations": [...],
    "context": {
      "keywords": ["auth", "api"],
      "filters_applied": {
        "fast_mode": true,
        "days_lookback": 30,
        "min_score": 1.0,
        "limit": 60
      }
    },
    "tool_results": {
      "cursor": {"total_conversations": 15},
      "claude-code": {"total_conversations": 10}
    }
  },
  "isError": false
}
```

## get_project_info

Project metadata, Git status, and file statistics.

**Parameters:**

- `include_stats` (boolean, default: true): Include file statistics

**Response Structure (MCP 2025-06-18 Format):**

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"project_root\": \"/path/to/project\", ...}",
      "annotations": {
        "audience": ["assistant"],
        "priority": 0.8
      }
    }
  ],
  "structuredContent": {
    "project": {
      "name": "my-project",
      "root": "/path/to/project",
      "valid": true
    },
    "git": {
      "is_git_repo": true,
      "current_branch": "main",
      "repo_root": "/path/to/project"
    },
    "statistics": {
      "files": 150,
      "directories": 25
    },
    "metadata": {
      "timestamp": 1641234567.89,
      "sanitized": false
    }
  },
  "isError": false
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
  "protocol_version": "2025-06-18",
  "server_name": "gandalf-mcp"
}
```

**Examples:**

```bash
get_server_version()
```

## Logging & Diagnostics

### Dynamic Log Level Control

The server supports dynamic log level adjustment during runtime using the MCP `logging/setLevel` request:

**Supported Log Levels** (RFC 5424):

- `debug`: Detailed diagnostic information
- `info`: General operational messages
- `notice`: Normal but significant events
- `warning`: Warning conditions
- `error`: Error conditions
- `critical`: Critical conditions
- `alert`: Action must be taken immediately
- `emergency`: System is unusable

**Session Logs Location:**

```bash
~/.gandalf/logs/gandalf_session_{session_id}_{timestamp}.log
```

**Log Format:**

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "info",
  "message": "Operation completed successfully",
  "session_id": "abc12345",
  "logger": "tool_call_recall_conversations",
  "data": { "processing_time": 0.045 }
}
```

## Performance Guidelines

| Project Size          | Configuration    | Example                                                |
| --------------------- | ---------------- | ------------------------------------------------------ |
| Small (<50 files)     | Default settings | `list_project_files()`                                 |
| Medium (50-500 files) | Enable fast mode | `recall_conversations(fast_mode=true)`                 |
| Large (500+ files)    | Limit scope      | `list_project_files(file_types=[".py"], max_files=50)` |

## Cross-Platform Support

Automatically detects and aggregates from:

- **Cursor**: SQLite database conversations with workspace detection
- **Claude Code**: JSONL session files with project-specific context
- **Windsurf**: State database integration with session tracking

### MCP Protocol Compliance

- **Protocol Version**: 2025-06-18
- **Server Capabilities**:
  - Tools with change notifications (`listChanged: true`)
  - Dynamic logging level control
  - Session-based structured logging
- **JSON-RPC 2.0**: Full specification compliance with enhanced error handling

### Enhanced Response Format

All tools now return **structured content** alongside text content according to MCP 2025-06-18:

- **Text Content**: Human-readable JSON for backward compatibility
- **Structured Content**: Parsed data optimized for AI consumption
- **Annotations**: Content metadata including audience and priority
- **Error Handling**: Distinguishes protocol errors from tool execution errors

### Tool Change Notifications

The server automatically sends `notifications/tools/list_changed` when tool definitions are updated, ensuring clients stay synchronized with available capabilities.

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
      "text": "Failed to access conversation database: Permission denied",
      "annotations": {
        "audience": ["assistant"],
        "priority": 0.9
      }
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
