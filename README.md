# Gandalf

Gandalf is a Model Context Protocol for intelligent code assistance for your projects in Cursor. In the Lord of the Rings, Gandalf the Grey is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much an maiar can do; that's where we mortals come in.

In order for Gandalf to assist us, we provide him context in the form:

- Access and listing of all files and directories in a given project repository.
- Visibility into the current git status of the project.
- Conversation history with the AI assistant, as well as local storage of conversations.
- Recently used or edited files.

Although model dependent, with Gandalf we can provide a more comprehensive context to the AI assistant, allowing it to make more informed decisions and provide more accurate and helpful responses. Test it out with some complex commands and watch the conversation window show it use the tool calls to get incredible details and learn from its mistakes.

## What is a Model Context Protocol (MCP)?

"The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context and tools to LLMs. Think of MCP as a plugin system for Cursor - it allows you to extend the Agent's capabilities by connecting it to various data sources and tools through standardized interfaces." - [Source](https://www.cursor.com/blog/mcp-model-context-protocol)

## Key Features

- Smart Context Selection: Related files based on imports and dependencies
- Cursor Integration: Aware of current editing location, recent edits, and import relationships.
- Git Integration: Tracks repository status and changes
- Background Caching: Fast startup with persistent file caching
- Conversation Storage: Basic conversation history storage
- Allows fine tuning of context based on the current project and conversation history through weighting and filtering.

## Quick Start

```bash
# 1. One-time setup
gandalf setup

# 2. Configure for current repository
gandalf install

# 3. Test the installation
gandalf test

# 4. Restart Cursor, (optional)
```

## CLI Alias

For faster typing, add this alias to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
alias gdlf='/path/to/gandalf/gandalf'
```

## Commands

| Command                  | Purpose                      | Usage                                    |
| ------------------------ | ---------------------------- | ---------------------------------------- |
| `gandalf setup`          | Verify Python 3.10+ and Git  | Run once globally                        |
| `gandalf install [path]` | Configure repository for MCP | Run per repository                       |
| `gandalf test [path]`    | Run comprehensive test suite | Verify installation                      |
| `gandalf reset [server]` | Remove MCP configurations    | Clean reset                              |
| `gandalf run [path]`     | Start server manually        | Debugging only                           |
| `gandalf lembas [repo]`  | Complete validation workflow | Full test -> reset -> install -> test    |
| `gandalf conv store ID`  | Store conversation data      | Manual data storage                      |
| `gandalf conv list`      | List stored conversations    | Shows manual and auto-generated sessions |
| `gandalf conv show ID`   | Show conversation details    | View any stored conversation             |

## How It Works

### Server Architecture

Lightweight MCP server implementation:

- Modular code organization, simple and easy to understand.
- Type annotations for better type checking; I chose python because it's easier for everyone else to understand.
- No external dependencies - uses only Python 3.10+ standard library.

Each repository gets its own MCP server instance - no conflicts between projects.

The server is designed to be managed automatically by Cursor. For debugging, you can run it manually:

```bash
# Debug the server directly
python3 gandalf/server/main.py --project-root /path/to/project

# Or use the unified gandalf command
gandalf run --project-root /path/to/project
```

### Tools Available

These tool calls are available to the Gandalf and it makes the decision when to use them, or can be asked directly by the user.

- `list_project_files` - Lists relevant project files (filtered by gitignore)
- `get_project_info` - Returns project metadata and Git information
- `get_git_status` - Shows current Git repository status
- `get_conversation_context` - Get recent conversation history for context
- `store_conversation` - Store current conversation for future reference
- `list_conversations` - List recent conversations for this project

### Context Collection

- Open and recently edited files in Cursor
- Cursor position and recent edits
- Import relationships between files
- Git repository status
- Conversation history

### Custom Prioritization

Files scored by relevance. Default values are shown below, but can be edited in `weights.yaml`

- Active File (10.0): Currently editing, open files
- Import Neighbors (5.0): Files imported by/importing active file (modules, packages, etc.)
- Recent Edits (2.0): Recently modified files
- Cursor Activity (1.0): Recent cursor...stuff

### File Filtering

Excludes common patterns using [.gitignore](.gitignore)

- Python: `__pycache__`, `.pyc`, `.pyo` files
- Node.js: `node_modules`, cache directories
- Build: `dist`, `build`, `target` directories
- IDEs: `.vscode`, `.idea` directories
- System: `.DS_Store`, `Thumbs.db` files

### Auto-Conversation Tracking

The server automatically tracks tool usage sessions for debugging and context continuity with asynchronous storage:

- Session Creation: Creates unique sessions when MCP tools are called
- Session Format: `{16-character-hash}.json` stored in `~/.gandalf/conversations/project-name/`
- Short ID: First 9 characters for `gdlf conv show {short-id}`
- Meaningful Names: Auto-generated based on tool usage patterns:
  - Single tool: "List Project Files - 18:06"
  - Multiple tools: "Multi-tool Session (3 tools) - 14:32"
- Auto-Storage Triggers:
  - After 1 tool interaction (configurable via `AUTO_STORE_THRESHOLD`)
  - On server shutdown (ensures no data loss)
- Async Storage Benefits:
  - Low to zero latency impact on tool calls (~0.1ms vs 5-15ms for sync)
  - Thread-safe with locking mechanisms
  - Fallback protection to synchronous storage if thread creation fails
  - Immediate context preservation without performance penalty
- Behavior: Each save overwrites the same session file with accumulated messages
- Context Continuity: Keeps last 15 messages in memory between saves
- Configuration: `export AUTO_STORE_THRESHOLD=4` to change threshold

**Important**: Tool sessions are separate from chat conversations. Only MCP tool calls trigger auto-storage, not regular chat messages. (This is not something I want to support.)

For Gandalf, it is important to distinguish between conversations, sessions, messages, and tool calls:

- Message: A single exchange between the user and the assistant. This includes either a user prompt or the assistant's response.
- Conversation: A collection of messages that together form a logical dialogue between the user and the assistant.
- Session: A collection of tool calls associated with a user's interaction. Sessions are scoped around tool-level activities rather than conversational continuity.
- Tool Call: A discrete invocation (fancy way of saying calling a function) of an external tool (e.g., file search, web search, code execution) performed during a session. Tool calls may not have a 1:1 mapping with user messages.

Gandalf persists conversations, not sessions. This means while tool activity (sessions) occurs during runtime, there is no persistent linkage stored between tool calls and the encompassing conversation context. Tool calls are transient and tracked separately, without direct references to the user-visible message history.

Example output from `gandalf conv list`:

```
ID            Name                      Created
--------------------------------------------------------
A1B2C3D4E     List Project Files -...   2025-06-13T18:06
F5G6H7I8J     Get Project Info - 1...   2025-06-13T18:06
K9L0M1N2O     Get Git Status - 18:06    2025-06-13T18:06
```

These sessions document tool usage for debugging and usage analytics.

Note: These are system-generated conversations documenting tool usage, separate from your conversations with AI assistants. We set this config in [gandalf/src/tool_calls/conversations/conversation_cache.py](gandalf/src/tool_calls/conversations/conversation_cache.py)

## Configuration

Gandalf uses a clean, simplified configuration approach with clear separation between user AI tuning and system settings:

### AI Context Weights (`weights.yaml`) - For Users

Contains all AI context intelligence settings with detailed explanations and controls:

- Relevance Scoring Weights: How different factors influence file priority (recent edits, imports, etc.)
- Display Limits: How many files to show in different priority categories
- File Extension Priorities: Which file types are most important (.py, .js, .md, etc.)
- Directory Importance: Which directories get priority (src/, lib/, tests/, etc.)
- Scoring Parameters: Fine-tuning for context intelligence algorithms

### System Constants - For Developers

The server uses sensible built-in defaults and automatically reads environment variables for overrides:

```python
# Example from server/config/constants.py
MAX_PROJECT_FILES = int(os.environ.get('MAX_PROJECT_FILES', '1000'))
MCP_CACHE_TTL = int(os.environ.get('MCP_CACHE_TTL', '300'))
MCP_DEBUG = os.environ.get('MCP_DEBUG', 'false').lower() == 'true'
```

**Environment Variables** can be set via:

1. **Shell environment:**

   ```bash
   export MAX_PROJECT_FILES=5000
   export MCP_DEBUG=true
   gandalf run
   ```

2. **MCP server configuration** in `~/.cursor/mcp.json`:
   ```json
   {
     "mcpServers": {
       "repo-myproject": {
         "env": {
           "MAX_PROJECT_FILES": "5000",
           "MCP_CACHE_TTL": "600",
           "MCP_DEBUG": "true"
         }
       }
     }
   }
   ```

- Environment variables with built-in defaults - Standard Python/system pattern
- Single configuration file for users - Just `weights.yaml` with comprehensive documentation
- No shell script dependencies - All scripts work independently
- Clear separation of concerns - User AI tuning vs developer system settings

## Requirements

- Python 3.10+ (no external dependencies)
- Git repository
- Cursor with MCP support

## Admin Rules

This is where you can lock or unlock Gandalf's power. To add this rule:

1. Open the admin rules in Cursor.
   a. On Mac, press `Command + Shift + P` and type "Admin Rules".
   b. On Windows, press `Ctrl + Shift + P` and type "Admin Rules".
2. Copy and paste the following rule:

```
Use the MCP servers to increase your context when needed. When working on complex tasks or getting stuck:

1. Leverage available context tools - Use gandalf conv list, gandalf conv show, and other MCP tools to gather relevant information
2. Search before asking - Check existing conversations, project files, and documentation using available search capabilities
3. Build on previous work - Reference past conversations and established patterns rather than starting from scratch
4. Context is king - More context leads to better solutions, so don't hesitate to gather comprehensive information before proceeding. The system is designed to help you help users more effectively by providing rich project context and conversation history.
```

3. Set the rule type to "Always" or "Auto" for best results.
4. Save the rule.

## Troubleshooting

1. To watch the logs within Cursor, go to `View` -> `Output` -> and select`MCP Logs` from the dropdown.
2. Opening `.mdc` files in Cursor while a conversation is active will majorly slow down your IDE. This appears to be a known bug.
3. The `claude-4-sonnet` thinking model yielded the best results for me; it very rarely failed to sufficiently respond to my queries and I almost never had to correct it.
4. For best results, turn on "auto-run" for your agent.
5. To reset the server, open "MCP Settings", click the restart button.
6. If throughout the duration of a chat you hit `stop`, or chat disconnects, and then trigger chat with a new conversation, it can sometimes read like the agent forgot the earlier context or will even ignore your new context. Fortunately with our caching system this includes _both_ older and latest messages and your agent _should_ pick handle all your messages. The order it manages them it will choose on its own.
7. The agent's are extremely sensitive to the rules set out in [./gandalf-rules.txt](./gandalf-rules.txt). If you change them, you will need to restart the server. More importantly, rules here can completely change how your agent interacts with the MCP; during my testing at one point it started commiting any change it made without asking, and would remove files forcibly without checking with me.

## Notes

- Each of the README's in this project were generated _without_ AI. If any of them are unclear please ask me (Tristan) to clarify.
- Storing state of MCP tool calls has a wicked benefit of pseud-state management. You could ask the agent to modify a large number of files and have them in a pending commit state. If you then ask the agent to revert back to the original state before creating this changes it will know exactly where to return to _without_ needing git hashes as reference.

## TODO:

- Improve scoring algorithm to better handle edge cases (very large files, binary files, etc.)
- Allow context intelligence to learn from user behavior and adjust weights automatically
- Improve file cache performance for large repositories (>10k files)
- Validate `weights.yaml` on startup and provide helpful error messages for invalid configs
- Add guided setup wizard for first-time users; maybe we use `dialog`.
- Add command to show current server status, cache health, and configuration summary; important to do next.
- Add ability to restart the IDE completely.
- Ensure that the conversation details are stored and able to referenced in the future. Not just ids, but actual conversation data. This ties in with the status dashboard.
- Add ability to send notifications to the IDE.
