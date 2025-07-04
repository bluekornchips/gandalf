"""Test Windsurf query functionality."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.tool_calls.windsurf_query import (
    WindsurfQuery,
    handle_query_windsurf_conversations,
    handle_search_windsurf_conversations,
)


class TestWindsurfQuery:
    """Test Windsurf query functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_workspace_storage = Path("/test/windsurf/workspaceStorage")
        self.test_db_path = (
            self.test_workspace_storage / "rivendell_workspace" / "state.vscdb"
        )

        self.sample_chat_sessions = {
            "entries": {
                "frodo_ring_quest": {
                    "id": "frodo_ring_quest",
                    "title": "The Ring Bearer's Burden",
                    "messages": [
                        {
                            "role": "user",
                            "content": "All we have to decide is what to do with the time that is given us. How do I destroy the One Ring?",
                        },
                        {
                            "role": "assistant",
                            "content": "The Ring must be taken deep into Mordor and cast back into the fiery chasm from whence it came. I will take the Ring to Mordor, though I do not know the way.",
                        },
                    ],
                    "timestamp": "2024-01-01T10:00:00Z",
                },
                "gandalf_wisdom": {
                    "id": "gandalf_wisdom",
                    "title": "A Wizard's Counsel",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Even the very wise cannot see all ends. What about the Balrog in Moria?",
                        },
                        {
                            "role": "assistant",
                            "content": "You shall not pass! This foe is beyond any of you. Run! Fly, you fools!",
                        },
                    ],
                    "timestamp": "2024-01-01T11:00:00Z",
                },
                "aragorn_leadership": {
                    "id": "aragorn_leadership",
                    "title": "The Return of the King",
                    "messages": [
                        {
                            "role": "user",
                            "content": "A day may come when the courage of men fails, but how do I lead?",
                        },
                        {
                            "role": "assistant",
                            "content": "I am Aragorn, son of Arathorn. The hands of the king are the hands of a healer. You bow to no one.",
                        },
                    ],
                    "timestamp": "2024-01-01T12:00:00Z",
                },
                "sam_loyalty": {
                    "id": "sam_loyalty",
                    "title": "The Gardener's Devotion",
                    "messages": [
                        {
                            "role": "user",
                            "content": "There's some good in this world, Mr. Frodo. How do I help my friend?",
                        },
                        {
                            "role": "assistant",
                            "content": "I can't carry it for you, but I can carry you! Share and enjoy, Mr. Frodo.",
                        },
                    ],
                    "timestamp": "2024-01-01T13:00:00Z",
                },
            }
        }

    def test_windsurf_query_initialization(self):
        """Test WindsurfQuery initialization."""
        query = WindsurfQuery(silent=True)
        assert query.silent is True
        assert query.workspace_storage is not None

    @patch("src.tool_calls.windsurf_query.WINDSURF_WORKSPACE_STORAGE")
    def test_find_workspace_databases(self, mock_workspace_storage):
        """Test finding workspace databases."""
        mock_workspace_storage.exists.return_value = True
        mock_workspace_storage.iterdir.return_value = [
            MagicMock(
                is_dir=lambda: True,
                __truediv__=lambda self, other: MagicMock(exists=lambda: True),
            )
        ]

        query = WindsurfQuery(silent=True)
        query.workspace_storage = mock_workspace_storage

        with patch.object(Path, "iterdir") as mock_iterdir:
            mock_workspace_dir = MagicMock()
            mock_workspace_dir.is_dir.return_value = True
            mock_db_file = MagicMock()
            mock_db_file.exists.return_value = True
            mock_workspace_dir.__truediv__.return_value = mock_db_file
            mock_iterdir.return_value = [mock_workspace_dir]

            databases = query.find_workspace_databases()
            assert isinstance(databases, list)

    def test_get_data_from_db_success(self):
        """Test successful data extraction from database."""
        query = WindsurfQuery(silent=True)
        test_data = {"elrond": "The Ring must be destroyed"}

        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [json.dumps(test_data)]
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            result = query.get_data_from_db(self.test_db_path, "rivendell.council")
            assert result == test_data

    def test_get_data_from_db_no_result(self):
        """Test data extraction when no result found."""
        query = WindsurfQuery(silent=True)

        with patch("sqlite3.connect") as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = None
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value.__enter__.return_value = mock_conn

            result = query.get_data_from_db(self.test_db_path, "isengard.secrets")
            assert result is None

    def test_get_data_from_db_error_handling(self):
        """Test error handling in database operations."""
        query = WindsurfQuery(silent=True)

        with patch("sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.Error("Database corrupted")

            result = query.get_data_from_db(self.test_db_path, "moria.depths")
            assert result is None

    def test_query_conversations_from_db_with_chat_sessions(self):
        """Test querying conversations with chat session data."""
        query = WindsurfQuery(silent=True)

        with patch.object(query, "get_data_from_db") as mock_get_data:

            def mock_get_data_side_effect(db_path, key):
                if key == "chat.ChatSessionStore.index":
                    return self.sample_chat_sessions
                return None

            mock_get_data.side_effect = mock_get_data_side_effect

            result = query.query_conversations_from_db(self.test_db_path)

            assert "conversations" in result
            assert len(result["conversations"]) == 4
            assert result["total_conversations"] == 4
            assert str(self.test_db_path) in result["database_path"]

    def test_query_conversations_from_db_with_windsurf_conversations(self):
        """Test querying conversations with windsurf-specific data."""
        query = WindsurfQuery(silent=True)
        windsurf_convs = [
            {
                "id": "treebeard_counsel",
                "content": "I am on nobody's side, because nobody is on my side",
            },
            {"id": "ent_moot", "content": "Don't be hasty! This is an Ent-draught"},
        ]

        with patch.object(query, "get_data_from_db") as mock_get_data, patch.object(
            query.db_reader, "get_all_keys"
        ) as mock_get_all_keys:

            def mock_get_data_side_effect(db_path, key):
                if key == "windsurf.conversations":
                    return windsurf_convs
                return None

            mock_get_data.side_effect = mock_get_data_side_effect
            mock_get_all_keys.return_value = ["windsurf.conversations"]

            result = query.query_conversations_from_db(self.test_db_path)

            assert "conversations" in result
            assert len(result["conversations"]) == 2
            assert result["conversations"][0]["id"] == "treebeard_counsel"

    def test_query_conversations_from_db_with_cascade_data(self):
        """Test querying conversations with cascade state data."""
        query = WindsurfQuery(silent=True)
        cascade_data = {
            "conversations": [
                {
                    "id": "dead_men_oath",
                    "content": "The dead do not suffer the living to pass",
                },
                {
                    "id": "king_summons",
                    "content": "What say you? Will you follow the king?",
                },
            ]
        }

        with patch.object(query, "get_data_from_db") as mock_get_data, patch.object(
            query.db_reader, "get_all_keys"
        ) as mock_get_all_keys:

            def mock_get_data_side_effect(db_path, key):
                if key == "windsurf.cascadeViewContainerId.state":
                    return cascade_data
                return None

            mock_get_data.side_effect = mock_get_data_side_effect
            mock_get_all_keys.return_value = ["windsurf.cascadeViewContainerId.state"]

            result = query.query_conversations_from_db(self.test_db_path)

            assert "conversations" in result
            assert len(result["conversations"]) == 2
            assert result["conversations"][0]["id"] == "dead_men_oath"

    def test_query_all_conversations(self):
        """Test querying all conversations from multiple databases."""
        query = WindsurfQuery(silent=True)

        with patch.object(
            query, "_find_workspace_databases"
        ) as mock_find_dbs, patch.object(
            query, "query_conversations_from_db"
        ) as mock_query_db:

            mock_find_dbs.return_value = [self.test_db_path]
            mock_query_db.return_value = {
                "conversations": [
                    {
                        "id": "legolas_archery",
                        "content": "That still only counts as one!",
                    }
                ],
                "total_conversations": 1,
            }

            result = query.query_all_conversations()

            assert "conversations" in result
            assert result["total_conversations"] == 1
            assert result["total_databases"] == 1
            assert "query_timestamp" in result

    def test_search_conversations(self):
        """Test searching conversations for specific content."""
        query = WindsurfQuery(silent=True)

        mock_conversations = [
            {
                "id": "galadriel_mirror",
                "session_data": {
                    "content": "I give you the light of Eärendil, our most beloved star"
                },
                "title": "The Mirror of Galadriel",
            },
            {
                "id": "boromir_temptation",
                "session_data": {"content": "One does not simply walk into Mordor"},
                "title": "The Temptation of the Ring",
            },
            {
                "id": "gimli_friendship",
                "session_data": {
                    "content": "Never thought I'd die fighting side by side with an Elf"
                },
                "title": "An Unlikely Friendship",
            },
        ]

        with patch.object(query, "query_all_conversations") as mock_query_all:
            mock_query_all.return_value = {
                "conversations": mock_conversations,
                "total_conversations": 3,
            }

            results = query.search_conversations("light", limit=10)

            assert len(results) == 1
            assert results[0]["conversation"]["id"] == "galadriel_mirror"
            assert results[0]["match_count"] >= 1

    def test_search_conversations_multiple_matches(self):
        """Test searching conversations with multiple matches."""
        query = WindsurfQuery(silent=True)

        mock_conversations = [
            {
                "id": "theoden_speech",
                "title": "Arise, Riders of Théoden",
                "content": "Ride now! Ride now! Ride for ruin and the world's ending!",
                "messages": [
                    "Forth Eorlingas! Death! Ride to ruin and the world's ending!"
                ],
            }
        ]

        with patch.object(query, "query_all_conversations") as mock_query_all:
            mock_query_all.return_value = {
                "conversations": mock_conversations,
                "total_conversations": 1,
            }

            results = query.search_conversations("ride", limit=10)

            assert len(results) == 1
            assert results[0]["match_count"] >= 3

    def test_search_conversations_limit(self):
        """Test search conversation limit functionality."""
        query = WindsurfQuery(silent=True)

        mock_conversations = [
            {
                "id": f"gondor_soldier_{i}",
                "title": f"For Gondor {i}",
                "content": "Gondor calls for aid",
            }
            for i in range(5)
        ]

        with patch.object(query, "query_all_conversations") as mock_query_all:
            mock_query_all.return_value = {
                "conversations": mock_conversations,
                "total_conversations": 5,
            }

            results = query.search_conversations("Gondor", limit=3)

            assert len(results) == 3


class TestWindsurfQueryHandlers:
    """Test Windsurf query handler functions."""

    def test_handle_query_windsurf_conversations_json_format(self):
        """Test querying conversations in JSON format."""
        arguments = {"format": "json", "summary": False, "limit": 10}
        project_root = Path("/test/minas_tirith")

        mock_data = {
            "conversations": [
                {"id": "elrond_council", "title": "The Council of Elrond"}
            ],
            "total_conversations": 1,
            "total_databases": 1,
        }

        with patch("src.tool_calls.windsurf_query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = mock_data

            result = handle_query_windsurf_conversations(arguments, project_root)

            assert "content" in result
            assert len(result["content"]) > 0

            content_text = result["content"][0]["text"]
            parsed_data = json.loads(content_text)
            assert "conversations" in parsed_data

    def test_handle_query_windsurf_conversations_markdown_format(self):
        """Test querying conversations in Markdown format."""
        arguments = {"format": "markdown", "limit": 5}
        project_root = Path("/test/grey_havens")

        mock_data = {
            "conversations": [
                {
                    "id": "frodo_departure",
                    "workspace_id": "shire_workspace",
                    "source": "windsurf_chat_session",
                    "session_data": {
                        "content": "I will diminish, and go into the West"
                    },
                }
            ],
            "total_conversations": 1,
        }

        with patch("src.tool_calls.windsurf_query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = mock_data

            result = handle_query_windsurf_conversations(arguments, project_root)

            assert "content" in result
            content_text = result["content"][0]["text"]
            assert "# Windsurf Conversations" in content_text
            assert "## Conversation 1" in content_text

    def test_handle_query_windsurf_conversations_invalid_format(self):
        """Test querying conversations with invalid format."""
        arguments = {"format": "sauron_script"}
        project_root = Path("/test/isengard")

        result = handle_query_windsurf_conversations(arguments, project_root)

        assert "content" in result or "isError" in result

    def test_handle_query_windsurf_conversations_with_limit(self):
        """Test querying conversations with limit applied."""
        arguments = {"format": "json", "limit": 2}
        project_root = Path("/test/helms_deep")

        mock_conversations = [
            {"id": f"defender_{i}", "title": f"Defense Strategy {i}"} for i in range(5)
        ]
        mock_data = {"conversations": mock_conversations, "total_conversations": 5}

        with patch("src.tool_calls.windsurf_query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = mock_data

            result = handle_query_windsurf_conversations(arguments, project_root)

            content_text = result["content"][0]["text"]
            parsed_data = json.loads(content_text)

            assert len(parsed_data["conversations"]) == 2
            assert parsed_data["limited_results"] is True
            assert parsed_data["limit_applied"] == 2

    def test_handle_search_windsurf_conversations_basic(self):
        """Test basic conversation search functionality."""
        arguments = {"query": "Rohan", "limit": 10, "include_content": False}
        project_root = Path("/test/edoras")

        mock_search_results = [
            {
                "conversation": {
                    "id": "theoden_restoration",
                    "workspace_id": "rohan_workspace",
                    "source": "windsurf_chat_session",
                },
                "matches": [
                    {"type": "title", "content": "The King of Rohan rides again"}
                ],
                "match_count": 1,
            }
        ]

        with patch("src.tool_calls.windsurf_query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.search_conversations.return_value = mock_search_results

            result = handle_search_windsurf_conversations(arguments, project_root)

            assert "content" in result
            content_text = result["content"][0]["text"]
            parsed_data = json.loads(content_text)

            assert parsed_data["query"] == "Rohan"
            assert len(parsed_data["conversations"]) == 1
            assert parsed_data["total_results"] == 1

    def test_handle_search_windsurf_conversations_with_content(self):
        """Test conversation search with full content included."""
        arguments = {"query": "Galadriel", "include_content": True}
        project_root = Path("/test/lothlorien")

        mock_search_results = [
            {
                "conversation": {
                    "id": "lady_galadriel",
                    "workspace_id": "lorien_workspace",
                },
                "matches": [
                    {
                        "type": "content",
                        "content": "Even the smallest person can change the course of the future",
                    }
                ],
                "match_count": 1,
            }
        ]

        with patch("src.tool_calls.windsurf_query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.search_conversations.return_value = mock_search_results

            result = handle_search_windsurf_conversations(arguments, project_root)

            content_text = result["content"][0]["text"]
            parsed_data = json.loads(content_text)

            match = parsed_data["conversations"][0]["matches"][0]
            assert "full_content" in match

    def test_handle_search_windsurf_conversations_no_query(self):
        """Test conversation search without query parameter."""
        arguments = {"limit": 10}
        project_root = Path("/test/shire")

        result = handle_search_windsurf_conversations(arguments, project_root)

        assert "content" in result or "isError" in result

    def test_handle_search_windsurf_conversations_empty_results(self):
        """Test conversation search with no matching results."""
        arguments = {"query": "dragon_treasure", "limit": 10}
        project_root = Path("/test/erebor")

        with patch("src.tool_calls.windsurf_query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.search_conversations.return_value = []

            result = handle_search_windsurf_conversations(arguments, project_root)

            content_text = result["content"][0]["text"]
            parsed_data = json.loads(content_text)

            assert parsed_data["total_results"] == 0
            assert len(parsed_data["conversations"]) == 0

    @patch("src.tool_calls.windsurf_query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_exception(self, mock_query_class):
        """Test conversation querying handler with exception."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.side_effect = ValueError("Test error")
        project_root = Path("/test/project")

        arguments = {"format": "json"}
        result = handle_query_windsurf_conversations(arguments, project_root)

        assert result["isError"] is True
        assert "Error querying Windsurf conversations" in result["error"]

    @patch("src.tool_calls.windsurf_query.WindsurfQuery")
    def test_handle_search_windsurf_conversations_error_handling(
        self, mock_query_class
    ):
        """Test error handling in search conversations."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.search_conversations.side_effect = ValueError(
            "Database connection failed"
        )
        project_root = Path("/test/project")

        arguments = {"query": "balrog"}
        result = handle_search_windsurf_conversations(arguments, project_root)

        assert result["isError"] is True
        assert "Error searching Windsurf conversations" in result["error"]
