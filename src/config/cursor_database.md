# Cursor IDE Database Structure & Conversation Export

This document provides comprehensive information about Cursor IDE's database structure and how to export conversations using the Gandalf MCP server.

## Overview

Cursor IDE stores conversation data in SQLite databases located in workspace-specific directories. Each workspace has its own database containing conversations, user prompts, and AI-generated responses.

## Database Structure

### Database Locations

Cursor databases are typically found in these locations:

**macOS:**

```
~/Library/Application Support/Cursor/workspaceStorage/{workspace-hash}/
```

**Linux:**

```
~/.config/Cursor/workspaceStorage/{workspace-hash}/
```

**Windows:**

```
%APPDATA%\Cursor\workspaceStorage\{workspace-hash}\
```

**WSL (Windows Subsystem for Linux):**

```
/mnt/c/Users/{username}/AppData/Roaming/Cursor/workspaceStorage/{workspace-hash}/
```

### Database Files

Each workspace directory contains one of these SQLite database files:

- `state.vscdb` (most common)
- `workspace.db`
- `storage.db`
- `cursor.db`

### Database Schema

The databases use a simple key-value structure with a primary table called `ItemTable`:

```sql
CREATE TABLE ItemTable (
    key TEXT PRIMARY KEY,
    value TEXT  -- JSON data
);
```

### Key Data Structures

#### 1. Conversations (`composer.composerData`)

Main conversation metadata and structure:

```json
{
  "allComposers": [
    {
      "composerId": "uuid-string",
      "name": "Conversation Title",
      "createdAt": 1640995200000,
      "lastUpdatedAt": 1640995800000,
      "messages": [
        {
          "id": "message-id",
          "role": "user|assistant",
          "content": "message content",
          "timestamp": 1640995200000
        }
      ]
    }
  ]
}
```

**Key Fields:**

- `composerId`: Unique identifier for the conversation
- `name`: User-defined conversation title
- `createdAt`: Unix timestamp (milliseconds) when conversation was created
- `lastUpdatedAt`: Unix timestamp (milliseconds) of last activity
- `messages`: Array of conversation messages

#### 2. User Prompts (`aiService.prompts`)

User input messages and context:

```json
[
  {
    "id": "prompt-id",
    "conversationId": "composer-id",
    "text": "User's question or request",
    "timestamp": 1640995200000,
    "unixMs": 1640995200000,
    "context": {
      "files": ["file1.py", "file2.js"],
      "selection": "selected code snippet"
    }
  }
]
```

**Key Fields:**

- `conversationId`: Links to `composerId` in conversations
- `text`: The actual user prompt text
- `timestamp`/`unixMs`: When the prompt was sent
- `context`: File context and code selections

#### 3. AI Generations (`aiService.generations`)

AI assistant responses:

```json
[
  {
    "id": "generation-id",
    "conversationId": "composer-id",
    "text": "AI assistant response",
    "timestamp": 1640995300000,
    "unixMs": 1640995300000,
    "model": "claude-3-sonnet",
    "finishReason": "stop"
  }
]
```

**Key Fields:**

- `conversationId`: Links to `composerId` in conversations
- `text`: The AI-generated response text
- `model`: AI model used for generation
- `finishReason`: How the generation ended (stop, length, etc.)

## Export Functionality

### Simple Export Function

The `export_conversations()` function provides an easy way to export all conversation data:

```python
from src.utils.conversation_export import export_conversations

# Basic export to JSON
result = export_conversations("my_conversations.json")

# Export to markdown format
result = export_conversations(
    "conversations.md",
    format_type="markdown"
)

# Export with filters
result = export_conversations(
    "debug_conversations.json",
    conversation_filter="debugging",
    include_generations=True,
    include_prompts=True
)
```

### Function Parameters

| Parameter             | Type        | Default  | Description                                          |
| --------------------- | ----------- | -------- | ---------------------------------------------------- |
| `output_path`         | `str\|Path` | Required | Where to save the exported file                      |
| `format_type`         | `str`       | `"json"` | Export format: `"json"`, `"markdown"`, or `"cursor"` |
| `include_prompts`     | `bool`      | `True`   | Include user prompts in export                       |
| `include_generations` | `bool`      | `True`   | Include AI responses in export                       |
| `workspace_filter`    | `List[str]` | `None`   | Only include specific workspace hashes               |
| `conversation_filter` | `str`       | `None`   | Filter by conversation name (partial match)          |
| `silent`              | `bool`      | `False`  | Suppress console output                              |

### Command Line Usage

The export utility can also be used from the command line:

```bash
# Basic export
python -m src.utils.conversation_export conversations.json

# Export to markdown
python -m src.utils.conversation_export conversations.md --format markdown

# Filter conversations
python -m src.utils.conversation_export debug.json --filter "debugging"

# Export specific workspace
python -m src.utils.conversation_export workspace.json --workspace abc123def

# List available workspaces
python -m src.utils.conversation_export --list-workspaces

# Export without prompts (responses only)
python -m src.utils.conversation_export responses.json --no-prompts
```

### MCP Tool Integration

The export functionality is also available through MCP tools:

```bash
# Export individual conversations to current directory
./gandalf/scripts/conversations.sh export --format=json --limit=10
./gandalf/scripts/conversations.sh export --format=md --conversation_filter="debugging"

# Query conversations directly for bulk export
./gandalf/scripts/conversations.sh query --query="debugging authentication"

# List workspaces
./gandalf/scripts/conversations.sh workspaces
```

#### Individual Conversation Export

The `export` command exports each conversation to a separate file in the current directory:

```bash
# Export recent conversations as JSON files
gdlf conv export --format=json --limit=20

# Export specific conversations as Markdown
gdlf conv export --format=md --conversation_filter="authentication"

# Export from specific workspace
gdlf conv export --format=txt --workspace_filter=abc123def456
```

**Output format:**

- Each conversation becomes a separate file
- Files are named based on conversation titles (sanitized for filesystem)
- Command line shows summary: ID, title, date, filename
- All files saved to current working directory

## Export Formats

### JSON Format

Complete structured data with all metadata:

```json
{
  "workspaces": [
    {
      "workspace_hash": "abc123def456",
      "database_path": "/path/to/database",
      "conversations": [...],
      "prompts": [...],
      "generations": [...]
    }
  ],
  "query_timestamp": "2024-01-01T12:00:00.000Z",
  "total_databases": 5,
  "databases_with_conversations": 3
}
```

### Markdown Format

Human-readable format for documentation:

```markdown
# Cursor Conversations

Queried: 2024-01-01T12:00:00.000Z

## Workspace abc123def456

### Debugging Authentication Issues

- **ID**: conv-123-456
- **Created**: 2024-01-01 10:30:00
- **Updated**: 2024-01-01 11:45:00
```

### Cursor Format

Detailed format matching Cursor's native conversation display:

```markdown
# Cursor Chat History

Queried: 2024-01-01T12:00:00.000Z
Total Workspaces: 3

## Workspace: abc123def456

Conversations: 15

### Debugging Authentication Issues

**ID:** conv-123-456
**Created:** 2024-01-01 10:30:00
**Updated:** 2024-01-01 11:45:00

**Conversation:**

**User:** How do I fix authentication errors in my app?

**Assistant:** Here are several approaches to debugging authentication...

---
```

## Data Relationships

```
Workspace Database
├── ItemTable
    ├── composer.composerData (conversations metadata)
    ├── aiService.prompts (user inputs)
    └── aiService.generations (AI responses)

Relationships:
- conversations.composerId ↔ prompts.conversationId
- conversations.composerId ↔ generations.conversationId
- prompts.timestamp ↔ generations.timestamp (conversation flow)
```

## Usage Examples

### Export All Conversations

```python
from src.utils.conversation_export import export_conversations

# Export everything to JSON
result = export_conversations("all_conversations.json")
print(f"Exported {result['total_conversations']} conversations")
```

### Export Recent Debugging Sessions

```python
# Filter for debugging-related conversations
result = export_conversations(
    "debug_sessions.md",
    format_type="markdown",
    conversation_filter="debug"
)
```

### Export Specific Workspace

```python
# First, list available workspaces
from src.utils.conversation_export import list_workspaces

workspaces = list_workspaces()
for ws in workspaces:
    print(f"{ws['workspace_hash']}: {ws['conversation_count']} conversations")

# Export specific workspace
result = export_conversations(
    "project_conversations.json",
    workspace_filter=["abc123def456"]
)
```

### Export Without AI Responses (Prompts Only)

```python
# Export only user prompts for analysis
result = export_conversations(
    "user_prompts.json",
    include_generations=False,
    include_prompts=True
)
```

## Statistics and Metadata

The export function returns detailed statistics:

```python
result = export_conversations("conversations.json")
print(result)
# {
#   "success": True,
#   "output_path": "conversations.json",
#   "format": "json",
#   "total_workspaces": 5,
#   "total_conversations": 127,
#   "total_prompts": 384,
#   "total_generations": 298,
#   "export_timestamp": "2024-01-01T12:00:00.000Z",
#   "filters_applied": {...}
# }
```

## Troubleshooting

### Common Issues

1. **No databases found**

   - Verify Cursor is installed and has been used
   - Check if running in WSL (databases are on Windows side)
   - Ensure proper permissions to access Cursor data directory

2. **Empty conversations**

   - Some workspaces may not have conversation data
   - Check if conversations exist in Cursor IDE
   - Verify database files are not corrupted

3. **Permission errors**
   - Ensure read access to Cursor data directories
   - On macOS, may need to grant terminal access to Application Support

### Debug Information

Enable verbose output to see what's happening:

```python
result = export_conversations(
    "conversations.json",
    silent=False  # Enable console output
)
```

Or use the command line with verbose output:

```bash
python -m src.utils.conversation_export conversations.json
# Shows: "Querying conversations from Cursor databases..."
# Shows: "Successfully exported 127 conversations to conversations.json"
```

## Security Considerations

- Conversation data may contain sensitive information
- Exported files are not encrypted by default
- Consider the security implications of storing conversation data
- Be mindful of sharing exported files as they contain your development context

## Integration with Gandalf MCP

This export functionality integrates seamlessly with the Gandalf MCP server's conversation intelligence features:

- **Context Gathering**: Export conversations for analysis
- **Pattern Recognition**: Use exported data to identify conversation patterns
- **Knowledge Base**: Build searchable archives of development conversations
- **Team Sharing**: Export and share relevant conversation threads

For more advanced conversation analysis, use the MCP tools:

- `recall_cursor_conversations` - Recall and analyze recent conversations with AI
- `search_cursor_conversations` - Search conversations by topic

## Limitations

- Database structure may change between Cursor versions
- Some conversation metadata may not be available in older versions
- Prompt/generation counts are estimates due to database structure limitations
- Large exports may take time to process and consume significant memory

## Contributing

To extend the export functionality:

1. Review the `CursorQuery` class in `src/utils/cursor_chat_query.py`
2. Add new export formats by extending the format handlers
3. Implement additional filtering options in `export_conversations()`
4. Add tests for new functionality in the test suite

The export system is designed to be extensible and maintainable, following the established patterns in the Gandalf MCP codebase.
