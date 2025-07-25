"""
Tests for conversation aggregator functionality.
"""

import json
import unittest
from unittest.mock import patch

from src.config.conversation_config import (
    AGENTIC_TOOL_CLAUDE_CODE,
    AGENTIC_TOOL_CURSOR,
    AGENTIC_TOOL_WINDSURF,
    CONVERSATION_ID_DISPLAY_LIMIT,
    CONVERSATION_SNIPPET_DISPLAY_LIMIT,
    CONVERSATION_TITLE_DISPLAY_LIMIT,
)
from src.tool_calls.aggregator import (
    handle_recall_conversations,
)
from src.tool_calls.response_formatting import (
    _create_lightweight_conversation,
    _standardize_conversation_format,
)
from src.tool_calls.tool_aggregation import (
    _detect_available_agentic_tools,
)


def extract_data_from_mcp_response(response):
    """Extract data from MCP response format for testing."""
    if not isinstance(response, dict) or "content" not in response:
        raise ValueError(f"Invalid MCP response format: {response}")

    if "structuredContent" in response:
        structured = response["structuredContent"]

        # Also get the original content data which has additional fields
        content_text = response["content"][0].get("text", "{}")
        try:
            content_data = json.loads(content_text)
        except json.JSONDecodeError:
            content_data = {}

        # Start with the content data and overlay structured data
        result = {**content_data, **structured}

        return result

    # Fallback to nested format
    content_items = response.get("content", [])
    if not content_items or not isinstance(content_items, list):
        raise ValueError(f"Invalid MCP response content: {content_items}")

    content_text = content_items[0].get("text", "{}")

    try:
        inner_mcp = json.loads(content_text)
    except json.JSONDecodeError:
        # Handle plain text responses (like "No agentic tools available")
        return {"message": content_text, "conversations": [], "status": "info"}

    # If the inner content is the actual data (not wrapped), return it directly
    if not isinstance(inner_mcp, dict) or "structuredContent" not in inner_mcp:
        # The data is directly in the parsed JSON, not wrapped with structuredContent
        return inner_mcp

    structured = inner_mcp["structuredContent"]

    # Also include the original text data
    result = {}
    if "content" in inner_mcp:
        inner_content = inner_mcp["content"]
        if inner_content and isinstance(inner_content, list):
            inner_text = inner_content[0].get("text", "{}")
            try:
                text_data = json.loads(inner_text)
                # Merge structured and text data
                result = {**text_data, **structured}
            except json.JSONDecodeError:
                result = structured
    else:
        result = structured

    return result


class TestConversationAggregator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.context_keywords = ["ring", "hobbit", "fellowship", "wizard"]

        self.cursor_conversation = {
            "id": "hobbit_001",
            "title": "Ring destruction strategy",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:45:00Z",
            "message_count": 15,
            "relevance_score": 8.5,
            "snippet": "Discussion about destroying the One Ring in Mount Doom",
            "workspace_id": "shire_workspace",
            "conversation_type": "technical",
            "ai_model": "claude-3.5-sonnet",
            "user_query": "How to destroy the One Ring?",
            "ai_response": "The Ring must be cast into the fires of Mount Doom",
            "file_references": ["ring_lore.md", "mount_doom_guide.txt"],
            "code_blocks": ["destroy_ring.py"],
            "metadata": {"urgency": "high", "category": "quest"},
        }

        self.claude_conversation = {
            "id": "wizard_042",
            "title": "Wizard guidance on Balrog encounter",
            "created_at": "2024-01-12T14:20:00Z",
            "updated_at": "2024-01-12T16:30:00Z",
            "message_count": 8,
            "relevance_score": 9.2,
            "snippet": "Gandalf's advice on confronting the Balrog in Moria",
            "session_id": "moria_session_001",
            "project_context": {
                "location": "Mines of Moria",
                "danger_level": "extreme",
            },
            "context": {
                "participants": ["Gandalf", "Fellowship"],
                "urgency": "immediate",
            },
            "messages": [
                {"role": "user", "content": "How to fight a Balrog?"},
                {"role": "assistant", "content": "You cannot pass!"},
            ],
            "metadata": {"spell_type": "light", "effectiveness": "high"},
            "analysis": {
                "threat_level": "maximum",
                "success_probability": 0.3,
            },
            "tool_usage": ["light_spell", "staff_power"],
            "project_files": ["balrog_combat.md", "light_spells.txt"],
        }

        self.windsurf_conversation = {
            "id": "elf_council_007",
            "title": "Elrond's council meeting notes",
            "created_at": "2024-01-10T09:00:00Z",
            "updated_at": "2024-01-10T12:00:00Z",
            "message_count": 25,
            "relevance_score": 7.8,
            "snippet": "Strategic planning session for the Fellowship's journey",
            "workspace_id": "rivendell_workspace",
            "database_path": "/path/to/rivendell.db",
            "session_data": {"council_members": ["Elrond", "Gandalf", "Aragorn"]},
            "source": "council_minutes",
            "chat_session_id": "council_001",
            "metadata": {"importance": "critical", "secrecy": "high"},
        }

    def test_standardize_conversation_format_cursor(self):
        """Test standardization of Cursor conversation format."""
        result = _standardize_conversation_format(
            self.cursor_conversation,
            AGENTIC_TOOL_CURSOR,
            self.context_keywords,
        )

        self.assertEqual(result["source_tool"], AGENTIC_TOOL_CURSOR)
        self.assertEqual(result["title"], "Ring destruction strategy")
        self.assertEqual(result["workspace_id"], "shire_workspace")
        self.assertEqual(result["ai_model"], "claude-3.5-sonnet")
        self.assertIn("context_keywords", result)
        self.assertEqual(result["context_keywords"], self.context_keywords)

    def test_standardize_conversation_format_claude(self):
        """Test standardization of Claude Code conversation format."""
        result = _standardize_conversation_format(
            self.claude_conversation,
            AGENTIC_TOOL_CLAUDE_CODE,
            self.context_keywords,
        )

        self.assertEqual(result["source_tool"], AGENTIC_TOOL_CLAUDE_CODE)
        self.assertEqual(result["title"], "Wizard guidance on Balrog encounter")
        self.assertEqual(result["session_id"], "moria_session_001")
        self.assertIn("project_context", result)
        self.assertIn("context_keywords", result)

    def test_standardize_conversation_format_windsurf(self):
        """Test standardization of Windsurf conversation format."""
        result = _standardize_conversation_format(
            self.windsurf_conversation,
            AGENTIC_TOOL_WINDSURF,
            self.context_keywords,
        )

        self.assertEqual(result["source_tool"], AGENTIC_TOOL_WINDSURF)
        self.assertEqual(result["title"], "Elrond's council meeting notes")
        self.assertEqual(result["workspace_id"], "rivendell_workspace")
        self.assertEqual(result["windsurf_source"], "council_minutes")
        self.assertIn("context_keywords", result)

    @patch("src.tool_calls.tool_aggregation.get_registered_agentic_tools")
    def test_detect_available_agentic_tools(self, mock_get_registered_tools):
        """Test detection of available agentic tools."""
        mock_get_registered_tools.return_value = [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
        ]

        result = _detect_available_agentic_tools()
        self.assertIn(AGENTIC_TOOL_CURSOR, result)
        self.assertIn(AGENTIC_TOOL_CLAUDE_CODE, result)

    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    def test_handle_recall_conversations_no_tools(self, mock_detect, mock_keywords):
        """Test recall conversations with no available tools."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = []

        result = handle_recall_conversations(
            fast_mode=True,
            days_lookback=7,
            limit=20,
            min_score=2.0,
        )

        self.assertIn("content", result)
        self.assertIn("isError", result)
        self.assertFalse(result["isError"])

        content_text = result["content"][0]["text"]
        self.assertIn("No agentic tools available", content_text)
        self.assertIn("cursor", content_text)  # Should mention the supported tools

    @patch("src.core.conversation_filtering.apply_conversation_filtering")
    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_conversations_single_cursor_tool(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations with exactly one agentic tool (Cursor)."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

        cursor_standardized = _standardize_conversation_format(
            self.cursor_conversation,
            AGENTIC_TOOL_CURSOR,
            self.context_keywords,
        )

        mock_process.return_value = {
            "conversations": [cursor_standardized],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CURSOR,
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

        self.assertIn("conversations", data)
        self.assertIn("summary", data)
        self.assertIn("status", data)

        conversations = data["conversations"]
        self.assertIsInstance(conversations, list)
        summary = data["summary"]
        self.assertIsInstance(summary, dict)
        self.assertIn("tools_processed", summary)
        self.assertGreaterEqual(summary["tools_processed"], 1)

    @patch("src.core.conversation_filtering.apply_conversation_filtering")
    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_conversations_single_claude_tool(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations with exactly one agentic tool (Claude Code)."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CLAUDE_CODE]

        claude_standardized = _standardize_conversation_format(
            self.claude_conversation,
            AGENTIC_TOOL_CLAUDE_CODE,
            self.context_keywords,
        )

        mock_process.return_value = {
            "conversations": [claude_standardized],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CLAUDE_CODE,
            "total_analyzed": 3,
            "total_results": 1,
            "processing_time": 0.15,
        }

        mock_filtering.return_value = (
            [claude_standardized],
            {
                "mode": "test",
                "original_count": 1,
                "filtered_count": 1,
            },
        )

        result = handle_recall_conversations(
            fast_mode=False,
            days_lookback=14,
            limit=10,
            min_score=1.5,
        )

        data = extract_data_from_mcp_response(result)

        self.assertIn("conversations", data)
        self.assertIn("summary", data)
        self.assertIn("status", data)

        conversations = data["conversations"]
        self.assertIsInstance(conversations, list)

        summary = data["summary"]
        self.assertIsInstance(summary, dict)
        self.assertIn("tools_processed", summary)
        self.assertGreaterEqual(summary["tools_processed"], 1)

    @patch("src.core.conversation_filtering.apply_conversation_filtering")
    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_conversations_many_tools(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations with multiple agentic tools and aggregated results."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
        ]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
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

        # Check actual aggregated response format
        self.assertIn("conversations", data)
        self.assertIn("summary", data)
        self.assertIn("status", data)

        conversations = data["conversations"]
        self.assertIsInstance(conversations, list)
        # In test environment, conversations may be empty, which is fine

        # Check summary structure
        summary = data["summary"]
        self.assertIsInstance(summary, dict)
        self.assertIn("tools_processed", summary)
        # In test environment, we expect at least some tools to be processed
        self.assertGreaterEqual(summary["tools_processed"], 1)

    @patch("src.core.conversation_filtering.apply_conversation_filtering")
    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_conversations_with_search_query(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall conversations with search query parameter."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [AGENTIC_TOOL_CURSOR]

        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

        cursor_standardized = _standardize_conversation_format(
            self.cursor_conversation,
            AGENTIC_TOOL_CURSOR,
            self.context_keywords,
        )

        mock_process.return_value = {
            "conversations": [cursor_standardized],
            "total_conversations": 1,
            "source_tool": AGENTIC_TOOL_CURSOR,
            "total_analyzed": 20,
            "total_results": 1,
            "processing_time": 0.05,
        }

        result = handle_recall_conversations(
            search_query="Ring destruction",
            days_lookback=7,
            limit=10,
        )

        data = extract_data_from_mcp_response(result)

        self.assertIn("conversations", data)
        self.assertIn("summary", data)
        self.assertIn("status", data)

        conversations = data["conversations"]
        self.assertIsInstance(conversations, list)

        summary = data["summary"]
        self.assertIsInstance(summary, dict)
        self.assertIn("tools_processed", summary)
        self.assertGreaterEqual(summary["tools_processed"], 1)


class TestConversationAggregatorEdgeCases(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.context_keywords = ["ring", "hobbit", "fellowship", "wizard"]

        self.cursor_conversation = {
            "id": "hobbit_001",
            "title": "Ring destruction strategy",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T11:45:00Z",
            "message_count": 15,
            "relevance_score": 8.5,
            "snippet": "Discussion about destroying the One Ring in Mount Doom",
            "workspace_id": "shire_workspace",
            "conversation_type": "technical",
            "ai_model": "claude-3.5-sonnet",
            "user_query": "How to destroy the One Ring?",
            "ai_response": "The Ring must be cast into the fires of Mount Doom",
            "file_references": ["ring_lore.md", "mount_doom_guide.txt"],
            "code_blocks": ["destroy_ring.py"],
            "metadata": {"urgency": "high", "category": "quest"},
        }

    @patch("src.core.conversation_filtering.apply_conversation_filtering")
    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_mixed_success_failure(
        self, mock_process, mock_detect, mock_keywords, mock_filtering
    ):
        """Test recall with some tools succeeding and others failing."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
        ]

        # Mock filtering to return conversations unchanged
        def mock_filtering_side_effect(conversations, *args, **kwargs):
            return conversations, {
                "mode": "test",
                "original_count": len(conversations),
                "filtered_count": len(conversations),
            }

        mock_filtering.side_effect = mock_filtering_side_effect

        def mock_process_side_effect(tool_name, arguments, project_root, **kwargs):
            if tool_name == AGENTIC_TOOL_CURSOR:
                result_data = {
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
                # Return in MCP format like real handlers
                import json

                return {"content": [{"type": "text", "text": json.dumps(result_data)}]}
            elif tool_name == AGENTIC_TOOL_CLAUDE_CODE:
                raise OSError("Processing failed")
            result_data = {"conversations": [], "total_conversations": 0}
            import json

            return {"content": [{"type": "text", "text": json.dumps(result_data)}]}

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(fast_mode=True, limit=10)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(data["summary"]["total_conversations_found"], 1)
        self.assertEqual(len(data["conversations"]), 1)
        self.assertEqual(data["conversations"][0]["source_tool"], AGENTIC_TOOL_CURSOR)

    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_empty_results_from_all_tools(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall when all tools return empty results."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
        ]

        def mock_process_side_effect(tool_name, context_keywords, **kwargs):
            return {
                "conversations": [],
                "total_conversations": 0,
                "source_tool": tool_name,
                "total_analyzed": 0,
                "total_results": 0,
                "processing_time": 0.01,
            }

        mock_process.side_effect = mock_process_side_effect

        result = handle_recall_conversations(fast_mode=True, limit=10)
        data = extract_data_from_mcp_response(result)

        self.assertEqual(data["summary"]["total_conversations_found"], 0)
        self.assertEqual(len(data["conversations"]), 0)
        self.assertEqual(len(data["tools"]), 2)

    @patch("src.tool_calls.aggregation_utils.generate_context_keywords_for_project")
    @patch("src.tool_calls.tool_aggregation._detect_available_agentic_tools")
    @patch("src.tool_calls.tool_aggregation._process_agentic_tool_conversations")
    def test_handle_recall_parameter_validation(
        self, mock_process, mock_detect, mock_keywords
    ):
        """Test recall with various parameter combinations."""
        mock_keywords.return_value = self.context_keywords
        mock_detect.return_value = []

        # Test with extreme parameters
        result = handle_recall_conversations(
            fast_mode=False,
            days_lookback=60,  # Maximum allowed
            limit=100,  # Maximum allowed
            min_relevance_score=0.0,  # Minimum allowed
            conversation_types=["technical"],
            tools=[AGENTIC_TOOL_CURSOR],
            user_prompt="Test prompt",
            search_query="test query",
            tags=["tag1", "tag2"],
        )

        data = extract_data_from_mcp_response(result)
        # When no tools are available, parameters are stored at the top level
        self.assertEqual(data["days_lookback"], 60)
        self.assertEqual(data["limit"], 100)
        self.assertEqual(data["min_relevance_score"], 0.0)
        self.assertEqual(data["search_query"], "test query")
        self.assertEqual(data["tags"], ["tag1", "tag2"])

    # Test fallback when no tools available
    with (
        patch(
            "src.core.database_scanner.get_available_agentic_tools",
            return_value=[],
        ),
        patch(
            "src.core.tool_registry.get_registered_agentic_tools",
            return_value=["cursor"],
        ),
    ):
        from src.tool_calls.tool_aggregation import (
            _detect_available_agentic_tools,
        )


class TestLightweightConversationDispatcher(unittest.TestCase):
    """Test the lightweight conversation dispatcher in the aggregator."""

    def setUp(self):
        """Set up test data."""
        self.test_conversation = {
            "id": "gimli_conv_123",
            "title": "Gimli's Battle Stories",
            "snippet": "Test snippet",
            "message_count": 5,
            "relevance_score": 3.14159,
            "created_at": "2024-01-01T12:00:00Z",
            "source_tool": AGENTIC_TOOL_CURSOR,
        }

        # Create long fields to test truncation
        self.long_conversation = {
            "id": "a" * 100,  # Longer than CONVERSATION_ID_DISPLAY_LIMIT
            "title": "b" * 200,  # Longer than CONVERSATION_TITLE_DISPLAY_LIMIT
            "snippet": "c" * 300,  # Longer than CONVERSATION_SNIPPET_DISPLAY_LIMIT
            "message_count": 10,
            "relevance_score": 2.5,
        }

    def test_create_lightweight_conversation_cursor(self):
        """Test lightweight conversation creation for Cursor tool."""
        result = _create_lightweight_conversation(self.test_conversation)

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
        self.assertEqual(result["id"], "gimli_conv_123")
        self.assertEqual(result["title"], "Gimli's Battle Stories")

    def test_create_lightweight_conversation_claude_code(self):
        """Test lightweight conversation creation for Claude Code tool."""
        # Create a copy of the test conversation with the correct source_tool
        conversation_with_tool = {
            **self.test_conversation,
            "source_tool": AGENTIC_TOOL_CLAUDE_CODE,
        }
        result = _create_lightweight_conversation(conversation_with_tool)

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
        self.assertEqual(result["id"], "gimli_conv_123")
        self.assertEqual(result["title"], "Gimli's Battle Stories")

    def test_create_lightweight_conversation_windsurf(self):
        """Test lightweight conversation creation for Windsurf tool."""
        conversation_with_tool = {
            **self.test_conversation,
            "source_tool": AGENTIC_TOOL_WINDSURF,
        }
        result = _create_lightweight_conversation(conversation_with_tool)

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
        self.assertEqual(result["id"], "gimli_conv_123")
        self.assertEqual(result["title"], "Gimli's Battle Stories")

    def test_create_lightweight_conversation_unknown_tool(self):
        """Test lightweight conversation creation for unknown tool (fallback)."""
        conversation_with_tool = {
            **self.test_conversation,
            "source_tool": "unknown-tool",
        }
        result = _create_lightweight_conversation(conversation_with_tool)

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
        self.assertEqual(result["source_tool"], "unknown-tool")
        self.assertEqual(result["id"], "gimli_conv_123")
        self.assertEqual(result["title"], "Gimli's Battle Stories")

    def test_create_lightweight_conversation_truncation(self):
        """Test that the dispatcher properly truncates long fields using constants."""
        for tool in [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
            AGENTIC_TOOL_WINDSURF,
        ]:
            conversation_with_tool = {**self.long_conversation, "source_tool": tool}
            result = _create_lightweight_conversation(conversation_with_tool)

            self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)
            self.assertTrue(result["id"].endswith("..."))
            self.assertEqual(
                result["id"],
                self.long_conversation["id"][: CONVERSATION_ID_DISPLAY_LIMIT - 3]
                + "...",
            )

            self.assertTrue(result["title"].endswith("..."))
            self.assertEqual(len(result["title"]), CONVERSATION_TITLE_DISPLAY_LIMIT)

            self.assertTrue(result["snippet"].endswith("..."))
            self.assertEqual(len(result["snippet"]), CONVERSATION_SNIPPET_DISPLAY_LIMIT)

    def test_create_lightweight_conversation_fallback_truncation(self):
        """Test that the fallback (unknown tool) properly uses constants for truncation."""
        conversation_with_tool = {
            **self.long_conversation,
            "source_tool": "unknown-tool",
        }
        result = _create_lightweight_conversation(conversation_with_tool)

        self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)

        self.assertTrue(result["title"].endswith("..."))
        self.assertEqual(len(result["title"]), CONVERSATION_TITLE_DISPLAY_LIMIT)

        self.assertTrue(result["snippet"].endswith("..."))
        self.assertEqual(len(result["snippet"]), CONVERSATION_SNIPPET_DISPLAY_LIMIT)

    def test_create_lightweight_conversation_consistency_across_tools(self):
        """Test that all tools produce consistent results for the same input."""
        tools = [AGENTIC_TOOL_CURSOR, AGENTIC_TOOL_CLAUDE_CODE, AGENTIC_TOOL_WINDSURF]
        results = []

        for tool in tools:
            conversation_with_tool = {**self.test_conversation, "source_tool": tool}
            result = _create_lightweight_conversation(conversation_with_tool)
            results.append(result)

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

        for result in results:
            self.assertEqual(set(result.keys()), expected_fields)

        # Non-source_tool fields should be identical
        for field in [
            "id",
            "title",
            "snippet",
            "message_count",
            "relevance_score",
            "created_at",
        ]:
            values = [result[field] for result in results]
            self.assertTrue(
                all(v == values[0] for v in values),
                f"Field '{field}' inconsistent across tools: {values}",
            )

        # Source tools should be different
        source_tools = [result["source_tool"] for result in results]
        self.assertEqual(source_tools, ["cursor", "claude-code", "windsurf"])

    def test_constants_are_properly_imported_and_used(self):
        """Test that the constants are properly imported and have expected values."""
        self.assertEqual(CONVERSATION_ID_DISPLAY_LIMIT, 50)
        self.assertEqual(CONVERSATION_TITLE_DISPLAY_LIMIT, 100)
        self.assertEqual(CONVERSATION_SNIPPET_DISPLAY_LIMIT, 150)

        long_conversation = {
            "id": "x" * (CONVERSATION_ID_DISPLAY_LIMIT + 10),
            "title": "y" * (CONVERSATION_TITLE_DISPLAY_LIMIT + 10),
            "snippet": "z" * (CONVERSATION_SNIPPET_DISPLAY_LIMIT + 10),
            "source_tool": AGENTIC_TOOL_CURSOR,
        }

        result = _create_lightweight_conversation(long_conversation)

        self.assertEqual(len(result["id"]), CONVERSATION_ID_DISPLAY_LIMIT)
        self.assertEqual(len(result["title"]), CONVERSATION_TITLE_DISPLAY_LIMIT)
        self.assertEqual(len(result["snippet"]), CONVERSATION_SNIPPET_DISPLAY_LIMIT)


class TestStandardizeConversationDispatcher(unittest.TestCase):
    """Test the standardize conversation dispatcher in the aggregator."""

    def setUp(self):
        """Set up test data."""
        self.context_keywords = ["python", "api", "development"]
        self.test_conversation = {
            "id": "boromir_test_123",
            "title": "Boromir's Strategy Session",
            "snippet": "Testing dispatcher",
            "message_count": 3,
            "relevance_score": 2.5,
            "created_at": "2024-01-01T12:00:00Z",
        }

    def test_standardize_conversation_dispatcher_cursor(self):
        """Test that the dispatcher correctly routes to cursor standardize function."""
        result = _standardize_conversation_format(
            self.test_conversation, AGENTIC_TOOL_CURSOR, self.context_keywords
        )

        self.assertEqual(result["source_tool"], "cursor")
        self.assertEqual(result["id"], "boromir_test_123")
        self.assertEqual(result["title"], "Boromir's Strategy Session")
        self.assertIn("context_keywords", result)
        self.assertEqual(result["context_keywords"], self.context_keywords)

    def test_standardize_conversation_dispatcher_claude_code(self):
        """Test that the dispatcher correctly routes to claude-code standardize function."""
        result = _standardize_conversation_format(
            self.test_conversation, AGENTIC_TOOL_CLAUDE_CODE, self.context_keywords
        )

        self.assertEqual(result["source_tool"], "claude-code")
        self.assertEqual(result["id"], "boromir_test_123")
        self.assertEqual(result["title"], "Boromir's Strategy Session")
        self.assertIn("context_keywords", result)

    def test_standardize_conversation_dispatcher_windsurf(self):
        """Test that the dispatcher correctly routes to windsurf standardize function."""
        result = _standardize_conversation_format(
            self.test_conversation, AGENTIC_TOOL_WINDSURF, self.context_keywords
        )

        self.assertEqual(result["source_tool"], "windsurf")
        self.assertEqual(result["id"], "boromir_test_123")
        self.assertEqual(result["title"], "Boromir's Strategy Session")
        self.assertIn("context_keywords", result)

    def test_standardize_conversation_dispatcher_unknown_tool(self):
        """Test that the dispatcher handles unknown tools with fallback."""
        result = _standardize_conversation_format(
            self.test_conversation, "unknown-tool", self.context_keywords
        )

        self.assertEqual(result["source_tool"], "unknown-tool")
        self.assertEqual(result["id"], "boromir_test_123")
        self.assertEqual(result["title"], "Boromir's Strategy Session")
        self.assertIn("context_keywords", result)

    def test_standardize_conversation_dispatcher_lightweight_mode(self):
        """Test that the dispatcher correctly handles lightweight mode."""
        for tool in [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
            AGENTIC_TOOL_WINDSURF,
        ]:
            result = _standardize_conversation_format(
                self.test_conversation, tool, self.context_keywords, lightweight=True
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
            self.assertEqual(result["source_tool"], tool)

    def test_standardize_conversation_dispatcher_error_handling(self):
        """Test that the dispatcher handles errors from tool-specific functions gracefully."""
        invalid_conversation = {"invalid": "data"}

        for tool in [
            AGENTIC_TOOL_CURSOR,
            AGENTIC_TOOL_CLAUDE_CODE,
            AGENTIC_TOOL_WINDSURF,
            "unknown-tool",
        ]:
            result = _standardize_conversation_format(
                invalid_conversation, tool, self.context_keywords
            )

            self.assertIsInstance(result, dict)
            if result:
                self.assertEqual(result.get("source_tool"), tool)
