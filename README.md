# Gandalf

**Agentic Tool Integrator for Development Assistants**

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](https://github.com/bluekornchips/gandalf/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://modelcontextprotocol.io)

Gandalf is a conversation aggregator and Model Context Protocol (MCP) server for intelligent code assistance using agentic tools. With just several core tools, Gandalf provides contextual intelligence that bridges past discussions with current work.

In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

[**Quick Start**](#quick-start) • [**Installation**](docs/INSTALLATION.md) • [**API Reference**](docs/API.md) • [**Troubleshooting**](docs/TROUBLESHOOTING.md)

## Quick Start

**Prerequisites**

- Python 3.10 or higher
- Git (required for repository operations)
- IDE: Cursor IDE, Claude Code, or Windsurf with MCP support

**Installation**

```bash
# Clone and navigate
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf

# Install (auto-detects your IDE)
./gandalf.sh install

# Verify installation
./gandalf.sh test

# Extended verification
./gandalf.sh lembas --all
```

**First Use**

```bash
# Core workflow - always start here
recall_conversations(fast_mode=true, days_lookback=7)

# Get project context for unfamiliar codebases
get_project_info()

# Discover relevant files for multi-file work
list_project_files(max_files=50, file_types=['.py', '.js'])
```

## Key Features

**Cross-Platform Intelligence**

- Unified Context: Aggregates conversations from Cursor IDE, Claude Code, and Windsurf
- Smart Detection: Automatically identifies and configures your development environment
- Zero Configuration: Works out-of-the-box with intelligent defaults

**Performance Optimized**

- Fast Processing: Sub-50ms conversation aggregation
- Intelligent Caching: Smart cache invalidation with file system monitoring
- Scalable Architecture: Adapts to project size automatically

**Core Tools**

- Relevance Scoring: Multi-point analysis for optimal context prioritization
- Project Awareness: Deep understanding of codebase structure

**Enterprise Ready**

- Production Tested: Battle-tested in enterprise environments
- Comprehensive Testing: 90%+ test coverage with automated validation
- Professional Support: Detailed documentation and troubleshooting guides

## The Core Toolkit

**Conversation Intelligence**

- `recall_conversations`: Get recent relevant conversations across all tools (always start here)
- `search_conversations`: Search conversation history for specific topics (finding past solutions)

**Project Context**

- `get_project_info`: Project metadata, Git status, and statistics (unfamiliar projects)
- `list_project_files`: Smart file discovery with relevance scoring (multi-file operations)

**System & Export**

- `get_server_version`: Server version and protocol information (troubleshooting MCP)
- `export_individual_conversations`: Export conversations to files (backup/documentation)

## Supported Development Environments

**Cursor IDE**

- Full conversation history
- Workspace detection
- SQLite integration
- Rich metadata

**Claude Code**

- Session history
- Project-specific context
- JSONL format
- Analysis integration

**Windsurf**

- System metadata
- Session tracking
- Cascade integration
- Memory system
- **Note:** Windsurf uses flow-based interactions; conversational content typically empty by design. Check Cascade Memories and Rules instead.

## Cross-Platform Aggregation

Gandalf automatically detects and combines conversations from all available tools:

- **Zero Configuration**: No setup required; works automatically
- **Unified Context**: All conversations accessible through single interface
- **Intelligent Scoring**: Best solutions prioritized across all tools
- **Fast Processing**: Complete aggregation in ~0.05 seconds

## Documentation

- **[Installation Guide](docs/INSTALLATION.md)**: Complete setup instructions for all platforms
- **[API Reference](docs/API.md)**: Detailed tool documentation with examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[Contributing](docs/CONTRIBUTING.md)**: Development guidelines and standards

## Advanced Usage

**Performance Optimization**

Project Size Guidelines:

- **Small** (<50 files): `max_files=50`
- **Medium** (50-500 files): `max_files=100, fast_mode=true`
- **Large** (500+ files): `max_files=50, file_types=['.py']`

**Global Configuration**

```bash
# Create global alias for convenience
alias gdlf='/path/to/gandalf/gandalf.sh'

# Environment variables
export GANDALF_CACHE_TTL=600
export GANDALF_MAX_FILES=500
export GANDALF_DEBUG=false
```

## Testing & Validation

```bash
# Run comprehensive test suite
./gandalf.sh test

# Run specific test categories
./gandalf.sh test --python    # Python tests only
./gandalf.sh test --shell     # Shell tests only

# Full validation workflow
./gandalf.sh lembas
```

**Test Coverage**

- Python: `pytest`, `unittest` with 90%+ coverage
- Shell: `bats`, inline test blocks
- Integration: End-to-end MCP protocol testing
- Performance: Load testing and benchmarking

## Commands Reference

- `./gandalf.sh deps`: Check system dependencies
- `./gandalf.sh install`: Configure MCP for repository
- `./gandalf.sh test`: Run comprehensive test suite
- `./gandalf.sh lembas`: Full validation workflow
- `./gandalf.sh uninstall`: Remove all configurations

## Contributing

Please see the [Contributing Guidelines](docs/CONTRIBUTING.md) for details.

## License

Licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bluekornchips/gandalf/discussions)

## Notes

- Storing state of MCP tool calls has a significant benefit of pseudo-state management. You could ask the agent to modify a large number of files and have them in a pending commit state. If you then ask the agent to revert back to the original state before creating these changes it will know exactly where to return to without needing git hashes as reference.

## TODO

- Implement persistent disk cache for cross-session performance; add cache warming on project initialization; smart cache invalidation based on file system events
- Validate `gandalf-weights.yaml` on startup and provide helpful error messages for invalid configs
- Add ability to send notifications to the IDE
- Complete the export conversation tool. Add another directory in the home folder under conversation called "imports" that will store imported conversations. These are not stored or ever intended to be stored in the actual agent's database or conversation history, these are just part of the "minas_tirith" component, the library of conversations that are not part of the agent's conversation history.
- Update the recall_conversations to be better optimized for performance. Using tags, filtering, and other methods to make it faster and more efficient and consume less tokens.
- Create automation for a "gandalf" user on the system that will run the MCP server and handle the conversation history, and run any cli commands to keep a clean and clear separation of access, permissions, and history.
