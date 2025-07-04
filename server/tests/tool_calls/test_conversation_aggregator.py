"""
Tests for conversation aggregator functionality.

Tests the primary conversation interface that aggregates data from multiple agentic tools.
"""

import json
import unittest
from unittest.mock import Mock, patch

from src.config.constants import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_WINDSURF,
)
from src.tool_calls.conversation_aggregator import (
    _detect_available_agentic_tools,
    _standardize_conversation_format,
    handle_recall_conversations,
    handle_search_conversations,
)


def extract_data_from_mcp_response(response):
    """Helper function to extract data from MCP-wrapped response."""
    if isinstance(response, dict) and "content" in response:
        text_content = response["content"][0]["text"]
        return json.loads(text_content)
    return response


class TestConversationAggregator(unittest.TestCase):
    """Test conversation aggregation across agentic tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.context_keywords = ["fellowship", "ring", "quest"]

        self.cursor_conversation = {
            "id": "frodo_ring_quest",
            "title": "Ring destruction strategy",
            "workspace_id": "rivendell_workspace",
            "conversation_type": "architecture",
            "ai_model": "gandalf-the-grey",
            "user_query": "How to destroy the One Ring?",
            "ai_response": "Cast it into the fires of Mount Doom where it was forged",
            "file_references": ["ring.py", "mount_doom.py"],
            "code_blocks": ["def destroy_ring(): return mount_doom.cast_ring()"],
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:30:00Z",
            "message_count": 5,
            "relevance_score": 8.5,
            "snippet": "Ring destruction planning",
        }

        self.claude_conversation = {
            "id": "gandalf_wisdom",
            "title": "Wizard guidance on Balrog encounter",
            "session_id": "moria_session",
            "project_context": {"name": "fellowship_quest"},
            "context": {"files": ["balrog.py"]},
            "messages": [{"role": "user", "content": "How to defeat a Balrog?"}],
            "created_at": "2024-01-01T11:00:00Z",
            "updated_at": "2024-01-01T11:45:00Z",
            "message_count": 3,
            "relevance_score": 7.2,
            "snippet": "Balrog encounter strategy",
        }

        self.windsurf_conversation = {
            "id": "windsurf_session_1",
            "title": "Windsurf Chat windsurf_se",
            "workspace_id": "rivendell_workspace",
            "database_path": "/path/to/windsurf/state.vscdb",
            "session_data": {
                "title": "Ring Bearer Quest Planning",
                "messages": [
                    {"role": "user", "content": "How to destroy the One Ring?"},
                    {"role": "assistant", "content": "Cast it into Mount Doom"},
                ],
            },
            "windsurf_source": "windsurf_chat_session",
            "chat_session_id": "session_1",
            "windsurf_metadata": {"version": "1.0"},
            "created_at": "2024-01-01T12:00:00Z",
            "updated_at": "2024-01-01T12:30:00Z",
            "message_count": 2,
            "relevance_score": 8.0,
            "snippet": "Ring Bearer quest planning discussion",
        }

    def test_standardize_conversation_format_cursor(self):
        """Test standardizing Cursor conversation format."""
        result = _standardize_conversation_format(
            self.cursor_conversation, AGENTIC_TOOL_CURSOR, self.context_keywords
        )

        self.assertEqual(result["source_tool"], AGENTIC_TOOL_CURSOR)
        self.assertEqual(result["id"], "frodo_ring_quest")
        self.assertEqual(result["title"], "Ring destruction strategy")
        self.assertEqual(result["workspace_id"], "rivendell_workspace")
        self.assertEqual(result["conversation_type"], "architecture")
        self.assertEqual(result["ai_model"], "gandalf-the-grey")
        self.assertEqual(result["context_keywords"], self.context_keywords)
        self.assertIn("file_references", result)
        self.assertIn("code_blocks", result)

    def test_standardize_conversation_format_claude(self):
        """Test standardizing Claude Code conversation format."""
        result = _standardize_conversation_format(
            self.claude_conversation, AGENTIC_TOOL_CLAUDE_CODE, self.context_keywords
        )

        self.assertEqual(result["source_tool"], AGENTIC_TOOL_CLAUDE_CODE)
        self.assertEqual(result["id"], "gandalf_wisdom")
        self.assertEqual(result["title"], "Wizard guidance on Balrog encounter")
        self.assertEqual(result["session_id"], "moria_session")
        self.assertEqual(result["project_context"], {"name": "fellowship_quest"})
        self.assertEqual(result["context_keywords"], self.context_keywords)
        self.assertIn("messages", result)
        self.assertIn("analysis_results", result)

    def test_standardize_conversation_format_windsurf(self):
        """Test standardizing Windsurf conversation format."""
        result = _standardize_conversation_format(
            self.windsurf_conversation, AGENTIC_TOOL_WINDSURF, self.context_keywords
        )

        self.assertEqual(result["source_tool"], AGENTIC_TOOL_WINDSURF)
        self.assertEqual(result["id"], "windsurf_session_1")
        self.assertEqual(result["title"], "Windsurf Chat windsurf_se")
        self.assertEqual(result["workspace_id"], "rivendell_workspace")
        self.assertEqual(result["database_path"], "/path/to/windsurf/state.vscdb")
        self.assertEqual(result["windsurf_source"], "windsurf_chat_session")
        self.assertEqual(result["chat_session_id"], "session_1")
        self.assertEqual(result["windsurf_metadata"], {"version": "1.0"})
        self.assertEqual(result["context_keywords"], self.context_keywords)
        self.assertIn("session_data", result)

    @patch("src.tool_calls.conversation_aggregator.get_available_agentic_tools")
    def test_detect_available_agentic_tools(self, mock_get_available_tools):
        """Test detection of available agentic tools."""
        mock_get_available_tools.return_value = [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
            AGENTIC_TOOL_WINDSURF,
        ]

        result = _detect_available_agentic_tools()

        self.assertCountEqual(
            result,
            [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE, AGENTIC_TOOL_WINDSURF],
        )
        mock_get_available_tools.assert_called_once_with(silent=True)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    def test_handle_recall_conversations_no_tools(self, mock_detect, mock_keywords):
        """Test recall conversations when no agentic tools are detected."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = []

        result = handle_recall_conversations()
        data = extract_data_from_mcp_response(result)

        self.assertEqual(data["available_tools"], [])
        self.assertEqual(data["total_conversations"], 0)
        self.assertEqual(data["conversations"], [])
        self.assertIn("message", data)
        self.assertEqual(data["context_keywords"], self.context_keywords)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_search_conversations_with_multiple_tools(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test search conversations with multiple agentic tools available."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
            AGENTIC_TOOL_WINDSURF,
        ]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_CURSOR:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.cursor_conversation,
                            AGENTIC_TOOL_CURSOR,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CURSOR,
                }
            elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.claude_conversation,
                            AGENTIC_TOOL_CLAUDE_CODE,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CLAUDE_CODE,
                }
            elif tool_name == AGENTIC_TOOL_WINDSURF:
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
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_search_conversations(query="fellowship quest")

        data = extract_data_from_mcp_response(result)
        self.assertEqual(
            data["available_tools"],
            [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE, AGENTIC_TOOL_WINDSURF],
        )
        self.assertEqual(len(data["conversations"]), 3)
        self.assertEqual(data["query"], "fellowship quest")
        self.assertIn("processing_time", data)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    def test_handle_recall_conversations_zero_tools(self, mock_detect, mock_keywords):
        """Test recall conversations returns proper structure when zero tools detected."""
        mock_keywords.return_value = []
        mock_detect.return_value = []

        result = handle_recall_conversations(
            fast_mode=True,
            days_lookback=7,
            limit=20,
            min_score=2.0,
        )

        data = extract_data_from_mcp_response(result)
        self.assertEqual(data["available_tools"], [])
        self.assertEqual(data["total_conversations"], 0)
        self.assertEqual(data["conversations"], [])
        self.assertTrue(data["fast_mode"])
        self.assertEqual(data["days_lookback"], 7)
        self.assertEqual(data["limit"], 20)
        self.assertEqual(data["min_score"], 2.0)
        self.assertIn("processing_time", data)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_single_cursor_tool(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall conversations with exactly one agentic tool (Cursor)."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR]

        cursor_standardized = _standardize_conversation_format(
            self.cursor_conversation, AGENTIC_TOOL_CURSOR, self.context_keywords
        )

        mock_process.return_value = {
            "conversations": [cursor_standardized],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CURSOR,
            "handler": "recall",
            "total_analyzed": 5,
            "total_results": 1,
            "processing_time": 0.1,
        }

        result = handle_recall_conversations(
            fast_mode=True,
            days_lookback=7,
            limit=20,
        )

        data = extract_data_from_mcp_response(result)
        self.assertEqual(data["available_tools"], [AGENTIC_TOOL_CURSOR])
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(data["conversations"][0]["source_tool"], AGENTIC_TOOL_CURSOR)
        self.assertEqual(data["conversations"][0]["title"], "Ring destruction strategy")
        self.assertTrue(data["fast_mode"])
        self.assertEqual(data["days_lookback"], 7)
        self.assertIn("tool_results", data)
        self.assertIn(AGENTIC_TOOL_CURSOR, data["tool_results"])

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_single_claude_tool(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall conversations with exactly one agentic tool (Claude Code)."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CLAUDE_CODE]

        claude_standardized = _standardize_conversation_format(
            self.claude_conversation, AGENTIC_TOOL_CLAUDE_CODE, self.context_keywords
        )

        mock_process.return_value = {
            "conversations": [claude_standardized],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CLAUDE_CODE,
            "handler": "recall",
            "total_analyzed": 3,
            "total_results": 1,
            "processing_time": 0.15,
        }

        result = handle_recall_conversations(
            fast_mode=False,
            days_lookback=14,
            limit=10,
            min_score=1.5,
        )

        data = extract_data_from_mcp_response(result)
        self.assertEqual(data["available_tools"], [AGENTIC_TOOL_CLAUDE_CODE])
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(
            data["conversations"][0]["source_tool"], AGENTIC_TOOL_CLAUDE_CODE
        )
        self.assertEqual(
            data["conversations"][0]["title"], "Wizard guidance on Balrog encounter"
        )
        self.assertFalse(data["fast_mode"])
        self.assertEqual(data["days_lookback"], 14)
        self.assertEqual(data["limit"], 10)
        self.assertEqual(data["min_score"], 1.5)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_conversations_many_tools(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall conversations with multiple agentic tools and aggregated results."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_CURSOR:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.cursor_conversation,
                            AGENTIC_TOOL_CURSOR,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CURSOR,
                    "handler": "recall",
                    "total_analyzed": 10,
                    "total_results": 1,
                    "processing_time": 0.1,
                }
            elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.claude_conversation,
                            AGENTIC_TOOL_CLAUDE_CODE,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CLAUDE_CODE,
                    "handler": "recall",
                    "total_analyzed": 5,
                    "total_results": 1,
                    "processing_time": 0.08,
                }
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(
            fast_mode=True,
            days_lookback=30,
            limit=50,
            conversation_types=["technical", "debugging"],
        )

        data = extract_data_from_mcp_response(result)
        self.assertIn(AGENTIC_TOOL_CURSOR, data["available_tools"])
        self.assertIn(AGENTIC_TOOL_CLAUDE_CODE, data["available_tools"])
        self.assertEqual(len(data["conversations"]), 2)
        self.assertTrue(data["fast_mode"])
        self.assertEqual(data["days_lookback"], 30)
        self.assertEqual(data["limit"], 50)
        self.assertIn("tool_results", data)
        self.assertIn(AGENTIC_TOOL_CURSOR, data["tool_results"])
        self.assertIn(AGENTIC_TOOL_CLAUDE_CODE, data["tool_results"])

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    def test_handle_search_conversations_zero_tools(self, mock_detect, mock_keywords):
        """Test search conversations returns proper structure when zero tools detected."""
        mock_keywords.return_value = ["ring"]
        mock_detect.return_value = []

        result = handle_search_conversations(
            query="mount doom strategy",
            days_lookback=15,
            include_content=True,
            limit=25,
        )

        data = extract_data_from_mcp_response(result)
        self.assertEqual(data["available_tools"], [])
        self.assertEqual(data["total_conversations"], 0)
        self.assertEqual(data["conversations"], [])
        self.assertEqual(data["query"], "mount doom strategy")
        self.assertEqual(data["days_lookback"], 15)
        self.assertTrue(data["include_content"])
        self.assertEqual(data["limit"], 25)
        self.assertIn("processing_time", data)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_search_conversations_single_tool(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test search conversations with a single agentic tool."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR]

        cursor_standardized = _standardize_conversation_format(
            self.cursor_conversation, AGENTIC_TOOL_CURSOR, self.context_keywords
        )

        mock_process.return_value = {
            "conversations": [cursor_standardized],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CURSOR,
            "handler": "search",
            "total_analyzed": 20,
            "total_results": 1,
            "processing_time": 0.05,
        }

        result = handle_search_conversations(
            query="Ring destruction",
            days_lookback=7,
            include_content=False,
            limit=10,
        )

        data = extract_data_from_mcp_response(result)
        self.assertEqual(data["available_tools"], [AGENTIC_TOOL_CURSOR])
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(data["conversations"][0]["source_tool"], AGENTIC_TOOL_CURSOR)
        self.assertEqual(data["conversations"][0]["title"], "Ring destruction strategy")
        self.assertEqual(data["query"], "Ring destruction")
        self.assertEqual(data["days_lookback"], 7)
        self.assertFalse(data["include_content"])
        self.assertEqual(data["limit"], 10)
        self.assertIn("tool_results", data)
        self.assertIn(AGENTIC_TOOL_CURSOR, data["tool_results"])

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_search_conversations_partial_tool_failures(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test search conversations with partial agentic tool failures."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_CURSOR:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.cursor_conversation,
                            AGENTIC_TOOL_CURSOR,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CURSOR,
                }
            elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                raise OSError("Processing failed")
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_search_conversations(query="balrog encounter")

        data = extract_data_from_mcp_response(result)
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(data["conversations"][0]["source_tool"], AGENTIC_TOOL_CURSOR)
        self.assertEqual(data["query"], "balrog encounter")
        self.assertIn("tool_results", data)
        self.assertIn(AGENTIC_TOOL_CURSOR, data["tool_results"])
        self.assertIn(AGENTIC_TOOL_CLAUDE_CODE, data["tool_results"])
        self.assertIn("error", data["tool_results"][AGENTIC_TOOL_CLAUDE_CODE])


class TestConversationAggregatorEdgeCases(unittest.TestCase):
    """Extended tests for conversation aggregator edge cases and integration scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.context_keywords = ["fellowship", "ring", "quest"]

        self.cursor_conversation = {
            "id": "samwise_courage",
            "title": "The Gardener's Bravery",
            "workspace_id": "shire_workspace",
            "conversation_type": "debugging",
            "ai_model": "gandalf-the-grey",
            "user_query": "There's some good in this world, Mr. Frodo. How do I support my friend?",
            "ai_response": "I can't carry it for you, but I can carry you! Share and enjoy, Mr. Frodo.",
            "file_references": ["loyalty.py", "friendship.py"],
            "code_blocks": ["def carry_friend(): return True"],
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:30:00Z",
            "message_count": 5,
            "relevance_score": 8.5,
            "snippet": "Friendship and loyalty patterns",
        }

        self.claude_conversation = {
            "id": "aragorn_kingship",
            "title": "From Strider to Elessar",
            "session_id": "gondor_session",
            "project_context": {"name": "return_of_the_king"},
            "context": {"files": ["leadership.py"]},
            "messages": [
                {
                    "role": "user",
                    "content": "A day may come when the courage of men fails. How do I lead effectively?",
                }
            ],
            "created_at": "2024-01-01T11:00:00Z",
            "updated_at": "2024-01-01T11:45:00Z",
            "message_count": 3,
            "relevance_score": 7.2,
            "snippet": "The hands of the king are the hands of a healer",
        }

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_all_tools_fail(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall when all tools are detected but all fail to return data."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_CURSOR:
                raise OSError("Database corrupted")
            elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                raise OSError("Access blocked")
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(fast_mode=True, limit=10)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(
            data["available_tools"], [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]
        )
        self.assertEqual(data["total_conversations"], 0)
        self.assertEqual(data["conversations"], [])
        self.assertIn("tool_results", data)
        self.assertIn("error", data["tool_results"][AGENTIC_TOOL_CURSOR])
        self.assertIn("error", data["tool_results"][AGENTIC_TOOL_CLAUDE_CODE])

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_mixed_success_failure(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall with some tools succeeding and others failing."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            if tool_name == AGENTIC_TOOL_CURSOR:
                return {
                    "conversations": [
                        _standardize_conversation_format(
                            self.cursor_conversation,
                            AGENTIC_TOOL_CURSOR,
                            self.context_keywords,
                        )
                    ],
                    "total_conversations": 1,
                    "source_tool": AGENTIC_TOOL_CURSOR,
                }
            elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                raise OSError("Processing failed")
            return {"conversations": [], "total_conversations": 0}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(fast_mode=True, limit=10)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(data["total_conversations"], 1)
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(data["conversations"][0]["source_tool"], AGENTIC_TOOL_CURSOR)
        self.assertIn("tool_results", data)
        self.assertIn(AGENTIC_TOOL_CURSOR, data["tool_results"])
        self.assertIn(AGENTIC_TOOL_CLAUDE_CODE, data["tool_results"])
        self.assertIn("error", data["tool_results"][AGENTIC_TOOL_CLAUDE_CODE])

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_empty_results_from_all_tools(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall when all tools succeed but return no conversations."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            return {
                "conversations": [],
                "total_conversations": 0,
                "source_tool": tool_name,
                "handler": handler_name,
                "total_analyzed": 0,
                "total_results": 0,
                "processing_time": 0.01,
            }

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(fast_mode=True, limit=10)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(
            data["available_tools"], [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]
        )
        self.assertEqual(data["total_conversations"], 0)
        self.assertEqual(data["conversations"], [])
        self.assertIn("tool_results", data)
        self.assertEqual(
            data["tool_results"][AGENTIC_TOOL_CURSOR]["total_conversations"], 0
        )
        self.assertEqual(
            data["tool_results"][AGENTIC_TOOL_CLAUDE_CODE]["total_conversations"], 0
        )

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_very_large_result_sets(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall with very large result sets from multiple tools."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]

        def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
            conversations = []
            for i in range(100):
                if tool_name == AGENTIC_TOOL_CURSOR:
                    conv = self.cursor_conversation.copy()
                    conv["id"] = f"hobbit_tale_{i}"
                    conv["title"] = f"Tales from the Shire {i}"
                    conversations.append(
                        _standardize_conversation_format(
                            conv, tool_name, self.context_keywords
                        )
                    )
                elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                    conv = self.claude_conversation.copy()
                    conv["id"] = f"white_council_{i}"
                    conv["title"] = f"Council of the Wise {i}"
                    conversations.append(
                        _standardize_conversation_format(
                            conv, tool_name, self.context_keywords
                        )
                    )

            return {
                "conversations": conversations,
                "total_conversations": len(conversations),
                "source_tool": tool_name,
                "handler": handler_name,
                "total_analyzed": len(conversations),
                "total_results": len(conversations),
                "processing_time": 0.5,
            }

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(fast_mode=True, limit=50)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(
            data["available_tools"], [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE]
        )

        if "conversations" in data:
            total_conversations_found = len(data["conversations"])
        else:
            total_conversations_found = data.get("total_conversations", 0)

        self.assertEqual(total_conversations_found, 200)
        self.assertEqual(data["total_conversations"], 200)

        if data.get("summary_mode", False):
            self.assertIn("tool_summaries", data)
            self.assertIn("optimization_applied", data)
            self.assertTrue(data["optimization_applied"])
        else:
            self.assertIn("tool_results", data)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    def test_handle_recall_registry_detection_failure(self, mock_detect, mock_keywords):
        """Test recall when registry detection itself fails."""
        mock_keywords.return_value = self.context_keywords

        mock_detect.side_effect = OSError("Registry detection failed")

        result = handle_recall_conversations(fast_mode=True, limit=10)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(data["available_tools"], [])
        self.assertEqual(data["total_conversations"], 0)
        self.assertEqual(data["conversations"], [])
        self.assertIn("message", data)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_search_different_tool_counts(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test search with different numbers of available tools (0, 1, 2, many)."""
        mock_keywords.return_value = self.context_keywords

        test_scenarios = [
            ([], "No tools available"),
            ([AGENTIC_TOOL_CURSOR], "Single Cursor tool"),
            ([AGENTIC_TOOL_CLAUDE_CODE], "Single Claude tool"),
            (
                [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE],
                "Two tools available",
            ),
        ]

        for tools, scenario_name in test_scenarios:
            with self.subTest(scenario=scenario_name, tools=tools):
                mock_detect.return_value = tools

                def mock_process_side_effect(tool_name, handler_name, *args, **kwargs):
                    if tool_name == AGENTIC_TOOL_CURSOR:
                        return {
                            "conversations": [
                                _standardize_conversation_format(
                                    self.cursor_conversation,
                                    AGENTIC_TOOL_CURSOR,
                                    self.context_keywords,
                                )
                            ],
                            "total_conversations": 1,
                            "source_tool": AGENTIC_TOOL_CURSOR,
                        }
                    elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                        return {
                            "conversations": [
                                _standardize_conversation_format(
                                    self.claude_conversation,
                                    AGENTIC_TOOL_CLAUDE_CODE,
                                    self.context_keywords,
                                )
                            ],
                            "total_conversations": 1,
                            "source_tool": AGENTIC_TOOL_CLAUDE_CODE,
                        }
                    return {"conversations": [], "total_conversations": 0}

                mock_process.side_effect = mock_process_side_effect

                result = handle_search_conversations(query="fellowship strategy")
                data = extract_data_from_mcp_response(result)

                self.assertEqual(data["available_tools"], tools)
                self.assertEqual(len(data["conversations"]), len(tools))
                self.assertEqual(data["query"], "fellowship strategy")

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_project_root_edge_cases(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall with various project root scenarios."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR]

        mock_process.return_value = {
            "conversations": [
                _standardize_conversation_format(
                    self.cursor_conversation,
                    AGENTIC_TOOL_CURSOR,
                    self.context_keywords,
                )
            ],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CURSOR,
        }

        result = handle_recall_conversations(project_root=None)
        data = extract_data_from_mcp_response(result)
        self.assertEqual(len(data["conversations"]), 1)

        from pathlib import Path

        result = handle_recall_conversations(project_root=Path("/mnt/doom/path"))
        data = extract_data_from_mcp_response(result)
        self.assertEqual(len(data["conversations"]), 1)

        result = handle_recall_conversations(project_root="/shire/hobbiton/path")
        data = extract_data_from_mcp_response(result)
        self.assertEqual(len(data["conversations"]), 1)

    @patch("src.tool_calls.conversation_aggregator.generate_shared_context_keywords")
    @patch("src.tool_calls.conversation_aggregator._detect_available_agentic_tools")
    @patch("src.tool_calls.conversation_aggregator._process_agentic_tool_conversations")
    def test_handle_recall_parameter_validation(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall with various parameter edge cases."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR]

        mock_process.return_value = {
            "conversations": [],
            "total_conversations": 0,
            "source_tool": AGENTIC_TOOL_CURSOR,
        }

        test_cases = [
            {"limit": 0, "expected_conversations": 0},
            {"limit": 1, "expected_conversations": 0},
            {"limit": 10000, "expected_conversations": 0},
            {"min_score": -1.0, "expected_conversations": 0},
            {"min_score": 0.0, "expected_conversations": 0},
            {"min_score": 10.0, "expected_conversations": 0},
            {"days_lookback": 0, "expected_conversations": 0},
            {"days_lookback": 1, "expected_conversations": 0},
            {"days_lookback": 365, "expected_conversations": 0},
        ]

        for test_case in test_cases:
            with self.subTest(params=test_case):
                expected = test_case.pop("expected_conversations")

                result = handle_recall_conversations(**test_case)
                data = extract_data_from_mcp_response(result)

                self.assertIsInstance(data, dict)
                self.assertIn("available_tools", data)
                self.assertIn("conversations", data)
                self.assertEqual(len(data["conversations"]), expected)
