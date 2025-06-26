"""
Tests for conversation ingestion functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.tool_calls.conversation_ingestion import (
    handle_ingest_conversations,
    handle_query_conversation_context,
)


class TestConversationIngestion:
    """Test conversation ingestion functionality."""

    def test_handle_ingest_conversations_basic(self):
        """Test basic conversation ingestion."""
        arguments = {"fast_mode": True, "limit": 10, "days_lookback": 7}

        project_root = Mock()

        with patch(
            "src.tool_calls.conversation_ingestion.CursorQuery"
        ) as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = {
                "workspaces": [
                    {
                        "workspace_hash": "eowyn123",
                        "conversations": [
                            {
                                "id": "conv1",
                                "name": "Do you wish then that our places had been exchanged?",
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

            with patch(
                "src.tool_calls.conversation_ingestion.generate_context_keywords"
            ) as mock_keywords:
                mock_keywords.return_value = ["test", "keywords"]

                result = handle_ingest_conversations(arguments, project_root)

                assert "content" in result
                assert len(result["content"]) > 0

    def test_handle_query_conversation_context_basic(self):
        """Test basic conversation context querying."""
        arguments = {
            "query": "test query",
            "limit": 10,
            "include_content": False,
        }

        project_root = Mock()

        with patch(
            "src.tool_calls.conversation_ingestion.CursorQuery"
        ) as mock_cursor:
            mock_instance = Mock()
            mock_cursor.return_value = mock_instance
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
                        "prompts": [
                            {"id": "prompt1", "text": "Fly, you fools!"}
                        ],
                        "generations": [
                            {
                                "id": "gen1",
                                "text": "I will not say: do not weep; for not all tears are an evil.",
                            }
                        ],
                    }
                ]
            }

            result = handle_query_conversation_context(arguments, project_root)

            assert "content" in result
            assert len(result["content"]) > 0

    def test_invalid_arguments_handling(self):
        """Test handling of invalid arguments."""
        arguments = {}
        project_root = Mock()

        result = handle_query_conversation_context(arguments, project_root)

        assert "content" in result or "isError" in result
