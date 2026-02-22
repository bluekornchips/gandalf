# Changelog

## [0.1.0] - 2026-02-22

### Added

- MCP Server: full MCP 2025-06-18 JSON-RPC compliance (`server/`)
- Core tools
  - `echo`: connectivity and health check
  - `get_server_info`: version, capabilities, and status
  - `recall_conversations`: cross-platform conversation aggregation
- Conversation aggregation
  - Cursor IDE: SQLite-backed conversation database with workspace detection
  - Claude Code: JSONL session format with project-specific context
  - Keyword / phrase search and recency scoring
  - Conversation threading support
- Spells: YAML-defined tool definitions (`spells/`) with live file-system reloading
- CLI (`gandalf.sh`): install, uninstall, server lifecycle (start / stop / status / pid), and registry management
- Registry system: auto-detect and register development tools and database paths
- Python packaging: `pyproject.toml` with `setuptools`, `ruff`, `mypy`, and `pytest`
- Test suites: Python unit tests (`pytest`) and shell tests (`bats`), including integration tests

[0.1.0]: https://github.com/bluekornchips/gandalf/releases/tag/v0.1.0
