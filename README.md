# Gandalf

Model Context Protocol (MCP) Server for Agentic Development Tools

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/bluekornchips/gandalf/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/protocol-MCP%202025--06--18-purple.svg)](https://modelcontextprotocol.io)

Gandalf aggregates conversations from multiple agentic tools (Cursor, Claude Code) and provides intelligent context for AI-assisted development.

In the Lord of the Rings, Gandalf is a powerful wizard, but he is not omnipotent. He can see much, but there's only so much a maiar can do; that's where we mortals come in.

## Quick Start

### Prerequisites

- Python 3.10+
- Git
- IDE: Cursor or  Claude Code  with MCP support

### Installation

```bash
# Clone repository
git clone https://github.com/bluekornchips/gandalf.git
cd gandalf

# Install and configure (auto-detects tools & sets up registry)
./gandalf.sh --install

# Start the server
./gandalf.sh --server start

# Check server status
./gandalf.sh --server status
```

### First Use

```bash
# Test server connectivity
echo("Hello, Gandalf!")

# Get server information
get_server_info()

# Recall conversations from registered tools
recall_conversations()
```

## Core Features

### MCP Server

- JSON-RPC Protocol: Full MCP 2025-06-18 compliance
- Tool Registry: Dynamic tool registration and management
- Async Processing: Non-blocking tool execution
- Error Handling: Comprehensive request validation and error recovery

### Conversation Aggregation

- Multi-Tool Support: Cursor, Claude Code integration
- Database Detection: Automatic discovery of conversation databases
- Smart Filtering: Keyword-based conversation search
- Export Capabilities: Individual conversation export functionality

### Development Ready

- Zero Configuration: Works immediately with intelligent defaults
- Cross-Platform: Linux, macOS, and Windows support
- CLI Management: Full command-line interface for server control
- Registry System: Tool registration and database path management

## Available Tools

| Tool                   | Purpose                                          | Usage                 |
| ---------------------- | ------------------------------------------------ | --------------------- |
| `echo`                 | Test server connectivity and basic functionality | Development/testing   |
| `get_server_info`      | Server version, capabilities, and status         | Troubleshooting       |
| `recall_conversations` | Cross-platform conversation aggregation          | Primary functionality |

## Supported Development Environments

### Cursor IDE

- SQLite conversation database
- Workspace detection
- Rich metadata support

### Claude Code

- JSONL session format
- Project-specific context
- Analysis integration

## Usage Guidelines

Gandalf provides intelligent conversation aggregation with configurable parameters:

### Conversation Recall

```bash
# Basic conversation recall
recall_conversations()

# Search with keywords
recall_conversations(keywords="python debugging")

# Limit results
recall_conversations(limit=10)

# Include/exclude content types
recall_conversations(include_prompts=true, include_generations=false)
```

### Server Management

```bash
# Start server
./gandalf.sh --server start

# Check status
./gandalf.sh --server status

# Stop server
./gandalf.sh --server stop

# View server PID
./gandalf.sh --server pid
```

## CLI Commands

```bash
# Installation and setup
./gandalf.sh --install       # Install and configure Gandalf
./gandalf.sh --uninstall     # Remove Gandalf configuration

# Server management
./gandalf.sh --server start  # Start the MCP server
./gandalf.sh --server stop   # Stop the MCP server
./gandalf.sh --server status # Check server status
./gandalf.sh --server pid    # Show server process ID

# General
./gandalf.sh --version       # Show version information
./gandalf.sh --help          # Show help
```

### Registry Management

```bash
# Auto-detect and register development tools
./gandalf.sh --registry auto-register

# List registered tools
./gandalf.sh --registry list

# Register specific tool
./gandalf.sh --registry register <tool>

# Unregister tool
./gandalf.sh --registry unregister <tool>
```

## Development

### Project Structure

```
gandalf/
├── cli/                    # Command-line interface
│   ├── bin/                # Executable scripts
│   ├── lib/                # Core library functions
│   └── tests/              # CLI tests
├── server/                 # MCP server implementation
│   ├── src/                # Source code
│   │   ├── tools/          # Tool implementations
│   │   ├── protocol/       # MCP protocol handling
│   │   └── utils/          # Utilities
│   └── tests/              # Server tests
├── spec/                   # Specifications and rules
└── gandalf.sh              # Main CLI entry point
```

### Running Tests

```bash
# Run server tests
cd server && python -m pytest

# Run CLI tests
cd cli && ./tests/bin/install-tests.sh
```

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Support

- Issues: [GitHub Issues](https://github.com/bluekornchips/gandalf/issues)
- Repository: [GitHub Repository](https://github.com/bluekornchips/gandalf)
