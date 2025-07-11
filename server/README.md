# Gandalf Server

Python MCP server implementation.

## Architecture

```
src/
├── main.py           # Server entry point
├── config/           # Configuration and validation
├── core/             # Business logic
├── tool_calls/       # MCP tool implementations
└── utils/            # Caching and utilities
```

## Development

```bash
# Setup
pip install -r requirements.txt

# Test with coverage
pytest --cov=src --cov-report=html

# Format
black src/ && isort src/ && flake8 src/
```
