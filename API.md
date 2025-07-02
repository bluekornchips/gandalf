# API Reference

Gandalf MCP server provides **6 essential tools** for intelligent code assistance in **Cursor IDE** and **Claude Code**. Tools automatically adapt based on your environment.

## Essential Workflow

**ALWAYS start with conversation history:**

```bash
recall_conversations(fast_mode=true)
```

Then use other tools based on need:

- **Unfamiliar project?** → `get_project_info()`
- **Multi-file work?** → `list_project_files()` with file types
- **Looking for past solutions?** → `search_conversations()` with keywords
- **MCP issues?** → `get_server_version()`

## The 6 Tools

### **Conversation Intelligence**

#### `recall_conversations`

**PRIMARY TOOL**: Get recent relevant conversations across all development tools.

**Key Parameters**:

- `fast_mode` (default: true): Quick extraction vs comprehensive analysis
- `days_lookback` (default: 7): Days to search back
- `limit` (default: 20): Max conversations per tool

**Usage**:

```bash
recall_conversations(fast_mode=true, limit=10)
```

#### `search_conversations`

Search conversation history for specific topics or keywords.

**Key Parameters**:

- `query` (required): Search query string
- `days_lookback` (default: 30): Search timeframe
- `limit` (default: 20): Max results per tool

**Usage**:

```bash
search_conversations(query="authentication bug fix", days_lookback=14)
```

### **Project Context**

#### `get_project_info`

Get project metadata, Git status, and file statistics.

**Parameters**:

- `include_stats` (default: true): Include file count statistics

**Usage**:

```bash
get_project_info()
```

#### `list_project_files`

Discover project structure with intelligent relevance scoring.

**Key Parameters**:

- `file_types` (optional): Filter by extensions like `[".py", ".js"]`
- `max_files` (default: 1000): Maximum files to return
- `use_relevance_scoring` (default: true): Enable smart prioritization

**Usage**:

```bash
list_project_files(file_types=[".py", ".js"], max_files=50)
```

### **System & Export**

#### `get_server_version`

Get server version and protocol information.

**Usage**:

```bash
get_server_version()
```

#### `export_individual_conversations`

Export conversations to files for backup or analysis.

**Key Parameters**:

- `format` (default: json): Export format (json, md, txt)
- `limit` (default: 20): Max conversations to export
- `output_dir` (optional): Export directory

**Usage**:

```bash
export_individual_conversations(format="md", limit=10)
```

## Performance Guidelines

### **Project Size Optimization**

- **Small projects (<50 files)**: `max_files=50`, full features
- **Medium projects (50-500 files)**: `max_files=100`, `fast_mode=true`
- **Large projects (500+ files)**: `max_files=50`, specific `file_types`

### **Best Practices**

- Always use `fast_mode=true` for recall (default)
- Limit `max_files` based on actual need
- Use specific `file_types` to reduce noise
- Don't gather context you won't use

## Response Formats

All tools return consistent JSON with:

- **Status**: Success/error information
- **Data**: Requested information
- **Metadata**: Processing time, relevance scores, source info

## Architecture

- **Current**: 6 essential tools with intelligent aggregation
- **Previous**: 14 tools with overlapping functionality
- **Benefits**: 57% faster loading, reduced complexity, easier maintenance

## Tool Detection

Gandalf automatically detects your environment:

1. **Primary Tool Detection**: Identifies main development environment
2. **Cross-Platform Support**: Unified access across Cursor IDE and Claude Code
3. **Dynamic Availability**: Tools adapt based on installation and configuration

## Error Handling

**Common Solutions**:

- **Tool fails**: Try alternative approaches (e.g., `list_project_files` if `get_project_info` fails)
- **Performance issues**: Reduce scope with `fast_mode=true`, smaller `max_files`
- **MCP issues**: Check `get_server_version()` for compatibility

## Example Workflows

### **Starting New Work**

```bash
# 1. Always start here
recall_conversations(fast_mode=true)

# 2. If unfamiliar project
get_project_info()

# 3. If multi-file work
list_project_files(file_types=["py", "ts"], max_files=50)
```

### **Finding Past Solutions**

```bash
# 1. Check recent context
recall_conversations(fast_mode=true, days_lookback=14)

# 2. Search for specific topics
search_conversations(query="authentication patterns")
```

### **Troubleshooting**

```bash
# Check MCP status
get_server_version()

# Export conversations for analysis
export_individual_conversations(format="json", limit=5)
```
