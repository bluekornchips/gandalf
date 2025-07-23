"""
Tests for database scanner functionality.

Tests for detecting conversation databases across different tools.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.database_counter import ConversationCounter
from src.core.database_scanner import (
    ConversationDatabase,
    DatabaseScanner,
    get_available_agentic_tools,
)


class TestConversationDatabase(unittest.TestCase):
    """Test ConversationDatabase data class."""

    def test_conversation_database_creation(self):
        """Test creating a ConversationDatabase instance."""
        db = ConversationDatabase(
            path="/path/to/db.sqlite",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1234567890.0,
            conversation_count=42,
            is_accessible=True,
        )

        self.assertEqual(db.path, "/path/to/db.sqlite")
        self.assertEqual(db.tool_type, "cursor")
        self.assertEqual(db.size_bytes, 1024)
        self.assertEqual(db.last_modified, 1234567890.0)
        self.assertEqual(db.conversation_count, 42)
        self.assertTrue(db.is_accessible)
        self.assertIsNone(db.error_message)

    def test_conversation_database_with_error(self):
        """Test creating a ConversationDatabase with error."""
        db = ConversationDatabase(
            path="/path/to/broken.db",
            tool_type="claude-code",
            size_bytes=0,
            last_modified=0.0,
            conversation_count=None,
            is_accessible=False,
            error_message="Permission denied",
        )

        self.assertEqual(db.path, "/path/to/broken.db")
        self.assertEqual(db.tool_type, "claude-code")
        self.assertFalse(db.is_accessible)
        self.assertEqual(db.error_message, "Permission denied")


class TestDatabaseScanner(unittest.TestCase):
    """Test DatabaseScanner functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.scanner = DatabaseScanner(project_root=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        from src.utils.database_pool import close_database_pool

        close_database_pool()

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scanner_initialization(self):
        """Test DatabaseScanner initialization."""
        scanner = DatabaseScanner()
        self.assertEqual(scanner.config.project_root, Path.cwd())
        self.assertEqual(scanner.databases, [])
        self.assertIsNotNone(scanner.config.cache_ttl)

        custom_scanner = DatabaseScanner(project_root=self.temp_dir)
        self.assertEqual(custom_scanner.config.project_root, self.temp_dir)

    @patch("src.core.database_scanner.log_debug")
    def test_count_conversations_sqlite_success(self, mock_log):
        """Test counting conversations in SQLite database successfully."""
        # Create a mock SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            db_path = Path(temp_db.name)

        try:
            # Create a simple database with conversations table
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "CREATE TABLE conversations (id INTEGER PRIMARY KEY, text TEXT)"
                )
                cursor.execute(
                    "INSERT INTO conversations (text) VALUES ('Frodo needs help with the One Ring')"
                )
                cursor.execute(
                    "INSERT INTO conversations (text) VALUES ('Gandalf provides guidance in Rivendell')"
                )
                conn.commit()

            count = ConversationCounter.count_conversations_sqlite(db_path)
            self.assertEqual(count, 2)

        finally:
            db_path.unlink(missing_ok=True)

    @patch("src.core.database_counter.log_error")
    def test_count_conversations_sqlite_failure(self, mock_log):
        """Test counting conversations when SQLite fails."""
        # Create a file that's not a valid SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db.write(b"This is not a valid SQLite database")
            db_path = Path(temp_db.name)

        try:
            count = ConversationCounter.count_conversations_sqlite(db_path)
            self.assertIsNone(count)
            mock_log.assert_called()

        finally:
            db_path.unlink(missing_ok=True)

    def test_count_conversations_sqlite_no_tables(self):
        """Test counting conversations when no recognizable tables exist."""
        # Create a valid SQLite database but with no conversation tables
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            db_path = Path(temp_db.name)

        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE unrelated_table (id INTEGER PRIMARY KEY)")
                conn.commit()

            count = ConversationCounter.count_conversations_sqlite(db_path)
            self.assertEqual(count, 0)

        finally:
            db_path.unlink(missing_ok=True)

    @patch.object(DatabaseScanner, "_scan_tool_databases")
    def test_scan_all_tools(self, mock_scan_tool):
        """Test scanning all supported tools."""
        cursor_db = ConversationDatabase(
            path="/cursor/path.vscdb",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1000.0,
            conversation_count=5,
        )
        claude_db = ConversationDatabase(
            path="/claude/session.json",
            tool_type="claude-code",
            size_bytes=512,
            last_modified=2000.0,
            conversation_count=3,
        )

        # Mock _scan_tool_databases to return different results based on tool_type
        def mock_scan_side_effect(tool_type):
            if tool_type == "cursor":
                return [cursor_db]
            elif tool_type == "claude-code":
                return [claude_db]
            else:  # windsurf
                return []

        mock_scan_tool.side_effect = mock_scan_side_effect

        databases = self.scanner.scan()

        self.assertEqual(len(databases), 2)
        # Note: Order may vary based on tool scanning order
        db_paths = {db.path for db in databases}
        self.assertIn("/cursor/path.vscdb", db_paths)
        self.assertIn("/claude/session.json", db_paths)

    def test_scan_uses_cache(self):
        """Test that scan uses cache when appropriate."""
        # Mock some databases
        mock_db = ConversationDatabase(
            path="/test/path.db",
            tool_type="cursor",
            size_bytes=100,
            last_modified=1000.0,
            conversation_count=1,
        )

        # Mock cache to return databases
        with patch.object(
            self.scanner.cache, "get_cached_databases", return_value=[mock_db]
        ):
            with patch.object(self.scanner, "_scan_tool_databases") as mock_scan:
                databases = self.scanner.scan()
                mock_scan.assert_not_called()
                self.assertEqual(databases, [mock_db])

    def test_scan_force_rescan(self):
        """Test forcing a rescan ignores cache."""
        mock_db = ConversationDatabase(
            path="/test/path.db",
            tool_type="cursor",
            size_bytes=100,
            last_modified=1000.0,
            conversation_count=1,
        )

        self.scanner.databases = [mock_db]
        self.scanner._last_scan_time = 1000.0

        with patch("time.time", return_value=1100.0):  # Within TTL
            with patch.object(self.scanner, "_scan_tool_databases", return_value=[]):
                databases = self.scanner.scan(force_rescan=True)
                self.assertEqual(databases, [])

    def test_get_databases_by_tool(self):
        """Test filtering databases by tool type."""
        cursor_db = ConversationDatabase(
            path="/cursor/path.vscdb",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1000.0,
            conversation_count=5,
        )
        claude_db = ConversationDatabase(
            path="/claude/session.json",
            tool_type="claude-code",
            size_bytes=512,
            last_modified=2000.0,
            conversation_count=3,
        )

        self.scanner.databases = [cursor_db, claude_db]

        cursor_dbs = self.scanner.get_databases_by_tool("cursor")
        self.assertEqual(cursor_dbs, [cursor_db])

        claude_dbs = self.scanner.get_databases_by_tool("claude-code")
        self.assertEqual(claude_dbs, [claude_db])

        unknown_dbs = self.scanner.get_databases_by_tool("unknown")
        self.assertEqual(unknown_dbs, [])

    @patch.object(DatabaseScanner, "_scan_tool_databases")
    def test_get_summary_empty(self, mock_scan_tool):
        """Test getting summary with no databases."""
        # Mock empty scan results for all tool types
        mock_scan_tool.return_value = []

        summary = self.scanner.get_summary()

        # Check all fields except the dynamic cache_info
        self.assertEqual(summary["total_databases"], 0)
        self.assertEqual(summary["accessible_databases"], 0)
        self.assertEqual(summary["databases_with_conversations"], 0)
        self.assertEqual(summary["total_conversations"], 0)
        self.assertEqual(summary["tools"], {})
        self.assertIn("cache_info", summary)
        self.assertIsInstance(summary["cache_info"], dict)

    def test_get_summary_with_databases(self):
        """Test getting summary with various databases."""
        cursor_db1 = ConversationDatabase(
            path="/cursor/db1.vscdb",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1000.0,
            conversation_count=5,
            is_accessible=True,
        )
        cursor_db2 = ConversationDatabase(
            path="/cursor/db2.vscdb",
            tool_type="cursor",
            size_bytes=512,
            last_modified=2000.0,
            conversation_count=None,
            is_accessible=False,
        )
        claude_db = ConversationDatabase(
            path="/claude/session.json",
            tool_type="claude-code",
            size_bytes=256,
            last_modified=3000.0,
            conversation_count=3,
            is_accessible=True,
        )

        self.scanner.databases = [cursor_db1, cursor_db2, claude_db]
        summary = self.scanner.get_summary()

        # Check top-level summary fields
        self.assertEqual(summary["total_databases"], 3)
        self.assertEqual(summary["accessible_databases"], 2)
        self.assertEqual(summary["databases_with_conversations"], 2)
        self.assertEqual(summary["total_conversations"], 8)  # 5 + 0 + 3

        # Check tools section
        self.assertIn("cursor", summary["tools"])
        self.assertIn("claude-code", summary["tools"])

        cursor_info = summary["tools"]["cursor"]
        self.assertEqual(cursor_info["database_count"], 2)
        self.assertEqual(cursor_info["accessible_count"], 1)
        self.assertEqual(cursor_info["with_conversations"], 1)
        self.assertEqual(cursor_info["conversation_count"], 5)
        self.assertIn("total_size_mb", cursor_info)

        claude_info = summary["tools"]["claude-code"]
        self.assertEqual(claude_info["database_count"], 1)
        self.assertEqual(claude_info["accessible_count"], 1)
        self.assertEqual(claude_info["with_conversations"], 1)
        self.assertEqual(claude_info["conversation_count"], 3)
        self.assertIn("total_size_mb", claude_info)

        # Check cache_info exists (dynamic content)
        self.assertIn("cache_info", summary)
        self.assertIsInstance(summary["cache_info"], dict)

    def test_get_summary_only_includes_tools_with_databases(self):
        """Test that summary only includes tools that have databases."""
        # Create database for only one tool type
        cursor_db = ConversationDatabase(
            path="/cursor/db.vscdb",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1000.0,
            conversation_count=5,
            is_accessible=True,
        )

        self.scanner.databases = [cursor_db]
        summary = self.scanner.get_summary()

        # Should only include cursor in tools section
        self.assertIn("cursor", summary["tools"])
        self.assertNotIn("claude-code", summary["tools"])

    def test_get_summary_handles_unknown_tool_types(self):
        """Test that summary handles unknown tool types gracefully."""
        # Add a database with a tool type not in SUPPORTED_AGENTIC_TOOLS
        unknown_db = ConversationDatabase(
            path="/unknown/db.xyz",
            tool_type="unknown-tool",
            size_bytes=100,
            last_modified=1000.0,
            conversation_count=1,
            is_accessible=True,
        )

        self.scanner.databases = [unknown_db]
        summary = self.scanner.get_summary()

        # Should not appear in tools section since it's not in SUPPORTED_AGENTIC_TOOLS
        self.assertNotIn("unknown-tool", summary["tools"])
        self.assertEqual(summary["total_databases"], 1)
        self.assertEqual(summary["total_conversations"], 1)


class TestGetAvailableAgenticTools(unittest.TestCase):
    """Test get_available_agentic_tools function."""

    @patch("src.core.database_scanner.DatabaseScanner")
    def test_get_available_agentic_tools_success(self, mock_scanner_class):
        """Test successful detection of available tools."""
        # Mock scanner and databases
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner

        cursor_db = ConversationDatabase(
            path="/cursor/db.vscdb",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1000.0,
            conversation_count=5,
            is_accessible=True,
        )
        claude_db = ConversationDatabase(
            path="/claude/session.json",
            tool_type="claude-code",
            size_bytes=512,
            last_modified=2000.0,
            conversation_count=3,
            is_accessible=True,
        )

        mock_scanner.scan.return_value = [cursor_db, claude_db]

        result = get_available_agentic_tools()

        self.assertEqual(set(result), {"cursor", "claude-code"})

    @patch("src.core.database_scanner.DatabaseScanner")
    def test_get_available_agentic_tools_no_accessible_databases(
        self, mock_scanner_class
    ):
        """Test when no accessible databases are found."""
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner

        # Create inaccessible database
        inaccessible_db = ConversationDatabase(
            path="/cursor/broken.vscdb",
            tool_type="cursor",
            size_bytes=0,
            last_modified=1000.0,
            conversation_count=None,
            is_accessible=False,
        )

        mock_scanner.scan.return_value = [inaccessible_db]

        result = get_available_agentic_tools()

        self.assertEqual(result, [])

    @patch("src.core.database_scanner.DatabaseScanner")
    def test_get_available_agentic_tools_zero_conversations(self, mock_scanner_class):
        """Test when databases have zero conversations."""
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner

        # Create database with zero conversations
        empty_db = ConversationDatabase(
            path="/cursor/empty.vscdb",
            tool_type="cursor",
            size_bytes=100,
            last_modified=1000.0,
            conversation_count=0,
            is_accessible=True,
        )

        mock_scanner.scan.return_value = [empty_db]

        result = get_available_agentic_tools()

        self.assertEqual(result, [])

    @patch("src.core.database_scanner.DatabaseScanner")
    @patch("src.core.database_scanner.log_error")
    def test_get_available_agentic_tools_exception(self, mock_log, mock_scanner_class):
        """Test handling exceptions during scanning."""
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan.side_effect = OSError("Scan failed")

        result = get_available_agentic_tools()

        self.assertEqual(result, [])
        mock_log.assert_called()

    @patch("src.core.database_scanner.DatabaseScanner")
    def test_get_available_agentic_tools_silent_mode(self, mock_scanner_class):
        """Test silent mode doesn't log."""
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan.return_value = []

        with patch("src.core.database_scanner.log_info") as mock_log:
            result = get_available_agentic_tools(silent=True)

            self.assertEqual(result, [])
            mock_log.assert_not_called()

    @patch("src.core.database_scanner.DatabaseScanner")
    def test_get_available_agentic_tools_removes_duplicates(self, mock_scanner_class):
        """Test that duplicate tool types are removed."""
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner

        # Create multiple databases for same tool type
        cursor_db1 = ConversationDatabase(
            path="/cursor/db1.vscdb",
            tool_type="cursor",
            size_bytes=1024,
            last_modified=1000.0,
            conversation_count=5,
            is_accessible=True,
        )
        cursor_db2 = ConversationDatabase(
            path="/cursor/db2.vscdb",
            tool_type="cursor",
            size_bytes=512,
            last_modified=2000.0,
            conversation_count=3,
            is_accessible=True,
        )

        mock_scanner.scan.return_value = [cursor_db1, cursor_db2]

        result = get_available_agentic_tools()

        # Should only return "cursor" once, even though there are two databases
        self.assertEqual(result, ["cursor"])
