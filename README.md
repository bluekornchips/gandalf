# Gandalf

Model Context Protocol (MCP) Server for Agentic Development Tools

[![Version](https://img.shields.io/badge/version-2.2.0-blue.svg)](https://github.com/bluekornchips/gandalf/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-1107%20passing-green.svg)](#testing)

Gandalf is a conversation aggregator and Model Context Protocol (MCP) server for intelligent code assistance using agentic tools. With several core tools, Gandalf provides contextual intelligence that bridges past discussions with current work.

In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

[**Quick Start**](#quick-start) - [**Installation**](INSTALLATION.md) - [**API Reference**](API.md) - [**Troubleshooting**](TROUBLESHOOTING.md)

## Quick Start

### Prerequisites

- Python 3.10+
- Git
- IDE: Cursor, Claude Code, or Windsurf with MCP support

### Installation

```bash
# Clone repository
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf

# Install
./gandalf.sh install

# Verify installation
./gandalf.sh test

# Extended verification
./gandalf.sh lembas --all
```

### First Use

```bash
# Start with conversation recall
recall_conversations(fast_mode=true, days_lookback=7)

# Get project context
get_project_info()

# Find relevant files
list_project_files(max_files=50, file_types=['.py', '.js'])
```

## Core Features

### Cross-Platform Intelligence

- Unified Context: Aggregates conversations from all supported tools
- Smart Detection: Auto-configures development environment
- Zero Configuration: Works immediately with intelligent defaults

### Performance Optimized

- Fast Processing: Sub-50ms conversation aggregation
- Intelligent Caching: File system monitoring with cache invalidation
- Scalable Architecture: Adapts to project size automatically

### Enterprise Ready

- Relevance Scoring: Multi-point analysis for optimal context prioritization
- Project Awareness: Deep understanding of codebase structure

## Essential Tools

| Tool                              | Purpose                                     | Usage                 |
| --------------------------------- | ------------------------------------------- | --------------------- |
| `recall_conversations`            | Cross-platform conversation aggregation     | Always start here     |
| `get_project_info`                | Project metadata and Git status             | Unfamiliar projects   |
| `list_project_files`              | Smart file discovery with relevance scoring | Multi-file operations |
| `export_individual_conversations` | Export conversations to files               | Backup/documentation  |

## Supported Development Environments

### Cursor IDE

- SQLite conversation database
- Workspace detection
- Rich metadata support

### Claude Code

- JSONL session format
- Project-specific context
- Analysis integration

### Windsurf

- State database integration
- Session tracking
- Cascade system support
- Note: Conversations may appear empty due to flow-based architecture

## Documentation

- [Installation](INSTALLATION.md): Setup instructions for all platforms
- [API Reference](API.md): Complete tool documentation with examples
- [Troubleshooting](TROUBLESHOOTING.md): Common issues and solutions
- [Contributing](CONTRIBUTING.md): Development guidelines

## Performance Guidelines

| Project Size          | Configuration    | Example                                                |
| --------------------- | ---------------- | ------------------------------------------------------ |
| Small (<50 files)     | Default settings | `list_project_files(max_files=50)`                     |
| Medium (50-500 files) | Enable fast mode | `recall_conversations(fast_mode=true)`                 |
| Large (500+ files)    | Limit scope      | `list_project_files(max_files=50, file_types=['.py'])` |

## Testing

```bash
# Run all tests
./gandalf.sh test

# Extended validation
./gandalf.sh lembas --all

# Test specific components
./gandalf.sh test --python    # Python tests only
./gandalf.sh test --shell     # Shell tests only
```

Test Coverage: 1,107 tests (160 shell + 947 Python) with 90%+ coverage

## Commands

```bash
./gandalf.sh deps        # Check dependencies
./gandalf.sh install     # Configure MCP
./gandalf.sh test        # Run tests
./gandalf.sh lembas      # Full validation
./gandalf.sh uninstall   # Remove configuration
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Discussions: [GitHub Discussions](https://github.com/bluekornchips/gandalf/discussions)
- Documentation: [Installation](INSTALLATION.md) | [API](API.md) | [Troubleshooting](TROUBLESHOOTING.md)
