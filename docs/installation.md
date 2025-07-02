# Installation Guide

Complete installation instructions for Gandalf, a conversation aggregator and MCP Server that provides unified intelligence across Cursor IDE, Claude Code, and Windsurf.

## Requirements

### System Requirements

- **Operating System**: macOS, Linux, or Windows (via WSL2)
- **Python**: Version 3.10 or higher
- **Git**: Required for repository analysis
- **Supported Tools**: Cursor IDE, Claude Code, or Windsurf with MCP support

### Verify Prerequisites

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check Git availability
git --version

# Check MCP support in your development tool
# Cursor: Settings > Extensions > Model Context Protocol
# Claude Code: ~/.claude/mcp.json should be configurable
# Windsurf: Settings > Extensions > Model Context Protocol
```

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone git@github.com:bluekornchips/gandalf.git
cd gandalf

# Automatic installation (detects your environment)
./gandalf.sh install

# Test installation
./gandalf.sh test
```

The install script automatically:

- Detects your development tool (Cursor IDE, Claude Code, or Windsurf)
- Installs Python dependencies
- Configures MCP integration
- Creates necessary configuration files

### Method 2: Manual Installation

If automatic installation fails, follow these steps:

#### 1. Python Environment Setup

```bash
cd gandalf
python3 -m venv .venv
source .venv/bin/activate
cd server
pip install -r requirements.txt
```

#### 2. Tool Configuration

**For Cursor IDE:**

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/absolute/path/to/gandalf/gandalf.sh",
      "args": ["run"]
    }
  }
}
```

**For Claude Code:**

Use the Claude CLI to add the server:

```bash
# Add gandalf MCP server globally
claude mcp add gandalf /absolute/path/to/gandalf/gandalf.sh -s user run \
  -e "PYTHONPATH=/absolute/path/to/gandalf/server" \
  -e "CLAUDECODE=1" \
  -e "CLAUDE_CODE_ENTRYPOINT=cli"
```

Or manually create/edit `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/absolute/path/to/gandalf/gandalf.sh",
      "args": ["run"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/gandalf/server",
        "CLAUDECODE": "1",
        "CLAUDE_CODE_ENTRYPOINT": "cli"
      }
    }
  }
}
```

**For Windsurf:**

Create or edit `~/.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "gandalf": {
      "command": "/absolute/path/to/gandalf/gandalf.sh",
      "args": ["run"]
    }
  }
}
```

**Note about Windsurf**: Windsurf uses Cascade AI with flow-based interactions rather than traditional chat conversations. While Gandalf can detect Windsurf and provide system metadata, conversational content will typically be empty by design. For Windsurf context, check Cascade Memories and Rules instead.

#### 3. Restart Your Development Tool

Completely restart your development tool to load the new MCP configuration.

## Verification

### Test MCP Server

```bash
# Test server directly
cd gandalf
echo '{"method": "tools/list"}' | ./gandalf.sh run

# Expected output: List of available tools
```

### Test in Your Development Tool

Ask your AI assistant:

- "What files are in my project?"
- "Show me recent conversations"
- "Get project information"

### Troubleshooting Commands

```bash
# Check installation status
./gandalf.sh test

# Run diagnostic tests
./gandalf.sh lembas

# Reinstall if needed
./gandalf.sh install -r
```

## Configuration Options

### Performance Settings

Large projects can benefit from configuration tuning. Add to your development tool's MCP config:

```json
{
  "gandalf": {
    "command": "/absolute/path/to/gandalf/gandalf.sh",
    "args": ["run"],
    "env": {
      "GANDALF_CACHE_TTL": "600",
      "GANDALF_MAX_FILES": "500"
    }
  }
}
```

## Environment Variables

| Variable               | Default     | Description                   |
| ---------------------- | ----------- | ----------------------------- |
| `GANDALF_CACHE_TTL`    | 300         | Cache lifetime in seconds     |
| `GANDALF_MAX_FILES`    | 1000        | Max files to analyze          |
| `GANDALF_DEBUG`        | false       | Enable debug logging          |
| `GANDALF_FALLBACK_IDE` | claude-code | Fallback when detection fails |

## Multi-Tool Setup

Gandalf can work with Cursor IDE, Claude Code, and Windsurf simultaneously:

1. Install normally: automatic detection handles all supported tools
2. Each tool gets its own configuration: no conflicts
3. Shared cache: improved performance

## Remote Development

### SSH/Remote Servers

When working remotely:

```bash
# Install Gandalf on the remote server
git clone <repository-url>
cd gandalf
./gandalf.sh install
```

**Important**: Conversation data availability varies by tool:

- Each development tool session (local vs remote) maintains separate MCP configurations; Gandalf must be installed separately in each environment.

## Advanced Installation

### Global Access

```bash
# Install with reset for global access
./gandalf.sh install -r

# Add alias for convenience
echo 'alias gdlf="/path/to/gandalf/gandalf.sh"' >> ~/.bashrc
source ~/.bashrc
```

### Force Specific Tool

```bash
# Force Cursor IDE configuration
./gandalf.sh install --tool cursor

# Force Claude Code configuration
./gandalf.sh install --tool claude-code
```

### Uninstall

```bash
# Remove all configurations (preserves conversation history)
./gandalf.sh uninstall

# Force removal without prompts
./gandalf.sh uninstall -f
```
