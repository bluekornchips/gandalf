"""
Tests for extract_conversation_data module.
"""

import json
import sqlite3
import tempfile
from unittest.mock import patch


from typing import Any, Dict

from src.database_management.extract_conversation_data import ConversationDataExtractor
from src.config.constants import RECALL_CONVERSATIONS_QUERIES


class TestConversationDataExtractor:
    """Test suite for ConversationDataExtractor class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.data_extractor = ConversationDataExtractor()

    def test_extract_conversation_data_without_keywords(self) -> None:
        """Test extract_conversation_data without keywords."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            # Create a test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"], "[]"),
            )
            conn.commit()
            conn.close()

            result = self.data_extractor.extract_conversation_data(temp_db.name, 50)

            assert "prompts" in result
            assert "generations" in result
            assert "history_entries" in result
            assert "database_path" in result
            assert result["database_path"] == temp_db.name
            assert result["error"] is None

    def test_extract_conversation_data_with_keywords(self) -> None:
        """Test extract_conversation_data with keywords."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            # Create a test database
            conn = sqlite3.connect(temp_db.name)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
            cursor.execute(
                "INSERT INTO ItemTable VALUES (?, ?)",
                (
                    RECALL_CONVERSATIONS_QUERIES["PROMPTS_KEY"],
                    json.dumps([{"text": "python programming tutorial"}]),
                ),
            )
            conn.commit()
            conn.close()

            result = self.data_extractor.extract_conversation_data(
                temp_db.name, 50, "python"
            )

            assert "prompts" in result
            assert "generations" in result
            assert "history_entries" in result
            assert "database_path" in result
            assert result["database_path"] == temp_db.name
            assert result["error"] is None

    def test_extract_conversation_data_database_error(self) -> None:
        """Test extract_conversation_data handles database errors."""
        # Test with non-existent database
        result = self.data_extractor.extract_conversation_data(
            "/nonexistent/path.db", 50
        )

        assert "error" in result
        assert result["error"] is not None

    def test_process_database_files_empty_registry(self) -> None:
        """Test process_database_files with empty registry."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.data_extractor.process_database_files(registry_data, 50)
        )

        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_with_keywords(self) -> None:
        """Test process_database_files with keywords parameter."""
        registry_data: Dict[str, Any] = {}
        conversations, paths, total_files, file_counts = (
            self.data_extractor.process_database_files(registry_data, 50, "python")
        )

        # Should handle keywords parameter gracefully even with empty registry
        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    def test_process_database_files_nonexistent_paths(self) -> None:
        """Test process_database_files with nonexistent paths."""
        registry_data = {
            "cursor": ["/nonexistent/path1", "/nonexistent/path2"],
            "claude": ["/nonexistent/path3"],
        }
        conversations, paths, total_files, file_counts = (
            self.data_extractor.process_database_files(registry_data, 50)
        )

        # Should handle nonexistent paths gracefully
        assert conversations == []
        assert paths == []
        assert total_files == 0
        assert file_counts == {}

    @patch("os.path.exists")
    @patch("os.walk")
    def test_process_database_files_with_existing_paths(
        self, mock_walk: Any, mock_exists: Any
    ) -> None:
        """Test process_database_files with existing paths and database files."""
        # Mock os.path.exists to return True for our test paths
        mock_exists.return_value = True

        # Mock os.walk to return different results for different paths
        def mock_walk_side_effect(path: str) -> list[tuple[str, list[str], list[str]]]:
            if path == "/test/path":
                return [("/test/path", [], ["cursor.db"])]
            elif path == "/test/path2":
                return [("/test/path2", [], ["claude.db"])]
            return []

        mock_walk.side_effect = mock_walk_side_effect

        registry_data = {
            "cursor": ["/test/path"],
            "claude": ["/test/path2"],
        }

        with patch.object(
            self.data_extractor, "extract_conversation_data"
        ) as mock_extract:

            def mock_extract_side_effect(
                db_path: str, limit: int, keywords: str
            ) -> Dict[str, Any]:
                return {
                    "prompts": [],
                    "generations": [],
                    "history_entries": [],
                    "database_path": db_path,
                    "error": None,
                }

            mock_extract.side_effect = mock_extract_side_effect

            conversations, paths, total_files, file_counts = (
                self.data_extractor.process_database_files(registry_data, 50)
            )

            # Should find and process database files
            assert len(conversations) == 2
            assert len(paths) == 2
            assert total_files == 2
            assert file_counts["cursor.db"] == 1
            assert file_counts["claude.db"] == 1
            assert "/test/path/cursor.db" in paths
            assert "/test/path2/claude.db" in paths

    def test_process_database_files_multiple_db_files(self) -> None:
        """Test process_database_files with multiple database files in same path."""
        with patch("os.path.exists", return_value=True):
            with patch("os.walk") as mock_walk:
                mock_walk.return_value = [
                    ("/test/path", [], ["cursor.db", "claude.db", "other.db"]),
                ]

                registry_data = {
                    "cursor": ["/test/path"],
                }

                with patch.object(
                    self.data_extractor, "extract_conversation_data"
                ) as mock_extract:
                    mock_extract.return_value = {
                        "prompts": [],
                        "generations": [],
                        "history_entries": [],
                        "database_path": "/test/path/cursor.db",
                        "error": None,
                    }

                    conversations, paths, total_files, file_counts = (
                        self.data_extractor.process_database_files(registry_data, 50)
                    )

                    # Should find all supported database files
                    assert len(conversations) == 2  # cursor.db and claude.db
                    assert len(paths) == 2
                    assert total_files == 2
                    assert file_counts["cursor.db"] == 1
                    assert file_counts["claude.db"] == 1
                    assert "other.db" not in file_counts  # Not in SUPPORTED_DB_FILES
