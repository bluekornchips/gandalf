"""
Test suite for conversation filtering functionality.

Tests the simple keyword-based filtering system.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core.conversation_filtering import (
    ConversationFilter,
    apply_conversation_filtering,
    create_conversation_filter,
)


class TestConversationFilter(unittest.TestCase):
    """Test the ConversationFilter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir(parents=True)

        # Create a simple README for context
        (self.project_root / "README.md").write_text(
            "# Test Project\nThis is a Python Django project with React frontend."
        )

    def teardown_method(self, method):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_filter_initialization(self):
        """Test filter initialization without user prompt."""
        filter_obj = ConversationFilter(self.project_root)

        self.assertEqual(filter_obj.project_root, self.project_root)
        self.assertIsNone(filter_obj.user_prompt)
        self.assertIsInstance(filter_obj.base_keywords, list)
        self.assertEqual(filter_obj.prompt_keywords, [])
        self.assertEqual(filter_obj.all_keywords, filter_obj.base_keywords)

    @patch("src.core.conversation_filtering.CONVERSATION_FILTERING_ENABLED", True)
    @patch("src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED", True)
    def test_filter_initialization_with_prompt(self):
        """Test filter initialization with user prompt."""
        user_prompt = (
            "I need help debugging a Python authentication issue in my Django app"
        )
        filter_obj = ConversationFilter(self.project_root, user_prompt)

        self.assertEqual(filter_obj.user_prompt, user_prompt)
        self.assertIsInstance(filter_obj.prompt_keywords, list)
        self.assertGreater(len(filter_obj.all_keywords), len(filter_obj.base_keywords))

    @patch("src.core.conversation_filtering.CONVERSATION_FILTERING_ENABLED", True)
    @patch("src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED", True)
    def test_prompt_keyword_extraction(self):
        """Test keyword extraction from user prompt."""
        user_prompt = "How do I fix authentication errors in my React TypeScript app?"
        filter_obj = ConversationFilter(self.project_root, user_prompt)

        # Should extract technical terms
        prompt_keywords = filter_obj.prompt_keywords
        self.assertIn("authentication", prompt_keywords)
        self.assertIn("react", prompt_keywords)
        self.assertIn("typescript", prompt_keywords)

    def test_conversation_matches_keywords(self):
        """Test keyword matching in conversations."""
        user_prompt = "Python debugging help needed"
        filter_obj = ConversationFilter(self.project_root, user_prompt)

        # Test conversation that matches keywords
        matching_conv = {
            "content": "I'm having trouble with Python debugging in my Django application",
            "title": "Python Debug Issue",
        }
        self.assertTrue(filter_obj._conversation_matches_keywords(matching_conv))

        # Test conversation that doesn't match - use very specific non-matching content
        non_matching_conv = {
            "content": "Recipe for chocolate cake with vanilla frosting",
            "title": "Baking Tutorial",
        }
        self.assertFalse(filter_obj._conversation_matches_keywords(non_matching_conv))

    def test_conversation_matches_keywords_empty_content(self):
        """Test keyword matching with empty conversation content."""
        filter_obj = ConversationFilter(self.project_root)

        empty_conv = {"content": "", "title": ""}
        self.assertFalse(filter_obj._conversation_matches_keywords(empty_conv))

    def test_conversation_matches_keywords_no_keywords(self):
        """Test behavior when no keywords are available."""
        filter_obj = ConversationFilter(self.project_root)
        filter_obj.all_keywords = []

        conv = {"content": "Some content"}
        self.assertTrue(filter_obj._conversation_matches_keywords(conv))

    def test_extract_prompt_keywords_disabled(self):
        """Test keyword extraction when disabled."""
        with patch(
            "src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED",
            False,
        ):
            filter_obj = ConversationFilter(self.project_root, "test prompt")
            self.assertEqual(filter_obj.prompt_keywords, [])

    def test_extract_prompt_keywords_error_handling(self):
        """Test keyword extraction error handling."""
        filter_obj = ConversationFilter(self.project_root)

        # Test with None prompt
        filter_obj.user_prompt = None
        keywords = filter_obj._extract_prompt_keywords()
        self.assertEqual(keywords, [])

    @patch("src.core.conversation_filtering.CONVERSATION_FILTERING_ENABLED", True)
    @patch("src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED", True)
    def test_simple_filtering(self):
        """Test simple keyword-based filtering."""
        filter_obj = ConversationFilter(self.project_root, "Python debugging")

        # Create test conversations
        conversations = [
            {
                "id": "conv1",
                "content": "Python debugging help needed",
                "title": "Debug Issue",
            },
            {
                "id": "conv2",
                "content": "JavaScript React component",
                "title": "React Help",
            },
            {
                "id": "conv3",
                "content": "Python Django authentication",
                "title": "Auth Issue",
            },
            {
                "id": "conv4",
                "content": "How to make coffee",
                "title": "Coffee Tutorial",
            },
        ]

        filtered = filter_obj.apply_conversation_filtering(conversations, 10)

        # Should include conversations that match "Python" or "debugging"
        filtered_ids = [conv["id"] for conv in filtered]
        self.assertIn("conv1", filtered_ids)  # Has both Python and debugging
        self.assertIn("conv3", filtered_ids)  # Has Python
        self.assertNotIn("conv4", filtered_ids)  # No matching keywords

    def test_filtering_summary(self):
        """Test filtering summary generation."""
        filter_obj = ConversationFilter(self.project_root, "test prompt")
        summary = filter_obj.get_filtering_summary()

        self.assertIn("conversation_filtering_enabled", summary)
        self.assertIn("keyword_match_enabled", summary)
        self.assertIn("base_keywords_count", summary)
        self.assertIn("prompt_keywords_count", summary)
        self.assertIn("total_keywords_count", summary)
        self.assertIn("sample_keywords", summary)


class TestConversationFilteringFunctions(unittest.TestCase):
    """Test the standalone filtering functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir(parents=True)

    def teardown_method(self, method):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_conversation_filter(self):
        """Test factory function for creating conversation filter."""
        filter_obj = create_conversation_filter(self.project_root)
        self.assertIsInstance(filter_obj, ConversationFilter)

    @patch("src.core.conversation_filtering.CONVERSATION_FILTERING_ENABLED", True)
    @patch("src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED", True)
    def test_apply_conversation_filtering(self):
        """Test the main filtering function."""
        conversations = [
            {"id": "conv1", "content": "Python debugging help"},
            {"id": "conv2", "content": "JavaScript tutorial"},
            {"id": "conv3", "content": "Python Django guide"},
        ]

        filtered_conversations, metadata = apply_conversation_filtering(
            conversations, self.project_root, 10, "Python"
        )

        self.assertIsInstance(filtered_conversations, list)
        self.assertIsInstance(metadata, dict)
        self.assertIn("mode", metadata)
        self.assertEqual(metadata["mode"], "keyword_filtering")
        self.assertIn("original_count", metadata)
        self.assertIn("filtered_count", metadata)

    @patch("src.core.conversation_filtering.CONVERSATION_FILTERING_ENABLED", False)
    def test_filtering_disabled(self):
        """Test behavior when conversation filtering is disabled."""
        conversations = [
            {"id": "conv1", "content": "Python debugging help"},
            {"id": "conv2", "content": "JavaScript tutorial"},
            {"id": "conv3", "content": "Python Django guide"},
        ]

        filtered_conversations, metadata = apply_conversation_filtering(
            conversations, self.project_root, 2
        )

        self.assertEqual(len(filtered_conversations), 2)
        self.assertEqual(metadata["mode"], "simple_limit")

    @patch("src.core.conversation_filtering.CONVERSATION_FILTERING_ENABLED", True)
    @patch("src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED", True)
    def test_filtering_with_user_prompt(self):
        """Test filtering with user prompt for keyword extraction."""
        conversations = [
            {"id": "conv1", "content": "Python debugging help"},
            {"id": "conv2", "content": "React component issue"},
            {"id": "conv3", "content": "General discussion"},
        ]

        user_prompt = "I need help with Python debugging"

        filtered_conversations, metadata = apply_conversation_filtering(
            conversations, self.project_root, 10, user_prompt
        )

        self.assertIn("prompt_keywords_count", metadata)
        self.assertGreater(metadata["prompt_keywords_count"], 0)

    def test_filtering_with_empty_conversations(self):
        """Test filtering with empty conversation list."""
        conversations = []

        filtered_conversations, metadata = apply_conversation_filtering(
            conversations, self.project_root, 10
        )

        self.assertEqual(len(filtered_conversations), 0)
        self.assertEqual(metadata["original_count"], 0)
        self.assertEqual(metadata["filtered_count"], 0)

    @patch(
        "src.core.conversation_filtering.CONVERSATION_KEYWORD_MATCH_ENABLED",
        False,
    )
    def test_keyword_matching_disabled(self):
        """Test behavior when keyword matching is disabled."""
        conversations = [
            {"id": "conv1", "content": "Python debugging help"},
            {"id": "conv2", "content": "JavaScript tutorial"},
        ]

        filtered_conversations, metadata = apply_conversation_filtering(
            conversations, self.project_root, 1
        )

        # Should fall back to simple limit
        self.assertEqual(len(filtered_conversations), 1)

    def test_merge_keywords_no_prompt(self):
        """Test keyword merging when no prompt keywords exist."""
        filter_obj = ConversationFilter(self.project_root)
        filter_obj.prompt_keywords = []

        merged = filter_obj._merge_keywords()
        self.assertEqual(merged, filter_obj.base_keywords)

    def test_merge_keywords_with_duplicates(self):
        """Test keyword merging with duplicate keywords."""
        filter_obj = ConversationFilter(self.project_root)
        filter_obj.base_keywords = ["python", "django", "test"]
        filter_obj.prompt_keywords = [
            "python",
            "flask",
            "test",
        ]  # Some duplicates

        merged = filter_obj._merge_keywords()

        # Should have no duplicates and preserve order (prompt first)
        self.assertEqual(merged, ["python", "flask", "test", "django"])

    def test_conversation_filtering_with_limit(self):
        """Test conversation filtering respects the limit."""
        filter_obj = ConversationFilter(self.project_root, "Python")

        # Create many matching conversations
        conversations = [
            {"id": f"conv{i}", "content": f"Python help {i}"} for i in range(10)
        ]

        filtered = filter_obj.apply_conversation_filtering(conversations, 5)

        # Should respect the limit
        self.assertEqual(len(filtered), 5)
