# Gandalf

Gandalf is a Model Context Protocol for intelligent code assistance for your projects in Cursor. In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much an maiar can do; that's where we mortals come in.

In the Lord of the Rings, Gandalf the Grey is a powerful wizard, but even he cannot see all ends. _"All we have to decide is what to do with the time that is given us."_ That's where we mortals come in - by providing Gandalf with the right context, we help him illuminate the path forward.

Although model dependent, with Gandalf we can provide a more comprehensive context to the AI assistant, allowing it to make more informed decisions and provide more accurate and helpful responses. Test it out with some complex commands and watch the conversation window show it use the tool calls to get incredible details and learn from its mistakes.

## What is a Model Context Protocol (MCP)?

"The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context and tools to LLMs. Think of MCP as a plugin system for Cursor - it allows you to extend the Agent's capabilities by connecting it to various data sources and tools through standardized interfaces." - [Source](https://www.cursor.com/blog/mcp-model-context-protocol)

## Key Features

- Smart Context Selection: Related files based on imports and dependencies
- Cursor Integration: Aware of current editing location, recent edits, and import relationships.
- Git Integration: Tracks repository status and changes
- Background Caching: Fast startup with persistent file caching
- Comprehensive Conversation Logging: Complete JSON-RPC protocol visibility
- Manual Conversation Storage: Explicit conversation saving for important dialogue
- Cursor Chat Extraction: Direct access to all your Cursor IDE conversations and chat history
- Allows fine tuning of context based on the current project and conversation history through weighting and filtering.

## 🆕 Cursor Chat Extraction

### **Automated Chat Export**

- **Direct database access** to Cursor's SQLite chat storage
- **Multi-workspace support** - automatically finds all your Cursor workspaces
- **Complete conversation history** - conversations, user messages, and AI responses
- **Multiple export formats** - JSON, Markdown, and Cursor-native format

### **Available Extraction Tools**

- `query_cursor_conversations` - Query conversations from Cursor IDE databases for AI context analysis
- `list_cursor_workspaces` - List available workspace databases

### **Use Cases**

- **Backup your conversations** before major Cursor updates
- **Analyze conversation patterns** and coding assistance trends
- **Export specific conversations** for documentation or sharing
- **Cross-reference past solutions** with current problems
- **Create searchable archives** of your AI-assisted development sessions

**Example Usage:**

```bash
# Get summary of all conversations
gdlf run query_cursor_conversations --summary

# Export all conversations to markdown
python3 gandalf/scripts/cursor_chat_query.py --format markdown --output my_conversations.md

# List available workspaces
python3 gandalf/scripts/cursor_chat_query.py --list-workspaces
```

**Technical Details:**

- Works by reading Cursor's SQLite databases at `~/Library/Application Support/Cursor/User/`
- Extracts data from multiple database keys: `composer.composerData`, `aiService.prompts`, `aiService.generations`
- Fully tested with comprehensive error handling for missing or corrupted databases
- **No modification** of Cursor's data - read-only access only

## Prerequisites

Gandalf requires the following dependencies:

- **Python 3.10+**: Required for the MCP server
- **Git**: Required for repository operations and context intelligence
- **PyYAML** (optional): For dynamic weights configuration - if not available, falls back to environment variables and defaults
- **System Tools**: `jq` and `bats` (for testing and analysis)

## Platform Support

### **macOS & Linux: Full Support**

Gandalf has comprehensive support for macOS and Linux systems with native installation and management scripts.

### **Windows: Not Supported**

Gandalf requires bash and Unix tools. Windows users should use WSL2 for full compatibility.

### Python Dependencies

Gandalf can optionally use PyYAML for its dynamic configuration system that allows you to tune AI behavior through the `weights.yaml` file. If PyYAML is not available, the system will fall back to environment variables and built-in defaults.

### Dependency Checking

Check your environment with the cross-platform dependency checker:

```bash
# Quick dependency check
./gandalf.sh deps

# Detailed environment information
./gandalf.sh deps --verbose

# Attempt automatic installation (with confirmation)
./gandalf.sh deps --install
```

The dependency checker provides platform-specific installation instructions for:

- **macOS**: Homebrew installation commands
- **Linux**: Package manager detection (apt, yum, dnf, pacman, etc.)
- **Windows**: Use WSL2

### Environment Setup

For Python package management, you can optionally install PyYAML:

```bash
# Install PyYAML for dynamic configuration (optional)
pip install PyYAML>=6.0
```

## Quick Start

```bash
# Check dependencies first
./gandalf.sh deps

# Install and configure
./gandalf.sh install

# Run tests to verify
./gandalf.sh test

# For global access, add alias:
alias gdlf='/path/to/gandalf/gandalf.sh'
```

## Requirements

- Python 3.10+
- Git repository
- Cursor with MCP support

## Available Tools

**File Operations:**

- `list_project_files` - Lists files with intelligent relevance scoring
- `get_project_info` - Project metadata and git information

## CLI Alias

For faster typing, add this alias to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
alias gdlf='/path/to/gandalf/gandalf'
```

## Commands

| Command                    | Purpose                      | Usage                                 |
| -------------------------- | ---------------------------- | ------------------------------------- |
| `gandalf deps [options]`   | Check system dependencies    | Verify Python, Git, BATS, and requirements |
| `gandalf install [path]`   | Configure repository for MCP | Run per repository                    |
| `gandalf test [path]`      | Run comprehensive test suite | Verify installation                   |
| `gandalf run [path]`       | Start server manually        | Debugging only                        |
| `gandalf lembas [repo]`    | Complete validation workflow | Full test -> reset -> install -> test |
| `gandalf conv store ID`    | Store conversation data      | Manual conversation storage           |
| `gandalf conv list`        | List stored conversations    | Shows manually stored conversations   |
| `gandalf conv show ID`     | Show conversation details    | View any stored conversation          |
| `gandalf analyze_messages` | Analyze MCP message logs     | View protocol activity and statistics |

### Dependency Management

The `deps` command provides comprehensive dependency checking:

```bash
# Check all dependencies
gandalf deps

# Check specific components
gandalf deps --python-only      # Python requirements only
gandalf deps --bats-only        # BATS testing framework only  
gandalf deps --core-only        # Core dependencies (Python, Git)

# Interactive installation assistance
gandalf deps --install          # Offers to help install missing deps

# Quiet mode for scripts
gandalf deps --quiet             # Exit codes only, minimal output
```

**Automatic Integration:**
- `gandalf install` automatically checks core dependencies before installation
- `gandalf test` verifies BATS and Python requirements before running tests
- `gandalf lembas` includes full dependency validation in its workflow

## Usage Recommendations

### When to Use Gandalf

**Best for extended, complex conversations:**

- Multi-file refactoring projects
- Architecture decisions requiring project context
- Debugging complex issues across multiple files
- Learning new codebases with thinking models like Claude Sonnet
- Long conversations where context accumulates value

**Gandalf's caching and context intelligence systems provide significant benefits for:**

- **Thinking models** (Claude Sonnet, etc.) that benefit from rich context
- **Extended sessions** where file relationships and conversation history matter
- **Complex projects** with many interconnected files

### When to Use Standard Models

**For quick, isolated tasks:**

- Simple code snippets or single-file changes
- Quick questions that don't require project context
- Fast iteration on small problems
- When you prefer minimal overhead

**Non-thinking models without MCP may be faster for:**

- Single-purpose queries
- Code generation without project context
- Quick documentation lookups

The 1-hour cache TTL and context intelligence overhead are optimized for sustained, complex work rather than quick one-off interactions.

## How It Works

### Server Architecture

- Gandalf is installed once in a fixed location (e.g., `~/home/gandalf/`)
- MCP configuration points to that location and never changes
- Project context is detected dynamically based on what Cursor has open
- When you open a React project, Gandalf analyzes that React project
- When you switch to a Python project, Gandalf automatically switches context

Lightweight MCP server implementation:

- **Single server instance serves all projects** - no conflicts, automatic context switching
- **ConversationLogger**: Comprehensive JSON-RPC protocol logging for debugging and analysis

The server detects the current project using multiple strategies:

1. Cursor's `WORKSPACE_FOLDER_PATHS` environment variable
2. PWD environment variable when set correctly by Cursor
3. Git repository detection from current working directory
4. Fallback to current working directory

The server is designed to be managed automatically by Cursor. For debugging, you can run it manually:

```bash
# Debug the server directly
python3 src/main.py --project-root /path/to/project

# Or use the unified gandalf command
gandalf run --project-root /path/to/project
```

### Tools Available

These tool calls are available to the Gandalf and it makes the decision when to use them, or can be asked directly by the user.

#### A Note on visibly redundant functionality

Gandalf intentionally re-implements some functionality that already exists in Cursor (file listing, git operations) to provide what I like to think of as a "BIOS-level" control over our agents context intelligence.

This redefinition allows users to configure file prioritization, scoring weights, and context selection without requiring the capability to build an entirely new model, agent, or MCP. I find it similar to building a desktop computer: we (usually) don't need to understand the CPU's architecture, but we can control settings in the bios menu. The context intelligence system gives us the same granular control over how files are prioritized and presented to the AI like overclocking, boot priority, or even bios flashing; none of which are possible with Cursor's built-in tools currently.

#### Why Git Operations When Cursor Has Git Support?

**Key Distinction: AI Context vs Human Interface**

| **Cursor's Git**                                     | **Gandalf's Git Operations**                          |
| ---------------------------------------------------- | ----------------------------------------------------- |
| **UI-focused**: Visual git interface, diffs, staging | **AI-focused**: Structured JSON data for AI reasoning |
| **Human interaction**: Click, drag, visual workflows | **Programmatic**: Machine-readable git context        |
| **Current session**: What you're actively working on | **Historical context**: Past commits, branch analysis |
| **IDE integration**: Gutter indicators, file status  | **MCP protocol**: Accessible via tool calls           |

**AI Context Intelligence Examples:**

- _"I see you're on the feature-auth branch with staged changes to login.py"_
- _"Based on your last 3 commits, you've been refactoring the database layer"_
- _"Let me check the git diff to understand what changed in that authentication function"_

**Structured Data for AI Reasoning:**

```json
{
  "current_branch": "feature-auth",
  "staged_files": [{"file": "src/auth/login.py", "status": "M"}],
  "last_commit": {
    "hash": "abc123",
    "message": "fix: resolve login validation bug",
    "author": "developer"
  }
}
```

The AI cannot "see" Cursor's visual git interface, but it can process structured git data to provide context-aware assistance. This enables responses like _"I notice you're working on authentication - let me check recent auth-related commits for context"_ rather than generic help as we are used to.

**Core Tools:**

- `list_project_files` - Lists relevant project files with intelligent relevance scoring
- `get_project_info` - Returns project metadata and Git information

**Conversation Analysis Tools:**

- `ingest_conversations` - Analyze and ingest relevant conversations from Cursor IDE history with intelligent caching
- `query_conversation_context` - Search conversations for specific topics, keywords, or context

**Cursor IDE Integration:**

- `query_cursor_conversations` - Query conversations from Cursor IDE databases for AI context analysis
- `list_cursor_workspaces` - List available Cursor workspace databases

### Real-time Conversation Analysis

The Gandalf MCP server provides conversation analysis tools through direct Cursor IDE database integration:

- `ingest_conversations` - Analyze and extract relevant conversations with smart caching and filtering
- `query_conversation_context` - Search conversations for specific topics, keywords, or context

These tools work directly with Cursor's conversation databases to provide real-time contextual intelligence for the AI assistant.

### Security & Validation

All MCP tools implement comprehensive security validation:

- **Input Sanitization**: All string inputs are sanitized for malicious patterns
- **Path Validation**: File paths are validated against directory traversal attacks
- **Size Limits**: Content is limited to prevent resource exhaustion
- **Format Validation**: JSON structures are strictly validated
- **Project Boundaries**: File operations are restricted to project scope

**Error Response Format:**

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Error: Detailed error message"
    }
  ]
}
```

**Success Response Format:**

```json
{
  "content": [
    {
      "type": "text",
      "text": "Response data or formatted results"
    }
  ]
}
```

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

### Priority Scoring System

Gandalf's **Context Intelligence** includes a **three-tier priority system** with configurable thresholds to categorize files by relevance:

**Note**: The Priority Scoring System **is part of** Context Intelligence, not separate from it. Context Intelligence is the broader system that analyzes file relationships, recent activity, and project patterns, while Priority Scoring is how those analysis results are categorized and displayed.

#### Priority Thresholds

| Priority Level      | Score Range | Description         | Typical Files                                       |
| ------------------- | ----------- | ------------------- | --------------------------------------------------- |
| **High Priority**   | ≥ 0.8       | Most relevant files | Currently open files, main modules, recently edited |
| **Medium Priority** | 0.4 - 0.7   | Moderately relevant | Related files, dependencies, configuration          |
| **Low Priority**    | < 0.4       | Less relevant       | Distant dependencies, old files, utilities          |

#### Context Intelligence vs Priority Scoring

- **Context Intelligence**: The comprehensive analysis system that:

  - Analyzes file relationships (imports, dependencies)
  - Tracks recent activity (edits, cursor position, open files)
  - Applies configurable weights from `weights.yaml`
  - Computes relevance scores for each file

- **Priority Scoring**: The categorization layer that:
  - Takes Context Intelligence scores and groups them into High/Medium/Low
  - Uses configurable thresholds (0.8, 0.4) to determine categories
  - Provides consistent display formatting
  - Enables neutral scoring (0.5) when intelligence is disabled

When `use_relevance_scoring=true`: Full Context Intelligence runs, computing sophisticated relevance scores, then Priority Scoring categorizes and displays them.

When `use_relevance_scoring=false`: Context Intelligence is bypassed, and all files get the neutral score (0.5) for consistent processing.

#### Neutral Score (0.5)

When relevance scoring is **disabled** (`use_relevance_scoring: false`), all files receive a **neutral score of 0.5**:

- **Purpose**: Ensures consistent data structure throughout the system
- **Category**: Falls in Medium Priority range (0.4 ≤ 0.5 < 0.8)
- **Benefit**: Files still get processed through the same code paths without expensive scoring computation
- **Use Case**: Quick file listing without context intelligence overhead

The neutral score of **0.5** was chosen strategically:

1. **Medium Priority Placement**: Not too high (avoids false importance), not too low (maintains visibility)
2. **Consistent Processing**: All code expects `(file_path, score)` tuples, so scoring-disabled mode maintains this structure
3. **Balanced Display**: Files appear in a reasonable priority bucket when relevance scoring is turned off
4. **Performance**: Avoids expensive context intelligence computation while maintaining functionality

#### Configuration

Priority thresholds are defined in `src/config/constants/system.py`:

```python
# File relevance scoring constants
PRIORITY_HIGH_THRESHOLD = 0.8      # Files with score >= 0.8 are high priority
PRIORITY_MEDIUM_THRESHOLD = 0.4    # Files with 0.4 <= score < 0.8 are medium priority
PRIORITY_NEUTRAL_SCORE = 0.5       # Default score when relevance scoring is disabled
```

### File Filtering

Excludes common patterns using [.gitignore](.gitignore)

- Python: `__pycache__`, `.pyc`, `.pyo` files
- Node.js: `node_modules`, cache directories
- Build: `dist`, `build`, `target` directories
- IDEs: `.vscode`, `.idea` directories
- System: `.DS_Store`, `Thumbs.db` files

### Comprehensive Conversation Logging

The server automatically logs **every single JSON-RPC message** exchanged with Cursor for complete visibility into MCP protocol activity:

**What's Captured:**

- All JSON-RPC messages: Requests, responses, notifications
- Session metadata: Project context, environment variables, timestamps
- Tool execution flow: Complete tool call lifecycle with arguments and results
- Error tracking: All errors with full context and stack traces
- Performance data: Timing information for debugging and optimization

**Storage & Format:**

- Location: `~/.gandalf/conversation_logs/mcp_conversation_{project}_{timestamp}_{session_id}.jsonl`
- Format: JSONL (JSON Lines) - one JSON object per line for streaming and easy parsing
- Session tracking: Unique session IDs with start/end markers
- Zero performance impact: Asynchronous logging with error handling

**Analysis Tools** via `gandalf analyze_messages`:

| Command                      | Purpose                            | Example                                                    |
| ---------------------------- | ---------------------------------- | ---------------------------------------------------------- |
| `list`                       | Show all available log files       | `gandalf analyze_messages list`                            |
| `latest`                     | Display the most recent session    | `gandalf analyze_messages latest`                          |
| `show <session_id>`          | Pretty-print specific session      | `gandalf analyze_messages show abc123def456`               |
| `stats <session_id>`         | Detailed statistics and tool usage | `gandalf analyze_messages stats abc123def456`              |
| `search <pattern>`           | Search across all logs             | `gandalf analyze_messages search "get_project_info"`       |
| `tools [session_id]`         | Tool usage analysis                | `gandalf analyze_messages tools`                           |
| `errors [session_id]`        | Error tracking                     | `gandalf analyze_messages errors`                          |
| `export <session_id> <file>` | Export to structured JSON          | `gandalf analyze_messages export abc123 /tmp/session.json` |
| `tail [session_id]`          | Real-time log monitoring           | `gandalf analyze_messages tail`                            |
| `summary <session_id>`       | Quick session overview             | `gandalf analyze_messages summary abc123`                  |

**Example Analysis Output:**

```bash
$ gandalf analyze_messages stats abc123def456
Statistics for Session: abc123def456
=====================================

Total Messages: 47
Requests: 8
Responses: 8
Notifications: 31
Errors: 0

Timeline:
Start: 2025-06-17T18:19:18.123456
End: 2025-06-17T18:54:32.789012

Tool Usage:
   5  get_project_info
   3  list_project_files
   2  ingest_conversations
   1  query_conversation_context
```

**Configuration:**

- Enable/Disable: Set `GANDALF_CONVERSATION_LOGGING=false` to disable (enabled by default)
- Log Rotation: Logs are kept indefinitely, so we can implement custom rotation as needed
- Privacy: Logs contain all tool arguments and responses; review before sharing...aka, no privacy.

**Benefits:**

- Complete visibility: Every protocol message captured, not just tool calls
- Rich analysis: Statistics, search, export, and real-time monitoring
- Debugging: Full protocol-level visibility for troubleshooting
- Performance: Async logging with zero latency impact
- Structured data: JSONL format for easy parsing and integration. JSONL is json, but with a newline.

### Real-time Conversation Access

Direct access to all Cursor IDE conversations through intelligent database queries:

**Available MCP Tools:**

- `ingest_conversations` - Analyze and extract relevant conversations with "smart" caching and filtering
- `query_conversation_context` - Search conversations for specific topics, keywords, or context
- `query_cursor_conversations` - Direct access to Cursor's conversation databases
- `list_cursor_workspaces` - List available Cursor workspace databases

**Key Benefits:**

- **Real-time access** - Always current with what's in Cursor
- **No duplication** - Conversations aren't stored separately
- **Complete coverage** - Access to ALL conversations, not just selected ones
- **Intelligent filtering** - Context-aware relevance scoring and keyword matching
- **Smart caching** - Performance optimization with TTL-based caching

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
# Example from src/config/constants/system.py
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

| Command                    | Purpose            |
| -------------------------- | ------------------ |
| `gandalf install [path]`   | Install MCP server |
| `gandalf test`             | Run test suite     |
| `gandalf analyze_messages` | Analyze MCP logs   |

## How It Works

- **Single Server**: One installation serves all projects
- **Auto-Detection**: Detects project context from Cursor's workspace
- **Smart Caching**: 1-hour TTL with intelligent invalidation
- **Context Intelligence**: Multi-factor file scoring and prioritization

## Troubleshooting

1. **MCP Logs**: View → Output → MCP Logs (set to DEBUG level)
2. **Reset**: `gandalf install -r` for clean reinstall
3. **Restart**: Restart Cursor completely after config changes

## gandalf-rules.md

This is where you can lock or unlock Gandalf's power; it is automatically "installed" when you run `gandalf install`, or re-isntalled with `gandalf install -r`

## Troubleshooting

1. **To watch the logs within Cursor**: Go to `View` -> `Output` -> and select `MCP Logs` from the dropdown.

   Set the MCP Logs level to `DEBUG` or `INFO` to see detailed tool call activity. If you only see basic connection messages but not tool execution details, you're likely on `ERROR` level only. This can waste hours of debugging time thinking tools aren't working when they're just not logging at your current level.

   **Tip**: Click the cogwheel icon next to the MCP Logs dropdown and select "Set as Default" to make `DEBUG` your permanent default log level for all MCP servers.

2. **If changes to rules or configuration aren't taking effect**: Run `gandalf reset gandalf` followed by `gandalf install -f` to force a clean reinstall, then restart Cursor completely.
3. Opening `.mdc` files in Cursor while a conversation is active will majorly slow down your IDE. This appears to be a known bug.
4. The `claude-4-sonnet` thinking model yielded the best results for me; it very rarely failed to sufficiently respond to my queries and I almost never had to correct it.
5. For best results, turn on "auto-run" for your agent.
6. If throughout the duration of a chat you hit `stop`, or chat disconnects, and then trigger chat with a new conversation, it can sometimes read like the agent forgot the earlier context or will even ignore your new context. Fortunately with our caching system this includes _both_ older and latest messages and your agent _should_ pick handle all your messages. The order it manages them it will choose on its own.
7. The agent's are extremely sensitive to the rules set out in [./gandalf-rules.md](./gandalf-rules.md). If you change them, you will need to restart the server. More importantly, rules here can completely change how your agent interacts with the MCP; during my testing at one point it started committing any change it made without asking, and would remove files forcibly without checking with me.

## Notes

- Each of the README's in this project were generated _without_ AI. If any of them are unclear please ask me (Tristan) to clarify.
- Storing state of MCP tool calls has a wicked benefit of pseud-state management. You could ask the agent to modify a large number of files and have them in a pending commit state. If you then ask the agent to revert back to the original state before creating this changes it will know exactly where to return to _without_ needing git hashes as reference.

## TODO:

- Re-implement Python test suite using pytest; comprehensive testing framework was temporarily removed during code cleanup and needs to be restored with proper test coverage for all MCP tools and core functionality
- Implement persistent disk cache for cross-session performance; add cache warming on project initialization; smart cache invalidation based on file system events
- Improve scoring algorithm to better handle edge cases (very large files, binary files, etc.)
- Allow context intelligence to learn from user behavior and adjust weights automatically
- Improve file cache performance for large repositories (>10k files)
- Validate `weights.yaml` on startup and provide helpful error messages for invalid configs
- Add guided setup wizard for first-time users; maybe we use `dialog`
- Add command to show current server status, cache health, and configuration summary
- Add ability to send notifications to the IDE
- Automate the "Export Chat" feature of the chat window. This is hidden behind Cursor's API
