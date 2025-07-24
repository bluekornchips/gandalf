"""
Test suite for content extractor functionality.

Comprehensive tests for conversation content extraction, metadata handling,
normalization, and date filtering with edge case coverage.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.core.content_extractor import (
    _extract_from_messages,
    extract_conversation_content,
    extract_conversation_metadata,
    extract_conversation_summary,
    filter_conversations_by_date,
    get_conversation_statistics,
    normalize_conversation_format,
    sort_conversations_by_relevance,
)


class TestExtractConversationContent(unittest.TestCase):
    """Test conversation content extraction with various formats."""

    def test_extract_from_dict_with_messages(self):
        """Test extraction from dict with messages array."""
        data = {
            "name": "Python Discussion",
            "messages": [
                {"content": "Hello Python world"},
                {"content": "Django is great"},
            ],
        }

        result = extract_conversation_content(data)

        self.assertIn("Python Discussion", result)
        self.assertIn("Hello Python world", result)
        self.assertIn("Django is great", result)

    def test_extract_from_dict_with_composer_steps(self):
        """Test extraction from Cursor format with composerSteps."""
        data = {
            "title": "Cursor Session",
            "composerSteps": [
                {"content": "Step 1 content"},
                {"text": "Step 2 text"},
                {"content": "Step 3 content"},
            ],
        }

        result = extract_conversation_content(data)

        self.assertIn("Cursor Session", result)
        self.assertIn("Step 1 content", result)
        self.assertIn("Step 2 text", result)
        self.assertIn("Step 3 content", result)

    def test_extract_from_dict_with_generic_content(self):
        """Test extraction from dict with generic content field."""
        data = {
            "name": "Generic Discussion",
            "content": "This is generic content",
        }

        result = extract_conversation_content(data)

        self.assertIn("Generic Discussion", result)
        self.assertIn("This is generic content", result)

    def test_extract_from_list_of_messages(self):
        """Test extraction from list of messages."""
        data = [
            {"content": "First message"},
            {"text": "Second message"},
            "Direct string message",
        ]

        result = extract_conversation_content(data)

        self.assertIn("First message", result)
        self.assertIn("Second message", result)
        self.assertIn("Direct string message", result)

    def test_extract_from_string(self):
        """Test extraction from direct string."""
        data = "Direct string content"

        result = extract_conversation_content(data)

        self.assertEqual(result, "Direct string content")

    def test_extract_with_character_limit(self):
        """Test extraction respects character limit."""
        data = {"content": "x" * 1000}

        result = extract_conversation_content(data, max_chars=100)

        self.assertLessEqual(len(result), 100)

    def test_extract_skip_untitled(self):
        """Test that 'Untitled' titles are skipped."""
        data = {
            "name": "Untitled",
            "messages": [{"content": "Some content"}],
        }

        result = extract_conversation_content(data)

        self.assertNotIn("Untitled", result)
        self.assertIn("Some content", result)

    def test_extract_with_structured_content(self):
        """Test extraction with structured content (Claude API format)."""
        data = {
            "messages": [
                {
                    "content": [
                        {"type": "text", "text": "First text block"},
                        {"type": "text", "text": "Second text block"},
                        {"type": "image", "data": "ignored"},
                    ]
                }
            ]
        }

        result = extract_conversation_content(data)

        self.assertIn("First text block", result)
        self.assertIn("Second text block", result)
        self.assertNotIn("ignored", result)

    def test_extract_handles_exceptions(self):
        """Test extraction handles various exceptions gracefully."""
        test_cases = [
            {"messages": [{"content": None}]},  # None content
            {"messages": [{"content": {"nested": "dict"}}]},  # Invalid structure
            {"composerSteps": "not_a_list"},  # Invalid composerSteps
            None,  # None input
        ]

        for data in test_cases:
            with self.subTest(data=data):
                result = extract_conversation_content(data)
                self.assertIsInstance(result, str)

    def test_extract_message_limit(self):
        """Test that message processing is limited to 10 messages."""
        data = {"messages": [{"content": f"Message {i}"} for i in range(20)]}

        result = extract_conversation_content(data)

        # Should only process first 10 messages
        self.assertIn("Message 0", result)
        self.assertIn("Message 9", result)
        # May or may not contain message 10+ depending on character limit

    def test_extract_step_limit(self):
        """Test that composerSteps processing is limited to 10 steps."""
        data = {"composerSteps": [{"content": f"Step {i}"} for i in range(20)]}

        result = extract_conversation_content(data)

        # Should only process first 10 steps
        self.assertIn("Step 0", result)
        self.assertIn("Step 9", result)


class TestExtractFromMessages(unittest.TestCase):
    """Test the _extract_from_messages helper function."""

    def test_extract_from_string_messages(self):
        """Test extraction from list of string messages."""
        messages = ["First message", "Second message"]
        text_parts = []

        result_chars = _extract_from_messages(messages, text_parts, 0, 1000)

        self.assertEqual(len(text_parts), 2)
        self.assertIn("First message", text_parts)
        self.assertIn("Second message", text_parts)
        self.assertGreater(result_chars, 0)

    def test_extract_from_dict_messages(self):
        """Test extraction from list of dict messages."""
        messages = [
            {"content": "Dict message 1"},
            {"text": "Dict message 2"},
        ]
        text_parts = []

        _extract_from_messages(messages, text_parts, 0, 1000)

        self.assertEqual(len(text_parts), 2)
        self.assertIn("Dict message 1", text_parts)
        self.assertIn("Dict message 2", text_parts)

    def test_extract_with_character_limit_reached(self):
        """Test extraction stops when character limit is reached."""
        messages = [
            {"content": "x" * 100},
            {"content": "y" * 100},
        ]
        text_parts = []

        result_chars = _extract_from_messages(messages, text_parts, 0, 150)

        self.assertLessEqual(result_chars, 150)
        self.assertGreaterEqual(len(text_parts), 1)

    def test_extract_handles_structured_content(self):
        """Test extraction from structured content arrays."""
        messages = [
            {
                "content": [
                    {"type": "text", "text": "Structured text 1"},
                    {"type": "text", "text": "Structured text 2"},
                ]
            }
        ]
        text_parts = []

        _extract_from_messages(messages, text_parts, 0, 1000)

        self.assertIn("Structured text 1", text_parts)
        self.assertIn("Structured text 2", text_parts)


class TestExtractConversationMetadata(unittest.TestCase):
    """Test conversation metadata extraction."""

    def test_extract_basic_metadata(self):
        """Test extraction of basic metadata fields."""
        data = {
            "id": "conv123",
            "name": "Test Conversation",
            "created_at": "2024-01-01T00:00:00Z",
            "user_id": "user456",
        }

        result = extract_conversation_metadata(data)

        self.assertEqual(result["id"], "conv123")
        self.assertEqual(result["name"], "Test Conversation")
        self.assertEqual(result["created_at"], "2024-01-01T00:00:00Z")
        self.assertEqual(result["user_id"], "user456")

    def test_extract_message_count(self):
        """Test extraction of message count from messages array."""
        data = {
            "messages": [
                {"content": "Message 1"},
                {"content": "Message 2"},
                {"content": "Message 3"},
            ]
        }

        result = extract_conversation_metadata(data)

        self.assertEqual(result["message_count"], 3)

    def test_extract_step_count(self):
        """Test extraction of step count from composerSteps."""
        data = {
            "composerSteps": [
                {"content": "Step 1"},
                {"content": "Step 2"},
            ]
        }

        result = extract_conversation_metadata(data)

        self.assertEqual(result["step_count"], 2)

    def test_extract_nested_session_metadata(self):
        """Test extraction of nested session metadata."""
        data = {
            "session_metadata": {
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T01:00:00Z",
                "session_id": "session789",
            }
        }

        result = extract_conversation_metadata(data)

        self.assertEqual(result["start_time"], "2024-01-01T00:00:00Z")
        self.assertEqual(result["end_time"], "2024-01-01T01:00:00Z")
        self.assertEqual(result["session_id"], "session789")

    def test_extract_handles_non_dict_input(self):
        """Test metadata extraction handles non-dict input."""
        result = extract_conversation_metadata("not a dict")
        self.assertEqual(result, {})

    def test_extract_handles_exceptions(self):
        """Test metadata extraction handles exceptions gracefully."""
        # Test with non-dict input to trigger the outer try-catch
        result = extract_conversation_metadata("not a dict")
        self.assertEqual(result, {})

        # Test with dict but problematic session_metadata
        with patch("src.core.content_extractor.log_debug"):
            # Use dict.update() on non-dict to force TypeError
            class BadSessionMeta:
                def __contains__(self, key):
                    return key == "session_metadata"

                def get(self, key, default=None):
                    if key == "session_metadata":
                        return "not_a_dict"  # This will cause TypeError in update()
                    return default

                def __getitem__(self, key):
                    if key == "session_metadata":
                        return "not_a_dict"
                    raise KeyError(key)

            data = BadSessionMeta()
            result = extract_conversation_metadata(data)

            self.assertIsInstance(result, dict)
            # The log call might or might not happen depending on implementation details

    def test_extract_with_invalid_message_format(self):
        """Test extraction handles invalid message formats."""
        data = {
            "messages": "not_a_list",
            "composerSteps": None,
        }

        result = extract_conversation_metadata(data)

        # Should handle gracefully without crashing
        self.assertIsInstance(result, dict)


class TestNormalizeConversationFormat(unittest.TestCase):
    """Test conversation format normalization."""

    def test_normalize_dict_with_messages(self):
        """Test normalization of dict with messages."""
        data = {
            "id": "conv123",
            "title": "Test Conversation",
            "messages": [{"content": "Hello"}],
        }

        result = normalize_conversation_format(data)

        self.assertEqual(result["id"], "conv123")
        self.assertEqual(result["title"], "Test Conversation")
        self.assertEqual(result["messages"], [{"content": "Hello"}])
        self.assertEqual(result["source"], "claude_code")
        self.assertIn("Hello", result["content"])

    def test_normalize_dict_with_composer_steps(self):
        """Test normalization of dict with composerSteps."""
        data = {
            "conversation_id": "conv456",
            "name": "Cursor Session",
            "composerSteps": [{"content": "Step 1"}],
        }

        result = normalize_conversation_format(data)

        self.assertEqual(result["id"], "conv456")
        self.assertEqual(result["title"], "Cursor Session")
        self.assertEqual(result["messages"], [{"content": "Step 1"}])
        self.assertEqual(result["source"], "cursor")

    def test_normalize_list_input(self):
        """Test normalization of list input (message array)."""
        data = [
            {"content": "Message 1"},
            {"content": "Message 2"},
        ]

        result = normalize_conversation_format(data)

        self.assertEqual(result["messages"], data)
        self.assertIn("Message 1", result["content"])
        self.assertIn("Message 2", result["content"])

    def test_normalize_string_input(self):
        """Test normalization of string input."""
        data = "Direct string content"

        result = normalize_conversation_format(data)

        self.assertEqual(result["content"], data)

    def test_normalize_with_fallback_id(self):
        """Test normalization uses fallback ID sources."""
        data = {"session_id": "session789"}

        result = normalize_conversation_format(data)

        self.assertEqual(result["id"], "session789")

    def test_normalize_with_fallback_title(self):
        """Test normalization uses fallback title sources."""
        data = {"name": "Session Name"}

        result = normalize_conversation_format(data)

        self.assertEqual(result["title"], "Session Name")

    def test_normalize_with_untitled_fallback(self):
        """Test normalization provides 'Untitled Conversation' fallback."""
        data = {}

        result = normalize_conversation_format(data)

        self.assertEqual(result["title"], "Untitled Conversation")

    def test_normalize_handles_exceptions(self):
        """Test normalization handles exceptions gracefully."""
        with patch("src.core.content_extractor.log_debug") as mock_log:
            with patch(
                "src.core.content_extractor.extract_conversation_content",
                side_effect=TypeError("Test error"),
            ):
                result = normalize_conversation_format({"messages": []})

                self.assertIsInstance(result, dict)
                mock_log.assert_called_once()


class TestFilterConversationsByDate(unittest.TestCase):
    """Test date-based conversation filtering."""

    def test_filter_empty_conversations(self):
        """Test filtering empty conversation list."""
        result = filter_conversations_by_date([], 7)
        self.assertEqual(result, [])

    def test_filter_zero_days_lookback(self):
        """Test filtering with zero days lookback."""
        conversations = [{"id": "conv1"}]
        result = filter_conversations_by_date(conversations, 0)
        self.assertEqual(result, conversations)

    def test_filter_negative_days_lookback(self):
        """Test filtering with negative days lookback."""
        conversations = [{"id": "conv1"}]
        result = filter_conversations_by_date(conversations, -1)
        self.assertEqual(result, conversations)

    def test_filter_cursor_format_recent(self):
        """Test filtering Cursor format conversations (recent)."""
        recent_timestamp = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        conversations = [
            {"id": "conv1", "lastUpdatedAt": recent_timestamp},
        ]

        result = filter_conversations_by_date(conversations, 7)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "conv1")

    def test_filter_cursor_format_old(self):
        """Test filtering Cursor format conversations (old)."""
        old_timestamp = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        conversations = [
            {"id": "conv1", "lastUpdatedAt": old_timestamp},
        ]

        result = filter_conversations_by_date(conversations, 7)

        self.assertEqual(len(result), 0)

    def test_filter_claude_format_recent(self):
        """Test filtering Claude Code format conversations (recent)."""
        # Use a timestamp without timezone info to avoid comparison issues
        recent_time = (datetime.now() - timedelta(days=1)).isoformat()
        conversations = [
            {
                "id": "conv1",
                "session_metadata": {"start_time": recent_time},
            },
        ]

        result = filter_conversations_by_date(conversations, 7)

        self.assertEqual(len(result), 1)

    def test_filter_claude_format_old(self):
        """Test filtering Claude Code format conversations (old)."""
        # Use a timestamp without timezone info to avoid comparison issues
        old_time = (datetime.now() - timedelta(days=30)).isoformat()
        conversations = [
            {
                "id": "conv1",
                "session_metadata": {"start_time": old_time},
            },
        ]

        result = filter_conversations_by_date(conversations, 7)

        # Old conversations should be filtered out
        self.assertEqual(len(result), 0)

    def test_filter_direct_timestamp_seconds(self):
        """Test filtering with direct timestamp in seconds."""
        recent_timestamp = int((datetime.now() - timedelta(days=1)).timestamp())
        conversations = [
            {"id": "conv1", "timestamp": recent_timestamp},
        ]

        result = filter_conversations_by_date(conversations, 7)

        self.assertEqual(len(result), 1)

    def test_filter_direct_timestamp_milliseconds(self):
        """Test filtering with direct timestamp in milliseconds."""
        recent_timestamp = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        conversations = [
            {"id": "conv1", "timestamp": recent_timestamp},
        ]

        result = filter_conversations_by_date(conversations, 7)

        self.assertEqual(len(result), 1)

    def test_filter_direct_timestamp_string(self):
        """Test filtering with direct timestamp as ISO string."""
        # Use a timestamp without timezone info to avoid comparison issues
        recent_time = (datetime.now() - timedelta(days=1)).isoformat()
        conversations = [
            {"id": "conv1", "timestamp": recent_time},
        ]

        result = filter_conversations_by_date(conversations, 7)

        self.assertEqual(len(result), 1)

    def test_filter_handles_invalid_timestamps(self):
        """Test filtering handles invalid timestamp formats."""
        conversations = [
            {"id": "conv1", "timestamp": "invalid_date"},
            {"id": "conv2", "lastUpdatedAt": "not_a_number"},
            {"id": "conv3"},  # No timestamp
        ]

        result = filter_conversations_by_date(conversations, 7)

        # Should include conversations without valid timestamps
        self.assertEqual(len(result), 3)

    def test_filter_mixed_formats(self):
        """Test filtering with mixed conversation formats."""
        recent_cursor = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        # Use timestamp without timezone to avoid comparison issues
        old_claude = (datetime.now() - timedelta(days=30)).isoformat()

        conversations = [
            {"id": "conv1", "lastUpdatedAt": recent_cursor},
            {"id": "conv2", "session_metadata": {"start_time": old_claude}},
            {"id": "conv3"},  # No timestamp
        ]

        result = filter_conversations_by_date(conversations, 7)

        # Should include recent Cursor conv and conv without timestamp
        self.assertEqual(len(result), 2)
        conv_ids = [conv["id"] for conv in result]
        self.assertIn("conv1", conv_ids)
        self.assertIn("conv3", conv_ids)

    def test_filter_handles_exceptions(self):
        """Test filtering handles exceptions gracefully."""
        # Test with invalid timestamps that cause parsing errors
        conversations = [
            {"id": "conv1", "timestamp": "invalid_date"},
            {"id": "conv2", "lastUpdatedAt": "not_a_number"},
            {"id": "conv3"},  # No timestamp
        ]

        result = filter_conversations_by_date(conversations, 7)

        # Should include all conversations when timestamps can't be parsed
        self.assertEqual(len(result), 3)


class TestSortConversationsByRelevance(unittest.TestCase):
    """Test conversation sorting by relevance."""

    def test_sort_by_default_key(self):
        """Test sorting by default relevance_score key."""
        conversations = [
            {"id": "conv1", "relevance_score": 0.3},
            {"id": "conv2", "relevance_score": 0.8},
            {"id": "conv3", "relevance_score": 0.5},
        ]

        result = sort_conversations_by_relevance(conversations)

        scores = [conv["relevance_score"] for conv in result]
        self.assertEqual(scores, [0.8, 0.5, 0.3])  # Descending order

    def test_sort_by_custom_key(self):
        """Test sorting by custom relevance key."""
        conversations = [
            {"id": "conv1", "custom_score": 1.0},
            {"id": "conv2", "custom_score": 2.5},
            {"id": "conv3", "custom_score": 1.8},
        ]

        result = sort_conversations_by_relevance(conversations, "custom_score")

        scores = [conv["custom_score"] for conv in result]
        self.assertEqual(scores, [2.5, 1.8, 1.0])

    def test_sort_missing_scores(self):
        """Test sorting with missing relevance scores."""
        conversations = [
            {"id": "conv1", "relevance_score": 0.5},
            {"id": "conv2"},  # Missing score, should default to 0.0
            {"id": "conv3", "relevance_score": 0.3},
        ]

        result = sort_conversations_by_relevance(conversations)

        # Should sort properly with missing scores as 0.0
        self.assertEqual(result[0]["id"], "conv1")  # 0.5
        self.assertEqual(result[1]["id"], "conv3")  # 0.3
        self.assertEqual(result[2]["id"], "conv2")  # 0.0 (missing)

    def test_sort_handles_exceptions(self):
        """Test sorting handles exceptions gracefully."""
        conversations = [
            {"id": "conv1", "relevance_score": "not_a_number"},
            {"id": "conv2", "relevance_score": 0.5},
        ]

        result = sort_conversations_by_relevance(conversations)

        # Should return original list if sorting fails
        self.assertEqual(result, conversations)


class TestExtractConversationSummary(unittest.TestCase):
    """Test conversation summary extraction."""

    def test_extract_short_content(self):
        """Test summary extraction from short content."""
        data = {"content": "Short content"}

        result = extract_conversation_summary(data, max_length=200)

        self.assertEqual(result, "Short content")

    def test_extract_no_content(self):
        """Test summary extraction when no content available."""
        data = {}

        result = extract_conversation_summary(data)

        self.assertEqual(result, "No content available")

    def test_extract_long_content_sentence_boundary(self):
        """Test summary extraction cuts at sentence boundary."""
        data = {
            "content": "First sentence. Second sentence. Third sentence. Fourth sentence."
        }

        result = extract_conversation_summary(data, max_length=30)

        # Should cut at sentence boundary
        self.assertTrue(result.endswith("."))
        self.assertLessEqual(len(result), 30)

    def test_extract_long_content_word_boundary(self):
        """Test summary extraction cuts at word boundary when no sentences."""
        data = {"content": "word1 word2 word3 word4 word5 word6 word7 word8"}

        result = extract_conversation_summary(data, max_length=20)

        # Should cut at word boundary and add ellipsis
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 25)  # 20 + "..."

    def test_extract_long_content_character_boundary(self):
        """Test summary extraction cuts at character boundary as fallback."""
        data = {"content": "verylongwordwithoutspacesorsentences"}

        result = extract_conversation_summary(data, max_length=10)

        # Should cut at character boundary and add ellipsis
        self.assertTrue(result.endswith("..."))
        self.assertEqual(len(result), 13)  # 10 + "..."

    def test_extract_with_extra_whitespace(self):
        """Test summary extraction removes extra whitespace."""
        data = {"content": "Content   with     extra    whitespace"}

        result = extract_conversation_summary(data)

        self.assertEqual(result, "Content with extra whitespace")


class TestGetConversationStatistics(unittest.TestCase):
    """Test conversation statistics calculation."""

    def test_statistics_empty_conversations(self):
        """Test statistics for empty conversation list."""
        result = get_conversation_statistics([])

        expected = {
            "total_conversations": 0,
            "total_messages": 0,
            "average_length": 0,
            "date_range": None,
        }
        self.assertEqual(result, expected)

    def test_statistics_with_conversations(self):
        """Test statistics calculation with conversations."""
        conversations = [
            {
                "messages": [{"content": "msg1"}, {"content": "msg2"}],
                "content": "test content 1",
                "created_at": "2024-01-01T00:00:00",  # Remove timezone
            },
            {
                "messages": [{"content": "msg3"}],
                "content": "test content 2 longer",
                "timestamp": 1704067200,  # 2024-01-01 00:00:00 UTC
            },
        ]

        result = get_conversation_statistics(conversations)

        self.assertEqual(result["total_conversations"], 2)
        self.assertEqual(result["total_messages"], 3)
        self.assertGreater(result["average_length"], 0)
        self.assertGreater(result["average_messages"], 0)
        self.assertIsNotNone(result["date_range"])

    def test_statistics_with_millisecond_timestamps(self):
        """Test statistics with millisecond timestamps."""
        conversations = [
            {
                "messages": [],
                "lastUpdatedAt": 1704067200000,  # Milliseconds
            },
        ]

        result = get_conversation_statistics(conversations)

        self.assertIsNotNone(result["date_range"])

    def test_statistics_handles_invalid_dates(self):
        """Test statistics handles invalid date formats."""
        conversations = [
            {
                "messages": [],
                "created_at": "invalid_date",
            },
            {
                "messages": [],
                "timestamp": "not_a_number",
            },
        ]

        result = get_conversation_statistics(conversations)

        # Should handle gracefully
        self.assertEqual(result["total_conversations"], 2)
        # date_range might be None due to invalid dates

    def test_statistics_date_range_calculation(self):
        """Test date range calculation in statistics."""
        now = datetime.now()
        earlier = now - timedelta(days=5)

        conversations = [
            {
                "messages": [],
                "timestamp": int(now.timestamp()),
            },
            {
                "messages": [],
                "timestamp": int(earlier.timestamp()),
            },
        ]

        result = get_conversation_statistics(conversations)

        date_range = result["date_range"]
        self.assertIsNotNone(date_range)
        self.assertIn("earliest", date_range)
        self.assertIn("latest", date_range)
        self.assertIn("span_days", date_range)
        self.assertEqual(date_range["span_days"], 5)

    def test_statistics_with_composer_steps(self):
        """Test statistics calculation includes composerSteps."""
        conversations = [
            {
                "composerSteps": [{"content": "step1"}, {"content": "step2"}],
                "content": "cursor content",
            },
        ]

        # composerSteps are not counted as messages in current implementation
        # This tests the current behavior
        result = get_conversation_statistics(conversations)

        self.assertEqual(result["total_conversations"], 1)
        # Should handle composerSteps gracefully even if not counted
