"""Test Windsurf integration with the conversation aggregator."""

import json
from pathlib import Path
from unittest.mock import patch

from src.config.constants.agentic import AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_WINDSURF
from src.tool_calls.aggregator import (
    _standardize_conversation_format,
    handle_recall_conversations,
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
            self.windsurf_conversation,
            AGENTIC_TOOL_WINDSURF,
            self.context_keywords,
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
            "attendees": [
                "Frodo",
                "Gandalf",
                "Aragorn",
                "Boromir",
                "Legolas",
                "Gimli",
            ],
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

    @patch("src.tool_calls.aggregator.apply_conversation_filtering")
    @patch("src.tool_calls.aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_with_windsurf(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations including Windsurf."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

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

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF:
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
        mcp_response = json.loads(content_text)

        # The actual data is the MCP response itself
        data = mcp_response

        assert data["available_tools"] == [AGENTIC_TOOL_WINDSURF]
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["source_tool"] == AGENTIC_TOOL_WINDSURF
        assert AGENTIC_TOOL_WINDSURF in data["tool_results"]

    @patch("src.tool_calls.aggregator.apply_conversation_filtering")
    @patch("src.tool_calls.aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_windsurf_with_other_tools(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations with Windsurf and other tools."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF, AGENTIC_TOOL_CURSOR]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

        cursor_conversation = {
            "id": "strider_guidance",
            "title": "Ranger's Path",
            "workspace_id": "bree_workspace",
            "conversation_type": "technical",
            "ai_model": "aragorn-ai",
            "user_query": "How to track the Black Riders?",
            "ai_response": "Follow the old forest paths and avoid the roads",
            "file_references": ["tracking.py", "stealth.py"],
            "code_blocks": ["def avoid_nazgul(): return stealth_mode()"],
            "created_at": "2024-01-01T11:00:00Z",
            "updated_at": "2024-01-01T11:30:00Z",
            "message_count": 3,
            "relevance_score": 8.0,
            "snippet": "Tracking and stealth techniques",
        }

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
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
                    "processing_time": 0.05,
                }
            elif tool_name == AGENTIC_TOOL_CURSOR:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            cursor_conversation,
                            AGENTIC_TOOL_CURSOR,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CURSOR,
                    "processing_time": 0.03,
                }
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=False,
            days_lookback=14,
            limit=50,
            min_score=1.0,
            project_root=self.project_root,
        )

        content_text = result["content"][0]["text"]
        mcp_response = json.loads(content_text)

        # The actual data is the MCP response itself
        data = mcp_response

        assert len(data["available_tools"]) == 2
        assert AGENTIC_TOOL_WINDSURF in data["available_tools"]
        assert AGENTIC_TOOL_CURSOR in data["available_tools"]
        assert data["total_conversations"] == 2

    @patch("src.tool_calls.aggregator.apply_conversation_filtering")
    @patch("src.tool_calls.aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_windsurf_error_handling(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations with Windsurf when errors occur."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
            if tool_name == AGENTIC_TOOL_WINDSURF:
                raise OSError("Windsurf database connection failed")
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True,
            days_lookback=7,
            limit=10,
            project_root=self.project_root,
        )

        content_text = result["content"][0]["text"]
        mcp_response = json.loads(content_text)

        # The actual data is the MCP response itself
        data = mcp_response

        assert data["available_tools"] == [AGENTIC_TOOL_WINDSURF]
        assert data["total_conversations"] == 0

    @patch("src.tool_calls.aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.aggregator._process_agentic_tool_conversations")
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

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
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
        mcp_response = json.loads(content_text)

        # The actual data is the MCP response itself
        data = mcp_response

        if data.get("summary_mode", False):
            assert data["summary_mode"] is True
            assert "tool_summaries" in data
        else:
            for conv in data["conversations"]:
                if "title" in conv:
                    assert len(conv["title"]) <= 100
                if "snippet" in conv:
                    assert len(conv["snippet"]) <= 150

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

    @patch("src.tool_calls.aggregator.apply_conversation_filtering")
    @patch("src.tool_calls.aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.aggregator._process_agentic_tool_conversations")
    def test_windsurf_conversation_relevance_scoring(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test that Windsurf conversations are properly scored and sorted."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_WINDSURF]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

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

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
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
        mcp_response = json.loads(content_text)

        # The actual data is the MCP response itself
        data = mcp_response

        returned_conversations = data["conversations"]
        assert len(returned_conversations) == 2

        scores = [conv["relevance_score"] for conv in returned_conversations]
        assert scores == [9.0, 5.0]
