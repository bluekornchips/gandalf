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

- Preserves valuable debugging sessions and architectural decisions from Cursor IDE history
- Enables intelligent project analysis with relevance scoring and context awareness
- Maintains continuity across sessions through conversation ingestion
- Creates searchable knowledge base of solutions and patterns

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

## Context Gathering Strategy

### Phase 1: Project Intelligence

1. **Start with project state:** `get_project_info` for metadata, git status, and statistics
2. **Understand file structure:** `list_project_files` with intelligent relevance scoring
   - Use file type filtering (e.g., `['.py', '.js']`) when working on specific languages
   - Enable `use_relevance_scoring: true` for intelligent prioritization
   - Adjust `max_files` based on project size (20-50 for focused work, 100+ for exploration)

### Phase 2: Conversation Intelligence

3. **Ingest relevant conversations:** `ingest_conversations` with smart caching for recent context
   - Use `fast_mode: true` for quick context gathering (recommended)
   - Set `days_lookback` to focus on recent conversations (default: 7 days)
   - Filter by `conversation_types` for specific contexts when needed

4. **Query specific context:** `query_conversation_context` for targeted searches
   - Search for specific keywords, technologies, or problem patterns
   - Use `include_content: true` when you need conversation snippets
   - Limit results appropriately for focused analysis

### Phase 3: Cursor IDE Integration

5. **Access Cursor chat history:** `query_cursor_conversations` for comprehensive conversation data
   - Use `summary: true` for quick overview of available conversations
   - Choose appropriate format: `cursor`, `markdown`, or `json`
   - List available workspaces with `list_cursor_workspaces`

## Enhanced Conversation Management

### Conversation Ingestion Guidelines

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
- `list_project_files` - Discover project structure with intelligent prioritization and relevance scoring

### Conversation Intelligence
- `ingest_conversations` - **PRIMARY**: Analyze and ingest relevant conversations with smart caching (defaults to 7 days)
- `query_conversation_context` - Search conversations for specific topics, keywords, or context

### Cursor IDE Integration
- `query_cursor_conversations` - Query conversations from Cursor IDE databases for AI context analysis
- `list_cursor_workspaces` - List available Cursor workspace databases

## Priority Order

1. **Project overview**: `get_project_info` for basic context and git status
2. **File structure**: `list_project_files` with intelligent scoring for project understanding
3. **Conversation context**: `ingest_conversations` in fast mode for recent relevant discussions
4. **Targeted search**: `query_conversation_context` for specific past work or solutions
5. **Cursor integration**: `query_cursor_conversations` when direct IDE history access is needed
6. **[Complete the requested work with full context]**

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

## Best Practices

### Conversation Ingestion
- Use `fast_mode: true` for quick context gathering
- Set appropriate `days_lookback` (default 7 days for recent focus)
- Limit results with sensible `limit` values (default 20)
- Filter by `conversation_types` when looking for specific contexts

### File Operations
- Always use `use_relevance_scoring: true` for intelligent file prioritization
- Filter by `file_types` when working with specific technologies
- Start with smaller `max_files` values and increase as needed

### Performance
- Leverage caching mechanisms for repeated operations
- Use summary modes when full data isn't needed
- Prefer fast modes for initial context gathering
- Apply appropriate limits to prevent resource exhaustion

## Summary Workflow

```
1. User sends message with request
2. get_project_info() to understand project context
3. list_project_files() with relevance scoring for structure
4. ingest_conversations(fast_mode=true) for recent context
5. query_conversation_context() for specific searches if needed
6. Apply gathered context to complete the requested work
```

This workflow ensures comprehensive context gathering while maintaining performance and leveraging the intelligent features of the Gandalf MCP system.
