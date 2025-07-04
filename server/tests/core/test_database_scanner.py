"""
Tests for database scanner functionality.

Tests for detecting conversation databases across different tools.
"""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.database_scanner import (
    ConversationDatabase,
    DatabaseScanner,
    get_available_agentic_tools,
)
from src.config.constants import SUPPORTED_AGENTIC_TOOLS


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

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scanner_initialization(self):
        """Test DatabaseScanner initialization."""
        scanner = DatabaseScanner()
        self.assertEqual(scanner.project_root, Path.cwd())
        self.assertEqual(scanner.databases, [])
        self.assertEqual(scanner._cache_ttl, 300.0)

        custom_scanner = DatabaseScanner(project_root=self.temp_dir)
        self.assertEqual(custom_scanner.project_root, self.temp_dir)

    def test_should_rescan_initial(self):
        """Test should_rescan returns True initially."""
        self.assertTrue(self.scanner._should_rescan())

    def test_should_rescan_after_scan(self):
        """Test should_rescan returns False immediately after scan."""
        self.scanner._last_scan_time = 1000.0
        with patch("time.time", return_value=1200.0):  # 200s later, within TTL
            self.assertFalse(self.scanner._should_rescan())

    def test_should_rescan_after_ttl(self):
        """Test should_rescan returns True after TTL expires."""
        self.scanner._last_scan_time = 1000.0
        with patch("time.time", return_value=1400.0):  # 400s later, beyond TTL
            self.assertTrue(self.scanner._should_rescan())

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
                cursor.execute("INSERT INTO conversations (text) VALUES ('Hello')")
                cursor.execute("INSERT INTO conversations (text) VALUES ('World')")
                conn.commit()

            count = self.scanner._count_conversations_sqlite(db_path)
            self.assertEqual(count, 2)

        finally:
            db_path.unlink(missing_ok=True)

    @patch("src.core.database_scanner.log_error")
    def test_count_conversations_sqlite_failure(self, mock_log):
        """Test counting conversations when SQLite fails."""
        # Create a file that's not a valid SQLite database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_db.write(b"This is not a valid SQLite database")
            db_path = Path(temp_db.name)

        try:
            count = self.scanner._count_conversations_sqlite(db_path)
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

            count = self.scanner._count_conversations_sqlite(db_path)
            self.assertEqual(count, 0)

        finally:
            db_path.unlink(missing_ok=True)

    @patch("src.core.database_scanner.CURSOR_SCANNER_PATHS")
    def test_scan_cursor_databases_no_paths(self, mock_cursor_paths):
        """Test scanning Cursor databases when no paths exist."""
        mock_cursor_paths.__iter__.return_value = iter(
            [self.temp_dir / "nonexistent1", self.temp_dir / "nonexistent2"]
        )
        databases = self.scanner._scan_cursor_databases()
        self.assertEqual(databases, [])

    @patch("src.core.database_scanner.CURSOR_SCANNER_PATHS")
    def test_scan_cursor_databases_with_files(self, mock_cursor_paths):
        """Test scanning Cursor databases with mock files."""
        workspace_storage1 = self.temp_dir / "workspace_storage1"
        workspace_storage2 = self.temp_dir / "workspace_storage2"
        workspace_storage1.mkdir(parents=True)
        workspace_storage2.mkdir(parents=True)

        mock_cursor_paths.__iter__.return_value = iter(
            [workspace_storage1, workspace_storage2]
        )

        # Create mock workspace with database files
        workspace1 = workspace_storage1 / "workspace1_hash"
        workspace1.mkdir()
        db1 = workspace1 / "conversations.vscdb"
        db1.touch()

        workspace2 = workspace_storage2 / "workspace2_hash"
        workspace2.mkdir()
        db2 = workspace2 / "other.db"
        db2.touch()

        with patch.object(self.scanner, "_count_conversations_sqlite", return_value=5):
            databases = self.scanner._scan_cursor_databases()

        self.assertEqual(len(databases), 2)
        self.assertTrue(all(db.tool_type == "cursor" for db in databases))
        self.assertTrue(all(db.conversation_count == 5 for db in databases))

    @patch("src.core.database_scanner.CLAUDE_SCANNER_PATHS")
    def test_scan_claude_databases_no_paths(self, mock_claude_paths):
        """Test scanning Claude Code databases when no paths exist."""
        mock_claude_paths.__iter__.return_value = iter(
            [self.temp_dir / "nonexistent1", self.temp_dir / "nonexistent2"]
        )
        databases = self.scanner._scan_claude_databases()
        self.assertEqual(databases, [])

    @patch("src.core.database_scanner.CLAUDE_SCANNER_PATHS")
    def test_scan_claude_databases_with_files(self, mock_claude_paths):
        """Test scanning Claude Code databases with mock files."""
        claude_dir1 = self.temp_dir / "claude1"
        claude_dir2 = self.temp_dir / "claude2"
        claude_dir1.mkdir()
        claude_dir2.mkdir()

        mock_claude_paths.__iter__.return_value = iter([claude_dir1, claude_dir2])

        # Create mock conversation files
        conv1 = claude_dir1 / "session1.json"
        conv1.touch()
        conv2 = claude_dir2 / "session2.json"
        conv2.touch()

        databases = self.scanner._scan_claude_databases()

        self.assertEqual(len(databases), 2)
        self.assertTrue(all(db.tool_type == "claude-code" for db in databases))
        self.assertTrue(all(db.conversation_count == 1 for db in databases))

    @patch.object(DatabaseScanner, "_scan_windsurf_databases")
    @patch.object(DatabaseScanner, "_scan_claude_databases")
    @patch.object(DatabaseScanner, "_scan_cursor_databases")
    def test_scan_all_tools(
        self, mock_cursor_scan, mock_claude_scan, mock_windsurf_scan
    ):
        """Test scanning all supported tools."""
        # Mock scan results
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

        mock_cursor_scan.return_value = [cursor_db]
        mock_claude_scan.return_value = [claude_db]
        mock_windsurf_scan.return_value = []

        databases = self.scanner.scan()

        self.assertEqual(len(databases), 2)
        self.assertEqual(databases[0], cursor_db)
        self.assertEqual(databases[1], claude_db)

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

        self.scanner.databases = [mock_db]
        self.scanner._last_scan_time = 1000.0

        with patch("time.time", return_value=1100.0):  # Within TTL
            with patch.object(self.scanner, "_scan_cursor_databases") as mock_scan:
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
            with patch.object(self.scanner, "_scan_cursor_databases", return_value=[]):
                with patch.object(
                    self.scanner, "_scan_claude_databases", return_value=[]
                ):
                    with patch.object(
                        self.scanner, "_scan_windsurf_databases", return_value=[]
                    ):
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

    @patch.object(DatabaseScanner, "_scan_windsurf_databases")
    @patch.object(DatabaseScanner, "_scan_claude_databases")
    @patch.object(DatabaseScanner, "_scan_cursor_databases")
    def test_get_summary_empty(
        self, mock_cursor_scan, mock_claude_scan, mock_windsurf_scan
    ):
        """Test getting summary with no databases."""
        # Mock empty scan results
        mock_cursor_scan.return_value = []
        mock_claude_scan.return_value = []
        mock_windsurf_scan.return_value = []

        summary = self.scanner.get_summary()

        expected = {
            "total_databases": 0,
            "accessible_databases": 0,
            "total_conversations": 0,
            "tools": {},
        }
        self.assertEqual(summary, expected)

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

        expected = {
            "total_databases": 3,
            "accessible_databases": 2,
            "total_conversations": 8,  # 5 + 0 + 3
            "tools": {
                "cursor": {
                    "database_count": 2,
                    "conversation_count": 5,  # Only accessible one counts
                    "accessible_count": 1,
                },
                "claude-code": {
                    "database_count": 1,
                    "conversation_count": 3,
                    "accessible_count": 1,
                },
            },
        }
        self.assertEqual(summary, expected)

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
