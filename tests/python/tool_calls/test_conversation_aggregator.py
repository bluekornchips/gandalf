"""
Tests for conversation aggregator.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.conversation_aggregator import (
    _detect_available_ides,
    _standardize_conversation_format,
    handle_recall_conversations,
    handle_search_conversations,
)


class TestConversationAggregator(unittest.TestCase):
    """Test conversation aggregator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.project_root = Path("/tmp/test_project")
        self.project_root.mkdir(exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        if self.project_root.exists():
            import shutil

            shutil.rmtree(self.project_root, ignore_errors=True)

    def test_standardize_conversation_format_cursor(self):
        """Test standardizing Cursor conversation format."""
        cursor_conv = {
            "conversation_id": "test-123",
            "name": "Test Conversation",
            "last_updated": "2024-01-01T00:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "workspace_hash": "abcd1234",
            "total_exchanges": 5,
            "activity_score": 3.5,
        }

        result = _standardize_conversation_format(cursor_conv, "cursor")

        self.assertEqual(result["source_ide"], "cursor")
        self.assertEqual(result["conversation_id"], "test-123")
        self.assertEqual(result["title"], "Test Conversation")
        self.assertEqual(result["message_count"], 5)
        self.assertEqual(result["relevance_score"], 3.5)

    def test_standardize_conversation_format_claude_code(self):
        """Test standardizing Claude Code conversation format."""
        claude_conv = {
            "session_id": "session-456",
            "summary": "This is a test conversation about Python...",
            "last_modified": "2024-01-01T00:00:00Z",
            "start_time": "2024-01-01T00:00:00Z",
            "working_directory": "/home/user/project",
            "message_count": 8,
            "relevance_score": 4.2,
            "conversation_type": "debugging",
            "keyword_matches": ["python", "error"],
            "file_references": ["main.py"],
        }

        result = _standardize_conversation_format(claude_conv, "claude-code")

        self.assertEqual(result["source_ide"], "claude-code")
        self.assertEqual(result["conversation_id"], "session-456")
        self.assertEqual(
            result["title"], "This is a test conversation about Python"
        )
        self.assertEqual(result["message_count"], 8)
        self.assertEqual(result["relevance_score"], 4.2)
        self.assertEqual(result["conversation_type"], "debugging")
        self.assertEqual(result["keyword_matches"], ["python", "error"])

    @patch("src.tool_calls.conversation_aggregator.get_available_ides")
    @patch("src.tool_calls.conversation_aggregator.AdapterFactory")
    def test_detect_available_ides(
        self, mock_factory, mock_get_available_ides
    ):
        """Test IDE detection functionality."""
        # Mock database scanner to return no IDEs, force fallback to environment detection
        mock_get_available_ides.return_value = []

        # Mock cursor adapter
        mock_cursor_adapter = Mock()
        mock_cursor_adapter.detect_ide.return_value = True

        # Mock claude-code adapter
        mock_claude_adapter = Mock()
        mock_claude_adapter.detect_ide.return_value = False

        def mock_create_adapter(explicit_ide=None):
            if explicit_ide == "cursor":
                return mock_cursor_adapter
            elif explicit_ide == "claude-code":
                return mock_claude_adapter
            return Mock()

        mock_factory.create_adapter.side_effect = mock_create_adapter

        result = _detect_available_ides()

        self.assertEqual(result, ["cursor"])
        self.assertEqual(mock_factory.create_adapter.call_count, 2)

    @patch("src.tool_calls.conversation_aggregator._detect_available_ides")
    @patch("src.tool_calls.conversation_aggregator.AdapterFactory")
    @patch(
        "src.tool_calls.conversation_aggregator.generate_shared_context_keywords"
    )
    def test_handle_recall_conversations_no_ides(
        self, mock_keywords, mock_factory, mock_detect
    ):
        """Test recall when no IDEs are available."""
        # Mock detection to return no IDEs
        mock_detect.return_value = []
        mock_keywords.return_value = ["python", "test"]

        arguments = {"limit": 10}
        result = handle_recall_conversations(arguments, self.project_root)

        self.assertIn("content", result)
        self.assertNotIn("isError", result)
        data = json.loads(result["content"][0]["text"])
        self.assertEqual(data["conversations"], [])
        self.assertEqual(data["available_ides"], [])
        self.assertEqual(data["message"], "No compatible IDEs detected")

    @patch("src.tool_calls.conversation_aggregator._detect_available_ides")
    @patch("src.tool_calls.conversation_aggregator.AdapterFactory")
    @patch(
        "src.tool_calls.conversation_aggregator.generate_shared_context_keywords"
    )
    def test_handle_search_conversations_with_multiple_ides(
        self, mock_keywords, mock_factory, mock_detect
    ):
        """Test search with multiple IDEs available."""
        # Mock scanner to return multiple IDEs
        mock_detect.return_value = ["cursor", "claude-code"]
        mock_keywords.return_value = ["python", "test"]

        # Mock adapters and handlers
        cursor_adapter = Mock()
        cursor_search_handler = Mock()
        cursor_search_handler.return_value = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "conversations": [
                                {
                                    "conversation_id": "cursor-123",
                                    "name": "Cursor Chat",
                                    "match_count": 2,
                                    "matches": [],
                                }
                            ],
                            "total_results": 1,
                            "processing_time": 0.3,
                        }
                    ),
                }
            ]
        }
        cursor_adapter.get_conversation_handlers.return_value = {
            "search_cursor_conversations": cursor_search_handler
        }

        claude_adapter = Mock()
        claude_search_handler = Mock()
        claude_search_handler.return_value = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "results": [
                                {
                                    "session_id": "claude-456",
                                    "summary": "Claude Chat about testing",
                                    "match_count": 1,
                                    "matches": [],
                                    "relevance_score": 3.0,
                                }
                            ],
                            "total_results": 1,
                            "processing_time": 0.4,
                        }
                    ),
                }
            ]
        }
        claude_adapter.get_conversation_handlers.return_value = {
            "search_claude_conversations": claude_search_handler
        }

        def mock_create_adapter(explicit_ide=None, project_root=None):
            if explicit_ide == "cursor":
                return cursor_adapter
            elif explicit_ide == "claude-code":
                return claude_adapter
            return Mock()

        mock_factory.create_adapter.side_effect = mock_create_adapter

        arguments = {"query": "python", "limit": 10}
        result = handle_search_conversations(arguments, self.project_root)

        self.assertIn("content", result)
        self.assertNotIn("isError", result)
        data = json.loads(result["content"][0]["text"])
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["available_ides"], ["cursor", "claude-code"])

        # Results should be sorted by relevance score
        self.assertEqual(
            data["results"][0]["source_ide"], "claude-code"
        )  # Higher score
        self.assertEqual(data["results"][1]["source_ide"], "cursor")

    def test_handle_search_conversations_missing_query(self):
        """Test search with missing query parameter."""
        arguments = {"limit": 10}
        result = handle_search_conversations(arguments, self.project_root)

        self.assertIn("isError", result)
        self.assertIn("query parameter is required", result["error"])


if __name__ == "__main__":
    unittest.main()
