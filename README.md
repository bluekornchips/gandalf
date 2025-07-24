# Gandalf

Model Context Protocol (MCP) Server for Agentic Development Tools

[![Version](https://img.shields.io/badge/version-2.4.0-blue.svg)](https://github.com/bluekornchips/gandalf/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP%202025--06--18-purple.svg)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-1118%20passing-green.svg)](#testing)

Gandalf aggregates conversations from multiple agentic tools (Cursor, Claude Code, Windsurf) and provides intelligent context for AI-assisted development.

In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

[Quick Start](#quick-start) - [Installation](docs/INSTALLATION.md) - [API Reference](docs/API.md) - [Troubleshooting](docs/TROUBLESHOOTING.md)

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

# Install and configure (auto-detects tools & sets up registry)
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

### Processing Features

- Connection Pooling: SQLite connection pools with health monitoring
- Intelligent Caching: Memory-managed cache with automatic eviction
- Streaming Processing: Memory-efficient file iteration
- Parallel Aggregation: Concurrent processing across multiple tools

### Team Ready

- Relevance Scoring: Multi-point analysis for optimal context prioritization
- Project Awareness: Deep understanding of codebase structure through context intelligence
- MCP 2025-06-18: Latest protocol version with enhanced capabilities
- Robust Error Handling: Comprehensive request validation and error recovery

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

## Usage Guidelines

Gandalf automatically optimizes for different project sizes:

| Project Size             | Recommended Usage | Manual Tuning                            |
| ------------------------ | ----------------- | ---------------------------------------- |
| Small (<50 files)        | Default settings  | `list_project_files()`                   |
| Medium (50-500 files)    | Enable fast mode  | `recall_conversations(fast_mode=true)`   |
| Large (500+ files)       | Limit scope       | `list_project_files(file_types=['.py'])` |
| Enterprise (1000+ files) | Use filtering     | `list_project_files(max_files=1000)`     |

The modular system automatically adapts resource usage based on:

- Available system memory
- Project complexity
- Database sizes
- Tool availability

## Documentation

- [Installation](docs/INSTALLATION.md): Setup instructions for all platforms
- [API Reference](docs/API.md): Complete tool documentation with examples
- [Database Layer](server/src/utils/README.md): Connection pooling and caching implementation
- [Troubleshooting](docs/TROUBLESHOOTING.md): Common issues and solutions
- [Contributing](docs/CONTRIBUTING.md): Development guidelines

## Testing

```bash
# Run all tests
./gandalf test

# Extended validation
./gandalf lembas --all
```

## Commands

```bash
./gandalf install           # Configure MCP & setup registry
./gandalf test              # Run tests
./gandalf lembas            # Full validation
./gandalf registry          # Manage agentic tools registry
./gandalf uninstall         # Remove configuration
```

### Registry Management

```bash
./gandalf registry auto-register    # Auto-detect and register tools
./gandalf registry list             # Show registered tools
./gandalf registry register <tool>  # Register specific tool
./gandalf registry unregister <tool># Remove tool registration
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Documentation: [Installation](docs/INSTALLATION.md) | [API](docs/API.md) | [Troubleshooting](docs/TROUBLESHOOTING.md)

## TODO:

- Complete MCP resource links and embedded resources
- semgrep integration and security automations
- Add log confirmation to the lembas server check to confirm logs are generated and appended
- Fix all the inline imports, move to top of file.