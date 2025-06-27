# Gandalf

Gandalf is a Model Context Protocol (MCP) server for intelligent code assistance in **Cursor IDE** and **Claude Code**. In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

In the Lord of the Rings, Gandalf the Grey is a powerful wizard, but even he cannot see all ends. _"All we have to decide is what to do with the time that is given us."_ That's where we mortals come in; by providing Gandalf with the right context, we help him illuminate the path forward.

## Quick Start

```bash
# Check dependencies
./gandalf.sh deps

# Install and configure (auto-detects Cursor or Claude Code)
./gandalf.sh install

# Verify installation
./gandalf.sh test

# For global access
alias gdlf='/path/to/gandalf/gandalf.sh'
```

## What is MCP?

The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context and tools to LLMs. Think of MCP as a plugin system for your IDE; it allows you to extend the AI agent's capabilities by connecting it to various data sources and tools through standardized interfaces.

## Supported IDEs

### **Cursor IDE**

- Full conversation history access
- Workspace detection and analysis
- Chat integration with SQLite database access

### **Claude Code**

- Session history management
- Project-specific conversation storage
- JSONL session format support
- Standard MCP configuration

**Environment Detection**: Gandalf automatically detects your IDE environment and adapts its functionality accordingly.

## Key Features

### **Smart Context Intelligence**

- **File Relevance Scoring**: Multi-point analysis based on Git activity, file size, type, relationships, and recency
- **Intelligent Prioritization**: Automatically surfaces the most relevant files for your current work
- **Project Awareness**: "Understands" your codebase structure and dependencies

### **Conversation Intelligence**

- **IDE Chat Integration**: Direct access to your IDE conversation history
- **Context-Aware Analysis**: Learns from past conversations to provide better assistance
- **Cross-Session Intelligence**: Maintains context across different IDE sessions

### **Developer Tools**

- **Git Integration**: Repository analysis and diff tracking
- **Performance Optimization**: Intelligent caching with 1-hour TTL and smart invalidation
- **Cross-Platform Support**: Works on macOS and Linux; Windows via WSL2

## Core MCP Tools

| Tool                   | Purpose                                             | Cursor | Claude Code |
| ---------------------- | --------------------------------------------------- | ------ | ----------- |
| `list_project_files`   | Smart file discovery with relevance scoring         | Yes    | Yes         |
| `get_project_info`     | Project metadata, Git status, and statistics        | Yes    | Yes         |
| `get_server_version`   | Get current server version and protocol information | Yes    | Yes         |
| `recall_conversations` | Recall and analyze IDE conversation history         | Yes    | Yes         |
| `search_conversations` | Search conversations for specific topics            | Yes    | Yes         |
| `query_conversations`  | Direct database/session access to chats             | Yes    | Yes         |
| `export_conversations` | Export conversations to files                       | Yes    | Yes         |

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
- **IDE**: Cursor IDE or Claude Code with MCP support
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

3. **Install (auto-detects your IDE):**

   ```bash
   ./gandalf.sh install
   ```

4. **Restart your IDE** and test MCP integration

### Advanced Installation

```bash
# Install with reset
./gandalf.sh install -r

# Force specific IDE
./gandalf.sh install --ide claude-code
./gandalf.sh install --ide cursor

# Install to specific repository
./gandalf.sh install /path/to/project

# Skip connectivity tests (faster)
./gandalf.sh install --skip-test
```

### IDE-Specific Setup

**Claude Code Manual Setup** (if auto-install fails):

```bash
claude mcp add gandalf python3 -m src.main --cwd /path/to/gandalf --env PYTHONPATH=/path/to/gandalf --env CLAUDECODE=1
```

**Cursor IDE Manual Setup** (if auto-install fails):

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/path/to/gandalf/gandalf.sh",
      "args": ["run"]
    }
  }
}
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

**Important**: When working in remote environments (SSH, WSL, containers), conversation data availability varies by IDE:

- **Claude Code**: Session data may be available depending on configuration
- **Cursor IDE**: Chat history is stored locally and not available on remote servers

Each IDE session (local vs remote) maintains separate MCP configurations; Gandalf must be installed separately in each environment.

## Documentation

- **[Installation Guide](INSTALLATION.md)** - Detailed setup instructions for both IDEs
- **[API Reference](API.md)** - Complete MCP tools documentation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Contributing](CONTRIBUTING.md)** - Development guidelines
- **[Rules](gandalf-rules.md)** - MCP interaction guidelines

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

### **Claude Code**

- **Status**: Use `/mcp` command in Claude Code
- **Configuration**: `claude mcp list` and `claude mcp get gandalf`
- **Logs**: Check Claude Code's output for MCP-related messages

### **Cursor IDE**

- **Logs**: View → Output → MCP Logs (set to DEBUG level)
- **Configuration**: Check `~/.cursor/mcp.json`

### **General**

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
- Remove the backwards compatability we have in place.
- Complete the export conversation tool. Add another directory in the home folder under conversation called "imports" that will store imported conversations. These are not stored or ever intended to be stored in the actual agent's database or conversation history, these are just part of the "minas_tirith" component, the library of conversations that are not part of the agent's conversation history.
- Create automation for a "gandalf" user on the system that will run the MCP server and handle the conversation history, and run any cli commands to keep a clean and clear seperaation of access, permissions, and history.
