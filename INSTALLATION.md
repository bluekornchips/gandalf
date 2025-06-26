# Installation

## Requirements

- Python 3.10+
- Git
- Cursor IDE

## Install

```bash
# Check dependencies
./gandalf.sh deps

# Install
./gandalf.sh install

# Restart Cursor completely

# Test
./gandalf.sh test
```

## Verify

In Cursor, ask: "What files are in my project?"

If it doesn't work:

- View → Output → MCP Logs (set to DEBUG)
- Run `./gandalf.sh install -r` and restart Cursor
