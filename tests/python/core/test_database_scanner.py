"""
Tests for database scanner functionality.

These tests ensure the scanner properly discovers and analyzes conversation
databases from various IDEs across the realms of Middle-earth.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.database_scanner import (
    ConversationDatabase,
    DatabaseScanner,
    get_available_ides,
    scan_conversation_databases,
)


class TestConversationDatabase:
    """Tests for ConversationDatabase dataclass."""

    def test_conversation_database_creation(self):
        """Test creating a ConversationDatabase instance."""
        db = ConversationDatabase(
            ide_type="cursor",
            database_path=Path("/test/path.db"),
            conversation_count=5,
            last_modified=1234567890.0,
            metadata={"test": "data"},
        )

        assert db.ide_type == "cursor"
        assert db.database_path == Path("/test/path.db")
        assert db.conversation_count == 5
        assert db.last_modified == 1234567890.0
        assert db.metadata == {"test": "data"}


class TestDatabaseScanner:
    """Tests for DatabaseScanner class."""

    def setup_method(self):
        """Setup test environment."""
        self.scanner = DatabaseScanner(silent=True)

    def test_scanner_initialization(self):
        """Test scanner initialization."""
        assert self.scanner.silent is True
        assert self.scanner._discovered_databases == []

    @patch("src.core.database_scanner.Path.expanduser")
    @patch("src.core.database_scanner.Path.exists")
    def test_scan_cursor_databases_no_locations(
        self, mock_exists, mock_expanduser
    ):
        """Test scanning when no Cursor locations exist."""
        mock_exists.return_value = False

        databases = self.scanner.scan_all_databases()

        assert databases == []

    def test_analyze_cursor_database_invalid_path(self):
        """Test analyzing a non-existent Cursor database."""
        fake_path = Path("/nonexistent/database.db")

        result = self.scanner._analyze_cursor_database(fake_path)

        assert result is None

    def test_analyze_cursor_database_valid(self):
        """Test analyzing a valid Cursor database with conversation data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_conversations.db"

            # Create test database with conversation data
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                # Create the table structure that the scanner expects
                cursor.execute(
                    """CREATE TABLE ItemTable (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )"""
                )

                # Mock conversation data using Fellowship members
                conversations = [
                    {
                        "id": "frodo-baggins",
                        "name": "Journey to Rivendell Planning",
                    },
                    {
                        "id": "gandalf-grey",
                        "name": "Council of Elrond Discussion",
                    },
                    {
                        "id": "aragorn-strider",
                        "name": "Path through Moria Strategy",
                    },
                ]

                # Insert data in the format the scanner expects
                composer_data = {"allComposers": conversations}
                cursor.execute(
                    "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                    ("composer.composerData", json.dumps(composer_data)),
                )
                conn.commit()

            result = self.scanner._analyze_cursor_database(db_path)

            assert result is not None
            assert result.ide_type == "cursor"
            assert result.database_path == db_path
            assert result.conversation_count == 3
            assert result.metadata["workspace"] == db_path.parent.name

    def test_analyze_claude_code_storage_empty(self):
        """Test analyzing empty Claude Code storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            result = self.scanner._analyze_claude_code_storage(storage_path)

            assert result is None

    def test_analyze_claude_code_storage_with_files(self):
        """Test analyzing Claude Code storage with conversation files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            # Create some mock conversation files with Hobbit themes
            (storage_path / "bagend_session.json").write_text(
                '{"hobbit": "frodo", "quest": "ring_bearer"}'
            )
            (storage_path / "rivendell_conversation.md").write_text(
                "# Council of Elrond Meeting Notes"
            )
            (storage_path / "moria_expedition_notes.txt").write_text(
                "Speak friend and enter"
            )

            result = self.scanner._analyze_claude_code_storage(storage_path)

            assert result is not None
            assert result.ide_type == "claude-code"
            assert result.database_path == storage_path
            assert result.conversation_count == 3
            assert result.metadata["storage_type"] == "file_based"
            assert result.metadata["file_count"] == 3

    def test_get_databases_by_ide(self):
        """Test filtering databases by IDE type."""
        # Mock databases from different realms
        cursor_db = ConversationDatabase(
            "cursor", Path("/minas_tirith.db"), 5, 123.0, {"realm": "gondor"}
        )
        claude_db = ConversationDatabase(
            "claude-code", Path("/rivendell"), 3, 456.0, {"realm": "elves"}
        )

        self.scanner._discovered_databases = [cursor_db, claude_db]

        cursor_dbs = self.scanner.get_databases_by_ide("cursor")
        claude_dbs = self.scanner.get_databases_by_ide("claude-code")

        assert len(cursor_dbs) == 1
        assert cursor_dbs[0] == cursor_db
        assert len(claude_dbs) == 1
        assert claude_dbs[0] == claude_db

    def test_get_total_conversation_count(self):
        """Test getting total conversation count across all databases."""
        isengard_db = ConversationDatabase(
            "cursor", Path("/isengard.db"), 5, 123.0, {"faction": "white_hand"}
        )
        shire_db = ConversationDatabase(
            "claude-code", Path("/shire"), 3, 456.0, {"faction": "hobbits"}
        )

        self.scanner._discovered_databases = [isengard_db, shire_db]

        total = self.scanner.get_total_conversation_count()

        assert total == 8

    def test_get_summary(self):
        """Test getting summary of discovered databases."""
        gondor_db = ConversationDatabase(
            "cursor",
            Path("/minas_tirith.db"),
            5,
            123.0,
            {"steward": "denethor"},
        )
        lorien_db = ConversationDatabase(
            "claude-code",
            Path("/caras_galadhon"),
            3,
            456.0,
            {"lady": "galadriel"},
        )

        self.scanner._discovered_databases = [gondor_db, lorien_db]

        summary = self.scanner.get_summary()

        assert summary["total_databases"] == 2
        assert summary["total_conversations"] == 8
        assert summary["ides"]["cursor"]["database_count"] == 1
        assert summary["ides"]["cursor"]["conversation_count"] == 5
        assert summary["ides"]["claude-code"]["database_count"] == 1
        assert summary["ides"]["claude-code"]["conversation_count"] == 3


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("src.core.database_scanner.DatabaseScanner")
    def test_scan_conversation_databases(self, mock_scanner_class):
        """Test scan_conversation_databases convenience function."""
        mock_scanner = Mock()
        mock_databases = [Mock(), Mock()]
        mock_scanner.scan_all_databases.return_value = mock_databases
        mock_scanner_class.return_value = mock_scanner

        result = scan_conversation_databases(silent=True)

        mock_scanner_class.assert_called_once_with(silent=True)
        mock_scanner.scan_all_databases.assert_called_once()
        assert result == mock_databases

    @patch("src.core.database_scanner.scan_conversation_databases")
    def test_get_available_ides(self, mock_scan):
        """Test get_available_ides convenience function."""
        mock_gondor_db = Mock()
        mock_gondor_db.ide_type = "cursor"
        mock_rohan_db = Mock()
        mock_rohan_db.ide_type = "claude-code"
        mock_duplicate_db = Mock()
        mock_duplicate_db.ide_type = "cursor"  # Duplicate, intentional

        mock_scan.return_value = [
            mock_gondor_db,
            mock_rohan_db,
            mock_duplicate_db,
        ]

        result = get_available_ides()

        # Should return unique IDE types
        assert set(result) == {"cursor", "claude-code"}
        assert len(result) == 2
