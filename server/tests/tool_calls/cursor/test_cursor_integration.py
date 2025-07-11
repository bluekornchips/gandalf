"""
Tests for cursor integration functionality.

Tests cursor database interaction, conversation retrieval, and integration
with the gandalf system for comprehensive cursor functionality testing.
"""

import json
import tempfile
from pathlib import Path

from src.tool_calls.cursor.recall import handle_recall_cursor_conversations
from src.config.constants.conversation import CONVERSATION_BATCH_SIZE


class TestCursorIntegration:
    """Test cursor integration functionality."""

    def test_handle_recall_cursor_conversations_basic(self):
        """Test basic cursor conversation recall functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Test basic function call
            arguments = {
                "fast_mode": True,
                "days_lookback": 30,
                "limit": 10,
                "min_score": 0.0,
            }

            result = handle_recall_cursor_conversations(arguments, project_root)

            # Should return a valid response structure
            assert isinstance(result, dict)
            assert "content" in result
            assert isinstance(result["content"], list)
            assert len(result["content"]) > 0

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content

    def test_handle_recall_cursor_conversations_with_search(self):
        """Test cursor conversation recall with search query."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            arguments = {
                "fast_mode": True,
                "days_lookback": 30,
                "limit": 10,
                "min_score": 0.0,
                "query": "Python",
            }

            result = handle_recall_cursor_conversations(arguments, project_root)

            # Should return a valid response structure
            assert isinstance(result, dict)
            assert "content" in result
            assert isinstance(result["content"], list)
            assert len(result["content"]) > 0

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content

    def test_cursor_integration_constants(self):
        """Test that cursor integration constants are accessible."""
        assert CONVERSATION_BATCH_SIZE > 0
