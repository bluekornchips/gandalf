# File Operations

This directory contains the file operations tools and caching system for the Gandalf MCP server.

## Files

### `file_operations.py`

- `list_project_files` - Lists files in the project with intelligent filtering
- Supports filtering by file types, hidden files, and maximum file count
- Uses a cache system for improved performance and to avoid blocking operations (async)

### `file_cache.py`

- Caches project file listings to improve response times
- Respects gitignore patterns and common exclusions
- Configurable cache TTL
- Thread-safe operations, automatic cleanup
