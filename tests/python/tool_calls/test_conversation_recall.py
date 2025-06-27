"""
Tests for conversation recall functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.tool_calls.conversation_recall import (
    handle_recall_cursor_conversations,
    handle_search_cursor_conversations,
)


class TestConversationRecall:
    """Test conversation recall functionality."""

    @pytest.fixture
    def mock_cursor_query(self):
        """Mock CursorQuery for testing."""
        with patch("src.tool_calls.conversation_recall.CursorQuery") as mock:
            yield mock

    @pytest.fixture
    def mock_generate_keywords(self):
        """Mock keyword generation for testing."""
        with patch(
            "src.tool_calls.conversation_recall.generate_context_keywords"
        ) as mock:
            mock.return_value = ["test", "keyword"]
            yield mock

    @patch("src.tool_calls.conversation_recall.CursorQuery")
    def test_recall_cursor_conversations_fast_mode(self, mock_cursor_query):
        """Test fast mode conversation recall."""
        arguments = {"fast_mode": True, "limit": 10, "days_lookback": 7}

        project_root = Mock()

        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "workspace_hash": "eowyn123",
                    "conversations": [
                        {
                            "id": "conv1",
                            "name": (
                                "Do you wish then that our places had been "
                                "exchanged?"
                            ),
                            "lastUpdatedAt": 1640995200000,  # 2022-01-01
                            "createdAt": 1640995200000,
                            "promptCount": 2,
                            "generationCount": 2,
                        }
                    ],
                    "prompts": [],
                    "generations": [],
                }
            ]
        }

        result = handle_recall_cursor_conversations(arguments, project_root)

        assert "content" in result
        assert len(result["content"]) > 0

    @patch("src.tool_calls.conversation_recall.CursorQuery")
    def test_search_cursor_conversations_basic(self, mock_cursor_query):
        """Test basic conversation search functionality."""
        arguments = {
            "query": "test query",
            "limit": 10,
            "include_content": False,
        }

        project_root = Mock()

        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "workspace_hash": "gandalf123",
                    "conversations": [
                        {
                            "id": "conv1",
                            "name": "So passes Denethor, son of Ecthelion.",
                            "lastUpdatedAt": 1640995200000,
                            "createdAt": 1640995200000,
                            "promptCount": 2,
                            "generationCount": 2,
                        }
                    ],
                    "prompts": [{"id": "prompt1", "text": "Fly, you fools!"}],
                    "generations": [
                        {
                            "id": "gen1",
                            "text": (
                                "I will not say: do not weep; for not all "
                                "tears are an evil."
                            ),
                        }
                    ],
                }
            ]
        }

        result = handle_search_cursor_conversations(arguments, project_root)

        assert "content" in result
        assert len(result["content"]) > 0

    def test_invalid_arguments_handling(self):
        """Test handling of invalid arguments."""
        arguments = {}
        project_root = Mock()

        result = handle_search_cursor_conversations(arguments, project_root)

        assert "content" in result or "isError" in result
