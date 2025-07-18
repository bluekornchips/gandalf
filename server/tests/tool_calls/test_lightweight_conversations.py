"""
Tests for lightweight conversation creation across all tools.
"""

import unittest

from src.config.constants.conversation import (
    CONVERSATION_ID_DISPLAY_LIMIT,
    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
)
from src.tool_calls.claude_code.recall import (
    create_lightweight_conversation as claude_create_lightweight,
)
from src.tool_calls.claude_code.recall import (
    standardize_conversation as claude_standardize_conversation,
)
from src.tool_calls.cursor.recall import (
    create_lightweight_conversation as cursor_create_lightweight,
)
from src.tool_calls.cursor.recall import (
    standardize_conversation as cursor_standardize_conversation,
)
from src.tool_calls.windsurf.recall import (
    create_lightweight_conversation as windsurf_create_lightweight,
)
from src.tool_calls.windsurf.recall import (
    standardize_conversation as windsurf_standardize_conversation,
)


class TestLightweightConversations(unittest.TestCase):
    """Test lightweight conversation creation for all tools."""

    def setUp(self):
        """Set up test data."""
        self.long_id = "a" * 100
        self.long_title = "b" * 200
        self.long_snippet = "c" * 300

        self.base_conversation = {
            "id": self.long_id,
            "title": self.long_title,
            "snippet": self.long_snippet,
            "message_count": 42,
            "relevance_score": 3.14159,
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:30:00Z",
        }

    def test_constants_are_defined(self):
        """Test that all lightweight conversation constants are properly defined."""
        self.assertEqual(CONVERSATION_ID_DISPLAY_LIMIT, 50)
        self.assertEqual(CONVERSATION_TITLE_DISPLAY_LIMIT, 100)
        self.assertEqual(CONVERSATION_SNIPPET_DISPLAY_LIMIT, 150)

    def test_claude_create_lightweight_conversation_basic(self):
        """Test Claude Code lightweight conversation creation with basic data."""
        conversation = {
            "id": "gandalf_session_123",
            "title": "Gandalf's Wisdom Session",
            "snippet": "A short snippet",
            "message_count": 5,
            "relevance_score": 2.5,
            "created_at": "2024-01-01T10:00:00Z",
        }

        result = claude_create_lightweight(conversation)

        expected_fields = {
            "id",
            "title",
            "source_tool",
            "message_count",
            "relevance_score",
            "created_at",
            "snippet",
        }
        self.assertEqual(set(result.keys()), expected_fields)
        self.assertEqual(result["source_tool"], "claude-code")
        self.assertEqual(result["id"], "gandalf_session_123")
        self.assertEqual(result["title"], "Gandalf's Wisdom Session")
        self.assertEqual(result["snippet"], "A short snippet")
        self.assertEqual(result["message_count"], 5)
        self.assertEqual(result["relevance_score"], 2.5)

    def test_claude_create_lightweight_conversation_truncation(self):
        """Test Claude Code lightweight conversation creation with field truncation."""
        result = claude_create_lightweight(self.base_conversation)

        self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)
        self.assertEqual(result["id"], self.long_id[:CONVERSATION_ID_DISPLAY_LIMIT])

        self.assertTrue(result["title"].endswith("..."))
        self.assertEqual(len(result["title"]), CONVERSATION_TITLE_DISPLAY_LIMIT + 3)

        self.assertTrue(result["snippet"].endswith("..."))
        self.assertEqual(len(result["snippet"]), CONVERSATION_SNIPPET_DISPLAY_LIMIT + 3)

    def test_claude_create_lightweight_conversation_fallback_fields(self):
        """Test Claude Code lightweight conversation with fallback field mappings."""
        conversation = {
            "session_id": "bilbo_session_456",
            "summary": "Bilbo's Adventure Summary",
            "start_time": "2024-01-01T09:00:00Z",
            "last_modified": "2024-01-01T09:30:00Z",
            "message_count": 3,
            "relevance_score": 1.8,
        }

        result = claude_create_lightweight(conversation)

        self.assertEqual(result["id"], "bilbo_session_456")
        self.assertEqual(result["title"], "Bilbo's Adventure Summary")
        self.assertEqual(result["created_at"], "2024-01-01T09:00:00Z")
        self.assertEqual(result["snippet"], "Bilbo's Adventure Summary")

    def test_cursor_create_lightweight_conversation_basic(self):
        """Test Cursor lightweight conversation creation with basic data."""
        conversation = {
            "id": "frodo_conv_789",
            "title": "Frodo's Quest Discussion",
            "snippet": "Ring bearer's journey",
            "message_count": 8,
            "relevance_score": 4.2,
            "created_at": "2024-01-01T11:00:00Z",
        }

        result = cursor_create_lightweight(conversation)

        expected_fields = {
            "id",
            "title",
            "source_tool",
            "message_count",
            "relevance_score",
            "created_at",
            "snippet",
        }
        self.assertEqual(set(result.keys()), expected_fields)
        self.assertEqual(result["source_tool"], "cursor")
        self.assertEqual(result["id"], "frodo_conv_789")
        self.assertEqual(result["title"], "Frodo's Quest Discussion")
        self.assertEqual(result["snippet"], "Ring bearer's journey")

    def test_cursor_create_lightweight_conversation_truncation(self):
        """Test Cursor lightweight conversation creation with field truncation."""
        result = cursor_create_lightweight(self.base_conversation)

        # Test same truncation behavior as Claude Code
        self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)
        self.assertTrue(result["title"].endswith("..."))
        self.assertTrue(result["snippet"].endswith("..."))

    def test_cursor_create_lightweight_conversation_fallback_fields(self):
        """Test Cursor lightweight conversation with fallback field mappings."""
        conversation = {
            "conversation_id": "samwise_fallback_101",
            "name": "Samwise's Garden Tales",
            "last_updated": "2024-01-01T14:00:00Z",
            "message_count": 6,
            "relevance_score": 3.7,
        }

        result = cursor_create_lightweight(conversation)

        self.assertEqual(result["id"], "samwise_fallback_101")
        self.assertEqual(result["title"], "Samwise's Garden Tales")

    def test_windsurf_create_lightweight_conversation_basic(self):
        """Test Windsurf lightweight conversation creation with basic data."""
        conversation = {
            "id": "aragorn_chat_202",
            "title": "Aragorn's Council Meeting",
            "snippet": "King's strategic planning",
            "message_count": 12,
            "relevance_score": 2.9,
            "created_at": "2024-01-01T13:00:00Z",
        }

        result = windsurf_create_lightweight(conversation)

        expected_fields = {
            "id",
            "title",
            "source_tool",
            "message_count",
            "relevance_score",
            "created_at",
            "snippet",
        }
        self.assertEqual(set(result.keys()), expected_fields)
        self.assertEqual(result["source_tool"], "windsurf")
        self.assertEqual(result["id"], "aragorn_chat_202")
        self.assertEqual(result["title"], "Aragorn's Council Meeting")

    def test_windsurf_create_lightweight_conversation_truncation(self):
        """Test Windsurf lightweight conversation creation with field truncation."""
        result = windsurf_create_lightweight(self.base_conversation)

        self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)
        self.assertTrue(result["title"].endswith("..."))
        self.assertTrue(result["snippet"].endswith("..."))

    def test_windsurf_create_lightweight_conversation_fallback_fields(self):
        """Test Windsurf lightweight conversation with fallback field mappings."""
        conversation = {
            "chat_session_id": "treebeard_fallback_303",
            "message_count": 1,
            "relevance_score": 1.5,
        }

        result = windsurf_create_lightweight(conversation)

        self.assertEqual(result["id"], "treebeard_fallback_303")
        # Should generate default title when no title provided
        self.assertTrue(result["title"].startswith("Windsurf Chat"))

    def test_windsurf_create_lightweight_conversation_default_title(self):
        """Test Windsurf lightweight conversation with default title generation."""
        conversation = {
            "id": "elrond_404",
            "message_count": 1,
            "relevance_score": 1.0,
        }

        result = windsurf_create_lightweight(conversation)

        # Should generate title with ID (actual implementation uses f"Windsurf Chat {id[:8]}")
        # For "elrond_404", the first 8 chars are "elrond_4"
        expected_title = "Windsurf Chat elrond_4"  # First 8 chars of "elrond_404"
        self.assertEqual(result["title"], expected_title)

    def test_all_tools_consistent_field_structure(self):
        """Test that all tools return consistent field structures."""
        test_conversation = {
            "id": "legolas_123",
            "title": "Fellowship Planning",
            "snippet": "Elven archer's insights",
            "message_count": 5,
            "relevance_score": 2.5,
            "created_at": "2024-01-01T12:00:00Z",
        }

        claude_result = claude_create_lightweight(test_conversation)
        cursor_result = cursor_create_lightweight(test_conversation)
        windsurf_result = windsurf_create_lightweight(test_conversation)

        # All should have the same field structure
        expected_fields = {
            "id",
            "title",
            "source_tool",
            "message_count",
            "relevance_score",
            "created_at",
            "snippet",
        }

        self.assertEqual(set(claude_result.keys()), expected_fields)
        self.assertEqual(set(cursor_result.keys()), expected_fields)
        self.assertEqual(set(windsurf_result.keys()), expected_fields)

        # Source tools should be different
        self.assertEqual(claude_result["source_tool"], "claude-code")
        self.assertEqual(cursor_result["source_tool"], "cursor")
        self.assertEqual(windsurf_result["source_tool"], "windsurf")

        # Other fields should be the same
        for field in ["id", "title", "snippet", "message_count", "relevance_score"]:
            self.assertEqual(claude_result[field], cursor_result[field])
            self.assertEqual(cursor_result[field], windsurf_result[field])

    def test_all_tools_handle_empty_conversation(self):
        """Test that all tools handle empty/minimal conversation data gracefully."""
        empty_conversation = {}

        claude_result = claude_create_lightweight(empty_conversation)
        cursor_result = cursor_create_lightweight(empty_conversation)
        windsurf_result = windsurf_create_lightweight(empty_conversation)

        for result in [claude_result, cursor_result, windsurf_result]:
            self.assertIn("id", result)
            self.assertIn("title", result)
            self.assertIn("source_tool", result)
            self.assertIn("message_count", result)
            self.assertIn("relevance_score", result)
            self.assertIn("created_at", result)
            self.assertIn("snippet", result)

        # Claude Code and Cursor should default message_count to 0, Windsurf defaults to 1
        self.assertEqual(claude_result["message_count"], 0)
        self.assertEqual(cursor_result["message_count"], 0)
        self.assertEqual(windsurf_result["message_count"], 1)  # Windsurf defaults to 1

        # All should default relevance score to 0
        for result in [claude_result, cursor_result, windsurf_result]:
            self.assertEqual(result["relevance_score"], 0.0)

    def test_relevance_score_rounding(self):
        """Test that relevance scores are properly rounded to 2 decimal places."""
        conversation = {
            "id": "test_rounding",
            "title": "Rounding Test",
            "relevance_score": 3.14159265359,  # Many decimal places
        }

        claude_result = claude_create_lightweight(conversation)
        cursor_result = cursor_create_lightweight(conversation)
        windsurf_result = windsurf_create_lightweight(conversation)

        for result in [claude_result, cursor_result, windsurf_result]:
            self.assertEqual(result["relevance_score"], 3.14)

    def test_constants_match_actual_truncation_behavior(self):
        """Test that the constants actually match the truncation behavior."""
        # Create conversation with fields exactly at the limit
        conversation = {
            "id": "x" * CONVERSATION_ID_DISPLAY_LIMIT,
            "title": "y" * CONVERSATION_TITLE_DISPLAY_LIMIT,
            "snippet": "z" * CONVERSATION_SNIPPET_DISPLAY_LIMIT,
        }

        for create_func in [
            claude_create_lightweight,
            cursor_create_lightweight,
            windsurf_create_lightweight,
        ]:
            result = create_func(conversation)

            # Fields at exactly the limit should not be truncated
            self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)
            self.assertEqual(len(result["title"]), CONVERSATION_TITLE_DISPLAY_LIMIT)
            self.assertEqual(len(result["snippet"]), CONVERSATION_SNIPPET_DISPLAY_LIMIT)
            self.assertFalse(result["title"].endswith("..."))
            self.assertFalse(result["snippet"].endswith("..."))


class TestStandardizeConversations(unittest.TestCase):
    """Test standardize conversation functions for all tools."""

    def setUp(self):
        """Set up test data."""
        self.context_keywords = ["python", "development", "api", "testing"]

        self.test_conversation = {
            "id": "legolas_conv_456",
            "title": "Legolas Standardize Conversation",
            "snippet": "Testing standardization",
            "message_count": 8,
            "relevance_score": 4.567,
            "created_at": "2024-01-01T15:00:00Z",
            "updated_at": "2024-01-01T16:00:00Z",
            "metadata": {"importance": "high"},
            "keyword_matches": ["python", "testing"],
        }

    def test_cursor_standardize_conversation_full(self):
        """Test Cursor standardize conversation with full format."""
        conversation = {
            **self.test_conversation,
            "workspace_id": "cursor_workspace_123",
            "conversation_type": "technical",
            "ai_model": "claude-3.5-sonnet",
            "user_query": "How to implement API?",
            "ai_response": "Here's how to implement the API...",
            "file_references": ["api.py", "tests.py"],
            "code_blocks": ["def api_endpoint(): pass"],
        }

        result = cursor_standardize_conversation(
            conversation, self.context_keywords, lightweight=False
        )

        # Check standard fields
        self.assertEqual(result["source_tool"], "cursor")
        self.assertEqual(result["id"], "legolas_conv_456")
        self.assertEqual(result["title"], "Legolas Standardize Conversation")
        self.assertEqual(result["message_count"], 8)
        self.assertEqual(result["relevance_score"], 4.57)  # Rounded to 2 decimal places

        # Check Cursor-specific fields
        self.assertEqual(result["workspace_id"], "cursor_workspace_123")
        self.assertEqual(result["conversation_type"], "technical")
        self.assertEqual(result["ai_model"], "claude-3.5-sonnet")
        self.assertEqual(result["user_query"], "How to implement API?")
        self.assertEqual(result["file_references"], ["api.py", "tests.py"])
        self.assertEqual(result["code_blocks"], ["def api_endpoint(): pass"])

        # Check context keywords
        self.assertEqual(result["context_keywords"], self.context_keywords)
        self.assertEqual(result["keyword_matches"], ["python", "testing"])

    def test_cursor_standardize_conversation_lightweight(self):
        """Test Cursor standardize conversation with lightweight format."""
        result = cursor_standardize_conversation(
            self.test_conversation, self.context_keywords, lightweight=True
        )

        # Should return lightweight format
        expected_fields = {
            "id",
            "title",
            "source_tool",
            "message_count",
            "relevance_score",
            "created_at",
            "snippet",
        }
        self.assertEqual(set(result.keys()), expected_fields)
        self.assertEqual(result["source_tool"], "cursor")

    def test_claude_standardize_conversation_full(self):
        """Test Claude Code standardize conversation with full format."""
        conversation = {
            **self.test_conversation,
            "session_id": "claude_session_789",
            "project_context": {"language": "python"},
            "context": {"environment": "development"},
            "messages": [{"role": "user", "content": "Hello"}],
            "analysis": {"complexity": "medium"},
            "tool_usage": ["code_analysis"],
            "project_files": ["main.py", "utils.py"],
            "working_directory": "/project",
        }

        result = claude_standardize_conversation(
            conversation, self.context_keywords, lightweight=False
        )

        # Check standard fields
        self.assertEqual(result["source_tool"], "claude-code")
        self.assertEqual(result["id"], "legolas_conv_456")
        self.assertEqual(result["title"], "Legolas Standardize Conversation")

        # Check Claude Code-specific fields
        self.assertEqual(result["session_id"], "claude_session_789")
        self.assertEqual(result["project_context"], {"language": "python"})
        self.assertEqual(result["conversation_context"], {"environment": "development"})
        self.assertEqual(result["messages"], [{"role": "user", "content": "Hello"}])
        self.assertEqual(result["analysis_results"], {"complexity": "medium"})
        self.assertEqual(result["tool_usage"], ["code_analysis"])
        self.assertEqual(result["project_files"], ["main.py", "utils.py"])
        self.assertEqual(result["working_directory"], "/project")

    def test_windsurf_standardize_conversation_full(self):
        """Test Windsurf standardize conversation with full format."""
        conversation = {
            **self.test_conversation,
            "workspace_id": "windsurf_workspace_456",
            "database_path": "/path/to/windsurf.db",
            "session_data": {"participants": ["user", "ai"]},
            "windsurf_source": "chat_session",
            "chat_session_id": "chat_123",
            "windsurf_metadata": {"priority": "normal"},
        }

        result = windsurf_standardize_conversation(
            conversation, self.context_keywords, lightweight=False
        )

        # Check standard fields
        self.assertEqual(result["source_tool"], "windsurf")
        self.assertEqual(result["id"], "legolas_conv_456")
        self.assertEqual(result["title"], "Legolas Standardize Conversation")

        # Check Windsurf-specific fields
        self.assertEqual(result["workspace_id"], "windsurf_workspace_456")
        self.assertEqual(result["database_path"], "/path/to/windsurf.db")
        self.assertEqual(result["session_data"], {"participants": ["user", "ai"]})
        self.assertEqual(result["windsurf_source"], "chat_session")
        self.assertEqual(result["chat_session_id"], "chat_123")
        self.assertEqual(result["windsurf_metadata"], {"priority": "normal"})

    def test_all_standardize_functions_handle_fallback_fields(self):
        """Test that all standardize functions handle fallback field mappings."""
        # Test with fallback field names
        cursor_conversation = {
            "conversation_id": "samwise_fallback_789",  # Fallback for id
            "name": "Samwise Fallback Name",  # Fallback for title
            "last_updated": "2024-01-01T18:00:00Z",  # Fallback for updated_at
            "workspace_hash": "hash123",  # Fallback for workspace_id
        }

        claude_conversation = {
            "session_id": "gandalf_fallback_101",  # Fallback for id
            "summary": "Gandalf Fallback Summary",  # Fallback for title
            "start_time": "2024-01-01T17:00:00Z",  # Fallback for created_at
            "last_modified": "2024-01-01T18:00:00Z",  # Fallback for updated_at
        }

        windsurf_conversation = {
            "chat_session_id": "treebeard_fallback_202",  # Fallback for id
            # No title provided, should generate default
        }

        cursor_result = cursor_standardize_conversation(
            cursor_conversation, self.context_keywords, lightweight=False
        )
        claude_result = claude_standardize_conversation(
            claude_conversation, self.context_keywords, lightweight=False
        )
        windsurf_result = windsurf_standardize_conversation(
            windsurf_conversation, self.context_keywords, lightweight=False
        )

        # Check fallback field mappings worked
        self.assertEqual(cursor_result["id"], "samwise_fallback_789")
        self.assertEqual(cursor_result["title"], "Samwise Fallback Name")
        self.assertEqual(cursor_result["updated_at"], "2024-01-01T18:00:00Z")
        self.assertEqual(cursor_result["workspace_id"], "hash123")

        self.assertEqual(claude_result["id"], "gandalf_fallback_101")
        self.assertEqual(claude_result["title"], "Gandalf Fallback Summary")
        self.assertEqual(claude_result["created_at"], "2024-01-01T17:00:00Z")
        self.assertEqual(claude_result["updated_at"], "2024-01-01T18:00:00Z")

        self.assertEqual(windsurf_result["id"], "treebeard_fallback_202")
        self.assertTrue(windsurf_result["title"].startswith("Windsurf Chat"))

    def test_all_standardize_functions_context_keywords_truncation(self):
        """Test that all standardize functions properly truncate context keywords."""
        # Create a large list of context keywords
        large_keywords = [f"keyword_{i}" for i in range(100)]

        for standardize_func in [
            cursor_standardize_conversation,
            claude_standardize_conversation,
            windsurf_standardize_conversation,
        ]:
            result = standardize_func(
                self.test_conversation, large_keywords, lightweight=False
            )

            from src.config.constants.context import (
                TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
            )

            self.assertEqual(
                len(result["context_keywords"]), TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS
            )
            self.assertEqual(
                result["context_keywords"],
                large_keywords[:TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS],
            )

    def test_standardize_functions_error_handling(self):
        """Test that standardize functions handle errors gracefully."""
        # Test with invalid conversation data
        invalid_conversation = None

        for standardize_func in [
            cursor_standardize_conversation,
            claude_standardize_conversation,
            windsurf_standardize_conversation,
        ]:
            result = standardize_func(
                invalid_conversation, self.context_keywords, lightweight=False
            )
            # Should return empty dict on error
            self.assertEqual(result, {})
