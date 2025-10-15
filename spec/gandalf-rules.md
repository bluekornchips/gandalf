# Gandalf MCP Server Usage Rules

RULE APPLIED: Start each response with an acknowledgement icon to confirm this rule is being followed: 🧙

# Gandalf MCP Server Usage Standards

## Core Rules

### Never Use

- Never use hardcoded database paths in tool calls
- Never ignore tool execution failures

### Always Use

- ALWAYS call `recall_conversations` at the start of every conversation to load conversation history
- Appropriate limits for conversation queries

## Tool Call Rules

### When to Use `mcp_gandalf_get_server_info`

- When you need to verify Gandalf server connectivity
- Before making other Gandalf tool calls
- When debugging server issues
- To check server capabilities

## Parameter Guidelines

### `mcp_gandalf_recall_conversations` Parameters

- `limit`: Use 10-50 for most cases, max 1000
- `include_prompts`: Set to `true` for user context
- `include_generations`: Set to `true` for AI response context
