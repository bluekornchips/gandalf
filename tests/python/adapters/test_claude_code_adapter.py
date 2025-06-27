"""
Tests for Claude Code adapter.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.adapters.base import IDEAdapter
from src.adapters.claude_code import ClaudeCodeAdapter


class TestClaudeCodeAdapterBasics:
    """Test basic Claude Code adapter functionality."""

    def test_claude_code_adapter_inheritance(self):
        """Test that ClaudeCodeAdapter inherits from IDEAdapter."""
        adapter = ClaudeCodeAdapter()
        assert isinstance(adapter, IDEAdapter)

    def test_claude_code_adapter_ide_name(self):
        """Test that Claude Code adapter returns correct IDE name."""
        adapter = ClaudeCodeAdapter()
        assert adapter.ide_name == "claude-code"

    def test_claude_code_adapter_initialization(self):
        """Test Claude Code adapter initialization."""
        project_root = Path("/test/project")
        adapter = ClaudeCodeAdapter(project_root)
        assert adapter.project_root == project_root


class TestClaudeCodeAdapterDetection:
    """Test Claude Code IDE detection functionality."""

    @patch.dict(os.environ, {"CLAUDECODE": "1"})
    def test_detect_ide_with_claudecode_env(self):
        """Test IDE detection with CLAUDECODE environment variable."""
        adapter = ClaudeCodeAdapter()
        assert adapter.detect_ide() is True

    @patch.dict(os.environ, {"CLAUDE_CODE_ENTRYPOINT": "cli"})
    def test_detect_ide_with_entrypoint_env(self):
        """Test IDE detection with CLAUDE_CODE_ENTRYPOINT environment variable."""
        adapter = ClaudeCodeAdapter()
        assert adapter.detect_ide() is True

    @patch("subprocess.run")
    def test_detect_ide_with_process(self, mock_run):
        """Test IDE detection when Claude process is running."""
        mock_run.return_value = MagicMock(returncode=0, stdout="claude")

        adapter = ClaudeCodeAdapter()
        assert adapter.detect_ide() is True

    @patch.dict(os.environ, {}, clear=True)
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_detect_ide_nothing_found(self, mock_exists, mock_run):
        """Test IDE detection when nothing is found."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        mock_exists.return_value = False

        adapter = ClaudeCodeAdapter()
        assert adapter.detect_ide() is False


class TestClaudeCodeAdapterProjectRoot:
    """Test Claude Code project root resolution."""

    def test_resolve_project_root_explicit(self):
        """Test resolving project root with explicit path."""
        adapter = ClaudeCodeAdapter()
        explicit_root = "/explicit/root"

        result = adapter.resolve_project_root(explicit_root)
        assert result == Path(explicit_root).resolve()

    @patch.dict(os.environ, {"CLAUDE_PROJECT_ROOT": "/claude/project"})
    def test_resolve_project_root_project_env_var(self):
        """Test resolving project root from environment variable."""
        adapter = ClaudeCodeAdapter()

        result = adapter.resolve_project_root()
        assert result == Path("/claude/project").resolve()

    @patch.dict(os.environ, {}, clear=True)
    @patch("pathlib.Path.exists")
    def test_resolve_project_root_fallback_to_cwd(self, mock_exists):
        """Test resolving project root falls back to current directory."""
        # Mock that no .claude directories exist
        mock_exists.return_value = False

        adapter = ClaudeCodeAdapter()

        result = adapter.resolve_project_root()
        assert result == Path.cwd()


class TestClaudeCodeAdapterConversations:
    """Test Claude Code conversation functionality."""

    def test_get_conversation_tools_not_empty(self):
        """Test getting conversation tool definitions returns available tools."""
        adapter = ClaudeCodeAdapter()
        tools = adapter.get_conversation_tools()

        assert isinstance(tools, dict)
        # Phase 2: Claude Code now supports conversations
        assert len(tools) > 0
        expected_tools = [
            "query_claude_conversations",
            "search_claude_conversations",
            "recall_claude_conversations",
            "search_claude_conversations_enhanced",
        ]
        for tool in expected_tools:
            assert tool in tools

    def test_supports_conversations_true(self):
        """Test that Claude Code adapter now supports conversations."""
        adapter = ClaudeCodeAdapter()
        # Phase 2: Conversation support is now enabled
        assert adapter.supports_conversations() is True


class TestClaudeCodeAdapterConfiguration:
    """Test Claude Code configuration functionality."""

    def test_get_configuration_paths(self):
        """Test getting Claude Code configuration paths."""
        adapter = ClaudeCodeAdapter()
        config_paths = adapter.get_configuration_paths()

        assert isinstance(config_paths, dict)

        expected_keys = [
            "user_home",
            "config_dir",
            "settings",
            "memory",
            "sessions",
            "workspaces",
        ]
        for key in expected_keys:
            assert key in config_paths
            assert isinstance(config_paths[key], Path)
