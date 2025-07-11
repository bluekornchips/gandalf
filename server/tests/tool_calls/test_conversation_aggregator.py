"""
Tests for conversation aggregator functionality.

Tests conversation recall, filtering, aggregation, and cross-platform
conversation analysis with comprehensive coverage.
"""

import json
import tempfile
from pathlib import Path

from src.tool_calls.aggregator import (
    handle_recall_conversations,
)


class TestHandleRecallConversations:
    """Test handle_recall_conversations function."""

    def test_handle_recall_basic(self):
        """Test basic conversation recall handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            result = handle_recall_conversations(project_root=project_root)

            assert isinstance(result, dict)
            assert "content" in result
            assert isinstance(result["content"], list)
            assert len(result["content"]) > 0

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content
            assert "available_tools" in parsed_content

    def test_handle_recall_with_arguments(self):
        """Test conversation recall with arguments."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            result = handle_recall_conversations(
                fast_mode=True, days_lookback=30, limit=5, project_root=project_root
            )

            assert isinstance(result, dict)
            assert "content" in result

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content
            assert "parameters" in parsed_content

    def test_handle_recall_with_search_query(self):
        """Test conversation recall with search query."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            result = handle_recall_conversations(
                search_query="Python", project_root=project_root
            )

            assert isinstance(result, dict)
            assert "content" in result

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content
            assert "search_query" in parsed_content
            assert parsed_content["search_query"] == "Python"

    def test_handle_recall_with_tools_filter(self):
        """Test conversation recall with tools filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            result = handle_recall_conversations(
                tools=["cursor"], project_root=project_root
            )

            assert isinstance(result, dict)
            assert "content" in result

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content
            assert "parameters" in parsed_content

    def test_handle_recall_with_tags(self):
        """Test conversation recall with tags."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            result = handle_recall_conversations(
                tags=["python", "debugging"], project_root=project_root
            )

            assert isinstance(result, dict)
            assert "content" in result

            # Parse JSON content
            content_text = result["content"][0]["text"]
            parsed_content = json.loads(content_text)
            assert "conversations" in parsed_content
            assert "tags" in parsed_content
