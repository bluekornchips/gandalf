---
description:
globs:
alwaysApply: true
---

# Gandalf MCP Rules

**Core Principle:** Gather context before making changes using intelligent conversation analysis and project awareness.

## CRITICAL: MCP Context Gathering Protocol

**REQUIRED WORKFLOW:**

1. **FIRST ACTION**: Use MCP tools to gather relevant context from conversations and project state
2. **WORK PHASE**: Apply context intelligence to understand project structure and make informed decisions
3. **FINAL ACTION**: Leverage conversation insights to provide comprehensive solutions

**Why This Matters:**

- Preserves valuable debugging sessions and architectural decisions from IDE history
- Enables intelligent project analysis with relevance scoring and context awareness
- Maintains continuity across sessions through conversation recall
- Creates searchable knowledge base of solutions and patterns

## IDE Environment Detection

**Gandalf automatically detects your IDE environment** and adapts its functionality accordingly.

### Supported IDEs

- **Cursor IDE** - Full conversation history, workspace detection, and chat integration
- **Claude Code** - Project analysis, file intelligence, and conversation support

### Dynamic Conversation Tool Detection

The system uses intelligent runtime detection to automatically provide conversation tools based on your environment:

**Automatic Detection Process:**

1. **Primary IDE Detection**: Detects your current IDE based on environment variables, processes, and configuration
2. **Tool Loading**: Loads conversation tools for the detected primary IDE (no prefix)
3. **Secondary IDE Detection**: Checks for other available IDEs and loads their tools with prefixes
4. **Dynamic Availability**: Tools become available automatically based on what's actually installed and configured

**Environment Detection Indicators:**

**Cursor Detection:**
- Environment variables: `CURSOR_TRACE_ID`, `VSCODE_INJECTION=1`
- Process detection: Running Cursor processes
- Application paths: `/Applications/Cursor.app` and related VSCode infrastructure
- Data directories: `~/Library/Application Support/Cursor`

**Claude Code Detection:**
- Environment variables: `CLAUDECODE=1`, `CLAUDE_CODE_ENTRYPOINT=cli`
- Process detection: Running Claude processes
- Configuration: `~/.claude`, `~/.config/claude` directories
- Context indicators: `.claude` files in project directories

### Tool Naming Convention

**Primary IDE Tools (no prefix):**
- Tools from your detected primary IDE have standard names
- Example: `recall_cursor_conversations`, `query_claude_conversations`

**Secondary IDE Tools (with prefix):**
- Tools from other available IDEs get prefixed with the IDE name
- Example: `cursor_recall_cursor_conversations`, `claude_code_query_claude_conversations`

### Verifying Your Environment

To check which tools are available, use the `tools/list` MCP command. The available conversation tools will indicate:
- Your primary IDE environment
- Any secondary IDE tools that were detected
- The total conversation tools available

**Expected tool patterns:**

- **Cursor Primary**: `recall_cursor_conversations`, `query_cursor_conversations` + potential `claude_code_*` tools
- **Claude Code Primary**: `recall_claude_conversations`, `query_claude_conversations` + potential `cursor_*` tools

### Fallback Behavior

When no IDE is clearly detected:

1. Checks `GANDALF_FALLBACK_IDE` environment variable
2. Scores environment hints for each IDE
3. Defaults to Claude Code if scores are equal
4. All core functionality remains available regardless of detection

## When to Use MCP Tools

**Always use for:**

- Understanding unfamiliar codebases or projects
- Complex refactoring or architectural changes
- Debugging issues without clear root cause
- Building on previous work or established patterns
- Analyzing conversation history for relevant context

**Use when helpful:**

- Writing documentation or explanations
- Making decisions that affect multiple files/components
- Reviewing or validating approach before implementation
- Finding patterns in past conversations

**Never execute, unless explicitly told to do so by the user:**

- git commands that alter state
- commands that alter files outside of the project root

## Version Awareness

**Check server version when:**

- Starting a new conversation or session
- User reports unexpected behavior or errors
- Before making significant changes to the project
- When troubleshooting MCP-related issues

**Use `get_server_version` to:**

- Verify you're working with the expected Gandalf version
- Include version info in debugging or error reports
- Ensure compatibility when suggesting features or tools

**Version checking workflow:**

1. Call `get_server_version` early in conversations
2. Current expected version: `2.0.0` (as of June 26, 2025)
3. If version seems outdated or unexpected, suggest: `gandalf install -r`
4. Do not proceed with complex operations if version mismatch detected
5. Include version info when reporting issues or unexpected behavior

**Version-specific considerations:**

- Version `2.0.0` includes all conversation tools and export functionality
- Versions below `1.1.0` may have limited conversation export capabilities
- Always verify tool availability if working with older versions

## Context Gathering Strategy

### Phase 1: Project Intelligence

1. **Start with project state:** `get_project_info` for metadata, git status, and statistics
2. **Understand file structure:** `list_project_files` with intelligent relevance scoring
   - Use file type filtering (e.g., `['.py', '.js']`) when working on specific languages
   - Enable `use_relevance_scoring: true` for intelligent prioritization
   - Adjust `max_files` based on project size (20-50 for focused work, 100+ for exploration)

### Phase 2: Conversation Intelligence

3. **Recall relevant conversations:** `recall_claude_conversations` with smart caching for recent context

   - Use `fast_mode: true` for quick context gathering (recommended)
   - Set `days_lookback` to focus on recent conversations (default: 7 days)
   - Filter by `conversation_types` for specific contexts when needed

4. **Query specific context:** `search_claude_conversations` for targeted searches
   - Search for specific keywords, technologies, or problem patterns
   - Use `include_content: true` when you need conversation snippets
   - Limit results appropriately for focused analysis

### Phase 3: IDE Integration

5. **Access IDE chat history:** `query_claude_conversations` for comprehensive conversation data
   - Use `summary: true` for quick overview of available conversations
   - Choose appropriate format based on your IDE
   - Access workspace-specific conversation history

## Enhanced Conversation Management

### Conversation Recall Guidelines

**Fast Mode (Recommended):**

- Ultra-fast conversation extraction in seconds
- Focuses on recent conversations (default 7 days)
- Minimal processing overhead
- Ideal for quick context gathering

**Enhanced Mode:**

- Comprehensive analysis with relevance scoring
- Intelligent keyword matching and context analysis
- Detailed conversation categorization
- Smart caching for performance optimization

**Conversation Types Available:**

- `architecture` - Design and structural discussions
- `debugging` - Problem-solving and error resolution
- `problem_solving` - General troubleshooting
- `code_discussion` - Code review and implementation
- `technical` - Technical knowledge and patterns
- `general` - General conversations

### Context Intelligence Features

**Intelligent File Scoring:**

- Multi-factor relevance analysis
- Git activity tracking
- File size optimization
- Directory importance weighting
- Recent modification scoring

**Conversation Analysis:**

- Keyword matching with project awareness
- File reference detection
- Recency scoring with time decay
- Pattern recognition for conversation types
- Smart caching with TTL management

## File Operations Best Practices

**Use `list_project_files` for:**

- Understanding project structure and architecture
- Finding relevant files before making changes
- Discovering patterns and conventions
- Identifying configuration files, tests, documentation

**Key parameters:**

- `file_types`: Filter by extensions (e.g., `['.py', '.md', '.json']`)
- `use_relevance_scoring: true`: Get intelligent prioritization
- `max_files`: Start with 50, increase if needed (max 10000)

**Example usage patterns:**

```
# Understand Python project structure
list_project_files(file_types=['.py'], max_files=50, use_relevance_scoring=true)

# Find all configuration files
list_project_files(file_types=['.json', '.yaml', '.toml', '.ini'], max_files=30)

# Get full project overview with intelligent scoring
list_project_files(max_files=100, use_relevance_scoring=true)
```

## Available Tools

### Project & File Operations

- `get_project_info` - Project metadata, Git info, and file statistics (fast shell-based)
- `get_server_version` - Get current server version and protocol information
- `list_project_files` - Discover project structure with intelligent prioritization and relevance scoring

### Conversation Intelligence

- `recall_claude_conversations` - **PRIMARY**: Analyze and recall relevant conversations with smart caching (defaults to 7 days)
- `search_claude_conversations` - Search conversations for specific topics, keywords, or context
- `search_claude_conversations_enhanced` - Enhanced search with context analysis and time filtering

### IDE Integration

- `query_claude_conversations` - Query conversations from IDE databases for AI context analysis
- `export_individual_conversations` - Export conversations to separate files for analysis or backup

**Note:** Tool availability may vary based on detected IDE environment. Cursor-specific tools are available when running in Cursor IDE.

## Priority Order

1. **Project overview**: `get_project_info` for basic context and git status
2. **File structure**: `list_project_files` with intelligent scoring for project understanding
3. **Conversation context**: `recall_claude_conversations` in fast mode for recent relevant discussions
4. **Targeted search**: `search_claude_conversations` for specific past work or solutions
5. **IDE integration**: `query_claude_conversations` when direct IDE history access is needed
6. **Export conversations**: `export_individual_conversations` for backing up important discussions
7. **[Complete the requested work with full context]**

## Context Intelligence Features

### File Relevance Scoring

- **High Priority** (score >= 0.8): Recently modified, optimal size, important file types
- **Medium Priority** (0.5 <= score < 0.8): Moderately relevant files
- **Low Priority** (score < 0.5): Less relevant but still accessible files

### Conversation Analysis

- **Smart Caching**: TTL-based caching with project state validation
- **Keyword Generation**: Intelligent project-aware keyword extraction
- **Pattern Recognition**: Automatic conversation type classification
- **Relevance Scoring**: Multi-factor analysis for conversation importance

### Performance Optimization

- **Fast Mode**: Ultra-fast conversation extraction (seconds)
- **Enhanced Mode**: Comprehensive analysis with caching (minutes)
- **Intelligent Filtering**: Early termination and batch processing
- **Security Validation**: Path validation and content sanitization

### Cache Strategy

- **Conversation Cache**: 1-hour TTL with project state validation
- **Context Keywords**: Cached per project with smart invalidation
- **File Lists**: Leveraged from existing project scans when available
- **Cache Warming**: Automatic on first tool usage per session

### Performance Guidelines by Project Size

**Small Projects (< 50 files):**

- Use `max_files: 50` for complete overview
- Enable all scoring features
- Use enhanced mode for comprehensive analysis

**Medium Projects (50-500 files):**

- Use `max_files: 100` for focused work, `200` for exploration
- Prioritize `fast_mode: true` for conversation recall
- Filter by `file_types` when working on specific technologies

**Large Projects (500+ files):**

- Start with `max_files: 50`, increase incrementally as needed
- Always use `fast_mode: true` for initial context gathering
- Use targeted `file_types` filtering to reduce scope
- Consider `days_lookback: 3-5` for recent focus

### Memory Optimization

- Limit conversation recall to `limit: 20` for routine work
- Use `limit: 50+` only for comprehensive research
- Clear cache with `gandalf install -r` if performance degrades
- Monitor cache size; rebuild if > 10MB

## Best Practices

### Conversation Recall

- Use `fast_mode: true` for quick context gathering (recommended default)
- Set appropriate `days_lookback` (default 7 days for recent focus)
- Limit results with sensible `limit` values (default 20)
- Filter by `conversation_types` when looking for specific contexts
- Use enhanced mode only for deep analysis or research tasks

### File Operations

- Always use `use_relevance_scoring: true` for intelligent file prioritization
- Filter by `file_types` when working with specific technologies
- Start with smaller `max_files` values and increase as needed
- Leverage cached file lists for performance optimization

### Conversation Management

- Use `export_individual_conversations` for backing up important discussions
- Export in `json` format for programmatic analysis, `markdown` for human reading
- Consider conversation exports before major refactoring sessions
- Search conversations before starting similar work to avoid duplication

### Context Optimization

- Leverage caching mechanisms for repeated operations
- Use summary modes when full data isn't needed
- Prefer fast modes for initial context gathering
- Apply appropriate limits to prevent resource exhaustion
- Combine multiple tool calls for comprehensive context when needed

## Summary Workflow

```
1. User sends message with request
2. get_project_info() to understand project context
3. list_project_files() with relevance scoring for structure
4. recall_claude_conversations(fast_mode=true) for recent context
5. search_claude_conversations() for specific searches if needed
6. export_individual_conversations() for important discussion backup (optional)
7. Apply gathered context to complete the requested work
```

This workflow ensures comprehensive context gathering while maintaining performance and leveraging the intelligent features of the Gandalf MCP system.
