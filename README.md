# Gandalf

Gandalf is a conversation aggregator and Model Context Protocol (MCP) server for intelligent code assistance using agentic tools. With just several essential tools, Gandalf provides contextual intelligence that bridges past discussions with current work.

In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

## The Essential Tools

| Tool                              | Purpose                                         | When to Use                | Cross-Tool Feature                        |
| --------------------------------- | ----------------------------------------------- | -------------------------- | ----------------------------------------- |
| `recall_conversations`            | Get recent relevant conversations across tools  | **Always start here**      | Aggregates Cursor, Claude Code & Windsurf |
| `search_conversations`            | Search conversation history for specific topics | Looking for past solutions | Searches all tools simultaneously         |
| `get_project_info`                | Project metadata, Git status, and statistics    | Unfamiliar projects        | -                                         |
| `list_project_files`              | Smart file discovery with relevance scoring     | Multi-file work            | -                                         |
| `get_server_version`              | Server version and protocol information         | Troubleshooting MCP        | -                                         |
| `export_individual_conversations` | Export conversations to files                   | Backup/documentation       | Exports from all supported tools          |

## Quick Start

```bash
# Check dependencies and install if needed
./gandalf.sh deps --install

# Install and configure (auto-detects Cursor or Claude Code)
./gandalf.sh install

# Verify installation
./gandalf.sh test

# For global access, create alias
alias gdlf='/path/to/gandalf/gandalf.sh'
```

## What is MCP?

The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context and tools to LLMs. Think of MCP as a plugin system for your IDE; it allows you to extend the AI agent's capabilities by connecting it to various data sources and tools through standardized interfaces.

## Supported IDEs

Gandalf automatically detects and aggregates conversations from three officially supported agentic tools:

### Cursor IDE

- Full conversation history access: Complete chat logs with user-agent exchanges
- Workspace detection and analysis: Automatic workspace identification
- SQLite database integration: Direct access to Cursor's conversation storage
- Rich metadata: File references, code blocks, AI model information

### Claude Code

- Session history management: JSONL-based conversation storage
- Project-specific conversations: Context-aware session tracking
- Message-based format: Structured conversation data with detailed metadata
- Analysis integration: Tool usage and project file tracking

### Windsurf IDE - Important Note

Windsurf uses a fundamentally different architecture than traditional chat-based IDEs. While Gandalf can detect Windsurf installations, meaningful conversation content will typically be empty. This is by design:

- Cascade AI System: Windsurf's [Cascade](https://docs.codeium.com/windsurf/memories) operates on flow-based interactions rather than persistent chat conversations like Cursor or Claude Code
- Memory & Rules System: Instead of conversations, Windsurf uses [Memories and Rules](https://docs.codeium.com/windsurf/memories) for context persistence

What Gandalf will see:

- System metadata and session tracking ( meaning empty conversation shells)
- Terminal history and file path records

For Windsurf context, check instead:

- Windsurf Settings > Cascade > Manage Memories
- `.windsurfrules` files in your projects
- `.windsurf/workflows/` directory for saved prompts

### Cross-Tool Detection

Environment Detection: Gandalf automatically detects your IDE and adapts accordingly. The system supports:

- Simultaneous detection, multiple tools can be detected and used together
- Automatic aggregation, results from all available tools are combined seamlessly
- Intelligent fallback, graceful handling when tools are unavailable

## Key Features

### Streamlined Architecture

- **Essential Tools**: Focused tool set eliminates complexity
- **Intelligent Aggregation**: Unified conversation access across IDEs

### Smart Context Intelligence

- **File Relevance Scoring**: Multi-point analysis based on Git activity, file relationships, and recency
- **Project Awareness**: Understands codebase structure and dependencies

## Cross-Tool Conversation Aggregation

Gandalf aggregates conversations from all supported tools, providing unified context without any additional setup.

### How It Works

The server automatically detects and combines conversations from all available tools. No configuration needed; the system handles all complexity behind the scenes.

### What This Means

- Cursor conversations are automatically included in results with full chat history
- Claude Code conversations are automatically included with session-based data
- Windsurf system data is included (though conversational content will be empty by design, unless you have rules that create memories)
- Relevance scoring prioritizes the most helpful solutions across all tools
- Processing time is typically under 0.05 seconds

## Commands

| Command                  | Purpose                      | Example                       |
| ------------------------ | ---------------------------- | ----------------------------- |
| `./gandalf.sh deps`      | Check system dependencies    | `./gandalf.sh deps --install` |
| `./gandalf.sh install`   | Configure MCP for repository | `./gandalf.sh install -r`     |
| `./gandalf.sh uninstall` | Remove all configurations    | `./gandalf.sh uninstall -f`   |
| `./gandalf.sh test`      | Run comprehensive test suite | `./gandalf.sh test --shell`   |
| `./gandalf.sh lembas`    | Full validation workflow     | `./gandalf.sh lembas --force` |

## Prerequisites

- **Python 3.10+** - Required for MCP server
- **Git** - Required for repository operations
- **Supported Tools**: Cursor, Claude Code, or Windsurf with MCP support
- **BATS** - For running shell tests (optional)

## Installation

### Basic Installation

1. **Clone and navigate:**

   ```bash
   git clone <repository-url>
   cd gandalf
   ```

2. **Install (auto-detects your IDE):**

   ```bash
   ./gandalf.sh install
   ```

3. **Restart your IDE** and test MCP integration

### Advanced Installation

```bash
# Install with reset (recommended for clean setup)
./gandalf.sh install -r

# Force specific IDE
./gandalf.sh install --ide cursor
./gandalf.sh install --ide claude-code
./gandalf.sh install --ide windsurf

# Uninstall completely
./gandalf.sh uninstall -f
```

### Global Access Setup

For convenient access from anywhere:

```bash
# Add to your shell profile (.bashrc, .zshrc, etc.)
alias gdlf='/path/to/gandalf/gandalf.sh'

# Then use anywhere
gdlf test
gdlf install -r
```

## Usage Recommendations

### Best Use Cases

- Complex refactoring across multiple files
- Architecture decisions requiring project context
- Learning new codebases with thinking models
- Extended conversations where context accumulates value

### When to Use Standard Models

- Quick code snippets or single-file changes
- Simple questions without project context
- Fast iteration on small problems

## Configuration

Gandalf automatically manages configuration in `~/.gandalf`:

```
~/.gandalf/
├── cache/                    # MCP server cache files
├── exports/                  # Conversation exports
├── backups/                  # Configuration backups
└── installation-state        # Installation tracking
```

## Performance

- **Fast Tool Loading**: Optimized architecture for quick response times
- **Intelligent Caching**: Smart caching with automatic invalidation
- **Scalable**: Adapts performance based on project size

## Testing

```bash
# Run all tests
./gandalf.sh test

# Run specific test suites
./gandalf.sh test --python    # Python tests only
./gandalf.sh test --shell     # Shell tests only

# Full validation workflow
./gandalf.sh lembas
```

## Troubleshooting

### Common Issues

- **MCP not working?** → Check `./gandalf.sh test` and use `get_server_version()` tool
- **Tools not found?** → Run `./gandalf.sh install -r` to reset configuration
- **Performance issues?** → Use `fast_mode=true` and limit `max_files` parameters
- **Cursor conversations not found?** → Restart IDE completely; conversation storage format may have changed

### Quick Diagnostics

```bash
# Check system dependencies
./gandalf.sh deps --verbose

# Verify MCP server status
./gandalf.sh test core

# Reset and reinstall if needed
./gandalf.sh install -r
```

**For detailed troubleshooting:** See `gandalf/docs/troubleshooting.md`

## Contributing

### Development Commands

```bash
# Reset for clean development
./gandalf.sh install -r

# Remove all configurations (preserves conversation history)
./gandalf.sh uninstall

# Verify all components
./gandalf.sh test

# Analyze environment
./gandalf.sh deps --verbose
```

## Quick Reference: MCP Tool Usage

### Essential Workflow

```bash
# 1. Always start with conversation recall
recall_conversations(fast_mode=true, days_lookback=7)

# 2. Search for specific topics if needed
search_conversations(query="your search terms", include_content=true)

# 3. Get project context for unfamiliar codebases
get_project_info()

# 4. Discover relevant files for multi-file work
list_project_files(max_files=50, file_types=['.py', '.js'])
```

### Success Indicators

```
Available tools detected: ['cursor', 'claude-code']
Queried 541 conversations in cursor format
Queried 3 conversations in json format
Recalled 8 total conversations from 2 tools in 0.03s
```

### Key Features

- **Both tools detected**: Registry finds both `cursor` and `claude-code`
- **Cross-tool aggregation**: Results combined from multiple sources
- **Relevance scoring**: Higher scores indicate better solutions
- **Fast processing**: Complete aggregation in ~0.05 seconds
- **Automatic optimization**: Large responses optimized for performance

## Automated Rules Generation

Gandalf automatically creates global rules files during installation to ensure consistent AI behavior across all supported tools and projects. Each tool receives the same core guidance adapted to its native format:

### Global Rules Files Created

| Tool            | Location                            | Format   | Notes                                  |
| --------------- | ----------------------------------- | -------- | -------------------------------------- |
| **Cursor**      | `~/.cursor/rules/gandalf-rules.mdc` | Markdown | Global rules for all Cursor projects   |
| **Claude Code** | `~/.claude/global_settings.json`    | JSON     | Global rules embedded in user settings |
| **Windsurf**    | `~/.windsurf/global_rules.md`       | Markdown | Global rules (6000 char limit)         |

### How It Works

1. **Source**: All rules derive from `spec/gandalf-rules.md`
2. **Installation**: Global rules are automatically created when running `./gandalf.sh install`
3. **Format Adaptation**: Content is adapted to each tool's native global rules system
4. **Character Limits**: Windsurf rules are automatically truncated if they exceed 6000 characters
5. **Backup**: Existing rules are backed up before replacement (with `-f` or `-r` flags)

### Tool-Specific Features

**Cursor**: Uses `~/.cursor/rules/*.mdc` files that are automatically loaded globally by the IDE

**Claude Code**: Integrates rules into global user settings as `gandalfRules` field for context awareness across all projects

**Windsurf**: Creates global rules (`~/.windsurf/global_rules.md`):

- Global rules: Apply to all projects and workspaces
- Truncated if needed to fit 6000 character limit
- Memory integration: Designed to work alongside Windsurf's Cascade Memories system

### Maintenance

Global rules are automatically updated during:

- `./gandalf.sh install -f` (force update)
- `./gandalf.sh install -r` (reset and reinstall)

To manually update rules without reinstalling:

```bash
./gandalf.sh install -f --skip-test
```

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Notes

- Each of the README files in this project were generated without AI. If any of them are unclear please ask me (Tristan) to clarify.
- Storing state of MCP tool calls has a significant benefit of pseudo-state management. You could ask the agent to modify a large number of files and have them in a pending commit state. If you then ask the agent to revert back to the original state before creating these changes it will know exactly where to return to without needing git hashes as reference.

## TODO

- Implement persistent disk cache for cross-session performance; add cache warming on project initialization; smart cache invalidation based on file system events
- Validate `gandalf-weights.yaml` on startup and provide helpful error messages for invalid configs
- Add ability to send notifications to the IDE
- Complete the export conversation tool. Add another directory in the home folder under conversation called "imports" that will store imported conversations. These are not stored or ever intended to be stored in the actual agent's database or conversation history, these are just part of the "minas_tirith" component, the library of conversations that are not part of the agent's conversation history.
- Update the recall_conversations to be better optimized for performance. Using tags, filtering, and other methods to make it faster and more efficient and consume less tokens.x
- Create automation for a "gandalf" user on the system that will run the MCP server and handle the conversation history, and run any cli commands to keep a clean and clear seperaation of access, permissions, and history.
