"""
Tests for conversation storage functionality.

Tests conversation data persistence, validation, caching, and metadata handling
with comprehensive coverage of edge cases and error conditions.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from src.core.conversation_storage import (
    clear_conversation_storage,
    get_conversation_storage_info,
    get_project_storage_hash,
    get_storage_directory,
    get_storage_file_path,
    get_storage_metadata_path,
    is_storage_valid,
    load_stored_conversations,
    save_conversations_to_storage,
)


class TestStoragePathFunctions:
    """Test storage path and directory functions."""

    @patch("src.core.conversation_storage.CONVERSATION_CACHE_DIR")
    def test_get_storage_directory_creates_directory(self, mock_cache_dir):
        """Test that storage directory is created if it doesn't exist."""
        mock_path = Mock(spec=Path)
        mock_cache_dir.return_value = mock_path

        result = get_storage_directory()

        mock_cache_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        assert result == mock_cache_dir

    @patch("src.core.conversation_storage.CONVERSATION_CACHE_FILE")
    def test_get_storage_file_path(self, mock_cache_file):
        """Test getting storage file path."""
        mock_path = Mock(spec=Path)
        mock_cache_file.return_value = mock_path

        result = get_storage_file_path()

        assert result == mock_cache_file

    @patch("src.core.conversation_storage.CONVERSATION_CACHE_METADATA_FILE")
    def test_get_storage_metadata_path(self, mock_metadata_file):
        """Test getting storage metadata path."""
        mock_path = Mock(spec=Path)
        mock_metadata_file.return_value = mock_path
        project_root = Path("/test/project")

        result = get_storage_metadata_path(project_root)

        assert result == mock_metadata_file


class TestProjectStorageHash:
    """Test project storage hash generation."""

    def test_get_project_storage_hash_basic(self):
        """Test basic hash generation with keywords."""
        project_root = Path("/test/project")
        keywords = ["python", "test"]

        result = get_project_storage_hash(project_root, keywords)

        assert isinstance(result, str)
        assert len(result) == 16
        assert result.isalnum()

    def test_get_project_storage_hash_with_git_head(self, tmp_path):
        """Test hash generation includes git HEAD content."""
        project_root = tmp_path
        git_dir = project_root / ".git"
        git_dir.mkdir()
        git_head = git_dir / "HEAD"
        git_head.write_text("ref: refs/heads/main")

        keywords = ["test"]
        result1 = get_project_storage_hash(project_root, keywords)

        git_head.write_text("ref: refs/heads/feature")
        result2 = get_project_storage_hash(project_root, keywords)

        assert result1 != result2

    def test_get_project_storage_hash_different_keywords(self):
        """Test that different keywords produce different hashes."""
        project_root = Path("/test/project")
        keywords1 = ["python", "test"]
        keywords2 = ["javascript", "web"]

        result1 = get_project_storage_hash(project_root, keywords1)
        result2 = get_project_storage_hash(project_root, keywords2)

        assert result1 != result2

    def test_get_project_storage_hash_sorted_keywords(self):
        """Test that keyword order doesn't affect hash."""
        project_root = Path("/test/project")
        keywords1 = ["python", "test", "web"]
        keywords2 = ["web", "test", "python"]

        result1 = get_project_storage_hash(project_root, keywords1)
        result2 = get_project_storage_hash(project_root, keywords2)

        assert result1 == result2

    @patch("src.core.conversation_storage.time.time", return_value=1234567890)
    def test_get_project_storage_hash_error_fallback(self, mock_time):
        """Test fallback hash generation on error."""
        mock_project_root = Mock()
        mock_project_root.__str__ = Mock(side_effect=ValueError("Test error"))

        keywords = ["test"]
        result = get_project_storage_hash(mock_project_root, keywords)

        assert isinstance(result, str)
        assert len(result) == 16

    def test_get_project_storage_hash_git_read_error(self, tmp_path):
        """Test hash generation when git HEAD can't be read."""
        project_root = tmp_path
        git_dir = project_root / ".git"
        git_dir.mkdir()
        git_head = git_dir / "HEAD"
        git_head.write_text("test")

        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            keywords = ["test"]
            result = get_project_storage_hash(project_root, keywords)

            assert isinstance(result, str)
            assert len(result) == 16


class TestStorageValidation:
    """Test storage validation functionality."""

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_is_storage_valid_missing_files(
        self, mock_storage_path, mock_metadata_path
    ):
        """Test validation fails when files don't exist."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = False
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = False
        mock_metadata_path.return_value = mock_metadata_file

        project_root = Path("/test")
        keywords = ["test"]

        result = is_storage_valid(project_root, keywords)

        assert result is False

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.CONVERSATION_CACHE_MAX_SIZE_MB", 1)
    def test_is_storage_valid_file_too_large(
        self, mock_storage_path, mock_metadata_path
    ):
        """Test validation fails when storage file is too large."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_stat = Mock()
        mock_stat.st_size = 2 * 1024 * 1024  # 2MB when limit is 1MB
        mock_storage_file.stat.return_value = mock_stat
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        project_root = Path("/test")
        keywords = ["test"]

        result = is_storage_valid(project_root, keywords)

        assert result is False

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.CONVERSATION_CACHE_TTL_HOURS", 1)
    @patch("src.core.conversation_storage.time.time", return_value=7200)
    def test_is_storage_valid_expired(
        self, mock_time, mock_storage_path, mock_metadata_path
    ):
        """Test validation fails when storage is expired."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_storage_file.stat.return_value = mock_stat
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        metadata = {"timestamp": 0}

        with patch("builtins.open", mock_open(read_data=json.dumps(metadata))):
            project_root = Path("/test")
            keywords = ["test"]

            result = is_storage_valid(project_root, keywords)

            assert result is False

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_project_storage_hash")
    def test_is_storage_valid_hash_mismatch(
        self, mock_hash, mock_storage_path, mock_metadata_path
    ):
        """Test validation fails when project hash doesn't match."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_storage_file.stat.return_value = mock_stat
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        mock_hash.return_value = "new_hash"

        metadata = {"timestamp": time.time(), "project_hash": "old_hash"}

        with patch("builtins.open", mock_open(read_data=json.dumps(metadata))):
            project_root = Path("/test")
            keywords = ["test"]

            result = is_storage_valid(project_root, keywords)

            assert result is False

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_project_storage_hash")
    def test_is_storage_valid_success(
        self, mock_hash, mock_storage_path, mock_metadata_path
    ):
        """Test successful validation when all conditions are met."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_storage_file.stat.return_value = mock_stat
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        mock_hash.return_value = "matching_hash"

        metadata = {"timestamp": time.time(), "project_hash": "matching_hash"}

        with patch("builtins.open", mock_open(read_data=json.dumps(metadata))):
            project_root = Path("/test")
            keywords = ["test"]

            result = is_storage_valid(project_root, keywords)

            assert result is True

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_is_storage_valid_json_decode_error(
        self, mock_storage_path, mock_metadata_path
    ):
        """Test validation handles JSON decode errors gracefully."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_storage_file.stat.return_value = mock_stat
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        with patch("builtins.open", mock_open(read_data="invalid json")):
            project_root = Path("/test")
            keywords = ["test"]

            result = is_storage_valid(project_root, keywords)

            assert result is False

    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_is_storage_valid_os_error(self, mock_storage_path, mock_metadata_path):
        """Test validation handles OS errors gracefully."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_storage_file.stat.side_effect = OSError("Permission denied")
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        project_root = Path("/test")
        keywords = ["test"]

        result = is_storage_valid(project_root, keywords)

        assert result is False


class TestLoadStoredConversations:
    """Test loading conversations from storage."""

    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_load_stored_conversations_file_not_exists(self, mock_storage_path):
        """Test loading returns None when file doesn't exist."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = False
        mock_storage_path.return_value = mock_storage_file

        project_root = Path("/test")
        result = load_stored_conversations(project_root)

        assert result is None

    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_load_stored_conversations_success(self, mock_storage_path):
        """Test successful loading of conversations."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_storage_path.return_value = mock_storage_file

        stored_data = {
            "conversations": [
                {"id": 1, "content": "test1"},
                {"id": 2, "content": "test2"},
            ],
            "metadata": {"test": "data"},
        }

        with patch("builtins.open", mock_open(read_data=json.dumps(stored_data))):
            project_root = Path("/test")
            result = load_stored_conversations(project_root)

            assert result == stored_data

    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_load_stored_conversations_json_error(self, mock_storage_path):
        """Test loading handles JSON decode errors."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_storage_path.return_value = mock_storage_file

        with patch("builtins.open", mock_open(read_data="invalid json")):
            project_root = Path("/test")
            result = load_stored_conversations(project_root)

            assert result is None

    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_load_stored_conversations_non_dict_json(self, mock_storage_path):
        """Test loading when JSON file contains valid JSON that's not a dict."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_storage_path.return_value = mock_storage_file

        # Test with list instead of dict
        non_dict_data = ["conversation1", "conversation2"]

        with patch("builtins.open", mock_open(read_data=json.dumps(non_dict_data))):
            project_root = Path("/test")
            result = load_stored_conversations(project_root)

            assert result is None

    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_load_stored_conversations_os_error(self, mock_storage_path):
        """Test loading handles OS errors."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_storage_path.return_value = mock_storage_file

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            project_root = Path("/test")
            result = load_stored_conversations(project_root)

            assert result is None

    @patch("src.core.conversation_storage.get_storage_file_path")
    def test_load_stored_conversations_empty_conversations(self, mock_storage_path):
        """Test loading with empty conversations list."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_storage_path.return_value = mock_storage_file

        stored_data = {"conversations": [], "metadata": {}}

        with patch("builtins.open", mock_open(read_data=json.dumps(stored_data))):
            project_root = Path("/test")
            result = load_stored_conversations(project_root)

            assert result == stored_data


class TestSaveConversationsToStorage:
    """Test saving conversations to storage."""

    @patch("src.core.conversation_storage.CONVERSATION_CACHE_MIN_SIZE", 5)
    def test_save_conversations_too_few(self):
        """Test saving fails when too few conversations."""
        project_root = Path("/test")
        conversations = [{"id": 1}]
        keywords = ["test"]
        metadata = {}

        result = save_conversations_to_storage(
            project_root, conversations, keywords, metadata
        )

        assert result is False

    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("src.core.conversation_storage.get_project_storage_hash")
    def test_save_conversations_success(
        self, mock_hash, mock_metadata_path, mock_storage_path
    ):
        """Test successful saving of conversations."""
        mock_storage_file = Mock()
        mock_storage_path.return_value = mock_storage_file
        mock_metadata_file = Mock()
        mock_metadata_path.return_value = mock_metadata_file

        mock_hash.return_value = "test_hash"

        mock_storage_stat = Mock()
        mock_storage_stat.st_size = 1024
        mock_storage_file.stat.return_value = mock_storage_stat

        project_root = Path("/test")
        conversations = [{"id": i} for i in range(10)]
        keywords = ["test"]
        metadata = {"test": "data"}

        with patch("builtins.open", mock_open()) as mock_file:
            result = save_conversations_to_storage(
                project_root, conversations, keywords, metadata
            )

            assert result is True
            assert mock_file.call_count == 2

    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_storage_metadata_path")
    def test_save_conversations_os_error(self, mock_metadata_path, mock_storage_path):
        """Test saving handles OS errors."""
        mock_storage_file = Path("/test/storage.json")
        mock_storage_path.return_value = mock_storage_file
        mock_metadata_file = Path("/test/metadata.json")
        mock_metadata_path.return_value = mock_metadata_file

        project_root = Path("/test")
        conversations = [{"id": i} for i in range(10)]
        keywords = ["test"]
        metadata = {}

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = save_conversations_to_storage(
                project_root, conversations, keywords, metadata
            )

            assert result is False

    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_storage_metadata_path")
    @patch("json.dump")
    def test_save_conversations_json_encode_error(
        self, mock_json_dump, mock_metadata_path, mock_storage_path
    ):
        """Test saving handles JSON encode errors."""
        mock_storage_file = Path("/test/storage.json")
        mock_storage_path.return_value = mock_storage_file
        mock_metadata_file = Path("/test/metadata.json")
        mock_metadata_path.return_value = mock_metadata_file

        mock_json_dump.side_effect = TypeError("Object is not JSON serializable")

        project_root = Path("/test")
        conversations = [{"id": i} for i in range(10)]
        keywords = ["test"]
        metadata = {}

        with patch("builtins.open", mock_open()):
            result = save_conversations_to_storage(
                project_root, conversations, keywords, metadata
            )

            assert result is False


class TestUtilityFunctions:
    """Test utility functions."""

    def test_clear_conversation_storage(self):
        """Test clearing conversation storage."""
        clear_conversation_storage()

    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_storage_metadata_path")
    def test_get_conversation_storage_info_files_exist(
        self, mock_metadata_path, mock_storage_path
    ):
        """Test getting storage info when files exist."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = True
        mock_stat = Mock()
        mock_stat.st_size = 2048
        mock_storage_file.stat.return_value = mock_stat
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_path.return_value = mock_metadata_file

        result = get_conversation_storage_info()

        expected = {
            "storage_file_exists": True,
            "metadata_file_exists": True,
            "cache_entries": 0,
            "keyword_cache_entries": 0,
            "storage_file_size_mb": round(2048 / (1024 * 1024), 2),
        }

        assert result == expected

    @patch("src.core.conversation_storage.get_storage_file_path")
    @patch("src.core.conversation_storage.get_storage_metadata_path")
    def test_get_conversation_storage_info_files_not_exist(
        self, mock_metadata_path, mock_storage_path
    ):
        """Test getting storage info when files don't exist."""
        mock_storage_file = Mock()
        mock_storage_file.exists.return_value = False
        mock_storage_path.return_value = mock_storage_file

        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = False
        mock_metadata_path.return_value = mock_metadata_file

        result = get_conversation_storage_info()

        expected = {
            "storage_file_exists": False,
            "metadata_file_exists": False,
            "cache_entries": 0,
            "keyword_cache_entries": 0,
        }

        assert result == expected

    def test_generate_context_keywords_alias(self):
        """Test that generate_context_keywords is properly aliased."""
        from src.core.conversation_storage import generate_context_keywords
        from src.core.keyword_extractor import generate_shared_context_keywords

        # Check that they point to the same function (same name)
        assert (
            generate_context_keywords.__name__
            == generate_shared_context_keywords.__name__
        )
        # Check that they're both from conversation_analysis module (ignoring src. prefix)
        assert generate_context_keywords.__module__.endswith("keyword_extractor")
        assert generate_shared_context_keywords.__module__.endswith("keyword_extractor")


class TestIntegration:
    """Integration tests for conversation storage."""

    def test_full_storage_cycle(self, tmp_path):
        """Test complete storage and retrieval cycle."""
        storage_file = tmp_path / "conversations.json"
        metadata_file = tmp_path / "metadata.json"

        with (
            patch(
                "src.core.conversation_storage.get_storage_file_path",
                return_value=storage_file,
            ),
            patch(
                "src.core.conversation_storage.get_storage_metadata_path",
                return_value=metadata_file,
            ),
        ):
            project_root = tmp_path / "project"
            conversations = [{"id": i, "content": f"test{i}"} for i in range(10)]
            keywords = ["python", "test"]
            metadata = {"source": "test"}

            save_result = save_conversations_to_storage(
                project_root, conversations, keywords, metadata
            )
            assert save_result is True

            assert storage_file.exists()
            assert metadata_file.exists()

            loaded_data = load_stored_conversations(project_root)
            assert loaded_data is not None
            assert len(loaded_data["conversations"]) == 10
            assert loaded_data["metadata"] == metadata

            is_valid = is_storage_valid(project_root, keywords)
            assert is_valid is True

    def test_storage_info_integration(self, tmp_path):
        """Test storage info with real files."""
        storage_file = tmp_path / "conversations.json"
        metadata_file = tmp_path / "metadata.json"

        storage_file.write_text('{"test": "data"}')
        metadata_file.write_text('{"test": "metadata"}')

        with (
            patch(
                "src.core.conversation_storage.get_storage_file_path",
                return_value=storage_file,
            ),
            patch(
                "src.core.conversation_storage.get_storage_metadata_path",
                return_value=metadata_file,
            ),
        ):
            info = get_conversation_storage_info()

            assert info["storage_file_exists"] is True
            assert info["metadata_file_exists"] is True
            assert info["storage_file_size_mb"] >= 0.0  # Small files may round to 0.0
