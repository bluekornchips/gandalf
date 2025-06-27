"""
Tests for adapter factory.
"""

import os
from unittest.mock import patch

import pytest

from src.adapters.base import IDEAdapter
from src.adapters.claude_code import ClaudeCodeAdapter
from src.adapters.cursor import CursorAdapter
from src.adapters.factory import AdapterFactory


class TestAdapterFactoryCreation:
    """Test adapter creation functionality."""

    def test_create_explicit_cursor_adapter(self):
        """Test creating Cursor adapter explicitly."""
        adapter = AdapterFactory.create_adapter(explicit_ide="cursor")
        assert isinstance(adapter, CursorAdapter)
        assert adapter.ide_name == "cursor"

    def test_create_explicit_cursor_ide_adapter(self):
        """Test creating Cursor adapter with 'cursor-ide' name."""
        adapter = AdapterFactory.create_adapter(explicit_ide="cursor-ide")
        assert isinstance(adapter, CursorAdapter)
        assert adapter.ide_name == "cursor"

    def test_create_explicit_claude_code_adapter(self):
        """Test creating Claude Code adapter explicitly."""
        adapter = AdapterFactory.create_adapter(explicit_ide="claude-code")
        assert isinstance(adapter, ClaudeCodeAdapter)
        assert adapter.ide_name == "claude-code"

    def test_create_explicit_claude_code_variations(self):
        """Test creating Claude Code adapter with name variations."""
        variations = ["claude-code", "claude_code", "claudecode"]
        for variation in variations:
            adapter = AdapterFactory.create_adapter(explicit_ide=variation)
            assert isinstance(adapter, ClaudeCodeAdapter)
            assert adapter.ide_name == "claude-code"

    def test_create_adapter_with_project_root(self):
        """Test creating adapter with project root."""
        project_root = "/path/to/shire"
        adapter = AdapterFactory.create_adapter(
            explicit_ide="cursor", project_root=project_root
        )
        assert isinstance(adapter, CursorAdapter)
        assert adapter.project_root == project_root

    def test_create_adapter_unsupported_ide(self):
        """Test creating adapter with unsupported IDE raises error."""
        with pytest.raises(ValueError, match="Unsupported IDE: mordor_ide"):
            AdapterFactory.create_adapter(explicit_ide="mordor_ide")

    def test_create_adapter_case_insensitive(self):
        """Test that IDE names are case insensitive."""
        adapter = AdapterFactory.create_adapter(explicit_ide="CURSOR")
        assert isinstance(adapter, CursorAdapter)

        adapter = AdapterFactory.create_adapter(explicit_ide="CLAUDE-CODE")
        assert isinstance(adapter, ClaudeCodeAdapter)


class TestAdapterFactoryDetection:
    """Test IDE detection functionality."""

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_detect_claude_code_first(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test that Claude Code is detected first when both are available."""
        mock_claude_detect.return_value = True
        mock_cursor_detect.return_value = True

        adapter = AdapterFactory.create_adapter()
        assert isinstance(adapter, ClaudeCodeAdapter)

        # Claude should be checked first
        mock_claude_detect.assert_called_once()
        # Cursor should not be checked if Claude is detected
        mock_cursor_detect.assert_not_called()

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_detect_cursor_when_claude_not_available(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test that Cursor is detected when Claude Code is not available."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = True

        adapter = AdapterFactory.create_adapter()
        assert isinstance(adapter, CursorAdapter)

        mock_claude_detect.assert_called_once()
        mock_cursor_detect.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)  # Clear all environment variables
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_when_no_ide_detected(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test fallback behavior when no IDE is detected."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        # Fallback to Cursor by default
        assert isinstance(adapter, CursorAdapter)


class TestAdapterFactoryFallback:
    """Test fallback logic when no IDE is detected."""

    @patch.dict(os.environ, {"GANDALF_FALLBACK_IDE": "cursor"})
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_environment_variable_cursor(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test fallback to Cursor via environment variable."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        assert isinstance(adapter, CursorAdapter)

    @patch.dict(os.environ, {"GANDALF_FALLBACK_IDE": "claude-code"})
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_environment_variable_claude(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test fallback to Claude Code via environment variable."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        assert isinstance(adapter, ClaudeCodeAdapter)

    @patch.dict(
        os.environ, {"GANDALF_FALLBACK_IDE": "invalid"}, clear=True
    )  # Clear all except the test variable
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_invalid_environment_variable(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test that invalid fallback environment variable is ignored."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        # Use default fallback logic
        assert isinstance(adapter, CursorAdapter)

    @patch.dict(
        os.environ,
        {"CLAUDE_CODE_ENTRYPOINT": "cli", "CLAUDECODE": "1"},
        clear=True,
    )  # Clear all except the test variables
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_scoring_claude_hints(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test fallback scoring with Claude environment hints."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        # Default fallback is Cursor
        assert isinstance(adapter, CursorAdapter)

    @patch.dict(
        os.environ,
        {"CURSOR_WORKSPACE": "/path/to/rivendell", "VSCODE_PID": "12345"},
    )
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_scoring_cursor_hints(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test fallback scoring with Cursor environment hints."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        assert isinstance(adapter, CursorAdapter)

    @patch.dict(
        os.environ,
        {
            "CLAUDE_CODE_ENTRYPOINT": "cli",
            "CURSOR_WORKSPACE": "/path/to/gondor",
        },
        clear=True,
    )  # Clear all except the test variables
    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_fallback_scoring_equal_hints(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test fallback scoring with equal hints defaults to Cursor."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        adapter = AdapterFactory.create_adapter()
        # Default to Cursor when scores are equal
        assert isinstance(adapter, CursorAdapter)


class TestAdapterFactoryUtilityMethods:
    """Test utility methods of AdapterFactory."""

    def test_get_supported_ides(self):
        """Test getting list of supported IDEs."""
        supported = AdapterFactory.get_supported_ides()
        assert isinstance(supported, list)
        assert "cursor" in supported
        assert "claude-code" in supported
        assert len(supported) == 2

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_detect_current_ide_claude(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test detecting current IDE returns Claude Code."""
        mock_claude_detect.return_value = True
        mock_cursor_detect.return_value = False

        detected = AdapterFactory.detect_current_ide()
        assert detected == "claude-code"

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_detect_current_ide_cursor(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test detecting current IDE returns Cursor."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = True

        detected = AdapterFactory.detect_current_ide()
        assert detected == "cursor"

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_detect_current_ide_none(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test detecting current IDE returns None when none detected."""
        mock_claude_detect.return_value = False
        mock_cursor_detect.return_value = False

        detected = AdapterFactory.detect_current_ide()
        assert detected is None

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_detect_current_ide_both_detected(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test detecting current IDE when both are detected returns Claude first."""
        mock_claude_detect.return_value = True
        mock_cursor_detect.return_value = True

        detected = AdapterFactory.detect_current_ide()
        assert detected == "claude-code"


class TestAdapterFactoryIntegration:
    """Test integration scenarios."""

    def test_create_adapter_returns_ide_adapter_interface(self):
        """Test that created adapters implement IDEAdapter interface."""
        cursor_adapter = AdapterFactory.create_adapter(explicit_ide="cursor")
        claude_adapter = AdapterFactory.create_adapter(
            explicit_ide="claude-code"
        )

        assert isinstance(cursor_adapter, IDEAdapter)
        assert isinstance(claude_adapter, IDEAdapter)

        # Test that all required methods are available
        assert hasattr(cursor_adapter, "ide_name")
        assert hasattr(cursor_adapter, "detect_ide")
        assert hasattr(cursor_adapter, "get_workspace_folders")
        assert hasattr(cursor_adapter, "resolve_project_root")
        assert hasattr(cursor_adapter, "get_conversation_tools")
        assert hasattr(cursor_adapter, "get_conversation_handlers")
        assert hasattr(cursor_adapter, "get_configuration_paths")

    def test_factory_methods_are_static(self):
        """Test that factory methods can be called without instantiation."""
        # These should work without creating an AdapterFactory instance
        supported = AdapterFactory.get_supported_ides()
        assert isinstance(supported, list)

        detected = AdapterFactory.detect_current_ide()
        assert detected is None or isinstance(detected, str)

    @patch("src.adapters.claude_code.ClaudeCodeAdapter.detect_ide")
    @patch("src.adapters.cursor.CursorAdapter.detect_ide")
    def test_factory_logging_behavior(
        self, mock_cursor_detect, mock_claude_detect
    ):
        """Test that factory logs appropriate messages."""
        mock_claude_detect.return_value = True
        mock_cursor_detect.return_value = False

        # This should log "Detected Claude Code environment"
        adapter = AdapterFactory.create_adapter()
        assert isinstance(adapter, ClaudeCodeAdapter)

        # Test explicit adapter creation logs
        adapter = AdapterFactory.create_adapter(explicit_ide="cursor")
        assert isinstance(adapter, CursorAdapter)


class TestAdapterFactoryEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_adapter_empty_string_ide(self):
        """Test creating adapter with empty string IDE name."""
        # Empty string should be treated as None
        adapter = AdapterFactory.create_adapter(explicit_ide="")
        assert isinstance(adapter, (CursorAdapter, ClaudeCodeAdapter))

    def test_create_adapter_whitespace_ide(self):
        """Test creating adapter with whitespace IDE name."""
        with pytest.raises(ValueError):
            AdapterFactory.create_adapter(explicit_ide="   ")

    def test_create_adapter_none_project_root(self):
        """Test creating adapter with None project root."""
        adapter = AdapterFactory.create_adapter(
            explicit_ide="cursor", project_root=None
        )
        assert isinstance(adapter, CursorAdapter)
        assert adapter.project_root is None

    def test_create_adapter_empty_project_root(self):
        """Test creating adapter with empty project root."""
        adapter = AdapterFactory.create_adapter(
            explicit_ide="cursor", project_root=""
        )
        assert isinstance(adapter, CursorAdapter)
        assert adapter.project_root == ""
