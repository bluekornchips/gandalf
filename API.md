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

### `recall_cursor_conversations`

Recall and analyze conversation history with caching.

**Parameters:**

- `days_lookback` (integer): Days to look back (default: 7)
- `limit` (integer): Max conversations (default: 20)
- `fast_mode` (boolean): Fast extraction (default: true)
- `conversation_types` (array): Filter by types when fast_mode=false

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
- `workspace_hash`: Unique identifier for the Cursor workspace
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

### `search_cursor_conversations`

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
