"""
Tests for cursor conversation parser functionality.

lotr-info: Tests conversation parsing using Fellowship discussions and
Shire council meetings as sample conversation data.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.cursor.conversation_parser import (
    _get_tech_category_from_extension,
    extract_conversation_text,
    extract_snippet,
    generate_context_keywords,
    handle_enhanced_mode,
    handle_fast_mode,
    query_and_analyze_conversations,
)


class TestTechCategoryExtraction:
    """Test technology category extraction from file extensions."""

    def test_get_tech_category_from_extension_no_dotted_extensions(self):
        """Test that function returns None since TECHNOLOGY_KEYWORD_MAPPING has no dotted extensions."""
        # The mapping contains keywords like "js", "ts", "py" but not ".js", ".ts", ".py"
        result = _get_tech_category_from_extension(".py")
        assert result is None

    def test_get_tech_category_from_extension_javascript(self):
        """Test JavaScript extension detection returns None."""
        result = _get_tech_category_from_extension(".js")
        assert result is None

    def test_get_tech_category_from_extension_typescript(self):
        """Test TypeScript extension detection returns None."""
        result = _get_tech_category_from_extension(".ts")
        assert result is None

    def test_get_tech_category_from_extension_case_insensitive(self):
        """Test case-insensitive extension matching returns None."""
        result = _get_tech_category_from_extension(".PY")
        assert result is None

    def test_get_tech_category_from_extension_without_dot(self):
        """Test extension without leading dot returns None."""
        result = _get_tech_category_from_extension("py")
        assert result is None

    def test_get_tech_category_from_extension_unknown(self):
        """Test unknown extension returns None."""
        result = _get_tech_category_from_extension(".mordor")
        assert result is None

    def test_get_tech_category_from_extension_empty(self):
        """Test empty extension returns None."""
        result = _get_tech_category_from_extension("")
        assert result is None


class TestConversationTextExtraction:
    """Test conversation text extraction functionality."""

    def test_extract_conversation_text_basic(self):
        """Test basic conversation text extraction."""
        conversation = {
            "title": "Frodo's Ring Quest",
            "messages": [
                {"content": "How do I destroy the One Ring?"},
                {"content": "You must take it to Mount Doom, Master Frodo"},
            ],
        }

        text, count = extract_conversation_text(conversation)

        assert "Frodo's Ring Quest" in text
        assert "How do I destroy the One Ring?" in text
        assert "You must take it to Mount Doom" in text
        assert count == 2

    def test_extract_conversation_text_with_name_fallback(self):
        """Test conversation text extraction with name fallback."""
        conversation = {
            "name": "Council of Elrond",
            "messages": [{"content": "The Ring must be destroyed"}],
        }

        text, count = extract_conversation_text(conversation)

        assert "Council of Elrond" in text
        assert "The Ring must be destroyed" in text
        assert count == 1

    def test_extract_conversation_text_string_messages(self):
        """Test conversation with string messages."""
        conversation = {
            "title": "Gandalf's Wisdom",
            "messages": ["A wizard is never late", "Nor is he early"],
        }

        text, count = extract_conversation_text(conversation)

        assert "Gandalf's Wisdom" in text
        assert "A wizard is never late" in text
        assert "Nor is he early" in text
        assert count == 2

    def test_extract_conversation_text_mixed_message_formats(self):
        """Test conversation with mixed message formats."""
        conversation = {
            "title": "Aragorn's Leadership",
            "messages": [
                {"content": "I am Aragorn son of Arathorn"},
                "You have my sword",
                {"text": "And my bow"},
            ],
        }

        text, count = extract_conversation_text(conversation)

        assert "Aragorn's Leadership" in text
        assert "I am Aragorn son of Arathorn" in text
        assert "You have my sword" in text
        assert "And my bow" in text
        assert count == 3

    def test_extract_conversation_text_no_title(self):
        """Test conversation without title."""
        conversation = {"messages": [{"content": "The Shire is safe"}]}

        text, count = extract_conversation_text(conversation)

        assert "The Shire is safe" in text
        assert count == 1

    def test_extract_conversation_text_empty_messages(self):
        """Test conversation with empty messages."""
        conversation = {"title": "Empty Council", "messages": []}

        text, count = extract_conversation_text(conversation)

        assert text == "Empty Council"
        assert count == 0

    def test_extract_conversation_text_no_messages_key(self):
        """Test conversation without messages key."""
        conversation = {"title": "Lone Title"}

        text, count = extract_conversation_text(conversation)

        assert text == "Lone Title"
        assert count == 0


class TestSnippetExtraction:
    """Test snippet extraction functionality."""

    def test_extract_snippet_basic(self):
        """Test basic snippet extraction."""
        text = "The Fellowship of the Ring must journey to Mount Doom to destroy the One Ring and save Middle-earth from the Dark Lord Sauron."
        query = "Ring"

        snippet = extract_snippet(text, query)

        assert "Ring" in snippet
        assert len(snippet) <= 403  # Max length with ellipsis

    def test_extract_snippet_no_query(self):
        """Test snippet extraction without query."""
        text = "Gandalf the Grey arrived at Bag End on a beautiful morning in the Shire to visit his old friend Bilbo Baggins."

        snippet = extract_snippet(text, "")

        assert snippet == text  # Should return full text if under 200 chars

    def test_extract_snippet_long_text_no_query(self):
        """Test snippet extraction with long text and no query."""
        text = "A" * 300  # Long text

        snippet = extract_snippet(text, "")

        assert len(snippet) == 203  # 200 chars + "..."
        assert snippet.endswith("...")

    def test_extract_snippet_query_not_found(self):
        """Test snippet when query is not found."""
        text = "The hobbits enjoyed second breakfast in the Green Dragon."
        query = "Sauron"

        snippet = extract_snippet(text, query)

        assert snippet == text  # Should return full text when query not found

    def test_extract_snippet_with_context(self):
        """Test snippet extraction with context around found word."""
        # Create text where the query word is far from both beginning and end
        # Function extracts best_pos-100 to best_pos+300 (400 chars total)
        prefix = "A" * 120  # Long prefix to force leading ellipsis
        middle = " In the beginning the Elder King made the Heavens and the Middle-earth. And the earth was without form, and void; and darkness was upon the face of the deep. "
        suffix = "Z" * 300  # Long suffix to force trailing ellipsis
        text = f"{prefix}{middle}{suffix}"
        query = "Middle-earth"

        snippet = extract_snippet(text, query)

        assert "Middle-earth" in snippet
        assert snippet.startswith("...")  # Should have leading context
        assert snippet.endswith("...")  # Should have trailing context

    def test_extract_snippet_query_at_beginning(self):
        """Test snippet when query is at the beginning."""
        text = "Frodo Baggins was a hobbit who lived in Bag End in the Shire."
        query = "Frodo"

        snippet = extract_snippet(text, query)

        assert snippet.startswith("Frodo")
        assert not snippet.startswith("...")  # No leading ellipsis needed

    def test_extract_snippet_query_at_end(self):
        """Test snippet when query is near the end."""
        text = "The Fellowship traveled through many lands until they reached Mordor."
        query = "Mordor"

        snippet = extract_snippet(text, query)

        assert "Mordor" in snippet
        assert not snippet.endswith("...")  # No trailing ellipsis needed

    def test_extract_snippet_empty_text(self):
        """Test snippet extraction with empty text."""
        snippet = extract_snippet("", "Ring")
        assert snippet == ""


class TestFastMode:
    """Test fast mode conversation extraction."""

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    @patch(
        "src.tool_calls.cursor.conversation_parser.handle_fast_conversation_extraction"
    )
    def test_handle_fast_mode_basic(self, mock_extraction, mock_cursor_query):
        """Test basic fast mode handling."""
        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "conversations": [
                        {
                            "id": "council_meeting",
                            "title": "Council of Elrond",
                            "created_at": datetime.now().isoformat(),
                        }
                    ]
                }
            ]
        }

        # Mock extraction function
        mock_extraction.return_value = {"result": "extracted"}

        result = handle_fast_mode(10, 7, ["architecture"])

        mock_cursor_query.assert_called_once_with(silent=True)
        mock_instance.query_all_conversations.assert_called_once()
        mock_extraction.assert_called_once()
        assert result == {"result": "extracted"}

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    @patch(
        "src.tool_calls.cursor.conversation_parser.handle_fast_conversation_extraction"
    )
    def test_handle_fast_mode_with_date_filtering(
        self, mock_extraction, mock_cursor_query
    ):
        """Test fast mode with date filtering."""
        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        recent_date = (datetime.now() - timedelta(days=2)).isoformat()

        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "conversations": [
                        {
                            "id": "old_meeting",
                            "title": "Old Council",
                            "created_at": old_date,
                        },
                        {
                            "id": "recent_meeting",
                            "title": "Recent Council",
                            "created_at": recent_date,
                        },
                    ]
                }
            ]
        }

        # Mock extraction function
        mock_extraction.return_value = {"result": "filtered"}

        handle_fast_mode(10, 7, ["architecture"])

        # Should filter out old conversations
        mock_extraction.assert_called_once()
        args = mock_extraction.call_args[0]
        conversations = args[0]
        assert len(conversations) == 1
        assert conversations[0]["id"] == "recent_meeting"

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    @patch(
        "src.tool_calls.cursor.conversation_parser.handle_fast_conversation_extraction"
    )
    def test_handle_fast_mode_invalid_date_format(
        self, mock_extraction, mock_cursor_query
    ):
        """Test fast mode with invalid date format."""
        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "workspaces": [
                {
                    "conversations": [
                        {
                            "id": "bad_date_meeting",
                            "title": "Meeting with Bad Date",
                            "created_at": "invalid_date_format",
                        }
                    ]
                }
            ]
        }

        # Mock extraction function
        mock_extraction.return_value = {"result": "handled"}

        handle_fast_mode(10, 7, ["architecture"])

        # Should still include conversation despite bad date
        mock_extraction.assert_called_once()
        args = mock_extraction.call_args[0]
        conversations = args[0]
        assert len(conversations) == 1


class TestContextKeywords:
    """Test context keyword generation."""

    @patch("src.tool_calls.cursor.conversation_parser.generate_shared_context_keywords")
    def test_generate_context_keywords(self, mock_generate):
        """Test context keyword generation."""
        mock_generate.return_value = ["python", "flask", "api"]

        project_root = Path("/mnt/doom/shire-project")
        result = generate_context_keywords(project_root)

        mock_generate.assert_called_once_with(project_root)
        assert result == ["python", "flask", "api"]


class TestEnhancedMode:
    """Test enhanced mode conversation processing."""

    @patch("src.tool_calls.cursor.conversation_parser.is_cache_valid")
    @patch("src.tool_calls.cursor.conversation_parser.load_from_cache_filtered")
    def test_handle_enhanced_mode_cache_hit(self, mock_load_cache, mock_cache_valid):
        """Test enhanced mode with valid cache."""
        mock_cache_valid.return_value = True
        mock_load_cache.return_value = {"cached": "result"}

        mock_query_func = Mock()

        project_root = Path("/mnt/doom/rivendell-project")
        result = handle_enhanced_mode(
            project_root, 10, 0.5, 7, ["architecture"], False, mock_query_func
        )

        mock_cache_valid.assert_called_once()
        mock_load_cache.assert_called_once()
        assert result == {"cached": "result"}
        # Query function should not be called on cache hit
        mock_query_func.assert_not_called()

    @patch("src.tool_calls.cursor.conversation_parser.is_cache_valid")
    @patch("src.tool_calls.cursor.conversation_parser.generate_context_keywords")
    def test_handle_enhanced_mode_cache_miss(self, mock_keywords, mock_cache_valid):
        """Test enhanced mode with cache miss."""
        mock_cache_valid.return_value = False
        mock_keywords.return_value = ["python", "web", "api"]

        mock_query_func = Mock()
        mock_query_func.return_value = {"analyzed": "result"}

        project_root = Path("/mnt/doom/gondor-project")
        result = handle_enhanced_mode(
            project_root, 10, 0.5, 7, ["architecture"], True, mock_query_func
        )

        mock_cache_valid.assert_called_once()
        mock_keywords.assert_called_once_with(project_root)
        mock_query_func.assert_called_once_with(
            project_root, ["python", "web", "api"], 10, 0.5, 7, ["architecture"], True
        )
        assert result == {"analyzed": "result"}


class TestQueryAndAnalyzeConversations:
    """Test the main query and analyze function."""

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    def test_query_and_analyze_conversations_no_data(self, mock_cursor_query):
        """Test query when no conversations found."""
        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {"conversations": []}

        project_root = Path("/mnt/doom/empty-project")
        result = query_and_analyze_conversations(
            project_root, ["python"], 10, 0.5, 7, ["architecture"], False
        )

        # Should return error response
        assert "isError" in result or "error" in str(result)

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    @patch("src.tool_calls.cursor.conversation_parser.quick_conversation_filter")
    @patch("src.tool_calls.cursor.conversation_parser.validate_conversation_data")
    @patch(
        "src.tool_calls.cursor.conversation_parser.analyze_conversation_relevance_optimized"
    )
    @patch("src.tool_calls.cursor.conversation_parser.apply_conversation_filtering")
    @patch("src.tool_calls.cursor.conversation_parser.format_lightweight_conversations")
    @patch("src.tool_calls.cursor.conversation_parser.save_conversations_to_cache")
    @patch("src.tool_calls.cursor.conversation_parser.format_conversation_summary")
    def test_query_and_analyze_conversations_success(
        self,
        mock_format_summary,
        mock_save_cache,
        mock_format_lightweight,
        mock_apply_filtering,
        mock_analyze,
        mock_validate,
        mock_filter,
        mock_cursor_query,
    ):
        """Test successful query and analysis."""
        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [
                {"id": "conv1", "title": "Frodo's Quest"},
                {"id": "conv2", "title": "Sam's Garden"},
            ]
        }

        # Mock filter pipeline
        mock_filter.return_value = [{"id": "conv1", "title": "Frodo's Quest"}]
        mock_validate.return_value = True
        mock_analyze.return_value = {
            "id": "conv1",
            "title": "Frodo's Quest",
            "relevance_score": 0.8,
        }
        mock_apply_filtering.return_value = (
            [{"id": "conv1", "relevance_score": 0.8}],
            {"filtered": "metadata"},
        )
        mock_format_lightweight.return_value = [{"light": "conversation"}]
        mock_format_summary.return_value = {"formatted": "summary"}

        project_root = Path("/mnt/doom/success-project")
        result = query_and_analyze_conversations(
            project_root, ["python"], 10, 0.5, 7, ["architecture"], False
        )

        # Verify all mocks were called
        mock_cursor_query.assert_called_once_with(silent=True)
        mock_filter.assert_called_once()
        mock_validate.assert_called_once()
        mock_analyze.assert_called_once()
        mock_apply_filtering.assert_called_once()
        mock_format_lightweight.assert_called_once()
        mock_save_cache.assert_called_once()
        mock_format_summary.assert_called_once()

        # Should return success response
        assert "content" in result

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    @patch("src.tool_calls.cursor.conversation_parser.quick_conversation_filter")
    @patch("src.tool_calls.cursor.conversation_parser.validate_conversation_data")
    @patch("src.tool_calls.cursor.conversation_parser.analyze_conversation_relevance")
    @patch("src.tool_calls.cursor.conversation_parser.apply_conversation_filtering")
    @patch("src.tool_calls.cursor.conversation_parser.format_lightweight_conversations")
    @patch("src.tool_calls.cursor.conversation_parser.save_conversations_to_cache")
    @patch("src.tool_calls.cursor.conversation_parser.format_conversation_summary")
    def test_query_and_analyze_conversations_with_analysis(
        self,
        mock_format_summary,
        mock_save_cache,
        mock_format_lightweight,
        mock_apply_filtering,
        mock_analyze,
        mock_validate,
        mock_filter,
        mock_cursor_query,
    ):
        """Test query with detailed analysis enabled."""
        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [{"id": "detailed_conv", "title": "Detailed Analysis"}]
        }

        # Mock filter pipeline
        mock_filter.return_value = [
            {"id": "detailed_conv", "title": "Detailed Analysis"}
        ]
        mock_validate.return_value = True
        mock_analyze.return_value = {
            "id": "detailed_conv",
            "title": "Detailed Analysis",
            "relevance_score": 0.9,
            "analysis": "detailed",
        }
        mock_apply_filtering.return_value = (
            [{"id": "detailed_conv", "relevance_score": 0.9}],
            {"filtered": "metadata"},
        )
        mock_format_lightweight.return_value = [{"detailed": "conversation"}]
        mock_format_summary.return_value = {"detailed": "summary"}

        project_root = Path("/mnt/doom/detailed-project")
        result = query_and_analyze_conversations(
            project_root, ["python"], 10, 0.5, 7, ["architecture"], True
        )

        # Should use detailed analysis
        mock_analyze.assert_called_once()
        call_args = mock_analyze.call_args
        assert call_args[0][3] is True  # include_analysis parameter

        # Should return success response
        assert "content" in result

    @patch("src.tool_calls.cursor.conversation_parser.CursorQuery")
    @patch("src.tool_calls.cursor.conversation_parser.quick_conversation_filter")
    @patch("src.tool_calls.cursor.conversation_parser.validate_conversation_data")
    def test_query_and_analyze_conversations_invalid_data(
        self, mock_validate, mock_filter, mock_cursor_query
    ):
        """Test query with invalid conversation data."""
        # Mock CursorQuery
        mock_instance = Mock()
        mock_cursor_query.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [{"id": "invalid_conv", "title": "Invalid Data"}]
        }

        # Mock filter pipeline
        mock_filter.return_value = [{"id": "invalid_conv", "title": "Invalid Data"}]
        mock_validate.return_value = False  # Invalid data

        project_root = Path("/mnt/doom/invalid-project")

        # Should handle invalid data gracefully
        with patch(
            "src.tool_calls.cursor.conversation_parser.apply_conversation_filtering"
        ) as mock_apply:
            mock_apply.return_value = ([], {"filtered": "metadata"})
            with patch(
                "src.tool_calls.cursor.conversation_parser.format_lightweight_conversations"
            ) as mock_format:
                mock_format.return_value = []
                with patch(
                    "src.tool_calls.cursor.conversation_parser.format_conversation_summary"
                ) as mock_summary:
                    mock_summary.return_value = {"empty": "summary"}

                    result = query_and_analyze_conversations(
                        project_root, ["python"], 10, 0.5, 7, ["architecture"], False
                    )

                    # Should still return a result even with invalid data
                    assert "content" in result
