"""
Tests for database scanner functionality.

Tests for detecting conversation databases across different tools.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.database_scanner import (
    DatabaseScanner,
    ScanResult,
    ToolType,
    get_available_agentic_tools,
    quick_scan_available_tools,
)


class TestDatabaseScanner(unittest.TestCase):
    """Test DatabaseScanner functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.scanner = DatabaseScanner(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scanner_initialization(self):
        """Test DatabaseScanner initialization."""
        scanner = DatabaseScanner(Path.cwd())
        self.assertEqual(scanner.project_root, Path.cwd())
        self.assertIsInstance(scanner._cache, dict)

    def test_tool_type_enum(self):
        """Test ToolType enum values."""
        self.assertEqual(ToolType.CURSOR.value, "cursor")
        self.assertEqual(ToolType.CLAUDE_CODE.value, "claude-code")
        self.assertEqual(ToolType.WINDSURF.value, "windsurf")

    def test_scan_result_dataclass(self):
        """Test ScanResult dataclass creation."""
        result = ScanResult(
            tool_type=ToolType.CURSOR,
            conversations=[{"id": "test", "title": "Test"}],
            database_path=Path("/test/path"),
            scan_time=1.5,
            error=None,
        )

        self.assertEqual(result.tool_type, ToolType.CURSOR)
        self.assertEqual(len(result.conversations), 1)
        self.assertEqual(result.database_path, Path("/test/path"))
        self.assertEqual(result.scan_time, 1.5)
        self.assertIsNone(result.error)

    def test_scan_result_with_error(self):
        """Test ScanResult with error."""
        result = ScanResult(
            tool_type=ToolType.CURSOR,
            conversations=[],
            database_path=Path(),
            scan_time=0.1,
            error="Database not found",
        )

        self.assertEqual(result.error, "Database not found")
        self.assertEqual(len(result.conversations), 0)

    @patch.object(DatabaseScanner, "_find_database_path")
    def test_scan_tool_databases_no_db_path(self, mock_find_path):
        """Test scan when no database path is found."""
        mock_find_path.return_value = None

        results = self.scanner.scan_tool_databases([ToolType.CURSOR])

        self.assertEqual(len(results), 0)

    @patch.object(DatabaseScanner, "_find_database_path")
    def test_scan_tool_databases_db_not_exists(self, mock_find_path):
        """Test scan when database path doesn't exist."""
        mock_find_path.return_value = Path("/nonexistent/path")

        results = self.scanner.scan_tool_databases([ToolType.CURSOR])

        self.assertEqual(len(results), 0)

    def test_find_database_path_method_exists(self):
        """Test that _find_database_path method exists and is callable."""
        # This is a basic test to ensure the method exists
        result = self.scanner._find_database_path(ToolType.CURSOR)
        # Result could be None or a Path, both are valid
        self.assertTrue(result is None or isinstance(result, Path))

    def test_extract_conversations_method_exists(self):
        """Test that _extract_conversations method exists and returns list."""
        # Create a temporary database file for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            db_path = Path(temp_db.name)

        try:
            result = self.scanner._extract_conversations(ToolType.CURSOR, db_path, 10)
            self.assertIsInstance(result, list)
        finally:
            db_path.unlink(missing_ok=True)


class TestGetAvailableAgenticTools(unittest.TestCase):
    """Test get_available_agentic_tools function."""

    @patch("src.core.database_scanner.timeout_context")
    @patch.object(DatabaseScanner, "_find_database_path")
    def test_get_available_agentic_tools_success(self, mock_find_path, mock_timeout):
        """Test successful detection of available tools."""
        # Mock timeout context to just yield
        mock_timeout.return_value.__enter__ = Mock()
        mock_timeout.return_value.__exit__ = Mock(return_value=None)

        # Mock database path finding
        def mock_find_side_effect(tool_type):
            if tool_type == ToolType.CURSOR:
                # Create a temporary file with sufficient size
                temp_file = Path(tempfile.mktemp(suffix=".db"))
                temp_file.write_bytes(b"x" * 2048)  # > 1KB
                return temp_file
            return None

        mock_find_path.side_effect = mock_find_side_effect

        result = get_available_agentic_tools(silent=True)

        # Should include cursor since it has a database > 1KB
        self.assertIn("cursor", result)

    @patch("src.core.database_scanner.timeout_context")
    def test_get_available_agentic_tools_timeout(self, mock_timeout):
        """Test handling timeout during scanning."""
        mock_timeout.side_effect = TimeoutError("Test timeout")

        result = get_available_agentic_tools(silent=True)

        self.assertEqual(result, [])

    def test_get_available_agentic_tools_silent_mode(self):
        """Test silent mode doesn't raise exceptions."""
        # This should not raise any exceptions even if no tools are found
        result = get_available_agentic_tools(silent=True)
        self.assertIsInstance(result, list)


class TestQuickScanAvailableTools(unittest.TestCase):
    """Test quick_scan_available_tools function."""

    def test_quick_scan_returns_dict(self):
        """Test that quick scan returns proper dictionary structure."""
        result = quick_scan_available_tools()

        self.assertIsInstance(result, dict)
        self.assertIn("available_tools", result)
        self.assertIn("tool_info", result)
        self.assertIn("scan_timestamp", result)

        self.assertIsInstance(result["available_tools"], list)
        self.assertIsInstance(result["tool_info"], dict)
        self.assertIsInstance(result["scan_timestamp"], float)

    @patch.object(DatabaseScanner, "_find_database_path")
    def test_quick_scan_with_databases(self, mock_find_path):
        """Test quick scan when databases are found."""
        # Create a temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db.write(b"x" * 2048)  # > 1KB
            db_path = Path(temp_db.name)

        try:
            # Mock finding this database for cursor
            def mock_find_side_effect(tool_type):
                if tool_type == ToolType.CURSOR:
                    return db_path
                return None

            mock_find_path.side_effect = mock_find_side_effect

            result = quick_scan_available_tools()

            self.assertIn("cursor", result["available_tools"])
            self.assertIn("cursor", result["tool_info"])

            cursor_info = result["tool_info"]["cursor"]
            self.assertIn("database_path", cursor_info)
            self.assertIn("size_bytes", cursor_info)
            self.assertIn("last_modified", cursor_info)

        finally:
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
