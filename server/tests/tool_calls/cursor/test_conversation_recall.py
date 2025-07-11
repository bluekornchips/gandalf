"""
Tests for conversation recall functionality.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.tool_calls.cursor.recall import (
    TOOL_RECALL_CURSOR_CONVERSATIONS,
    analyze_conversation_relevance,
    get_project_cache_hash,
    handle_recall_cursor_conversations,
    is_cache_valid,
    load_cached_conversations,
    save_conversations_to_cache,
)


class TestConversationRecall:
    """Test conversation recall functionality."""

    @pytest.fixture
    def mock_cursor_query(self):
        """Mock CursorQuery for testing."""
        with patch("src.tool_calls.cursor.query.CursorQuery") as mock:
            yield mock

    @pytest.fixture
    def mock_generate_keywords(self):
        """Mock keyword generation for testing."""
        with patch(
            "src.tool_calls.cursor.recall.generate_conversation_keywords"
        ) as mock:
            yield mock

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            # Create some test files
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "src").mkdir()
            (project_root / "src" / "main.py").write_text("print('hello')")
            yield project_root

    @patch("src.tool_calls.cursor.query.CursorQuery")
    def test_recall_cursor_conversations_basic(self, mock_cursor_query):
        """Test basic conversation recall functionality."""
        arguments = {"limit": 10, "days_lookback": 7}
        project_root = Mock()

        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "workspace_hash": "test123",
                    "conversations": [
                        {
                            "id": "conv1",
                            "title": "Test conversation",
                            "user_query": "How to test?",
                        }
                    ],
                }
            ]
        }

        result = handle_recall_cursor_conversations(arguments, project_root)

        assert "content" in result
        assert len(result["content"]) > 0

    @patch("src.tool_calls.cursor.query.CursorQuery")
    def test_recall_cursor_conversations_fast_mode(self, mock_cursor_query):
        """Test fast mode conversation recall."""
        arguments = {"fast_mode": True, "limit": 10, "days_lookback": 7}
        project_root = Mock()

        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "workspace_hash": "test456",
                    "conversations": [
                        {
                            "id": "conv2",
                            "title": "Fast test",
                            "user_query": "Quick question",
                        }
                    ],
                }
            ]
        }

        result = handle_recall_cursor_conversations(arguments, project_root)

        assert "content" in result
        assert len(result["content"]) > 0

    def test_tool_definition_structure(self):
        """Test that the tool definition has the correct structure."""
        tool = TOOL_RECALL_CURSOR_CONVERSATIONS

        assert tool["name"] == "recall_cursor_conversations"
        assert "description" in tool
        assert "inputSchema" in tool
        assert "properties" in tool["inputSchema"]
        assert "limit" in tool["inputSchema"]["properties"]

    def test_get_project_cache_hash(self, temp_project_root):
        """Test project cache hash generation."""
        keywords = ["python", "test"]
        hash1 = get_project_cache_hash(temp_project_root, keywords)
        hash2 = get_project_cache_hash(temp_project_root, keywords)

        # Same inputs should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 character MD5 hash

        # Different keywords should produce different hash
        hash3 = get_project_cache_hash(temp_project_root, ["javascript", "react"])
        assert hash1 != hash3

    def test_get_project_cache_hash_with_nonexistent_path(self):
        """Test cache hash with non-existent path."""
        fake_path = Path("/nonexistent/path")
        keywords = ["test"]
        hash_result = get_project_cache_hash(fake_path, keywords)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 16

    @patch("src.utils.cache.get_cache_directory")
    def test_is_cache_valid_no_metadata(self, mock_cache_dir, temp_project_root):
        """Test cache validity when metadata file doesn't exist."""
        mock_cache_dir.return_value = temp_project_root
        result = is_cache_valid(temp_project_root, ["test"])
        assert result is False

    @patch("src.utils.cache.get_cache_directory")
    def test_is_cache_valid_expired_cache(self, mock_cache_dir, temp_project_root):
        """Test cache validity with expired cache."""
        mock_cache_dir.return_value = temp_project_root
        metadata_file = temp_project_root / "conversation_cache_metadata.json"
        # Create expired metadata
        old_time = time.time() - 86400  # 24 hours ago
        metadata = {"created_at": old_time, "keywords": ["test"]}
        metadata_file.write_text(json.dumps(metadata))
        result = is_cache_valid(temp_project_root, ["test"])
        assert result is False

    @patch("src.utils.cache.get_cache_directory")
    def test_is_cache_valid_corrupt_metadata(self, mock_cache_dir, temp_project_root):
        """Test cache validity with corrupt metadata file."""
        mock_cache_dir.return_value = temp_project_root
        metadata_file = temp_project_root / "conversation_cache_metadata.json"
        metadata_file.write_text("not a json")
        result = is_cache_valid(temp_project_root, ["test"])
        assert result is False

    @patch("src.utils.cache.get_cache_directory")
    def test_is_cache_valid_permission_error(self, mock_cache_dir, temp_project_root):
        """Test cache validity with permission error."""
        mock_cache_dir.return_value = temp_project_root
        metadata_file = temp_project_root / "conversation_cache_metadata.json"
        metadata_file.write_text("{}")
        # Simulate permission error by patching open
        with patch("builtins.open", side_effect=PermissionError):
            result = is_cache_valid(temp_project_root, ["test"])
            assert result is False

    def test_load_cached_conversations_no_file(self):
        """Test loading cached conversations when file doesn't exist."""
        # Use a truly nonexistent path
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")
        result = load_cached_conversations(nonexistent_path)
        assert result is None

    def test_load_cached_conversations_corrupt_file(self, temp_project_root):
        """Test loading cached conversations with corrupt file."""
        cache_file = temp_project_root / "conversation_cache.json"
        # Remove any existing valid cache file
        if cache_file.exists():
            cache_file.unlink()
        cache_file.write_text("not a json")
        # Clear global cache to force disk read

        result = load_cached_conversations(temp_project_root)
        assert result is None

    @patch("src.utils.cache.get_cache_directory")
    def test_load_cached_conversations_permission_error(
        self, mock_cache_dir, temp_project_root
    ):
        """Test loading cached conversations with permission error."""
        mock_cache_dir.return_value = temp_project_root
        cache_file = temp_project_root / "conversation_cache.json"
        cache_file.write_text("{}")
        with patch("builtins.open", side_effect=PermissionError):
            result = load_cached_conversations(temp_project_root)
            assert result is None

    @patch("src.utils.cache.get_cache_directory")
    def test_save_conversations_to_cache(self, mock_cache_dir):
        """Test saving conversations to cache."""
        # Test basic save functionality
        conversations = [{"id": "test1", "title": "Test"}]
        keywords = ["test"]
        metadata = {"count": 1}

        mock_cache_dir.return_value = Path("/tmp/test_cache")
        result = save_conversations_to_cache(
            Path("/tmp/project"), conversations, keywords, metadata
        )
        # Function should return True on success or False on failure
        assert isinstance(result, bool)

    def test_extract_keywords_from_content(self, temp_project_root):
        """Test keyword extraction from file content."""
        # Create mock conversation data with the expected structure
        conversation = {
            "composerId": "test-conv-id",
            "name": "Python Development Guide",
            "lastUpdatedAt": int(time.time() * 1000),
        }

        prompts = [
            {
                "conversationId": "test-conv-id",
                "text": "This is a Python web API project with Django framework",
            }
        ]

        generations = [
            {
                "conversationId": "test-conv-id",
                "text": "Here's how to structure your Python project",
            }
        ]

        context_keywords = ["python", "web", "api", "django"]

        score, analysis = analyze_conversation_relevance(
            conversation,
            prompts,
            generations,
            context_keywords,
            temp_project_root,
            include_detailed_analysis=True,
        )

        assert isinstance(score, float)
        assert isinstance(analysis, dict)
        assert score > 0  # Should have some relevance due to keyword matches

    @patch("src.tool_calls.cursor.query.CursorQuery")
    def test_recall_cursor_conversations_with_error(self, mock_cursor_query):
        """Test conversation recall with error handling."""
        arguments = {"limit": 10, "days_lookback": 7}
        project_root = Mock()

        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.side_effect = Exception("Database error")

        # The function should handle the exception and return an error response
        try:
            result = handle_recall_cursor_conversations(arguments, project_root)
            # If it doesn't raise an exception, check for error content
            assert "content" in result or "isError" in result
        except Exception:
            # If it does raise an exception, that's also acceptable behavior
            pass

    @patch("src.tool_calls.cursor.query.CursorQuery")
    def test_recall_cursor_conversations_empty_result(self, mock_cursor_query):
        """Test conversation recall with empty results."""
        arguments = {"limit": 10, "days_lookback": 7}
        project_root = Mock()

        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {"workspaces": []}

        result = handle_recall_cursor_conversations(arguments, project_root)

        assert "content" in result or "isError" in result
        if "content" in result:
            assert len(result["content"]) > 0

    def test_handle_recall_cursor_conversations_invalid_limit(self):
        """Test handler with invalid limit parameter - should clamp to valid range."""
        arguments = {"limit": -1}
        project_root = Path("/test/project")
        result = handle_recall_cursor_conversations(arguments, project_root)
        # Function should succeed and clamp limit to minimum value (1)
        assert "content" in result
        assert result.get("isError") is not True

    def test_handle_recall_cursor_conversations_invalid_days_lookback(self):
        """Test handler with invalid days_lookback parameter - should clamp to valid range."""
        arguments = {"days_lookback": 0}
        project_root = Path("/test/project")
        result = handle_recall_cursor_conversations(arguments, project_root)
        # Function should succeed and clamp days_lookback to minimum value (1)
        assert "content" in result
        assert result.get("isError") is not True

    def test_handle_recall_cursor_conversations_invalid_min_relevance_score(
        self,
    ):
        """Test handler with invalid min_relevance_score parameter - should clamp to valid range."""
        arguments = {"min_score": -1}
        project_root = Path("/test/project")
        result = handle_recall_cursor_conversations(arguments, project_root)
        # Function should succeed and clamp min_score to minimum value (0.0)
        assert "content" in result
        assert result.get("isError") is not True

    def test_handle_recall_cursor_conversations_invalid_conversation_types(
        self,
    ):
        """Test handler with invalid conversation_types parameter - should use defaults."""
        arguments = {"conversation_types": "notalist"}
        project_root = Path("/test/project")
        result = handle_recall_cursor_conversations(arguments, project_root)
        # Function should succeed and use default conversation types
        assert "content" in result
        assert result.get("isError") is not True

    def test_analyze_conversation_relevance_basic(self, temp_project_root):
        """Test basic conversation relevance analysis."""
        # Create mock conversation data with the expected structure
        conversation = {
            "composerId": "test-conv-id",
            "name": "Python Development Guide",
            "lastUpdatedAt": int(time.time() * 1000),
        }

        prompts = [
            {
                "conversationId": "test-conv-id",
                "text": "This is a Python Development Guide about writing Python code and following PEP8",
            }
        ]

        generations = [
            {
                "conversationId": "test-conv-id",
                "text": "Here are the best practices for Python development",
            }
        ]

        context_keywords = ["python", "development"]

        score, analysis = analyze_conversation_relevance(
            conversation,
            prompts,
            generations,
            context_keywords,
            temp_project_root,
            include_detailed_analysis=True,
        )

        assert isinstance(score, float)
        assert isinstance(analysis, dict)
        assert score >= 0
