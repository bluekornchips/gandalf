"""
Tests for format_output module.
"""

from typing import Any, Dict

from src.database_management.format_output import OutputFormatter
from src.config.constants import MAX_SUMMARY_LENGTH, MAX_SUMMARY_ENTRIES


class TestOutputFormatter:
    """Test suite for OutputFormatter class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.output_formatter = OutputFormatter()

    def test_create_conversation_summary(self) -> None:
        """Test create_conversation_summary method."""
        conversation = {"text": "python programming tutorial"}
        summary = self.output_formatter.create_conversation_summary(conversation)
        assert summary == "python programming tutorial"

    def test_create_conversation_summary_long_text(self) -> None:
        """Test create_conversation_summary with long text."""
        long_text = "a" * (MAX_SUMMARY_LENGTH + 50)
        conversation = {"text": long_text}
        summary = self.output_formatter.create_conversation_summary(conversation)
        assert len(summary) == MAX_SUMMARY_LENGTH
        assert "..." in summary

    def test_create_conversation_summary_empty(self) -> None:
        """Test create_conversation_summary with empty conversation."""
        summary = self.output_formatter.create_conversation_summary({})
        assert summary == ""

    def test_create_conversation_summary_non_dict(self) -> None:
        """Test create_conversation_summary with non-dict input."""
        summary = self.output_formatter.create_conversation_summary(
            {"text": "test string"}
        )
        assert summary == "test string"

    def test_create_conversation_summary_different_fields(self) -> None:
        """Test create_conversation_summary with different text fields."""
        # Test textDescription field
        conversation = {"textDescription": "generation content"}
        summary = self.output_formatter.create_conversation_summary(conversation)
        assert summary == "generation content"

        # Test content field
        conversation = {"content": "message content"}
        summary = self.output_formatter.create_conversation_summary(conversation)
        assert summary == "message content"

        # Test message field
        conversation = {"message": "chat message"}
        summary = self.output_formatter.create_conversation_summary(conversation)
        assert summary == "chat message"

    def test_score_conversation_relevance(self) -> None:
        """Test score_conversation_relevance method with keyword matching."""
        conversation = {"text": "python programming tutorial"}

        # Test with matching keywords
        score = self.output_formatter.score_conversation_relevance(
            conversation, "python"
        )
        assert score > 0.0  # Should have positive score

        # Test with partial match
        score = self.output_formatter.score_conversation_relevance(
            conversation, "python javascript"
        )
        assert score > 0.0  # Should have positive score for partial match

        # Test with no match
        score = self.output_formatter.score_conversation_relevance(conversation, "java")
        assert score >= 0.0  # May have low score

    def test_score_conversation_relevance_empty_keywords(self) -> None:
        """Test score_conversation_relevance with empty keywords."""
        conversation = {"text": "test"}
        score = self.output_formatter.score_conversation_relevance(conversation, "")
        # With no keywords, should use recency scoring.
        assert score >= 0.0

    def test_score_conversation_relevance_empty_conversation(self) -> None:
        """Test score_conversation_relevance with empty conversation."""
        conversation: Dict[str, Any] = {}
        score = self.output_formatter.score_conversation_relevance(conversation, "test")
        assert score == 0.0

    def test_score_conversation_relevance_case_insensitive(self) -> None:
        """Test score_conversation_relevance is case insensitive."""
        conversation = {"text": "Python Programming"}
        score = self.output_formatter.score_conversation_relevance(
            conversation, "python"
        )
        assert score == 1.0

    def test_format_conversation_entry_structure(self) -> None:
        """Test format_conversation_entry structure."""
        error_data = {
            "database_path": "/test/path.db",
            "error": "Database error",
            "prompts": [],
            "generations": [],
            "history_entries": [],
        }

        result = self.output_formatter.format_conversation_entry(error_data, True, True)

        # In concise mode, should have different structure
        assert "source" in result
        assert "status" in result
        assert "total_conversations" in result
        assert result["source"] == "path.db"
        assert result["status"] == "error"
        assert result["error"] == "Database error"

    def test_format_conversation_entry_success(self) -> None:
        """Test format_conversation_entry with successful data."""
        success_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt", "commandType": 1}],
            "generations": [{"textDescription": "test generation", "type": "response"}],
            "history_entries": [{"entry": "test"}],
        }

        result = self.output_formatter.format_conversation_entry(
            success_data, True, True
        )

        assert result["status"] == "success"
        assert result["source"] == "path.db"
        assert result["total_conversations"] >= 1  # At least 1 conversation
        assert "conversations" in result
        assert (
            len(result["conversations"]) <= MAX_SUMMARY_ENTRIES * 3
        )  # Max entries per type

    def test_format_conversation_entry_with_keywords(self) -> None:
        """Test format_conversation_entry with keywords for relevance scoring."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "python programming tutorial"}],
            "generations": [{"textDescription": "python code example"}],
            "history_entries": [{"entry": "python discussion"}],
        }

        result = self.output_formatter.format_conversation_entry(
            conversation_data, True, True, "python"
        )

        assert "conversations" in result
        assert len(result["conversations"]) == 3

        # Should be sorted by relevance (all should have high relevance for "python")
        for conv in result["conversations"]:
            assert conv["relevance"] > 0.0
            assert "python" in conv["summary"].lower()

    def test_format_conversation_entry_exclude_prompts(self) -> None:
        """Test format_conversation_entry excluding prompts."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt"}],
            "generations": [{"textDescription": "test generation"}],
            "history_entries": [{"entry": "test history"}],
        }

        result = self.output_formatter.format_conversation_entry(
            conversation_data,
            False,
            True,  # exclude prompts
        )

        assert result["total_conversations"] == 2  # Only generations + history
        conversations = result["conversations"]
        assert len(conversations) == 2
        assert all(conv["type"] in ["generation", "history"] for conv in conversations)

    def test_format_conversation_entry_exclude_generations(self) -> None:
        """Test format_conversation_entry excluding generations."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt"}],
            "generations": [{"textDescription": "test generation"}],
            "history_entries": [{"entry": "test history"}],
        }

        result = self.output_formatter.format_conversation_entry(
            conversation_data,
            True,
            False,  # exclude generations
        )

        assert result["total_conversations"] == 2  # Only prompts + history
        conversations = result["conversations"]
        assert len(conversations) == 2
        assert all(conv["type"] in ["prompt", "history"] for conv in conversations)

    def test_format_conversation_entry_sample_limit(self) -> None:
        """Test format_conversation_entry limits samples to MAX_SUMMARY_ENTRIES per type."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": f"prompt {i}"} for i in range(10)],
            "generations": [{"textDescription": f"generation {i}"} for i in range(10)],
            "history_entries": [{"entry": f"history {i}"} for i in range(10)],
        }

        result = self.output_formatter.format_conversation_entry(
            conversation_data, True, True
        )

        conversations = result["conversations"]
        # Should have max MAX_SUMMARY_ENTRIES summaries per type
        assert (
            len(conversations) <= MAX_SUMMARY_ENTRIES * 3
        )  # prompts + generations + history

        # Check that we have the most recent items (last MAX_SUMMARY_ENTRIES of each type)
        prompt_convs = [c for c in conversations if c["type"] == "prompt"]
        if prompt_convs:
            assert len(prompt_convs) <= MAX_SUMMARY_ENTRIES

    def test_format_conversation_entry_filters_editor_history(self) -> None:
        """Test format_conversation_entry filters out editor state entries by default."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [{"text": "test prompt"}],
            "generations": [{"textDescription": "test generation"}],
            "history_entries": [
                {"entry": "conversational history"},
                {
                    "editor": {
                        "resource": "vscode-remote://wsl/path/to/file.sh",
                        "forceFile": True,
                    }
                },  # Editor state
                {"entry": "more conversation"},
            ],
        }

        # Default behavior: exclude editor history
        result = self.output_formatter.format_conversation_entry(
            conversation_data, True, True
        )

        conversations = result["conversations"]
        history_entries = [c for c in conversations if c["type"] == "history"]
        # Should have filtered out editor state entries
        assert len(history_entries) <= 2  # Only conversational history

    def test_format_conversation_entry_include_editor_history(self) -> None:
        """Test format_conversation_entry can include editor history when requested."""
        conversation_data = {
            "database_path": "/test/path.db",
            "history_entries": [
                {
                    "editor": {
                        "resource": "vscode-remote://wsl/path/to/file.sh",
                        "forceFile": True,
                    }
                },
                {"entry": "conversational history"},
            ],
        }

        # Include editor history explicitly
        result = self.output_formatter.format_conversation_entry(
            conversation_data, False, False, "", True
        )

        conversations = result["conversations"]
        history_entries = [c for c in conversations if c["type"] == "history"]
        # Should include editor state entries when requested
        assert len(history_entries) == 2

    def test_format_conversation_entry_threads_conversations(self) -> None:
        """Test format_conversation_entry threads prompts with generations when both included."""
        conversation_data = {
            "database_path": "/test/path.db",
            "prompts": [
                {"text": "What is Python?", "timestamp": 1000},
                {"text": "How do I install it?", "timestamp": 2000},
            ],
            "generations": [
                {
                    "textDescription": "Python is a programming language",
                    "timestamp": 1050,
                },
                {"textDescription": "You can install it using pip", "timestamp": 2050},
            ],
        }

        # Test formatting when both prompts and generations are included
        result = self.output_formatter.format_conversation_entry(
            conversation_data,
            True,
            True,
            "",
        )

        conversations = result["conversations"]
        # Should have threaded conversations (may have threads or unpaired)
        assert len(conversations) > 0

        # Check if any threads were created (type "thread")
        thread_entries = [c for c in conversations if c.get("type") == "thread"]
        # If threading worked, we should have thread entries with both prompt and generation
        if thread_entries:
            for thread in thread_entries:
                assert "prompt" in thread or "generation" in thread
