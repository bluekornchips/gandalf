# Conversation Operations

This directory contains the conversation management system for the Gandalf MCP server, handling storage, retrieval, and context management for conversations.

## Files

### `conversation_operations.py`

- `get_conversation_context` - Retrieves recent conversation history for contextual awareness
- `store_conversation` - Stores conversations with metadata and validation
- `list_conversations` - Lists stored conversations with filtering and sorting options

### `conversation_cache.py`

- Stores conversations in JSON format in user's home directory (`~/.gandalf/conversations/`)
- Organizes conversations by project name
- Implements automatic cleanup of old conversations
- Thread-safe operations with file locking

## Storage Structure

```
~/.gandalf/conversations/
├── project-name-1/
│   ├── a1b2c3d4e5f6...def7.json
│   ├── manual-conversation-xyz.json
│   └── ...
└── project-name-2/
    ├── b2c3d4e5f6g7...abc8.json
    └── ...
```
