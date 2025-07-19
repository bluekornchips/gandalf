# Gandalf

Model Context Protocol (MCP) Server for Agentic Development Tools

[![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)](https://github.com/bluekornchips/gandalf/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-1118%20passing-green.svg)](#testing)

Gandalf aggregates conversations from multiple agentic tools (Cursor, Claude Code, Windsurf) and provides intelligent context for AI-assisted development.

In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

[**Quick Start**](#quick-start) - [**Installation**](docs/INSTALLATION.md) - [**API Reference**](docs/API.md) - [**Troubleshooting**](docs/TROUBLESHOOTING.md)

## Quick Start

### Prerequisites

- Python 3.12+
- Git
- IDE: Cursor, Claude Code, or Windsurf with MCP support

### Installation

```bash
# Clone repository
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf

# Install and configure
./gandalf install

# Verify installation
./gandalf test

# Extended verification
./gandalf lembas --all
```

### First Use

```bash
# Start with conversation recall
recall_conversations()

# Get project context
get_project_info()

# Find relevant files
list_project_files()
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
| `get_server_version`              | Server version and protocol info            | Troubleshooting       |

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
- Flow-based architecture

## Performance Guidelines

| Project Size          | Configuration    | Example                                  |
| --------------------- | ---------------- | ---------------------------------------- |
| Small (<50 files)     | Default settings | `list_project_files()`                   |
| Medium (50-500 files) | Enable fast mode | `recall_conversations(fast_mode=true)`   |
| Large (500+ files)    | Limit scope      | `list_project_files(file_types=['.py'])` |

## Documentation

- [Installation](docs/INSTALLATION.md): Setup instructions for all platforms
- [API Reference](docs/API.md): Complete tool documentation with examples
- [Troubleshooting](docs/TROUBLESHOOTING.md): Common issues and solutions
- [Contributing](docs/CONTRIBUTING.md): Development guidelines

## Testing

```bash
# Run all tests
./gandalf test

# Extended validation
./gandalf lembas --all
```

Test Coverage: 1,118 tests (171 shell + 947 Python) with 90%+ coverage

## Commands

```bash
./gandalf install     # Configure MCP
./gandalf test        # Run tests
./gandalf lembas      # Full validation
./gandalf uninstall   # Remove configuration
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Documentation: [Installation](docs/INSTALLATION.md) | [API](docs/API.md) | [Troubleshooting](docs/TROUBLESHOOTING.md)


## TODO:
- Convert to flask server to serve requests.
- Add ability to send notifications to the IDE
- semgrep, random automations?
