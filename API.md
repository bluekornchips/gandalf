# API Reference

Gandalf MCP server provides intelligent code assistance tools for both **Cursor IDE** and **Claude Code**. Tools are automatically adapted based on your IDE environment.

## MCP Tools

### `get_project_info`

Get project metadata, Git information, and statistics.

**Parameters:**

- `include_stats` (boolean): Include file statistics (default: true)

**Supported IDEs:** Cursor IDE, Claude Code

**Example Response:**

```json
{
  "project_root": "/path/to/project",
  "git_info": {
    "branch": "main",
    "commit": "abc123",
    "is_dirty": false
  },
  "file_stats": {
    "total_files": 42,
    "total_size_mb": 1.2
  }
}
```

### `list_project_files`

List files with intelligent relevance scoring and filtering.

**Parameters:**

- `max_files` (integer): Maximum files to return (default: 1000, max: 10000)
- `file_types` (array): Filter by extensions (e.g., ['.py', '.js', '.md'])
- `use_relevance_scoring` (boolean): Enable scoring (default: true)

**Supported IDEs:** Cursor IDE, Claude Code

**Example Usage:**

```json
{
  "max_files": 50,
  "file_types": [".py", ".js"],
  "use_relevance_scoring": true
}
```

### `recall_conversations`

Recall and analyze conversation history with intelligent caching. Automatically adapts to your IDE environment.

**Parameters:**

- `days_lookback` (integer): Days to look back (default: 7, max: 60)
- `limit` (integer): Max conversations (default: 20, max: 100)
- `fast_mode` (boolean): Fast extraction vs full analysis (default: true)
- `conversation_types` (array): Filter by types when fast_mode=false
  - Available types: `architecture`, `debugging`, `problem_solving`, `technical`, `code_discussion`, `general`

**Supported IDEs:**

- **Cursor IDE**: Full SQLite database access
- **Claude Code**: JSONL session file parsing

**Response Structure:**

```json
{
  "mode": "ultra_fast_extraction",
  "total_conversations": 10,
  "parameters": {
    "limit": 10,
    "days_lookback": 7,
    "conversation_types": []
  },
  "processing_stats": {
    "total_processed": 161,
    "skipped": 128,
    "efficiency_percent": 20.5,
    "extraction_time_seconds": 0.05,
    "filtering_time_seconds": 0.0,
    "total_time_seconds": 0.05
  },
  "conversations": [
    {
      "name": "Conversation Title",
      "workspace_hash": "12b67621",
      "conversation_id": "uuid-string",
      "last_updated": 1750944865054,
      "created_at": 1750944863517,
      "prompt_count": 2,
      "generation_count": 2,
      "total_exchanges": 2,
      "activity_score": 2.0,
      "workspace_stats": {
        "total_conversations": 148,
        "total_prompts": 275,
        "total_generations": 100
      }
    }
  ],
  "database_note": "Additional context about data limitations"
}
```

**Response Fields:**

**Top Level:**

- `mode`: Extraction mode used ("ultra_fast_extraction" or "enhanced_mode")
- `total_conversations`: Number of conversations returned
- `parameters`: Echo of the input parameters used
- `processing_stats`: Performance metrics for the operation
- `conversations`: Array of conversation objects
- `database_note`: Additional context about data limitations or processing notes

**Processing Stats:**

- `total_processed`: Total conversations examined during extraction
- `skipped`: Number of conversations filtered out
- `efficiency_percent`: Percentage of conversations that passed filtering
- `extraction_time_seconds`: Time spent extracting conversation data
- `filtering_time_seconds`: Time spent filtering results
- `total_time_seconds`: Total processing time

**Conversation Object:**

- `name`: Display name/title of the conversation
- `workspace_hash`: Unique identifier for the workspace
- `conversation_id`: Unique UUID for this specific conversation
- `last_updated`: Unix timestamp (milliseconds) of last activity
- `created_at`: Unix timestamp (milliseconds) when conversation was created
- `prompt_count`: Number of user prompts in this conversation
- `generation_count`: Number of AI responses generated
- `total_exchanges`: Total back-and-forth exchanges (prompts + generations)
- `activity_score`: Relevance score based on recency and activity level
- `workspace_stats`: Aggregate statistics for the entire workspace

**Workspace Stats:**

- `total_conversations`: Total conversations in this workspace
- `total_prompts`: Total user prompts across all conversations
- `total_generations`: Total AI generations across all conversations

### `search_conversations`

Search conversations for specific topics, keywords, or context.

**Parameters:**

- `query` (string, required): Search terms
- `limit` (integer): Max results (default: 20, max: 100)
- `include_content` (boolean): Include content snippets (default: false)
- `days_lookback` (integer): Number of days to search (default: 30, 0 for all time)

**Supported IDEs:**

- **Cursor IDE**: Full-text search across SQLite database
- **Claude Code**: Content search across JSONL session files

**Example Usage:**

```json
{
  "query": "authentication error debugging",
  "limit": 10,
  "include_content": true,
  "days_lookback": 14
}
```

### `query_conversations`

Direct access to conversation databases/sessions for comprehensive analysis.

**Parameters:**

- `format` (string): Output format - 'cursor', 'markdown', 'json' (default: 'cursor')
- `summary` (boolean): Return stats only (default: false)

**Supported IDEs:**

- **Cursor IDE**: Direct SQLite database queries
- **Claude Code**: JSONL session file access

**IDE-Specific Behavior:**

- **Cursor**: Returns native Cursor conversation format
- **Claude Code**: Returns processed session data in requested format

### `export_individual_conversations`

Export conversations to separate files for backup or analysis.

**Parameters:**

- `limit` (integer): Max conversations to export (default: 20, max: 100)
- `format` (string): Export format - 'json', 'md', 'markdown', 'txt' (default: 'json')
- `output_dir` (string): Output directory (default: ~/.gandalf/exports)
- `conversation_filter` (string): Filter conversations by name (partial match)
- `workspace_filter` (string): Filter by specific workspace hash

**Supported IDEs:** Cursor IDE, Claude Code

**Example Usage:**

```json
{
  "limit": 50,
  "format": "markdown",
  "output_dir": "/path/to/exports",
  "conversation_filter": "debugging"
}
```

### `get_server_version`

Get current server version and protocol information.

**Parameters:**

- `random_string` (string, required): Dummy parameter for no-parameter tools

**Supported IDEs:** Cursor IDE, Claude Code

**Response:**

```json
{
  "server_version": "2.0.0",
  "protocol_version": "2024-11-05",
  "timestamp": 1750993030.567144,
  "detected_ide": "claude-code",
  "environment_info": {
    "python_version": "3.10.12",
    "platform": "darwin"
  }
}
```

## IDE-Specific Tools

### Cursor IDE Only

- **`list_cursor_workspaces`**: List available workspace databases
- **`recall_cursor_conversations`**: Cursor-specific conversation recall
- **`search_cursor_conversations`**: Cursor-specific conversation search
- **`query_cursor_conversations`**: Direct Cursor database access

### Claude Code Only

- **`recall_claude_conversations`**: Claude Code session recall
- **`search_claude_conversations`**: Claude Code session search
- **`search_claude_conversations_enhanced`**: Enhanced search with relevance scoring

## Core Functions

### Context Intelligence

- `get_context_intelligence(project_root, options)` - Main context analysis
- `analyze_project_context(project_root)` - Project analysis
- `get_intelligent_file_selection(files, context)` - File prioritization

### Conversation Storage

- `load_stored_conversations(filters)` - Load conversations
- `store_conversation(conversation_data)` - Cache conversations
- `search_conversations(query, options)` - Search conversations

### File Scoring

- `get_files_with_scores(project_root, options)` - Get scored files
- `calculate_relevance_score(file_path, context)` - Calculate score

**Scoring weights:** Recent activity (30%), File size (20%), File type (20%), Directory (15%), Imports (15%)

### Git Activity

- `GitActivityTracker(project_root)` - Git analysis class
- `get_recent_activity(days)` - Recent commits
- `get_file_activity_score(file_path)` - File activity score

### File Filtering

- `should_ignore_file(file_path, patterns)` - Check if ignored
- `load_ignore_patterns(project_root)` - Load ignore patterns

## CLI Commands

```bash
# Dependencies
./gandalf.sh deps [--verbose|--install]

# Installation
./gandalf.sh install [-r] [--ide cursor|claude-code] [path]

# Testing
./gandalf.sh test [--shell|--python] [--verbose]

# Utilities
./gandalf.sh lembas          # Full validation
./gandalf.sh run             # Run server
```

## Configuration

**Environment Variables:**

- `MCP_DEBUG` - Enable debug logging
- `MCP_SERVER_NAME` - Server identification (default: "gandalf")
- `CLAUDECODE` - Force Claude Code mode
- `CLAUDE_CODE_ENTRYPOINT` - Claude Code entry point
- `GANDALF_FALLBACK_IDE` - IDE fallback when detection fails

**Optional weights.yaml:**

```yaml
file_scoring:
  recent_activity: 0.3
  file_size: 0.2
  file_type: 0.2
  directory_importance: 0.15
  import_relationships: 0.15
```

## IDE Detection

Gandalf automatically detects your IDE environment using:

**Claude Code Detection:**

- Environment variables: `CLAUDECODE=1`, `CLAUDE_CODE_ENTRYPOINT=cli`
- Configuration directories: `~/.claude`, `~/.config/claude`
- Running processes: Claude processes

**Cursor IDE Detection:**

- Environment variables: `CURSOR_TRACE_ID`, `VSCODE_INJECTION=1`
- Application paths: `/Applications/Cursor.app`
- Data directories: `~/Library/Application Support/Cursor`
- Running processes: Cursor processes

## Error Handling

All tools implement graceful error handling:

- **Missing IDE data**: Returns empty results with informative messages
- **Permission issues**: Provides clear error messages and suggestions
- **Invalid parameters**: Validates input and returns helpful error messages
- **Network/file system errors**: Implements retry logic and fallback behavior
