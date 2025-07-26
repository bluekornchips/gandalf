"""
Tests for tool registry functionality.

Tests for the simplified tool registry that manages agentic tool registration.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.tool_registry import (
    get_available_tools,
    get_registered_agentic_tools,
)


class TestToolRegistry(unittest.TestCase):
    """Test simplified tool registry functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_available_tools_returns_list(self):
        """Test that get_available_tools returns a list."""
        result = get_available_tools(self.temp_dir)
        self.assertIsInstance(result, list)

    def test_get_registered_agentic_tools_returns_list(self):
        """Test that get_registered_agentic_tools returns a list."""
        result = get_registered_agentic_tools()
        self.assertIsInstance(result, list)

    @patch("src.core.tool_registry.DatabaseScanner")
    def test_get_available_tools_with_mock_scanner(self, mock_scanner_class):
        """Test get_available_tools with mocked scanner."""
        # Mock scanner instance
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner

        # Mock _find_database_path to return a path for cursor
        from src.core.database_scanner import ToolType

        def mock_find_path(tool_type):
            if tool_type == ToolType.CURSOR:
                return Path("/mock/cursor/path")
            return None

        mock_scanner._find_database_path.side_effect = mock_find_path

        result = get_available_tools(self.temp_dir)

        # Should include cursor since it has a database path
        self.assertIn("cursor", result)

        # Verify scanner was created with correct project root
        mock_scanner_class.assert_called_once_with(self.temp_dir)

    @patch("src.core.tool_registry.get_available_tools")
    def test_get_registered_agentic_tools_delegates(self, mock_get_available):
        """Test that get_registered_agentic_tools delegates to get_available_tools."""
        mock_get_available.return_value = ["cursor", "claude-code"]

        result = get_registered_agentic_tools()

        self.assertEqual(result, ["cursor", "claude-code"])
        mock_get_available.assert_called_once_with(Path.cwd())

    def test_get_available_tools_empty_project(self):
        """Test get_available_tools with empty project directory."""
        # Create empty temporary directory
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        result = get_available_tools(empty_dir)

        # Should return empty list for empty project
        self.assertIsInstance(result, list)

    @patch("src.core.tool_registry.DatabaseScanner")
    def test_get_available_tools_handles_scanner_exception(self, mock_scanner_class):
        """Test get_available_tools handles scanner exceptions gracefully."""
        # Mock scanner to raise exception
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner._find_database_path.side_effect = Exception("Scanner error")

        # Should not raise exception, should return empty list
        result = get_available_tools(self.temp_dir)
        self.assertIsInstance(result, list)
