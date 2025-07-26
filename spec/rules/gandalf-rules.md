---
description: Enhanced Gandalf MCP Server Rules with Performance Optimization and Smart Workflows
globs:
alwaysApply: true
---

# Gandalf MCP Server Rules

**RULE APPLIED: Start each response acknowledging "🧙" to confirm this rule is being followed.**

Names and phrases that reference this rule: "🧙", "gandalf", "mcp", "conversation recall", "project context", "troubleshooting"

## Section 1: Core Workflows (Always Active)

### Essential Context Discovery Pattern

Every interaction should begin with context establishment:

```bash
# Primary workflow - always begin here
recall_conversations(
    fast_mode=true,
    days_lookback=7,
    limit=20,
    min_relevance_score=0.0
)
```

### Decision Tree Framework

```
New problem or query?
├── Yes → recall_conversations(search_query="relevant keywords", conversation_types=["debugging", "problem_solving"])
└── No → Use existing context

Need project understanding?
├── Yes → get_project_info(include_stats=true)
└── No → Proceed with current knowledge

Multiple files involved?
├── Yes → list_project_files(use_relevance_scoring=true, max_files=optimal_limit)
└── No → Focus on current file context
```

### Standardized Parameter Templates

#### Template 1: Basic Context Recall

```bash
recall_conversations(
    fast_mode=true,           # Performance optimization
    days_lookback=7,          # Temporal scope
    limit=20,                 # Result count
    min_relevance_score=0.0   # Quality threshold
)
```

#### Template 2: Targeted Problem Search

```bash
recall_conversations(
    search_query="authentication bug",
    conversation_types=["debugging", "problem_solving"],
    tools=["cursor", "claude-code"],
    days_lookback=14,
    limit=30,
    min_relevance_score=1.0
)
```

#### Template 3: Architecture & Planning Context

```bash
recall_conversations(
    conversation_types=["architecture", "technical"],
    days_lookback=30,
    limit=40,
    min_relevance_score=0.5
)
```

#### Template 4: Project Analysis

```bash
# Auto-scaling based on project size
get_project_info(include_stats=true)
list_project_files(
    max_files=calculate_optimal_limit(),
    file_types=get_relevant_extensions(),
    use_relevance_scoring=true
)
```

## Section 2: Advanced Operations

### Multi-Tool Coordination

```bash
# Cross-tool conversation analysis
recall_conversations(
    tools=["cursor", "claude-code", "windsurf"],
    fast_mode=true,
    limit=25
)

# Export insights for documentation
export_individual_conversations(
    format="md",
    limit=20,
    output_dir="~/.gandalf/exports/$(date +%Y-%m-%d)"
)
```

### Large Project Handling

```bash
# Enterprise-scale projects (1000+ files)
list_project_files(
    max_files=30,
    file_types=[".py", ".js", ".ts"],
    use_relevance_scoring=true
)

recall_conversations(
    fast_mode=true,
    limit=10,
    min_relevance_score=1.0
)
```

### Cross-Conversation Analysis

```bash
# Knowledge building workflow
recall_conversations(
    search_query="API patterns",
    conversation_types=["technical", "code_discussion"],
    days_lookback=30
)
```

## Section 3: Performance Optimization

### Auto-Scaling Parameter Matrix

| Project Size   | Files    | Conversation Params                       | File List Params                    |
| -------------- | -------- | ----------------------------------------- | ----------------------------------- |
| **Tiny**       | <25      | `fast_mode=false, limit=50`               | `max_files=25`                      |
| **Small**      | 25-100   | `fast_mode=true, limit=30`                | `max_files=50`                      |
| **Medium**     | 100-500  | `fast_mode=true, limit=20`                | `max_files=100, file_types=['.py']` |
| **Large**      | 500-1000 | `fast_mode=true, limit=15`                | `max_files=50, file_types=['.py']`  |
| **Enterprise** | 1000+    | `fast_mode=true, limit=10, min_score=1.0` | `max_files=30, file_types=['.py']`  |

### Response Time Targets

| Operation                 | Target | Optimization Strategy    |
| ------------------------- | ------ | ------------------------ |
| Conversation aggregation  | <50ms  | Enable `fast_mode=true`  |
| File listing (1000 files) | <100ms | Use `file_types` filter  |
| Project analysis          | <200ms | Reduce `max_files` to 50 |
| Cross-tool search         | <300ms | Limit to single tool     |

### Context-Aware Workflow Selection

```bash
# Debugging session detection
if context_indicates_debugging:
    recall_conversations(
        conversation_types=["debugging", "problem_solving"],
        min_relevance_score=1.5,
        days_lookback=7,
        limit=20
    )

# Architecture planning detection
elif context_indicates_architecture:
    recall_conversations(
        conversation_types=["architecture", "technical"],
        days_lookback=30,
        limit=40
    )

# Default exploration
else:
    recall_conversations(fast_mode=true, limit=20)
```

### Dynamic Parameter Calculation

```python
# Smart parameter selection based on project analysis
project_info = get_project_info(include_stats=true)

if project_info.file_count < 50:
    params = {"max_files": project_info.file_count}
elif project_info.file_count < 500:
    params = {"max_files": 100, "fast_mode": True}
else:
    params = {
        "max_files": 50,
        "file_types": [".py", ".js", ".ts"],
        "fast_mode": True
    }
```

## Section 4: Error Recovery (Smart Activation)

### Quick Diagnostic Matrix

| Problem               | Immediate Action                       | CLI Command                 |
| --------------------- | -------------------------------------- | --------------------------- |
| Tools not appearing   | Restart IDE                            | `./gandalf install --force` |
| Server not responding | Check connectivity                     | `./gandalf test`            |
| Empty results         | Lower relevance threshold, extend days | N/A (parameter adjust)      |
| Slow performance      | Enable fast mode, reduce limits        | N/A (parameter adjust)      |

### Progressive Degradation Strategy

#### Level 1: Parameter Optimization

```bash
# Reduce computational load
recall_conversations(
    fast_mode=true,
    limit=20,  # Reduced from default 50
    min_relevance_score=0.5
)
```

#### Level 2: Scope Reduction

```bash
# Narrow temporal and tool scope
recall_conversations(
    days_lookback=7,  # Reduced from 30
    tools=["cursor"],  # Single tool only
    limit=15
)

list_project_files(
    max_files=30,  # Reduced from 100
    file_types=[".py"]  # Essential files only
)
```

#### Level 3: Emergency Mode

```bash
# Minimal viable operation
recall_conversations(
    fast_mode=true,
    limit=10,
    days_lookback=3
)

list_project_files(max_files=20)
```

#### Level 4: Fallback Operation

```bash
# Cache-only responses, no discovery
get_project_info(include_stats=false)
# Skip file listing and conversation recall
```

### Modern Recovery Commands

```bash
# Updated diagnostic sequence (current CLI interface)
./gandalf test                    # Basic connectivity test
get_server_version()             # Confirm MCP connection
get_project_info()               # Verify project access

# Full reset if needed
./gandalf install --force        # Clean installation
./gandalf test install           # Verify installation
```

### Smart Activation Triggers

The error recovery system activates automatically when:

- Response time > 5 seconds → Enable `fast_mode=true`
- Empty results returned → Lower `min_relevance_score` to 0.1
- Connection timeout → Execute restart sequence
- Tool not found error → Update available tools list

### Performance Recovery Workflow

```bash
# Performance troubleshooting sequence
1. recall_conversations(fast_mode=true, limit=15)
2. If still slow: reduce days_lookback to 3
3. If still slow: limit to single tool
4. If still slow: emergency mode parameters
5. Final fallback: get_project_info() only
```

### Enhanced Empty Results Recovery

```bash
# Multi-stage empty results recovery
1. recall_conversations(min_relevance_score=0.1, days_lookback=30)
2. If empty: try different conversation_types=["technical", "general"]
3. If empty: extend to tools=["cursor", "claude-code", "windsurf"]
4. If empty: get_project_info() to verify tool availability
5. Final step: manual context rebuild guidance
```

## Section 5: Best Practices Integration

### Workflow Strategy

1. **Start broad**: Use default parameters first
2. **Context-aware**: Adapt parameters based on query type
3. **Performance-first**: Monitor response times and adjust
4. **Graceful degradation**: Have fallback strategies ready
5. **Document insights**: Export important conversations

### File Discovery Optimization

1. **Use relevance scoring**: Always enable `use_relevance_scoring=true`
2. **Filter by extension**: Focus on relevant file types for the task
3. **Scale with project size**: Use appropriate `max_files` limits
4. **Monitor performance**: Adjust parameters if operations are slow

### Context Building Guidelines

1. **Temporal relevance**: Start with recent conversations (7 days)
2. **Query specificity**: Use targeted search terms when possible
3. **Type filtering**: Leverage `conversation_types` for focused results
4. **Tool awareness**: Consider which tools contain relevant context

## Section 6: Troubleshooting Reference

### Connection Issues

```bash
# Server connectivity problems
./gandalf run --debug          # Debug mode startup
./gandalf test                 # Basic connectivity test
get_server_version()          # Verify MCP protocol
```

### Performance Issues

```bash
# When operations are slow
recall_conversations(fast_mode=true, limit=10)
list_project_files(max_files=30, file_types=[".py"])
```

### Cache and Storage Issues

```bash
# When experiencing data inconsistencies
get_project_info(include_stats=true)  # Verify project access
# Note: Cache clearing now handled internally by server
```

### Integration Validation

```bash
# Verify all systems working
./gandalf test install         # Complete system verification
get_project_info()            # Project access test
recall_conversations(limit=5)  # Basic functionality test
```

This rule system provides comprehensive guidance for all Gandalf MCP Server operations while maintaining performance optimization and intelligent error recovery capabilities.
