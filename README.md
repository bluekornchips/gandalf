# Gandalf

Gandalf is a Model Context Protocol for intelligent code assistance for your projects in Cursor. In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much an maiar can do; that's where we mortals come in.

In the Lord of the Rings, Gandalf the Grey is a powerful wizard, but even he cannot see all ends. _"All we have to decide is what to do with the time that is given us."_ That's where we mortals come in - by providing Gandalf with the right context, we help him illuminate the path forward.

Although model dependent, with Gandalf we can provide a more comprehensive context to the AI assistant, allowing it to make more informed decisions and provide more accurate and helpful responses. Test it out with some complex commands and watch the conversation window show it use the tool calls to get incredible details and learn from its mistakes.

## What is a Model Context Protocol (MCP)?

"The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context and tools to LLMs. Think of MCP as a plugin system for Cursor - it allows you to extend the Agent's capabilities by connecting it to various data sources and tools through standardized interfaces." - [Source](https://www.cursor.com/blog/mcp-model-context-protocol)

## Key Features

### Core Intelligence

- Smart Context Selection: Related files based on imports, dependencies, and intelligent relevance scoring
- Cursor Integration: Aware of current editing location, recent edits, and import relationships
- Git Integration: Tracks repository status and changes with comprehensive project analysis
- Background Caching: Fast startup with persistent file caching and intelligent cache invalidation

### Conversation Intelligence

- Comprehensive Conversation Logging: Complete JSON-RPC protocol visibility with detailed analytics
- Manual Conversation Storage: Explicit conversation saving for important dialogue
- Cursor Chat Extraction: Direct access to all your Cursor IDE conversations and chat history
- Context-Aware Analysis: Fine-tuned context based on current project and conversation history through weighting and filtering

## MCP Tools

### File Operations

- `list_project_files` - Lists files with intelligent relevance scoring and multi-factor prioritization
- Advanced filtering by file types, size limits, and relevance thresholds
- Smart caching with security validation and performance optimization

### Project Intelligence

- `get_project_info` - Comprehensive project metadata including Git status, file statistics, and processing metrics
- Automatic workspace detection with multiple fallback strategies
- Cross-platform compatibility with optimized performance

### Conversation Analysis

- `ingest_conversations` - Analyze and ingest relevant conversations from Cursor IDE history with intelligent caching
- `query_conversation_context` - Search conversations for specific topics, keywords, or context
- Smart conversation filtering with relevance scoring and context awareness

### Cursor IDE Integration

- `query_cursor_conversations` - Query conversations directly from Cursor IDE databases for AI context analysis
- `list_cursor_workspaces` - List available Cursor workspace databases
- Multiple export formats (JSON, Markdown, Cursor-native)

## Cursor Chat Extraction

### Automated Chat Export

- Direct database access to Cursor's SQLite chat storage
- Multi-workspace support - automatically finds all your Cursor workspaces
- Complete conversation history - conversations, user messages, and AI responses
- Multiple export formats - JSON, Markdown, and Cursor-native format

### Remote Development Limitations

**Important Note for Remote Development Users:**

When working in remote development environments (SSH, WSL, remote containers, etc.), conversation data is **not available** on the remote server. Cursor stores chat conversations locally on your client machine for privacy and performance reasons.

- `query_cursor_conversations` will return 0 conversations when run on remote servers
- `list_cursor_workspaces` will show no available workspaces in remote environments
- Conversation history tools work only when run locally where Cursor IDE is installed

**Separate MCP Configurations:**

Each Cursor session maintains its own MCP configuration and server instances:

- Local Cursor session: Uses local MCP settings, runs MCP servers locally, has access to conversation data
- Remote SSH Cursor session: Uses remote MCP settings, runs MCP servers on remote machine, no conversation access
- Independent installations: Gandalf must be installed separately in each environment (`gandalf install`)

This means you'll see different MCP servers available in local vs remote Cursor sessions, and they don't share state or configuration.

This limitation is by design; Cursor keeps your conversation history secure and local rather than syncing it to remote development environments.

### Available Extraction Tools

- `query_cursor_conversations` - Query conversations from Cursor IDE databases for AI context analysis
- `list_cursor_workspaces` - List available workspace databases

### Use Cases

- Backup your conversations before major Cursor updates
- Analyze conversation patterns and coding assistance trends
- Export specific conversations for documentation or sharing
- Cross-reference past solutions with current problems
- Create searchable archives of your AI-assisted development sessions

**Example Usage:**

```bash
# Get summary of all conversations
python3 gandalf/src/utils/cursor_chat_query.py --summary

# Export all conversations to markdown
python3 gandalf/src/utils/cursor_chat_query.py --format markdown --output my_conversations.md

# List available workspaces
python3 gandalf/src/utils/cursor_chat_query.py --list-workspaces
```

**Technical Details:**

- Works by reading Cursor's SQLite databases at `~/Library/Application Support/Cursor/User/`
- Extracts data from multiple database keys: `composer.composerData`, `aiService.prompts`, `aiService.generations`
- Fully tested with comprehensive error handling for missing or corrupted databases
- No modification of Cursor's data - read-only access only

## Prerequisites

Gandalf requires the following dependencies:

- Python 3.10+: Required for the MCP server
- Git: Required for repository operations and context intelligence
- PyYAML (optional): For dynamic weights configuration - if not available, falls back to environment variables and defaults
- System Tools: `jq` and `bats` (for testing and analysis)

## Platform Support

### macOS & Linux: Full Support

Gandalf has comprehensive support for macOS and Linux systems with native installation and management scripts.

### Windows: Not Supported

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

- macOS: Homebrew installation commands
- Linux: Package manager detection (apt, yum, dnf, pacman, etc.)
- Windows: Use WSL2

### Environment Setup

For Python package management, you can optionally install PyYAML:

```bash
# Install PyYAML for dynamic configuration (optional)
pip install PyYAML>=6.0
```

## Quick Start

```bash
# Check dependencies first
gandalf deps

# Install and configure
gandalf install

# Run tests to verify
gandalf test

# For global access, add alias:
alias gdlf='/path/to/gandalf/gandalf.sh'
```

## Requirements

- Python 3.10+
- Git repository
- Cursor with MCP support

## Available Tools

**File Operations:**

- `list_project_files` - Lists files with intelligent relevance scoring and multi-factor prioritization
- `get_project_info` - Project metadata, Git information, and comprehensive file statistics

**Conversation Analysis Tools:**

- `ingest_conversations` - Analyze and ingest relevant conversations from Cursor IDE history with intelligent caching
- `query_conversation_context` - Search conversations for specific topics, keywords, or context

**Cursor IDE Integration:**

- `query_cursor_conversations` - Query conversations from Cursor IDE databases for AI context analysis
- `list_cursor_workspaces` - List available Cursor workspace databases

## CLI Alias

For faster typing, add this alias to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
alias gdlf='/path/to/gandalf/gandalf.sh'
```

## Commands

| Command                    | Purpose                      | Usage                                      |
| -------------------------- | ---------------------------- | ------------------------------------------ |
| `gandalf deps [options]`   | Check system dependencies    | Verify Python, Git, BATS, and requirements |
| `gandalf install [path]`   | Configure repository for MCP | Run per repository                         |
| `gandalf test [path]`      | Run comprehensive test suite | Verify installation                        |
| `gandalf run [path]`       | Start server manually        | Debugging only                             |
| `gandalf lembas [repo]`    | Complete validation workflow | Full test -> reset -> install -> test      |
| `gandalf conv store ID`    | Store conversation data      | Manual conversation storage                |
| `gandalf conv list`        | List stored conversations    | Shows manually stored conversations        |
| `gandalf conv show ID`     | Show conversation details    | View any stored conversation               |
| `gandalf analyze_messages` | Analyze MCP message logs     | View protocol activity and statistics      |

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

## Testing Framework

### Comprehensive Test Suite

Gandalf includes both Python and Shell test suites for comprehensive coverage:

**Python Tests (pytest):**

- `test_server_core.py` - Core MCP server functionality and JSON-RPC handling
- `test_project.py` - Project operations and Git integration
- `test_security.py` - Security validation and access control
- `test_performance.py` - Performance optimization and caching
- `test_common.py` - Common utilities and helper functions

**Shell Tests (bats):**

- `project-tests.sh` - Project-level operations and validation
- `workspace-detection-tests.sh` - Workspace detection strategies
- `performance-tests.sh` - Performance and load testing
- `integration-tests.sh` - End-to-end integration testing

### Test Categories

```bash
# Run specific test categories
gandalf test unit           # Unit tests only
gandalf test performance    # Performance tests only
gandalf test integration    # Integration tests only
gandalf test smoke          # Quick smoke tests
gandalf test lembas         # Fast tests for lembas workflow
gandalf test shell          # All shell tests
gandalf test all            # Complete test suite
```

### Test Management

The test suite manager provides flexible test execution:

```bash
# Run all tests with verbose output
gandalf test --verbose

# Show test count only
gandalf test --count

# Show execution timing
gandalf test --timing

# Run specific test suite
gandalf test project
gandalf test workspace-detection
```

## Usage Recommendations

### When to Use Gandalf

**Best for extended, complex conversations:**

- Multi-file refactoring projects
- Architecture decisions requiring project context
- Debugging complex issues across multiple files
- Learning new codebases with thinking models like Claude Sonnet
- Long conversations where context accumulates value

**Gandalf's caching and context intelligence systems provide significant benefits for:**

- Thinking models (Claude Sonnet, etc.) that benefit from rich context
- Extended sessions where file relationships and conversation history matter
- Complex projects with many interconnected files

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

- Project-Specific Installation: Each project has its own Gandalf installation and configuration
- Auto-Detection: Detects project context from current working directory and git repository
- Smart Caching: 1-hour TTL with intelligent invalidation based on project state
- Context Intelligence: Multi-factor file scoring and prioritization with conversation analysis
- Performance Optimization: Efficient file operations, batch processing, and intelligent resource management

## Troubleshooting

### Basic Troubleshooting

1. **MCP Logs**: View → Output → MCP Logs (set to DEBUG level)
2. **Reset**: `gandalf install -r` for clean reinstall
3. **Restart**: Restart Cursor completely after config changes

### Advanced Troubleshooting

4. **Test Suite**: Run `gandalf test` to verify all components
5. **Dependencies**: Use `gandalf deps --verbose` for detailed environment analysis
6. **Performance**: Check `gandalf analyze_messages` for protocol activity insights
7. **Cache Issues**: Clear cache with `gandalf install -r` and restart

### Common Issues

1. **To watch the logs within Cursor**: Go to `View` -> `Output` -> and select `MCP Logs` from the dropdown.

   Set the MCP Logs level to `DEBUG` or `INFO` to see detailed tool call activity. If you only see basic connection messages but not tool execution details, you're likely on `ERROR` level only. This can waste hours of debugging time thinking tools aren't working when they're just not logging at your current level.

   **Tip**: Click the cogwheel icon next to the MCP Logs dropdown and select "Set as Default" to make `DEBUG` your permanent default log level for all MCP servers.

2. **If changes to rules or configuration aren't taking effect**: Run `gandalf reset gandalf` followed by `gandalf install -f` to force a clean reinstall, then restart Cursor completely.
3. Opening `.mdc` files in Cursor while a conversation is active will majorly slow down your IDE. This appears to be a known bug.
4. The `claude-4-sonnet` thinking model yielded the best results for me; it very rarely failed to sufficiently respond to my queries and I almost never had to correct it.
5. For best results, turn on "auto-run" for your agent.
6. If throughout the duration of a chat you hit `stop`, or chat disconnects, and then trigger chat with a new conversation, it can sometimes read like the agent forgot the earlier context or will even ignore your new context. Fortunately with our caching system this includes _both_ older and latest messages and your agent _should_ pick handle all your messages. The order it manages them it will choose on its own.
7. The agent's are extremely sensitive to the rules set out in [./rules.md](./rules.md). If you change them, you will need to restart the server. More importantly, rules here can completely change how your agent interacts with the MCP; during my testing at one point it started committing any change it made without asking, and would remove files forcibly without checking with me.

## Notes

- Each of the README's in this project were generated _without_ AI. If any of them are unclear please ask me (Tristan) to clarify.
- Storing state of MCP tool calls has a wicked benefit of pseud-state management. You could ask the agent to modify a large number of files and have them in a pending commit state. If you then ask the agent to revert back to the original state before creating this changes it will know exactly where to return to _without_ needing git hashes as reference.

## TODO:

- Re-implement Python test suite using pytest; comprehensive testing framework was temporarily removed during code cleanup and needs to be restored with proper test coverage for all MCP tools and core functionality
- Implement persistent disk cache for cross-session performance; add cache warming on project initialization; smart cache invalidation based on file system events
- Validate `weights.yaml` on startup and provide helpful error messages for invalid configs
- Add ability to send notifications to the IDE
