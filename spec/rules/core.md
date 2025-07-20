---
description: Enhanced Gandalf MCP Server Rules with Performance Optimization and Advanced Workflows
globs:
alwaysApply: true
---

# Gandalf Rules Applied

**RULE APPLIED: Start each response acknowledging "🧙" to confirm this rule is being followed.**

Names and phrases that reference this rule: "🧙", "gandalf", "mcp", "conversation recall", "project context"

# Core Workflows and Decision Trees

## Essential Workflow

### 1. Always Start with Context

```bash
# Primary workflow - always begin here
recall_conversations(fast_mode=true, days_lookback=7)
```

### 2. Project Discovery

```bash
# For unfamiliar projects
get_project_info(include_stats=true)

# For multi-file operations
list_project_files(max_files=50, file_types=['.py', '.js'])
```

### 3. Decision Tree

```
New problem?
├── Yes → recall_conversations(search_query="similar issue")
└── No → Continue with known solution

Need project context?
├── Yes → get_project_info()
└── No → Proceed

Multiple files involved?
├── Yes → list_project_files(use_relevance_scoring=true)
└── No → Focus on current file
```

## Performance Optimization

### Project Size Guidelines

| Project Size   | Files          | Optimization Strategy | Example Parameters                                  |
| -------------- | -------------- | --------------------- | --------------------------------------------------- |
| **Tiny**       | <25 files      | Full analysis         | `max_files=25`                                      |
| **Small**      | 25-100 files   | Standard mode         | `max_files=50`                                      |
| **Medium**     | 100-500 files  | Fast mode + filters   | `max_files=100, fast_mode=true`                     |
| **Large**      | 500-1000 files | Type filtering        | `max_files=200, file_types=['.py', '.js']`          |
| **Enterprise** | 1000+ files    | Aggressive filtering  | `max_files=100, file_types=['.py'], fast_mode=true` |

### Response Time Targets

| Operation                 | Target | Fallback Strategy           |
| ------------------------- | ------ | --------------------------- |
| Conversation aggregation  | <50ms  | Reduce `days_lookback` to 3 |
| File listing (1000 files) | <100ms | Use `file_types` filter     |
| Project analysis          | <200ms | Enable `fast_mode=true`     |
| Cross-tool search         | <300ms | Limit to single tool        |

### Smart Parameter Selection

```python
# Auto-adjust based on project size
if file_count < 50:
    params = {"max_files": file_count}
elif file_count < 500:
    params = {"max_files": 100, "fast_mode": True}
else:
    params = {"max_files": 50, "file_types": [".py", ".js", ".ts"], "fast_mode": True}
```

## Advanced Workflows

### Comprehensive Context Discovery

```bash
# Step 1: Get recent context
recall_conversations(fast_mode=true, days_lookback=7, limit=20)

# Step 2: Project overview
get_project_info(include_stats=true)

# Step 3: Relevant files
list_project_files(max_files=50, use_relevance_scoring=true)
```

### Problem-Solving Workflow

```bash
# Search for similar issues
recall_conversations(
    search_query="error message keywords",
    conversation_types=["debugging", "problem_solving"],
    days_lookback=14
)

# Find related code
list_project_files(
    file_types=[".py", ".js", ".ts"],
    max_files=30
)
```

### Documentation & Knowledge Building

```bash
# Research patterns
recall_conversations(
    search_query="API documentation",
    conversation_types=["technical", "code_discussion"]
)

# Export for reference
export_individual_conversations(
    format="md",
    limit=25,
    output_dir="~/.gandalf/exports/$(date +%Y-%m-%d)"
)
```

### Performance Analysis

```bash
# Fast discovery for large projects
recall_conversations(fast_mode=true, limit=15, min_score=2.0)
list_project_files(max_files=30, file_types=[".py"])
```

## Best Practices

### Context Strategy

1. Start broad: Use default parameters first
2. Narrow down: Add filters based on initial results
3. Iterate: Refine search terms and filters
4. Document: Export important conversations

### Error Recovery

1. Graceful degradation: Reduce parameters on failure
2. Fallback options: Have alternative approaches ready
3. User feedback: Provide clear error messages
4. Recovery paths: Guide users to working solutions

### File Discovery

1. Use relevance scoring: `use_relevance_scoring=true`
2. Filter by extension: Focus on relevant file types
3. Limit scope: Use appropriate max_files for project size
4. Monitor performance: Adjust parameters if slow
