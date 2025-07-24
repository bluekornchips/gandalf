"""
Test suite for tool scanners functionality.

Comprehensive tests for CursorScanner, ClaudeScanner, WindsurfScanner,
and ScannerFactory classes with extensive edge case coverage.
"""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.database_scanner_base import ConversationDatabase
from src.core.tool_scanners import (
    ClaudeScanner,
    CursorScanner,
    ScannerFactory,
    WindsurfScanner,
)


class TestCursorScanner(unittest.TestCase):
    """Test CursorScanner functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.scanner = CursorScanner(scan_timeout=5)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def create_cursor_workspace_structure(self):
        """Create a mock Cursor workspace structure."""
        # Create the workspace storage directory structure
        workspace_storage = self.temp_path / "User" / "workspaceStorage"
        workspace_storage.mkdir(parents=True)

        workspace_hash = "test_workspace_123abc"
        workspace_dir = workspace_storage / workspace_hash
        workspace_dir.mkdir()

        return workspace_dir

    def create_cursor_database(self, workspace_dir: Path, with_conversations=True):
        """Create a mock Cursor database file."""
        db_file = workspace_dir / "state.vscdb"

        with sqlite3.connect(str(db_file)) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")

            if with_conversations:
                composer_data = {
                    "allComposers": [
                        {"id": "conv1", "title": "Test conversation 1"},
                        {"id": "conv2", "title": "Test conversation 2"},
                    ]
                }
                cursor.execute(
                    "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                    ("composer.composerData", json.dumps(composer_data)),
                )

            conn.commit()

        return db_file

    @patch("src.core.tool_scanners.CURSOR_WORKSPACE_STORAGE", "User/workspaceStorage")
    def test_cursor_scanner_init(self):
        """Test CursorScanner initialization."""
        scanner = CursorScanner(scan_timeout=10)
        self.assertEqual(scanner.scan_timeout, 10)

    def test_cursor_scanner_scan_databases_success(self):
        """Test successful Cursor database scanning."""
        workspace_dir = self.create_cursor_workspace_structure()
        db_file = self.create_cursor_database(workspace_dir, with_conversations=True)

        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            with patch(
                "src.core.tool_scanners.CURSOR_WORKSPACE_STORAGE",
                [self.temp_path / "User" / "workspaceStorage"],
            ):
                databases = self.scanner.scan_databases()

        self.assertGreater(len(databases), 0)
        found_db = next((db for db in databases if Path(db.path) == db_file), None)
        if found_db:
            self.assertEqual(found_db.tool_type, "cursor")
            self.assertGreater(found_db.size_bytes, 0)

    @patch("src.core.tool_scanners.CURSOR_WORKSPACE_STORAGE", "User/workspaceStorage")
    def test_cursor_scanner_scan_databases_no_home(self):
        """Test Cursor scanning when home directory doesn't exist."""
        with patch(
            "src.core.tool_scanners.Path.home", return_value=Path("/nonexistent")
        ):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.CURSOR_WORKSPACE_STORAGE", "User/workspaceStorage")
    def test_cursor_scanner_scan_databases_no_workspace_storage(self):
        """Test Cursor scanning when workspace storage doesn't exist."""
        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.CURSOR_WORKSPACE_STORAGE", "User/workspaceStorage")
    def test_cursor_scanner_scan_databases_empty_workspace(self):
        """Test Cursor scanning with empty workspace directory."""
        workspace_storage = self.temp_path / "User" / "workspaceStorage"
        workspace_storage.mkdir(parents=True)

        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.CURSOR_WORKSPACE_STORAGE", "User/workspaceStorage")
    def test_cursor_scanner_scan_databases_permission_error(self):
        """Test Cursor scanning with permission errors."""
        workspace_storage = self.temp_path / "User" / "workspaceStorage"
        workspace_storage.mkdir(parents=True)

        # Store original iterdir method
        original_iterdir = Path.iterdir

        def mock_iterdir(path_self):
            if str(path_self) == str(workspace_storage):
                raise PermissionError("Access denied")
            return original_iterdir(path_self)

        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            with patch.object(Path, "iterdir", mock_iterdir):
                databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.timeout_context")
    def test_cursor_scanner_scan_databases_timeout(self, mock_timeout):
        """Test Cursor scanning with timeout."""
        mock_timeout.side_effect = TimeoutError("Scan timed out")

        databases = self.scanner.scan_databases()
        self.assertEqual(databases, [])

    def test_cursor_scanner_matches_cursor_pattern(self):
        """Test Cursor database pattern matching."""
        test_files = [
            Path("state.vscdb"),
            Path("workspace.vscdb"),
            Path("other.vscdb"),
            Path("test.db"),
            Path("another.db"),
            Path("notadb.txt"),
            Path("file.json"),
        ]

        for file_path in test_files:
            result = self.scanner._matches_cursor_pattern(file_path)
            if file_path.name.endswith((".vscdb", ".db")):
                self.assertTrue(result, f"Should match {file_path}")
            else:
                self.assertFalse(result, f"Should not match {file_path}")

    def test_cursor_scanner_create_cursor_database(self):
        """Test creating ConversationDatabase entry for Cursor."""
        workspace_dir = self.create_cursor_workspace_structure()
        db_file = self.create_cursor_database(workspace_dir, with_conversations=True)

        db_entry = self.scanner._create_cursor_database(db_file)

        self.assertIsInstance(db_entry, ConversationDatabase)
        self.assertEqual(db_entry.path, str(db_file))
        self.assertEqual(db_entry.tool_type, "cursor")
        self.assertGreater(db_entry.size_bytes, 0)
        self.assertTrue(db_entry.is_accessible)

    def test_cursor_scanner_create_cursor_database_inaccessible(self):
        """Test creating ConversationDatabase entry for inaccessible database."""
        workspace_dir = self.create_cursor_workspace_structure()

        # Create a file that's not a valid database
        db_file = workspace_dir / "invalid.vscdb"
        with open(db_file, "w") as f:
            f.write("Not a database")

        db_entry = self.scanner._create_cursor_database(db_file)

        self.assertIsInstance(db_entry, ConversationDatabase)
        self.assertEqual(db_entry.path, str(db_file))
        self.assertEqual(db_entry.tool_type, "cursor")
        self.assertFalse(db_entry.is_accessible)
        self.assertIsNotNone(db_entry.error_message)


class TestClaudeScanner(unittest.TestCase):
    """Test ClaudeScanner functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.scanner = ClaudeScanner(scan_timeout=5)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def create_claude_directory_structure(self):
        """Create a mock Claude Code directory structure."""
        claude_dir = self.temp_path / ".claude"
        claude_dir.mkdir(parents=True)
        return claude_dir

    def create_claude_conversation_file(
        self, claude_dir: Path, filename: str, conversations_count=2
    ):
        """Create a mock Claude conversation file."""
        conv_file = claude_dir / filename

        conversations = [
            {"id": f"conv{i}", "title": f"Test conversation {i}"}
            for i in range(1, conversations_count + 1)
        ]

        with open(conv_file, "w") as f:
            json.dump(conversations, f)

        return conv_file

    @patch("src.core.tool_scanners.CLAUDE_HOME", ".claude")
    def test_claude_scanner_init(self):
        """Test ClaudeScanner initialization."""
        scanner = ClaudeScanner(scan_timeout=10)
        self.assertEqual(scanner.scan_timeout, 10)

    def test_claude_scanner_scan_databases_success(self):
        """Test successful Claude database scanning."""
        claude_dir = self.create_claude_directory_structure()
        conv_file = self.create_claude_conversation_file(
            claude_dir, "conversations.json"
        )

        with patch("src.core.tool_scanners.CLAUDE_HOME", [claude_dir]):
            databases = self.scanner.scan_databases()

        self.assertGreater(len(databases), 0)
        found_db = next((db for db in databases if Path(db.path) == conv_file), None)
        if found_db:
            self.assertEqual(found_db.tool_type, "claude-code")
            self.assertGreater(found_db.size_bytes, 0)

    @patch("src.core.tool_scanners.CLAUDE_HOME", ".claude")
    def test_claude_scanner_scan_databases_no_home(self):
        """Test Claude scanning when home directory doesn't exist."""
        with patch(
            "src.core.tool_scanners.Path.home", return_value=Path("/nonexistent")
        ):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.CLAUDE_HOME", ".claude")
    def test_claude_scanner_scan_databases_no_claude_dir(self):
        """Test Claude scanning when Claude directory doesn't exist."""
        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.CLAUDE_HOME", ".claude")
    def test_claude_scanner_scan_databases_empty_claude_dir(self):
        """Test Claude scanning with empty Claude directory."""
        self.create_claude_directory_structure()

        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    def test_claude_scanner_scan_databases_permission_error(self):
        """Test Claude scanning with permission errors."""
        claude_dir = self.create_claude_directory_structure()

        # Store original iterdir method
        original_iterdir = Path.iterdir

        def mock_iterdir(path_self):
            if str(path_self) == str(claude_dir):
                raise PermissionError("Access denied")
            return original_iterdir(path_self)

        with patch("src.core.tool_scanners.CLAUDE_HOME", [claude_dir]):
            with patch.object(Path, "iterdir", mock_iterdir):
                databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.timeout_context")
    def test_claude_scanner_scan_databases_timeout(self, mock_timeout):
        """Test Claude scanning with timeout."""
        mock_timeout.side_effect = TimeoutError("Scan timed out")

        databases = self.scanner.scan_databases()
        self.assertEqual(databases, [])

    def test_claude_scanner_matches_claude_pattern(self):
        """Test Claude conversation file pattern matching."""
        test_files = [
            Path("conversations.json"),
            Path("sessions.json"),
            Path("chat_history.json"),
            Path("notconversations.txt"),
            Path("data.xml"),
        ]

        for file_path in test_files:
            result = self.scanner._matches_claude_pattern(file_path)
            if file_path.name.endswith(".json"):
                # All JSON files match in basic implementation
                self.assertTrue(result, f"Should match {file_path}")
            else:
                self.assertFalse(result, f"Should not match {file_path}")

    def test_claude_scanner_create_claude_database(self):
        """Test creating ConversationDatabase entry for Claude."""
        claude_dir = self.create_claude_directory_structure()
        conv_file = self.create_claude_conversation_file(
            claude_dir, "conversations.json"
        )

        db_entry = self.scanner._create_claude_database(conv_file)

        self.assertIsInstance(db_entry, ConversationDatabase)
        self.assertEqual(db_entry.path, str(conv_file))
        self.assertEqual(db_entry.tool_type, "claude-code")
        self.assertGreater(db_entry.size_bytes, 0)
        self.assertTrue(db_entry.is_accessible)
        self.assertGreater(db_entry.conversation_count, 0)


class TestWindsurfScanner(unittest.TestCase):
    """Test WindsurfScanner functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.scanner = WindsurfScanner(scan_timeout=5)

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def create_windsurf_workspace_structure(self):
        """Create a mock Windsurf workspace structure."""
        workspace_storage = self.temp_path / "User" / "workspaceStorage"
        workspace_storage.mkdir(parents=True)

        workspace_hash = "test_windsurf_workspace_456def"
        workspace_dir = workspace_storage / workspace_hash
        workspace_dir.mkdir()

        return workspace_dir

    def create_windsurf_database(self, workspace_dir: Path, with_conversations=True):
        """Create a mock Windsurf database file."""
        db_file = workspace_dir / "state.vscdb"

        with sqlite3.connect(str(db_file)) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT)")

            if with_conversations:
                chat_data = {
                    "sessions": [
                        {"id": "sess1", "messages": ["hello"]},
                        {"id": "sess2", "messages": ["world"]},
                    ]
                }
                cursor.execute(
                    "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                    ("chat.sessionStore", json.dumps(chat_data)),
                )

            conn.commit()

        return db_file

    @patch(
        "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", ["User/workspaceStorage"]
    )
    def test_windsurf_scanner_init(self):
        """Test WindsurfScanner initialization."""
        scanner = WindsurfScanner(scan_timeout=10)
        self.assertEqual(scanner.scan_timeout, 10)

    def test_windsurf_scanner_scan_databases_success(self):
        """Test successful Windsurf database scanning."""
        workspace_dir = self.create_windsurf_workspace_structure()
        db_file = self.create_windsurf_database(workspace_dir, with_conversations=True)

        with patch(
            "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", [workspace_dir.parent]
        ):
            databases = self.scanner.scan_databases()

        self.assertGreater(len(databases), 0)
        found_db = next((db for db in databases if Path(db.path) == db_file), None)
        if found_db:
            self.assertEqual(found_db.tool_type, "windsurf")
            self.assertGreater(found_db.size_bytes, 0)

    @patch(
        "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", ["User/workspaceStorage"]
    )
    def test_windsurf_scanner_scan_databases_no_home(self):
        """Test Windsurf scanning when home directory doesn't exist."""
        with patch(
            "src.core.tool_scanners.Path.home", return_value=Path("/nonexistent")
        ):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch(
        "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", ["User/workspaceStorage"]
    )
    def test_windsurf_scanner_scan_databases_no_workspace_storage(self):
        """Test Windsurf scanning when workspace storage doesn't exist."""
        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch(
        "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", ["User/workspaceStorage"]
    )
    def test_windsurf_scanner_scan_databases_empty_workspace(self):
        """Test Windsurf scanning with empty workspace directory."""
        workspace_storage = self.temp_path / "User" / "workspaceStorage"
        workspace_storage.mkdir(parents=True)

        with patch("src.core.tool_scanners.Path.home", return_value=self.temp_path):
            databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch(
        "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", ["User/workspaceStorage"]
    )
    def test_windsurf_scanner_scan_databases_permission_error(self):
        """Test Windsurf scanning with permission errors."""
        workspace_storage = self.temp_path / "User" / "workspaceStorage"
        workspace_storage.mkdir(parents=True)

        # Store original iterdir method
        original_iterdir = Path.iterdir

        def mock_iterdir(path_self):
            if str(path_self) == str(workspace_storage):
                raise PermissionError("Access denied")
            return original_iterdir(path_self)

        with patch(
            "src.core.tool_scanners.WINDSURF_WORKSPACE_STORAGE", [workspace_storage]
        ):
            with patch.object(Path, "iterdir", mock_iterdir):
                databases = self.scanner.scan_databases()

        self.assertEqual(databases, [])

    @patch("src.core.tool_scanners.timeout_context")
    def test_windsurf_scanner_scan_databases_timeout(self, mock_timeout):
        """Test Windsurf scanning with timeout."""
        mock_timeout.side_effect = TimeoutError("Scan timed out")

        databases = self.scanner.scan_databases()
        self.assertEqual(databases, [])

    def test_windsurf_scanner_matches_windsurf_pattern(self):
        """Test Windsurf database pattern matching."""
        test_files = [
            Path("state.vscdb"),
            Path("workspace.vscdb"),
            Path("other.vscdb"),
            Path("notadb.txt"),
            Path("test.db"),
        ]

        for file_path in test_files:
            result = self.scanner._matches_windsurf_pattern(file_path)
            if file_path.name.endswith(".vscdb") or file_path.name.endswith(".db"):
                self.assertTrue(result, f"Should match {file_path}")
            else:
                self.assertFalse(result, f"Should not match {file_path}")

    def test_windsurf_scanner_create_windsurf_database(self):
        """Test creating ConversationDatabase entry for Windsurf."""
        workspace_dir = self.create_windsurf_workspace_structure()
        db_file = self.create_windsurf_database(workspace_dir, with_conversations=True)

        db_entry = self.scanner._create_windsurf_database(db_file)

        self.assertIsInstance(db_entry, ConversationDatabase)
        self.assertEqual(db_entry.path, str(db_file))
        self.assertEqual(db_entry.tool_type, "windsurf")
        self.assertGreater(db_entry.size_bytes, 0)

    def test_windsurf_scanner_create_windsurf_database_inaccessible(self):
        """Test creating ConversationDatabase entry for inaccessible database."""
        workspace_dir = self.create_windsurf_workspace_structure()

        # Create a file that's not a valid database
        db_file = workspace_dir / "invalid.vscdb"
        with open(db_file, "w") as f:
            f.write("Not a database")

        db_entry = self.scanner._create_windsurf_database(db_file)

        self.assertIsInstance(db_entry, ConversationDatabase)
        self.assertEqual(db_entry.path, str(db_file))
        self.assertEqual(db_entry.tool_type, "windsurf")
        self.assertFalse(db_entry.is_accessible)


class TestScannerFactory(unittest.TestCase):
    """Test ScannerFactory functionality."""

    def test_create_cursor_scanner(self):
        """Test creating CursorScanner via factory."""
        scanner = ScannerFactory.create_cursor_scanner(scan_timeout=15)

        self.assertIsInstance(scanner, CursorScanner)
        self.assertEqual(scanner.scan_timeout, 15)

    def test_create_claude_scanner(self):
        """Test creating ClaudeScanner via factory."""
        scanner = ScannerFactory.create_claude_scanner(scan_timeout=20)

        self.assertIsInstance(scanner, ClaudeScanner)
        self.assertEqual(scanner.scan_timeout, 20)

    def test_create_windsurf_scanner(self):
        """Test creating WindsurfScanner via factory."""
        scanner = ScannerFactory.create_windsurf_scanner(scan_timeout=25)

        self.assertIsInstance(scanner, WindsurfScanner)
        self.assertEqual(scanner.scan_timeout, 25)

    def test_create_scanner_with_default_timeout(self):
        """Test creating scanners with default timeout values."""
        cursor_scanner = ScannerFactory.create_cursor_scanner()
        claude_scanner = ScannerFactory.create_claude_scanner()
        windsurf_scanner = ScannerFactory.create_windsurf_scanner()

        self.assertIsInstance(cursor_scanner, CursorScanner)
        self.assertIsInstance(claude_scanner, ClaudeScanner)
        self.assertIsInstance(windsurf_scanner, WindsurfScanner)

        # All should have some reasonable default timeout
        self.assertGreater(cursor_scanner.scan_timeout, 0)
        self.assertGreater(claude_scanner.scan_timeout, 0)
        self.assertGreater(windsurf_scanner.scan_timeout, 0)
