# Core

This directory contains the core logic of the Gandalf MCP server.

## Modules

**`context_intelligence.py`** - File relevance scoring and prioritization  
**`conversation_storage.py`** - Conversation caching and retrieval  
**`file_scoring.py`** - File discovery and scoring algorithms  
**`git_activity.py`** - Git repository analysis  
**`server.py`** - MCP server implementation  
**`ignored_files.py`** - File filtering logic

## Architecture

Core modules handle business logic; `src/tool_calls/` handles MCP protocol.

```python
# Tool calls layer imports from core
from src.core.context_intelligence import get_context_intelligence
from src.core.conversation_storage import load_stored_conversations
from src.core.file_scoring import get_files_with_scores, get_files_list
from src.core.git_activity import GitActivityTracker
```
