# Configuration Organization

Configuration management for Gandalf MCP server with separation of concerns.

## Key Concepts

**Gandalf Home** (`~/.gandalf`) - Server configuration, cache, and data files
**File System Context Root** - Top-level directory where MCP commands query from

## Structure

```
config/
├── constants/
│   ├── agentic.py              # Supported agentic tools
│   ├── cache.py                # Cache configuration
│   ├── context.py              # Context processing settings
│   ├── conversation.py         # Conversation patterns & analysis
│   ├── database.py             # Database queries & metadata
│   ├── file_system_context.py  # Context root detection
│   ├── limits.py               # Processing limits & timeouts
│   ├── paths.py                # Gandalf home and app data paths
│   ├── security.py             # Security & validation rules
│   └── server.py               # Server configuration
├── config_data.py              # Structured configuration data
├── enums.py                    # Configuration enums
├── schemas.py                  # Configuration schemas
├── validation.py               # Config validation logic
└── weights.py                  # Weights management
```

## Constants Files

### Core Configuration

- **`agentic.py`** - List of supported agentic tools (cursor, windsurf, claude-code)
- **`server.py`** - MCP server info, capabilities, and protocol version
- **`paths.py`** - Gandalf home directory, cache paths, and application storage locations

### Processing & Limits

- **`limits.py`** - Processing limits, timeouts, and performance constraints
- **`cache.py`** - Cache configuration, TTL settings, and size limits
- **`context.py`** - Context processing settings and intelligence parameters

### Security & Validation

- **`security.py`** - File extension blocking, path validation, and security rules
- **`file_system_context.py`** - Project root detection indicators and depth limits

### Data Processing

- **`database.py`** - SQL queries, table names, and database metadata
- **`conversation.py`** - Conversation analysis patterns, exclusions, and scoring thresholds
  - Comprehensive documentation for tech patterns, domain exclusions, and conversation types
  - Regex patterns for identifying technical discussions
  - Word exclusions to filter out non-technical content
