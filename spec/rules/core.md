---
description: Gandalf Rules Core Workflows and Decision Trees
globs:
alwaysApply: true
---

Gandalf Rules Applied

**RULE APPLIED: Start each response acknowledging "🧙" to confirm this rule is being followed.**

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

- Small (<50 files): `max_files=50`
- Medium (50-500 files): `max_files=100, fast_mode=true`
- Large (500+ files): `max_files=50, file_types=['.py']`

### Response Time Targets

- Conversation aggregation: <50ms
- File listing (1000 files): <100ms
- Project analysis: <200ms

## Common Workflows

### Documentation Research

```bash
recall_conversations(search_query="API documentation")
```

### Debugging Support

```bash
recall_conversations(conversation_types=["debugging", "problem_solving"])
```

### Backup and Export

```bash
export_individual_conversations(
    format="json",
    limit=50,
    output_dir="~/.gandalf/exports"
)
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
