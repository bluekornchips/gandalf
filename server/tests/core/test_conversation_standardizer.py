"""Tests for conversation standardization functionality."""

from dataclasses import dataclass
from typing import Any

import pytest


# Mock the ConversationStandardizer class for testing the proposed refactored version
@dataclass(frozen=True)
class ConversationStandardizer:
    """Unified conversation processing for all agentic tools."""

    tool_name: str

    def standardize_conversation(
        self,
        conversation: dict[str, Any],
        context_keywords: list[str],
        lightweight: bool = False,
    ) -> dict[str, Any]:
        """Standardize conversation format across all tools."""
        if lightweight:
            return self._create_lightweight_conversation(conversation)

        return self._create_full_conversation(conversation, context_keywords)

    def _create_lightweight_conversation(
        self, conversation: dict[str, Any]
    ) -> dict[str, Any]:
        """Create lightweight conversation format."""
        conv_id = conversation.get("id", conversation.get("session_id", ""))
        title = conversation.get("title", f"{self.tool_name.title()} Session")

        return {
            "id": conv_id,
            "title": title,
            "tool": self.tool_name,
            "timestamp": conversation.get("timestamp"),
            "relevance_score": conversation.get("relevance_score", 0.0),
        }

    def _create_full_conversation(
        self, conversation: dict[str, Any], context_keywords: list[str]
    ) -> dict[str, Any]:
        """Create full conversation format with content."""
        base = self._create_lightweight_conversation(conversation)

        # Extract content based on tool type
        content = self._extract_content(conversation)

        # Calculate relevance score based on context keywords
        relevance_score = self._calculate_relevance_score(content, context_keywords)

        # Calculate message count based on tool type
        if self.tool_name == "cursor":
            message_count = len(conversation.get("composerSteps", []))
        elif self.tool_name == "claude-code":
            message_count = len(conversation.get("messages", []))
        elif self.tool_name == "windsurf":
            message_count = 1 if conversation.get("chat_data", {}).get("content") else 0
        else:
            message_count = len(conversation.get("messages", []))

        base.update(
            {
                "content": content,
                "relevance_score": relevance_score,
                "message_count": message_count,
                "context_keywords": context_keywords,
            }
        )

        return base

    def _extract_content(self, conversation: dict[str, Any]) -> str:
        """Extract content based on tool-specific format."""
        if self.tool_name == "cursor":
            # Cursor-specific content extraction
            steps = conversation.get("composerSteps", [])
            return " ".join([step.get("content", "") for step in steps])
        elif self.tool_name == "claude-code":
            # Claude Code specific extraction
            messages = conversation.get("messages", [])
            return " ".join([msg.get("content", "") for msg in messages])
        elif self.tool_name == "windsurf":
            # Windsurf specific extraction
            chat_data = conversation.get("chat_data", {})
            return chat_data.get("content", "")
        else:
            return str(conversation.get("content", ""))

    def _calculate_relevance_score(self, content: str, keywords: list[str]) -> float:
        """Calculate relevance score based on keyword matches."""
        if not content or not keywords:
            return 0.0

        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)

        return min(matches / len(keywords), 1.0) if keywords else 0.0


class TestConversationStandardizer:
    """Test conversation standardization functionality."""

    @pytest.fixture
    def cursor_standardizer(self):
        """Create Cursor conversation standardizer."""
        return ConversationStandardizer("cursor")

    @pytest.fixture
    def claude_code_standardizer(self):
        """Create Claude Code conversation standardizer."""
        return ConversationStandardizer("claude-code")

    @pytest.fixture
    def windsurf_standardizer(self):
        """Create Windsurf conversation standardizer."""
        return ConversationStandardizer("windsurf")

    @pytest.fixture
    def sample_cursor_conversation(self):
        """Sample Cursor conversation data."""
        return {
            "id": "frodo_session_123",
            "title": "Debug Authentication Issue",
            "composerSteps": [
                {"content": "Help me fix this authentication bug in the login system"},
                {"content": "The users can't authenticate properly"},
            ],
            "timestamp": "2023-12-01T10:00:00Z",
            "relevance_score": 0.8,
        }

    @pytest.fixture
    def sample_claude_code_conversation(self):
        """Sample Claude Code conversation data."""
        return {
            "id": "gandalf_chat_456",
            "title": "API Endpoint Development",
            "messages": [
                {"content": "Create a new API endpoint for user management"},
                {"content": "Add proper error handling and validation"},
            ],
            "timestamp": "2023-12-01T11:00:00Z",
        }

    @pytest.fixture
    def sample_windsurf_conversation(self):
        """Sample Windsurf conversation data."""
        return {
            "session_id": "aragorn_ws_789",
            "title": "Database Query Optimization",
            "chat_data": {
                "content": "Optimize these slow database queries for better performance"
            },
            "timestamp": "2023-12-01T12:00:00Z",
        }

    def test_cursor_lightweight_standardization(
        self, cursor_standardizer, sample_cursor_conversation
    ):
        """Test lightweight standardization for Cursor conversations."""
        result = cursor_standardizer.standardize_conversation(
            sample_cursor_conversation, ["authentication", "debug"], lightweight=True
        )

        assert result["id"] == "frodo_session_123"
        assert result["title"] == "Debug Authentication Issue"
        assert result["tool"] == "cursor"
        assert result["timestamp"] == "2023-12-01T10:00:00Z"
        assert result["relevance_score"] == 0.8

        # Lightweight should not include content
        assert "content" not in result
        assert "message_count" not in result

    def test_cursor_full_standardization(
        self, cursor_standardizer, sample_cursor_conversation
    ):
        """Test full standardization for Cursor conversations."""
        context_keywords = ["authentication", "debug", "login"]

        result = cursor_standardizer.standardize_conversation(
            sample_cursor_conversation, context_keywords, lightweight=False
        )

        assert result["id"] == "frodo_session_123"
        assert result["tool"] == "cursor"
        assert "content" in result
        assert "authentication" in result["content"]
        assert "login" in result["content"]
        assert result["message_count"] == 2
        assert result["context_keywords"] == context_keywords
        assert isinstance(result["relevance_score"], float)
        assert 0.0 <= result["relevance_score"] <= 1.0

    def test_claude_code_standardization(
        self, claude_code_standardizer, sample_claude_code_conversation
    ):
        """Test standardization for Claude Code conversations."""
        context_keywords = ["api", "endpoint", "management"]

        result = claude_code_standardizer.standardize_conversation(
            sample_claude_code_conversation, context_keywords, lightweight=False
        )

        assert result["id"] == "gandalf_chat_456"
        assert result["tool"] == "claude-code"
        assert "api" in result["content"].lower()
        assert "endpoint" in result["content"].lower()
        assert result["message_count"] == 2

    def test_windsurf_standardization(
        self, windsurf_standardizer, sample_windsurf_conversation
    ):
        """Test standardization for Windsurf conversations."""
        context_keywords = ["database", "optimization", "performance"]

        result = windsurf_standardizer.standardize_conversation(
            sample_windsurf_conversation, context_keywords, lightweight=False
        )

        assert result["id"] == "aragorn_ws_789"
        assert result["tool"] == "windsurf"
        assert "database" in result["content"].lower()
        assert "optimize" in result["content"].lower()

    def test_default_title_generation(self, cursor_standardizer):
        """Test default title generation when title is missing."""
        conversation_without_title = {
            "id": "legolas_session_999",
            "composerSteps": [{"content": "Test content"}],
        }

        result = cursor_standardizer.standardize_conversation(
            conversation_without_title, [], lightweight=True
        )

        assert result["title"] == "Cursor Session"

    def test_relevance_score_calculation(self, cursor_standardizer):
        """Test relevance score calculation with various keyword matches."""
        conversation = {
            "id": "test_conv",
            "composerSteps": [
                {"content": "This is about authentication and security testing"}
            ],
        }

        # Test with matching keywords
        keywords = ["authentication", "security", "testing"]
        result = cursor_standardizer.standardize_conversation(
            conversation, keywords, lightweight=False
        )
        assert result["relevance_score"] == 1.0  # All keywords match

        # Test with partial matches
        keywords = ["authentication", "database", "testing"]
        result = cursor_standardizer.standardize_conversation(
            conversation, keywords, lightweight=False
        )
        assert result["relevance_score"] == pytest.approx(0.667, rel=1e-2)  # 2/3 match

        # Test with no matches
        keywords = ["unrelated", "keywords"]
        result = cursor_standardizer.standardize_conversation(
            conversation, keywords, lightweight=False
        )
        assert result["relevance_score"] == 0.0

    def test_empty_conversation_handling(self, cursor_standardizer):
        """Test handling of empty or minimal conversation data."""
        empty_conversation = {}

        result = cursor_standardizer.standardize_conversation(
            empty_conversation, [], lightweight=True
        )

        assert result["id"] == ""
        assert result["title"] == "Cursor Session"
        assert result["tool"] == "cursor"
        assert result["timestamp"] is None
        assert result["relevance_score"] == 0.0

    def test_missing_content_handling(self, cursor_standardizer):
        """Test handling when conversation has no extractable content."""
        conversation_no_content = {"id": "gimli_session_111", "title": "Empty Session"}

        result = cursor_standardizer.standardize_conversation(
            conversation_no_content, ["test"], lightweight=False
        )

        assert result["content"] == ""
        assert result["relevance_score"] == 0.0
        assert result["message_count"] == 0

    def test_tool_specific_content_extraction(self):
        """Test that content extraction is tool-specific."""
        # Test different tools extract content differently
        cursor_conv = {"composerSteps": [{"content": "cursor content"}]}
        claude_conv = {"messages": [{"content": "claude content"}]}
        windsurf_conv = {"chat_data": {"content": "windsurf content"}}

        cursor_standardizer = ConversationStandardizer("cursor")
        claude_standardizer = ConversationStandardizer("claude-code")
        windsurf_standardizer = ConversationStandardizer("windsurf")

        cursor_result = cursor_standardizer._extract_content(cursor_conv)
        claude_result = claude_standardizer._extract_content(claude_conv)
        windsurf_result = windsurf_standardizer._extract_content(windsurf_conv)

        assert cursor_result == "cursor content"
        assert claude_result == "claude content"
        assert windsurf_result == "windsurf content"

    def test_case_insensitive_keyword_matching(self, cursor_standardizer):
        """Test that keyword matching is case insensitive."""
        conversation = {
            "id": "test_conv",
            "composerSteps": [{"content": "AUTHENTICATION and Security TESTING"}],
        }

        keywords = ["authentication", "security", "testing"]
        result = cursor_standardizer.standardize_conversation(
            conversation, keywords, lightweight=False
        )

        assert result["relevance_score"] == 1.0

    def test_standardizer_immutability(self, cursor_standardizer):
        """Test that ConversationStandardizer is immutable."""
        assert cursor_standardizer.tool_name == "cursor"

        # Verify it's frozen (dataclass)
        with pytest.raises(AttributeError):
            cursor_standardizer.tool_name = "modified"

    @pytest.mark.parametrize(
        "tool_name,expected_title",
        [
            ("cursor", "Cursor Session"),
            ("claude-code", "Claude-Code Session"),
            ("windsurf", "Windsurf Session"),
            ("unknown", "Unknown Session"),
        ],
    )
    def test_default_title_by_tool(self, tool_name, expected_title):
        """Test default title generation for different tools."""
        standardizer = ConversationStandardizer(tool_name)
        conversation = {"id": "test"}

        result = standardizer.standardize_conversation(
            conversation, [], lightweight=True
        )
        assert result["title"] == expected_title
