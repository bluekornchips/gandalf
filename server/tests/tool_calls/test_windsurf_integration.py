"""Test Windsurf integration with the conversation aggregator."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.config.constants import AGENTIC_TOOL_WINDSURF
from src.tool_calls.conversation_aggregator import (
    _standardize_conversation_format,
    handle_recall_conversations,
    handle_search_conversations,
)


class TestWindsurfIntegration:
    """Test Windsurf integration with conversation aggregator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/test/rivendell")
        self.context_keywords = [
            "fellowship",
            "ring",
            "quest",
            "python",
            "windsurf",
            "mithril",
            "palantír",
        ]

        self.windsurf_conversation = {
            "id": "elrond_council_session",
            "title": "The Council of Elrond",
            "workspace_id": "rivendell_workspace",
            "database_path": "/path/to/windsurf/rivendell.vscdb",
            "session_data": {
                "title": "The Fate of the Ring",
                "messages": [
                    {
                        "role": "user",
                        "content": "All we have to decide is what to do with the time that is given us. What shall we do with the Ring?",
                    },
                    {
                        "role": "assistant",
                        "content": "The Ring must be destroyed. One of you must do this. The Ring must be taken deep into Mordor and cast back into the fiery chasm from whence it came.",
                    },
                ],
            },
            "windsurf_source": "windsurf_chat_session",
            "chat_session_id": "council_of_elrond",
            "windsurf_metadata": {
                "version": "1.0",
                "location": "Rivendell",
                "attendees": [
                    "Frodo",
                    "Gandalf",
                    "Aragorn",
                    "Boromir",
                    "Legolas",
                    "Gimli",
                ],
            },
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:30:00Z",
            "message_count": 2,
            "relevance_score": 9.5,
            "snippet": "The Council debates the fate of the One Ring",
        }

    def test_standardize_windsurf_conversation_format(self):
        """Test standardizing Windsurf conversation format."""
        result = _standardize_conversation_format(
            self.windsurf_conversation, AGENTIC_TOOL_WINDSURF, self.context_keywords
        )

        assert result["source_tool"] == AGENTIC_TOOL_WINDSURF
        assert result["id"] == "elrond_council_session"
        assert result["title"] == "The Council of Elrond"
        assert result["workspace_id"] == "rivendell_workspace"
        assert result["context_keywords"] == self.context_keywords

        assert result["database_path"] == "/path/to/windsurf/rivendell.vscdb"
        assert result["session_data"] == self.windsurf_conversation["session_data"]
        assert result["windsurf_source"] == "windsurf_chat_session"
        assert result["chat_session_id"] == "council_of_elrond"
        assert result["windsurf_metadata"] == {
            "version": "1.0",
            "location": "Rivendell",
            "attendees": ["Frodo", "Gandalf", "Aragorn", "Boromir", "Legolas", "Gimli"],
        }

    def test_standardize_windsurf_conversation_lightweight(self):
        """Test lightweight standardization for Windsurf conversations."""
        result = _standardize_conversation_format(
            self.windsurf_conversation,
            AGENTIC_TOOL_WINDSURF,
            self.context_keywords,
            lightweight=True,
        )

        expected_fields = {
            "id",
            "title",
            "source_tool",
            "message_count",
            "relevance_score",
            "created_at",
            "snippet",
        }
        assert set(result.keys()) == expected_fields
        assert result["source_tool"] == AGENTIC_TOOL_WINDSURF
        assert len(result["id"]) <= 50
        assert len(result["title"]) <= 100

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_with_windsurf(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall conversations including Windsurf."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        windsurf_response = {
            "conversations": [
                _standardize_conversation_format(
                    self.windsurf_conversation,
                    AGENTIC_TOOL_WINDSURF,
                    self.context_keywords,
                )
            ],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_WINDSURF,
            "handler": "recall",
            "processing_time": 0.05,
        }

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF and handler_name == "recall":
                return windsurf_response
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True,
            days_lookback=7,
            limit=20,
            min_score=2.0,
            project_root=self.project_root,
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        assert data["available_tools"] == [AGENTIC_TOOL_WINDSURF]
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["source_tool"] == AGENTIC_TOOL_WINDSURF
        assert AGENTIC_TOOL_WINDSURF in data["tool_results"]

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_search_conversations_with_windsurf(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test search conversations including Windsurf."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        windsurf_response = {
            "conversations": [
                _standardize_conversation_format(
                    self.windsurf_conversation,
                    AGENTIC_TOOL_WINDSURF,
                    self.context_keywords,
                )
            ],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_WINDSURF,
            "handler": "search",
        }

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF and handler_name == "search":
                return windsurf_response
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_search_conversations(
            query="ring quest",
            days_lookback=30,
            include_content=True,
            limit=20,
            project_root=self.project_root,
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        assert data["available_tools"] == [AGENTIC_TOOL_WINDSURF]
        assert len(data["conversations"]) == 1
        assert data["query"] == "ring quest"
        assert data["conversations"][0]["source_tool"] == AGENTIC_TOOL_WINDSURF

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_windsurf_with_other_tools(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall conversations with Windsurf alongside other tools."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = ["cursor", "claude-code", AGENTIC_TOOL_WINDSURF]

        cursor_conversation = {
            "id": "aragorn_strider",
            "title": "The Ranger of the North",
            "source_tool": "cursor",
            "relevance_score": 7.0,
            "snippet": "A ranger's wisdom in the wild",
        }

        claude_conversation = {
            "id": "legolas_archery",
            "title": "Elven Marksmanship",
            "source_tool": "claude-code",
            "relevance_score": 6.5,
            "snippet": "That still only counts as one!",
        }

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.windsurf_conversation,
                            AGENTIC_TOOL_WINDSURF,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_WINDSURF,
                }
            elif tool_name == "cursor":
                return {
                    "conversations": [cursor_conversation],
                    "total_conversations": 1,
                    "source_tool": "cursor",
                }
            elif tool_name == "claude-code":
                return {
                    "conversations": [claude_conversation],
                    "total_conversations": 1,
                    "source_tool": "claude-code",
                }
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True, project_root=self.project_root
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        assert len(data["available_tools"]) == 3
        assert AGENTIC_TOOL_WINDSURF in data["available_tools"]
        assert "cursor" in data["available_tools"]
        assert "claude-code" in data["available_tools"]

        assert len(data["conversations"]) == 3
        source_tools = {conv["source_tool"] for conv in data["conversations"]}
        assert source_tools == {"cursor", "claude-code", AGENTIC_TOOL_WINDSURF}

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_windsurf_error_handling(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test error handling when Windsurf processing fails."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF:
                return {"error": "Processing failed"}
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True, project_root=self.project_root
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        assert data["available_tools"] == [AGENTIC_TOOL_WINDSURF]
        assert len(data["conversations"]) == 0
        assert AGENTIC_TOOL_WINDSURF in data["tool_results"]
        assert "error" in data["tool_results"][AGENTIC_TOOL_WINDSURF]

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    def test_handle_recall_conversations_windsurf_not_detected(
        self, mock_detect, mock_keywords
    ):
        """Test behavior when Windsurf is not detected."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = ["cursor", "claude-code"]

        result = handle_recall_conversations(
            fast_mode=True, project_root=self.project_root
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        assert AGENTIC_TOOL_WINDSURF not in data["available_tools"]
        assert AGENTIC_TOOL_WINDSURF not in data.get("tool_results", {})

    def test_windsurf_conversation_field_mapping(self):
        """Test that Windsurf-specific fields are properly mapped."""
        test_conversations = [
            {
                "id": "bilbo_birthday",
                "workspace_id": "shire_workspace",
                "source": "windsurf_chat_session",
                "session_data": {"title": "Bilbo's Eleventy-First Birthday"},
                "metadata": {"version": "1.0", "location": "Bag End"},
            },
            {
                "id": "ent_moot",
                "workspace_id": "fangorn_workspace",
                "source": "windsurf_cascade",
                "session_data": {"cascade_info": "Don't be hasty! This is Ent-draught"},
                "database_path": "/path/to/fangorn/entmoot.vscdb",
            },
            {
                "id": "rohirrim_charge",
                "source": "windsurf",
                "workspace_id": "edoras_workspace",
            },
        ]

        for conv in test_conversations:
            result = _standardize_conversation_format(
                conv, AGENTIC_TOOL_WINDSURF, self.context_keywords
            )

            assert "workspace_id" in result
            assert "database_path" in result
            assert "session_data" in result
            assert "windsurf_source" in result
            assert "chat_session_id" in result
            assert "windsurf_metadata" in result
            assert result["source_tool"] == AGENTIC_TOOL_WINDSURF

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_windsurf_conversation_relevance_scoring(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test that Windsurf conversations are properly scored and sorted."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        windsurf_conversations = [
            {
                **self.windsurf_conversation,
                "id": "galadriel_wisdom",
                "relevance_score": 9.0,
                "snippet": "Even the smallest person can change the course of the future",
            },
            {
                **self.windsurf_conversation,
                "id": "boromir_temptation",
                "relevance_score": 5.0,
                "snippet": "One does not simply walk into Mordor",
            },
            {
                **self.windsurf_conversation,
                "id": "gimli_friendship",
                "relevance_score": 2.0,
                "snippet": "Never thought I'd die fighting side by side with an Elf",
            },
        ]

        standardized_conversations = [
            _standardize_conversation_format(
                conv, AGENTIC_TOOL_WINDSURF, self.context_keywords
            )
            for conv in windsurf_conversations
        ]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF:
                min_score = kwargs.get("min_score", 0.0)
                filtered_conversations = [
                    conv
                    for conv in standardized_conversations
                    if conv.get("relevance_score", 0.0) >= min_score
                ]
                return {
                    "conversations": filtered_conversations,
                    "total_conversations": len(filtered_conversations),
                    "source_tool": AGENTIC_TOOL_WINDSURF,
                }
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True, min_score=3.0, project_root=self.project_root
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        returned_conversations = data["conversations"]
        assert len(returned_conversations) == 2

        scores = [conv["relevance_score"] for conv in returned_conversations]
        assert scores == [9.0, 5.0]

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_windsurf_token_optimization(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test token optimization for large Windsurf responses."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        many_conversations = []
        for i in range(20):
            conv = {
                **self.windsurf_conversation,
                "id": f"fellowship_member_{i}",
                "title": f"The Tale of {['Frodo', 'Sam', 'Merry', 'Pippin', 'Gandalf', 'Aragorn', 'Boromir', 'Legolas', 'Gimli'][i % 9]} {i}",
                "snippet": f"In the land of Mordor where the shadows lie, {['Frodo', 'Sam', 'Merry', 'Pippin'][i % 4]} faces great peril "
                * 5,
                "session_data": {
                    "content": "One Ring to rule them all, One Ring to find them " * 25
                },
            }
            many_conversations.append(
                _standardize_conversation_format(
                    conv, AGENTIC_TOOL_WINDSURF, self.context_keywords
                )
            )

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF:
                return {
                    "conversations": many_conversations,
                    "total_conversations": len(many_conversations),
                    "source_tool": AGENTIC_TOOL_WINDSURF,
                }
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True, project_root=self.project_root
        )

        content_text = result["content"][0]["text"]
        data = json.loads(content_text)

        if data.get("summary_mode", False):
            assert data["summary_mode"] is True
            assert "tool_summaries" in data
        else:
            for conv in data["conversations"]:
                if "title" in conv:
                    assert len(conv["title"]) <= 100
                if "snippet" in conv:
                    assert len(conv["snippet"]) <= 150
