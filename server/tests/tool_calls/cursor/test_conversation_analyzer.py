"""
Tests for cursor conversation analysis functionality.

This module tests the conversation analysis and scoring utilities
used for relevance determination and ranking.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tool_calls.cursor.conversation_analyzer import (
    analyze_conversation_relevance,
    analyze_conversation_relevance_optimized,
    score_file_references,
    score_keyword_matches_optimized,
    score_pattern_matches,
    score_recency,
)
from src.tool_calls.cursor.conversation_utils import quick_conversation_filter


class TestConversationAnalyzer:
    """Test conversation analysis functionality."""

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "src").mkdir()
            (project_root / "src" / "main.py").write_text("print('hello')")
            (project_root / "README.md").write_text("# Test Project")
            yield project_root

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversation data for testing."""
        return [
            {
                "id": "conv_frodo_001",
                "title": "Quest planning discussion",
                "messages": [
                    {"content": "We need to implement a Python function for parsing"},
                    {"content": "The main.py file should handle the core logic"},
                ],
                "created_at": "2024-03-21T10:30:00Z",
            },
            {
                "id": "conv_gandalf_002",
                "title": "Magic system implementation",
                "messages": [
                    {"content": "Error handling is crucial for the wizard class"},
                    {"content": "Debug the spell casting mechanism"},
                ],
                "created_at": "2024-03-20T15:20:00Z",
            },
        ]

    @pytest.fixture
    def context_keywords(self):
        """Sample context keywords for testing."""
        return ["python", "function", "error", "debug", "test"]

    def test_analyze_conversation_relevance_basic(
        self, temp_project_root, sample_conversations, context_keywords
    ):
        """Test basic conversation relevance analysis."""
        conversation = sample_conversations[0]

        result = analyze_conversation_relevance(
            conversation, context_keywords, temp_project_root, include_analysis=True
        )

        # Verify structure
        assert "conversation" in result
        assert "relevance_score" in result
        assert "message_count" in result
        assert "conversation_type" in result
        assert "analysis" in result

        # Verify types
        assert isinstance(result["relevance_score"], int | float)
        assert isinstance(result["message_count"], int)
        assert isinstance(result["conversation_type"], str)

        # Verify analysis details
        analysis = result["analysis"]
        assert "keyword_score" in analysis
        assert "recency_score" in analysis
        assert "file_score" in analysis
        assert "pattern_score" in analysis
        assert "file_references" in analysis
        assert "detected_keywords" in analysis

    def test_analyze_conversation_relevance_optimized(
        self, temp_project_root, sample_conversations, context_keywords
    ):
        """Test optimized conversation relevance analysis."""
        conversation = sample_conversations[0]

        result = analyze_conversation_relevance_optimized(
            conversation, context_keywords, temp_project_root
        )

        # Verify structure (should have fewer fields than full analysis)
        assert "conversation" in result
        assert "relevance_score" in result
        assert "message_count" in result
        assert "analysis" in result

        # Analysis should be simplified
        analysis = result["analysis"]
        assert "keyword_score" in analysis
        assert "recency_score" in analysis
        assert "file_score" in analysis
        assert "pattern_score" in analysis
        assert "file_references" in analysis

        # Should limit file references for performance
        assert len(analysis["file_references"]) <= 5

    def test_score_keyword_matches_optimized(self, context_keywords):
        """Test optimized keyword matching scoring."""
        text = "We need to implement a Python function for error handling and debug testing"

        score = score_keyword_matches_optimized(text, context_keywords)

        # Should find matches for: python, function, error, debug, test
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should find some matches

    def test_score_keyword_matches_optimized_no_matches(self, context_keywords):
        """Test keyword matching with no matches."""
        text = "This text contains no relevant terms whatsoever"

        score = score_keyword_matches_optimized(text, context_keywords)
        assert score == 0.0

    def test_score_keyword_matches_optimized_empty_input(self):
        """Test keyword matching with empty inputs."""
        # Empty text
        score = score_keyword_matches_optimized("", ["keyword"])
        assert score == 0.0

        # Empty keywords
        score = score_keyword_matches_optimized("some text", [])
        assert score == 0.0

        # Both empty
        score = score_keyword_matches_optimized("", [])
        assert score == 0.0

    def test_quick_conversation_filter(self, sample_conversations, context_keywords):
        """Test quick conversation filtering by basic criteria."""
        conversations = sample_conversations
        days_lookback = 7

        filtered = quick_conversation_filter(
            conversations, context_keywords, days_lookback
        )

        # Should return conversations within the date range
        assert isinstance(filtered, list)
        assert len(filtered) <= len(conversations)

        # All returned conversations should have valid structure
        for conv in filtered:
            assert "id" in conv
            assert "title" in conv

    def test_quick_conversation_filter_date_filtering(self, context_keywords):
        """Test date filtering in quick conversation filter."""
        # Create conversations with different dates
        old_conversation = {
            "id": "old_conv",
            "title": "Old conversation",
            "created_at": "2020-01-01T00:00:00Z",  # Very old
        }

        recent_conversation = {
            "id": "recent_conv",
            "title": "Recent conversation",
            "created_at": "2024-03-21T10:30:00Z",  # Recent
        }

        conversations = [old_conversation, recent_conversation]
        days_lookback = 30  # Last 30 days

        filtered = quick_conversation_filter(
            conversations, context_keywords, days_lookback
        )

        # Should filter out old conversation
        filtered_ids = [conv["id"] for conv in filtered]
        assert "old_conv" not in filtered_ids
        # Note: recent conversation might be filtered based on current date

    def test_score_recency(self):
        """Test recency scoring for conversations."""
        from datetime import datetime, timedelta

        # Very recent conversation (should score high)
        recent_time = datetime.now() - timedelta(hours=1)
        recent_conv = {"created_at": recent_time.isoformat()}
        recent_score = score_recency(recent_conv)

        # Old conversation (should score low)
        old_time = datetime.now() - timedelta(days=365)
        old_conv = {"created_at": old_time.isoformat()}
        old_score = score_recency(old_conv)

        # Recent should score higher than old
        assert recent_score > old_score
        assert 0.0 <= recent_score <= 1.0
        assert 0.0 <= old_score <= 1.0

    def test_score_recency_invalid_date(self):
        """Test recency scoring with invalid date formats."""
        # Missing created_at
        conv = {"title": "Test conversation"}
        score = score_recency(conv)
        assert score == 0.0

        # Invalid date format
        conv = {"created_at": "not a date"}
        score = score_recency(conv)
        assert score == 0.0

        # Non-string date
        conv = {"created_at": 12345}
        score = score_recency(conv)
        assert score >= 0.0  # Should handle gracefully

    def test_score_pattern_matches(self, context_keywords):
        """Test pattern matching scoring."""
        # Text with development patterns
        text = "We need to debug this error in our test suite and handle exceptions"

        score = score_pattern_matches(text, context_keywords)

        # Should find patterns like error, debug, test
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.0  # Should find some patterns

    def test_score_pattern_matches_no_patterns(self, context_keywords):
        """Test pattern matching with no matches."""
        text = "This is just plain text with no development terms"

        score = score_pattern_matches(text, context_keywords)
        assert score >= 0.0  # Might still get some score from keywords

    def test_score_file_references(self, temp_project_root):
        """Test file reference scoring."""
        # Text with file references that exist in project
        text = "We need to update the main.py file and check package.json configuration"

        score, refs = score_file_references(text, temp_project_root)

        # Should find existing file references
        assert isinstance(score, float)
        assert isinstance(refs, list)
        assert score >= 0.0

        # Should find main.py and package.json as they exist in temp project
        ref_names = [ref for ref in refs if ref in ["main.py", "package.json"]]
        assert len(ref_names) > 0

    def test_score_file_references_nonexistent_files(self, temp_project_root):
        """Test file reference scoring with non-existent files."""
        # Text with file references that don't exist
        text = (
            "We need to update the nonexistent.py file and missing.json configuration"
        )

        score, refs = score_file_references(text, temp_project_root)

        # Should have low score since files don't exist
        assert isinstance(score, float)
        assert isinstance(refs, list)
        assert score >= 0.0
        assert len(refs) == 0  # No valid file references

    def test_score_file_references_empty_text(self, temp_project_root):
        """Test file reference scoring with empty text."""
        score, refs = score_file_references("", temp_project_root)

        assert score == 0.0
        assert refs == []

    @patch("src.tool_calls.cursor.conversation_analyzer.extract_keywords_from_content")
    def test_keyword_extraction_integration(
        self, mock_extract_keywords, temp_project_root, sample_conversations
    ):
        """Test integration with keyword extraction."""
        mock_extract_keywords.return_value = ["python", "error", "function"]

        conversation = sample_conversations[0]
        context_keywords = ["python", "test"]

        result = analyze_conversation_relevance(
            conversation, context_keywords, temp_project_root, include_analysis=True
        )

        # Should call keyword extraction
        mock_extract_keywords.assert_called()

        # Should include extracted keywords in analysis
        assert "detected_keywords" in result["analysis"]
