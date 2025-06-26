# Gandalf

Gandalf is a Model Context Protocol for intelligent code assistance for your projects in Cursor. In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much an maiar can do; that's where we mortals come in.

In the Lord of the Rings, Gandalf the Grey is a powerful wizard, but even he cannot see all ends. _"All we have to decide is what to do with the time that is given us."_ That's where we mortals come in - by providing Gandalf with the right context, we help him illuminate the path forward.

## Quick Start

```bash
# Check dependencies
./gandalf.sh deps

# Install and configure
./gandalf.sh install

# Verify installation
./gandalf.sh test

# For global access
alias gdlf='/path/to/gandalf/gandalf.sh'
```

## What is MCP?

The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context and tools to LLMs. Think of MCP as a plugin system for Cursor; it allows you to extend the AI agent's capabilities by connecting it to various data sources and tools through standardized interfaces.

## Key Features

### **Smart Context Intelligence**

- **File Relevance Scoring**: Multi-point analysis based on Git activity, file size, type, relationships, and recency.
- **Intelligent Prioritization**: Automatically surfaces the most relevant files for your current work
- **Project Awareness**: "Understands" your codebase structure and dependencies

### **Conversation Intelligence**

- **Cursor Chat Integration**: Direct access to your Cursor IDE conversation history
- **Context-Aware Analysis**: Learns from past conversations to provide better assistance
- **Manual Conversation Storage**: Save important discussions for future reference

### **Developer Tools**

- **Git Integration**: Repository analysis and diff tracking (Remainder of features don't need MCP)
- **Performance Optimization**: Intelligent caching with 1-hour TTL and smart invalidation
- **Cross-Platform Support**: Works on macOS and Linux; Windows via WSL2

## Core MCP Tools

| Tool                         | Purpose                                      |
| ---------------------------- | -------------------------------------------- |
| `list_project_files`         | Smart file discovery with relevance scoring  |
| `get_project_info`           | Project metadata, Git status, and statistics |
| `ingest_conversations`       | Analyze Cursor IDE conversation history      |
| `query_conversation_context` | Search conversations for specific topics     |
| `query_cursor_conversations` | Direct database access to Cursor chats       |

## Commands

| Command           | Purpose                      | Example                       |
| ----------------- | ---------------------------- | ----------------------------- |
| `gandalf deps`    | Check system dependencies    | `./gandalf.sh deps --install` |
| `gandalf install` | Configure MCP for repository | `./gandalf.sh install -r`     |
| `gandalf test`    | Run comprehensive test suite | `./gandalf.sh test --shell`   |
| `gandalf lembas`  | Full validation workflow     | `./gandalf.sh lembas --force` |

## Prerequisites

- **Python 3.10+** - Required for MCP server
- **Git** - Required for repository operations
- **Cursor IDE** - With MCP support enabled
- **BATS** - For running shell tests (optional)

## Installation

### Basic Installation

1. **Clone and navigate:**

   ```bash
   git clone <repository-url>
   cd gandalf
   ```

2. **Check dependencies:**

   ```bash
   ./gandalf.sh deps
   ```

3. **Install to current repository:**

   ```bash
   ./gandalf.sh install
   ```

4. **Restart Cursor** and test MCP integration

### Advanced Installation

```bash
# Install with reset
./gandalf.sh install -r

# Install to specific repository, not neccesary though
./gandalf.sh install /path/to/project

# Skip connectivity tests, faster
./gandalf.sh install --skip-test
```

## Usage Recommendations

### **Best Use Cases**

- Complex refactoring across multiple files
- Architecture decisions requiring project context
- Learning new codebases with thinking models
- Extended conversations where context accumulates value

### **When to Use Standard Models**

- Quick code snippets or single-file changes
- Simple questions without project context
- Fast iteration on small problems

## Remote Development

**Important:** When working in remote environments (SSH, WSL, containers), conversation data is **not available** on the remote server. Cursor stores chat history locally for privacy and performance; Gandalf is not able to access it.

- Each Cursor session (local vs remote) maintains separate MCP configurations
- Gandalf must be installed separately in each environment
- Conversation tools only work in local Cursor sessions

## Documentation

- **[Installation Guide](INSTALLATION.md)** - Detailed setup instructions
- **[API Reference](API.md)** - Complete MCP tools documentation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Contributing](CONTRIBUTING.md)** - Development guidelines
- **[Rules](rules.md)** - MCP interaction guidelines

## Testing

```bash
# Run all tests
./gandalf.sh test

# Specific test categories
./gandalf.sh test --shell     # Shell tests only
./gandalf.sh test --python    # Python tests only
./gandalf.sh test performance # Performance tests

# Full validation, good way to check if everything is working
./gandalf.sh lembas
```

## Support

- **Logs**: View → Output → MCP Logs (set to DEBUG level)
- **Reset**: `./gandalf.sh install -r` for clean reinstall
- **Test**: `./gandalf.sh test` to verify components
- **Dependencies**: `./gandalf.sh deps --verbose` for environment analysis

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Notes

- Each of the README's in this project were generated _without_ AI. If any of them are unclear please ask me (Tristan) to clarify.
- Storing state of MCP tool calls has a wicked benefit of pseudo-state management. You could ask the agent to modify a large number of files and have them in a pending commit state. If you then ask the agent to revert back to the original state before creating this changes it will know exactly where to return to _without_ needing git hashes as reference.

## TODO:

- Re-implement Python test suite using pytest; comprehensive testing framework was temporarily removed during code cleanup and needs to be restored with proper test coverage for all MCP tools and core functionality
- Implement persistent disk cache for cross-session performance; add cache warming on project initialization; smart cache invalidation based on file system events
- Validate `weights.yaml` on startup and provide helpful error messages for invalid configs
- Add ability to send notifications to the IDE
- Rename "rules.md" to "gandalf-rules.md".
- Rename the naming pattern of "ingest_conversations" to "recall_cursor_conversations" and "query_conversation_context" to "recall_cursor_conversations". "recall" is a better name for the tool because it's more descriptive of what it does.
- Remove the backwards compatability we have in place.
- Add adapter pattern for integrations with claude code (and maybe windsurf?).
- Complete the export conversation tool. Add another directory in the home folder under conversation called "imports" that will store imported conversations. These are not stored or ever intended to be stored in the actual agent's database or conversation history, these are just part of the "minas_tirith" component, the library of conversations that are not part of the agent's conversation history.
- gandalf/src/config/cursor_database.md is out of date.
- make pyyaml required.
- Add a version checker to flag the user to run "gandalf install -r" if they are not on the latest version.
