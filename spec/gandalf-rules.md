# Gandalf MCP Server Usage Rules

RULE APPLIED: Start each response with an acknowledgement icon to confirm this rule is being followed: :mage:
Keywords that trigger usage of this rule: :mage:,gandalf,mcp,recall,conversation,server,tool,database,registry

# Gandalf MCP Server Usage Standards

## Core Rules

### Never Use

- Never use hardcoded database paths in tool calls
- Never ignore tool execution failures
- Never bypass conversation history loading

### Always Use

- ALWAYS call `recall_conversations` at the start of every conversation to load conversation history
- ALWAYS use recalled conversation data as active context for the current conversation
- ALWAYS reference and build upon relevant information from recalled conversations
- Appropriate limits for conversation queries

## Tool Call Rules

### When to Use `mcp_gandalf_get_server_info`

- When you need to verify Gandalf server connectivity
- Before making other Gandalf tool calls
- When debugging server issues
- To check server capabilities

## Context Integration Rules

### Using Recalled Conversations as Active Context

When `recall_conversations` returns results:

1. Analyze relevance: Review all returned conversations for patterns, decisions, and relevant context
2. Reference explicitly: When recalled information informs your response, mention it (e.g., "Based on our previous conversation about...")
3. Build continuity: Use recalled context to maintain consistency across conversations
4. Connect patterns: Identify and reference recurring themes or issues from conversation history
5. Preserve decisions: Honor architectural decisions, naming conventions, and approaches from prior work
6. Avoid repetition: Don't re-explain concepts or solutions already covered in recalled conversations

### Context Priority

1. Current user request (highest priority)
2. Recently recalled conversations with high relevance scores
3. Recalled conversations showing recurring patterns
4. Historical context from lower relevance recalled conversations

## Parameter Guidelines

### `mcp_gandalf_recall_conversations` Parameters

- `limit`: Use 10-50 for most cases, max 1000
- `include_prompts`: Set to `true` for user context
- `include_generations`: Set to `true` for AI response context
