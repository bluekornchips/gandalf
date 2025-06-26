# API Reference

## MCP Tools

### `get_project_info`

Get project metadata and Git information.

- `include_stats` (boolean): Include file statistics (default: true)

### `list_project_files`

List files with intelligent scoring.

- `max_files` (integer): Maximum files to return (default: 1000)
- `file_types` (array): Filter by extensions (e.g., ['.py', '.js'])
- `use_relevance_scoring` (boolean): Enable scoring (default: true)

### `ingest_conversations`

Analyze conversation history with caching.

- `days_lookback` (integer): Days to look back (default: 7)
- `limit` (integer): Max conversations (default: 20)
- `fast_mode` (boolean): Fast extraction (default: true)
- `conversation_types` (array): Filter by types when fast_mode=false

### `query_conversation_context`

Search conversations for topics.

- `query` (string, required): Search terms
- `limit` (integer): Max results (default: 10)
- `include_content` (boolean): Include snippets (default: false)

### `query_cursor_conversations`

Direct access to Cursor databases.

- `format` (string): Output format - 'cursor', 'markdown', 'json' (default: 'cursor')
- `summary` (boolean): Return stats only (default: false)

### `list_cursor_workspaces`

List available workspace databases.

- `random_string` (string, required): Dummy parameter

### `export_individual_conversations`

Export conversations to files.

- `limit` (integer): Max conversations (default: 20)
- `format` (string): Export format - 'json', 'md', 'txt' (default: 'json')

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
./gandalf.sh install [-r] [path]

# Testing
./gandalf.sh test [--shell|--python] [--verbose]

# Utilities
./gandalf.sh lembas          # Full validation
./gandalf.sh run             # Run server
```

## Configuration

**Environment Variables:**

- `MCP_DEBUG` - Enable debug logging
- `MCP_SERVER_NAME` - Server identification

**Optional weights.yaml:**

```yaml
file_scoring:
  recent_activity: 0.3
  file_size: 0.2
```
