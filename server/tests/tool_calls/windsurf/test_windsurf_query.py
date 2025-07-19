"""
Tests for Windsurf query functionality.
"""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from src.config.constants.conversation import (
    CONVERSATION_FALSE_POSITIVE_RATIO_THRESHOLD,
    CONVERSATION_MAX_ANALYSIS_LENGTH,
    CONVERSATION_MAX_LIST_ITEMS_TO_CHECK,
    CONVERSATION_MIN_CONTENT_LENGTH,
)
from src.config.constants.database import (
    WINDSURF_KEY_CHAT_SESSION_STORE,
)
from src.config.constants.windsurf import (
    WINDSURF_CONTENT_KEYS,
    WINDSURF_CONVERSATION_PATTERNS,
    WINDSURF_FALSE_POSITIVE_INDICATORS,
    WINDSURF_MESSAGE_INDICATORS,
    WINDSURF_STRONG_CONVERSATION_INDICATORS,
)
from src.tool_calls.windsurf.query import (
    TOOL_QUERY_WINDSURF_CONVERSATIONS,
    ConversationExtractor,
    ConversationValidator,
    DatabaseReader,
    WindsurfQuery,
    _format_response,
    handle_query_windsurf_conversations,
)


class TestWindsurfQuery:
    """Test Windsurf query functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "project"
        self.project_root.mkdir()

    def teardown_method(self):
        """Clean up test fixtures and database connections."""
        import gc
        import shutil
        import sqlite3

        try:
            # Force immediate garbage collection
            for _ in range(5):
                gc.collect()

            # Close any SQLite connections found in garbage collector
            for obj in gc.get_objects():
                if isinstance(obj, sqlite3.Connection):
                    try:
                        if not obj.in_transaction:
                            obj.close()
                    except Exception:
                        pass

            # Force another round of garbage collection
            for _ in range(3):
                gc.collect()

        except Exception:
            # Ignore cleanup errors but ensure directory cleanup happens
            pass

        # Clean up test directory
        if hasattr(self, "temp_dir") and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_mock_database(self, conversations=None):
        """Create a mock database for testing."""
        if conversations is None:
            conversations = [
                {
                    "id": "conv1",
                    "title": "Test conversation",
                    "content": "How to implement feature X?",
                    "timestamp": "2024-01-01T10:00:00Z",
                }
            ]

        db_path = self.temp_dir / "test.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()

            # Create ItemTable structure like Windsurf uses
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            # Insert chat session data
            chat_data = {
                "entries": {
                    "session1": {
                        "messages": [
                            {"content": "Hello", "user": "human"},
                            {"content": "Hi there!", "user": "assistant"},
                        ],
                        "text": "This is a conversation about coding",
                    }
                }
            }

            cursor.execute(
                """
                INSERT INTO ItemTable (key, value)
                VALUES (?, ?)
            """,
                (WINDSURF_KEY_CHAT_SESSION_STORE, json.dumps(chat_data)),
            )

            conn.commit()

        return db_path

    def test_windsurf_query_initialization(self):
        """Test WindsurfQuery initialization."""
        query = WindsurfQuery()
        assert query is not None
        assert hasattr(query, "query_all_conversations")
        assert hasattr(query, "search_conversations")
        assert hasattr(query, "silent")
        assert hasattr(query, "workspace_storage")
        assert hasattr(query, "global_storage")
        assert hasattr(query, "db_reader")
        assert hasattr(query, "validator")
        assert hasattr(query, "extractor")

    def test_windsurf_query_initialization_silent(self):
        """Test WindsurfQuery initialization with silent mode."""
        query = WindsurfQuery(silent=True)
        assert query.silent is True
        assert query.db_reader.silent is True

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_basic(self, mock_query_class):
        """Test basic query handling."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [
                {
                    "id": "test1",
                    "title": "Test conversation",
                    "content": "Sample content",
                }
            ],
            "total": 1,
        }

        arguments = {"format": "json"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert "content" in result
        assert len(result["content"]) > 0
        mock_instance.query_all_conversations.assert_called_once()

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_with_summary(self, mock_query_class):
        """Test query handling with summary format."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [{"id": "test1", "title": "Test"}],
            "total": 1,
        }

        arguments = {"format": "json", "summary": True}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert "content" in result
        mock_instance.query_all_conversations.assert_called_once()

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_windsurf_conversations_exception(self, mock_query_class):
        """Test query handling with exception."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.side_effect = ValueError("Test error")

        arguments = {"format": "json"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert result["isError"] is True
        assert "Error querying Windsurf conversations" in result["content"][0]["text"]

    def test_handle_query_invalid_format(self):
        """Test query handling with invalid format."""
        arguments = {"format": "invalid"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)

        assert result["isError"] is True
        assert "format must be one of" in result["content"][0]["text"]

    def test_windsurf_query_search_conversations_method(self):
        """Test the search_conversations method exists and can be called."""
        query = WindsurfQuery()

        # Mock the internal methods to avoid actual database operations
        with patch.object(query, "_find_workspace_databases", return_value=[]):
            result = query.search_conversations(query="test", limit=10)

            # Should return a list
            assert isinstance(result, list)

    def test_windsurf_query_query_all_conversations_method(self):
        """Test the query_all_conversations method exists and can be called."""
        query = WindsurfQuery()

        # Mock the internal methods to avoid actual database operations
        with patch.object(query, "_find_workspace_databases", return_value=[]):
            result = query.query_all_conversations()

            # Should return a dictionary with expected structure
            assert isinstance(result, dict)

    def test_tool_definition_structure(self):
        """Test that the tool definition has the correct structure."""
        tool = TOOL_QUERY_WINDSURF_CONVERSATIONS

        assert tool["name"] == "query_windsurf_conversations"
        assert "description" in tool
        assert "inputSchema" in tool
        assert "properties" in tool["inputSchema"]
        assert "format" in tool["inputSchema"]["properties"]

    @patch("src.tool_calls.windsurf.query.WindsurfQuery")
    def test_handle_query_with_different_formats(self, mock_query_class):
        """Test query handling with different output formats."""
        mock_instance = Mock()
        mock_query_class.return_value = mock_instance
        mock_instance.query_all_conversations.return_value = {
            "conversations": [{"id": "test1"}],
            "total": 1,
        }

        # Test markdown format
        arguments = {"format": "markdown"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)
        assert "content" in result

        # Test windsurf format
        arguments = {"format": "windsurf"}
        result = handle_query_windsurf_conversations(arguments, self.project_root)
        assert "content" in result

    def test_windsurf_query_with_mock_database_operations(self):
        """Test WindsurfQuery with mocked database operations."""
        query = WindsurfQuery()

        # Mock database finding to return our test database
        mock_db_path = self.create_mock_database()

        with patch.object(
            query, "_find_workspace_databases", return_value=[mock_db_path]
        ):
            result = query.query_all_conversations()
            assert isinstance(result, dict)
            assert "conversations" in result

    def test_windsurf_query_error_handling(self):
        """Test WindsurfQuery error handling."""
        query = WindsurfQuery()

        # Test with invalid database path
        with patch.object(
            query,
            "_find_workspace_databases",
            return_value=[Path("/nonexistent/path")],
        ):
            result = query.query_all_conversations()
            # Should handle errors gracefully
            assert isinstance(result, dict)

    def test_windsurf_query_get_data_from_db(self):
        """Test get_data_from_db method."""
        query = WindsurfQuery()
        mock_db_path = self.create_mock_database()

        # Test successful data retrieval
        result = query.get_data_from_db(mock_db_path, WINDSURF_KEY_CHAT_SESSION_STORE)
        assert result is not None
        assert isinstance(result, dict)
        assert "entries" in result

    def test_windsurf_query_get_data_from_db_error(self):
        """Test get_data_from_db method with error."""
        query = WindsurfQuery()

        # Test with nonexistent database
        result = query.get_data_from_db(Path("/nonexistent/path"), "test_key")
        assert result is None

    def test_windsurf_query_find_workspace_databases(self):
        """Test find_workspace_databases method."""
        query = WindsurfQuery()

        # Mock the storage paths to avoid accessing real system
        with patch.object(query, "workspace_storage", self.temp_dir):
            with patch.object(query, "global_storage", self.temp_dir):
                # Create mock workspace structure
                workspace_dir = self.temp_dir / "workspace1"
                workspace_dir.mkdir()
                db_file = workspace_dir / "state.vscdb"
                db_file.write_text("mock db")

                # Create global db
                global_db = self.temp_dir / "state.vscdb"
                global_db.write_text("mock global db")

                databases = query.find_workspace_databases()
                assert len(databases) >= 1

    def test_windsurf_query_search_conversations_with_data(self):
        """Test search_conversations with actual data."""
        query = WindsurfQuery()

        # Mock query_all_conversations to return test data
        test_conversations = [
            {
                "id": "conv1",
                "session_data": {"messages": [{"content": "python programming"}]},
                "title": "Python Help",
                "content": "How to use python?",
            },
            {
                "id": "conv2",
                "session_data": {"messages": [{"content": "javascript coding"}]},
                "title": "JS Help",
                "content": "How to use javascript?",
            },
        ]

        with patch.object(query, "query_all_conversations") as mock_query:
            mock_query.return_value = {"conversations": test_conversations}

            # Search for "python"
            results = query.search_conversations("python", limit=10)
            assert len(results) == 1
            assert results[0]["conversation"]["id"] == "conv1"

    def test_windsurf_query_query_conversations_from_db(self):
        """Test query_conversations_from_db method."""
        query = WindsurfQuery()
        mock_db_path = self.create_mock_database()

        result = query.query_conversations_from_db(mock_db_path)
        assert isinstance(result, dict)
        assert "conversations" in result
        assert "total_conversations" in result
        assert "database_path" in result

    def test_format_response_json(self):
        """Test _format_response with JSON format."""
        data = {
            "conversations": [{"id": "test1", "workspace_id": "ws1", "source": "test"}]
        }

        result = _format_response(data, "json")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "conversations" in parsed

    def test_format_response_markdown(self):
        """Test _format_response with markdown format."""
        data = {
            "conversations": [
                {
                    "id": "test1",
                    "workspace_id": "ws1",
                    "source": "test",
                    "session_data": {"content": "test content"},
                }
            ]
        }

        result = _format_response(data, "markdown")
        assert isinstance(result, str)
        assert "# Windsurf Conversations" in result
        assert "## Conversation 1" in result

    def test_format_response_windsurf(self):
        """Test _format_response with windsurf format."""
        data = {"conversations": [{"id": "test1"}]}

        result = _format_response(data, "windsurf")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "conversations" in parsed

    def test_handle_query_with_limit(self):
        """Test query handling with limit parameter."""
        with patch("src.tool_calls.windsurf.query.WindsurfQuery") as mock_query_class:
            mock_instance = Mock()
            mock_query_class.return_value = mock_instance

            # Create more conversations than the limit
            conversations = [{"id": f"conv{i}"} for i in range(10)]
            mock_instance.query_all_conversations.return_value = {
                "conversations": conversations
            }

            arguments = {"format": "json", "limit": 5}
            result = handle_query_windsurf_conversations(arguments, self.project_root)

            assert "content" in result
            response_data = json.loads(result["content"][0]["text"])
            assert len(response_data["conversations"]) == 5
            assert response_data["limited_results"] is True
            assert response_data["limit_applied"] == 5


class TestConversationValidator:
    """Test ConversationValidator class."""

    def test_is_valid_conversation_dict_with_content(self):
        """Test validation of dictionary with valid content."""
        data = {
            "messages": [
                {"content": "Hello, how can I help?", "user": "assistant"},
                {"content": "I need help with Python", "user": "human"},
            ],
            "text": "This is a conversation about programming",
        }

        assert ConversationValidator.is_valid_conversation(data) is True

    def test_is_valid_conversation_list_with_messages(self):
        """Test validation of list with message-like items."""
        data = [
            {"content": "First message", "message": "test"},
            {"content": "Second message", "user": "assistant"},
        ]

        assert ConversationValidator.is_valid_conversation(data) is True

    def test_is_valid_conversation_no_strong_indicators(self):
        """Test validation fails when no strong indicators present."""
        data = {"setting": "value", "config": "option"}

        assert ConversationValidator.is_valid_conversation(data) is False

    def test_is_valid_conversation_too_many_false_positives(self):
        """Test validation fails with too many false positive indicators."""
        data = {
            "messages": "test",  # Has one strong indicator
            "workbench": "test",
            "panel": "test",
            "view": "test",
            "container": "test",
            "storage": "test",
            "settings": "test",  # Many false positive indicators
        }

        assert ConversationValidator.is_valid_conversation(data) is False

    def test_is_valid_conversation_invalid_types(self):
        """Test validation with invalid data types."""
        assert ConversationValidator.is_valid_conversation("string") is False
        assert ConversationValidator.is_valid_conversation(123) is False
        assert ConversationValidator.is_valid_conversation(None) is False

    def test_validate_dict_structure_with_content(self):
        """Test _validate_dict_structure with valid content."""
        data = {"content": "This is meaningful content with enough length"}
        assert ConversationValidator._validate_dict_structure(data) is True

    def test_validate_dict_structure_with_list_content(self):
        """Test _validate_dict_structure with list content."""
        data = {"messages": [{"text": "message"}]}
        assert ConversationValidator._validate_dict_structure(data) is True

    def test_validate_dict_structure_no_content_keys(self):
        """Test _validate_dict_structure without content keys."""
        data = {"setting": "value", "option": "test"}
        assert ConversationValidator._validate_dict_structure(data) is False

    def test_validate_dict_structure_short_content(self):
        """Test _validate_dict_structure with too short content."""
        data = {"content": "hi"}  # Too short
        assert ConversationValidator._validate_dict_structure(data) is False

    def test_validate_list_structure_with_messages(self):
        """Test _validate_list_structure with message-like items."""
        data = [
            {"content": "test message", "message": "indicator"},
            {"text": "another message", "conversation": "indicator"},
        ]
        assert ConversationValidator._validate_list_structure(data) is True

    def test_validate_list_structure_empty_list(self):
        """Test _validate_list_structure with empty list."""
        assert ConversationValidator._validate_list_structure([]) is False

    def test_validate_list_structure_no_message_indicators(self):
        """Test _validate_list_structure without message indicators."""
        data = [{"setting": "value"}, {"config": "option"}]
        assert ConversationValidator._validate_list_structure(data) is False

    def test_validate_structure_delegates_correctly(self):
        """Test _validate_structure delegates to correct methods."""
        # Test dict delegation
        dict_data = {"messages": "test"}
        with patch.object(
            ConversationValidator,
            "_validate_dict_structure",
            return_value=True,
        ) as mock_dict:
            result = ConversationValidator._validate_structure(dict_data)
            assert result is True
            mock_dict.assert_called_once_with(dict_data)

        # Test list delegation
        list_data = [{"messages": "test"}]
        with patch.object(
            ConversationValidator,
            "_validate_list_structure",
            return_value=True,
        ) as mock_list:
            result = ConversationValidator._validate_structure(list_data)
            assert result is True
            mock_list.assert_called_once_with(list_data)

        # Test invalid type
        assert ConversationValidator._validate_structure("string") is False


class TestDatabaseReader:
    """Test DatabaseReader class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_reader = DatabaseReader(silent=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_database(self):
        """Create a test database with ItemTable structure."""
        db_path = self.temp_dir / "test.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            # Insert test data
            test_data = [
                ("test_key", json.dumps({"content": "test value"})),
                ("chat.session", json.dumps({"messages": ["hello"]})),
                (
                    "conversation.data",
                    json.dumps({"text": "conversation content"}),
                ),
            ]

            cursor.executemany(
                "INSERT INTO ItemTable (key, value) VALUES (?, ?)", test_data
            )
            conn.commit()

        return db_path

    def test_database_reader_init(self):
        """Test DatabaseReader initialization."""
        reader = DatabaseReader()
        assert reader.silent is False

        reader_silent = DatabaseReader(silent=True)
        assert reader_silent.silent is True

    def test_get_data_success(self):
        """Test successful data retrieval."""
        db_path = self.create_test_database()

        result = self.db_reader.get_data(db_path, "test_key")
        assert result is not None
        assert isinstance(result, dict)
        assert result["content"] == "test value"

    def test_get_data_key_not_found(self):
        """Test data retrieval with non-existent key."""
        db_path = self.create_test_database()

        result = self.db_reader.get_data(db_path, "nonexistent_key")
        assert result is None

    def test_get_data_database_error(self):
        """Test data retrieval with database error."""
        result = self.db_reader.get_data(Path("/nonexistent/path"), "test_key")
        assert result is None

    def test_get_data_json_decode_error(self):
        """Test data retrieval with JSON decode error."""
        db_path = self.temp_dir / "bad_json.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )
            cursor.execute(
                "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                ("bad_key", "invalid json"),
            )
            conn.commit()

        result = self.db_reader.get_data(db_path, "bad_key")
        assert result is None

    def test_get_all_keys_success(self):
        """Test successful key retrieval."""
        db_path = self.create_test_database()

        keys = self.db_reader.get_all_keys(db_path)
        assert isinstance(keys, list)
        assert len(keys) == 3
        assert "test_key" in keys
        assert "chat.session" in keys
        assert "conversation.data" in keys

    def test_get_all_keys_database_error(self):
        """Test key retrieval with database error."""
        keys = self.db_reader.get_all_keys(Path("/nonexistent/path"))
        assert keys == []

    def test_find_conversation_keys(self):
        """Test finding conversation-related keys."""
        db_path = self.create_test_database()

        conv_keys = self.db_reader.find_conversation_keys(db_path)
        assert isinstance(conv_keys, list)
        assert "chat.session" in conv_keys
        assert "conversation.data" in conv_keys
        assert "test_key" not in conv_keys  # Should not match conversation patterns


class TestConversationExtractor:
    """Test ConversationExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_reader = DatabaseReader(silent=True)
        self.validator = ConversationValidator()
        self.extractor = ConversationExtractor(self.db_reader, self.validator)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_database_with_chat_sessions(self):
        """Create test database with chat session data."""
        db_path = self.temp_dir / "chat_test.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            chat_data = {
                "entries": {
                    "session1": {
                        "messages": [
                            {"content": "Hello", "user": "human"},
                            {"content": "Hi there!", "user": "assistant"},
                        ],
                        "text": "conversation content",
                    },
                    "session2": {
                        "messages": [
                            {"content": "How to code?", "user": "human"},
                            {"content": "Here's how...", "user": "assistant"},
                        ],
                        "text": "coding help conversation",
                    },
                }
            }

            cursor.execute(
                "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                (WINDSURF_KEY_CHAT_SESSION_STORE, json.dumps(chat_data)),
            )
            conn.commit()

        return db_path

    def test_extractor_init(self):
        """Test ConversationExtractor initialization."""
        extractor = ConversationExtractor(self.db_reader, self.validator)
        assert extractor.db_reader == self.db_reader
        assert extractor.validator == self.validator
        assert extractor.query_instance is None

    def test_extractor_init_with_query_instance(self):
        """Test ConversationExtractor initialization with query instance."""
        mock_query = Mock()
        extractor = ConversationExtractor(self.db_reader, self.validator, mock_query)
        assert extractor.query_instance == mock_query

    def test_extract_from_chat_sessions_success(self):
        """Test successful extraction from chat sessions."""
        db_path = self.create_test_database_with_chat_sessions()

        conversations = self.extractor.extract_from_chat_sessions(db_path)
        assert isinstance(conversations, list)
        assert len(conversations) == 2

        # Check first conversation
        conv1 = conversations[0]
        assert conv1["id"] == "session1"
        assert conv1["source"] == "windsurf_chat_session"
        assert "session_data" in conv1

    def test_extract_from_chat_sessions_no_data(self):
        """Test extraction when no chat session data exists."""
        db_path = self.temp_dir / "empty.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )
            conn.commit()

        conversations = self.extractor.extract_from_chat_sessions(db_path)
        assert conversations == []

    def test_extract_from_chat_sessions_with_query_instance(self):
        """Test extraction using query instance."""
        db_path = self.create_test_database_with_chat_sessions()
        mock_query = Mock()
        mock_query.get_data_from_db.return_value = {
            "entries": {
                "test_session": {
                    "messages": [{"content": "test message"}],
                    "text": "test conversation",
                }
            }
        }

        extractor = ConversationExtractor(self.db_reader, self.validator, mock_query)
        conversations = extractor.extract_from_chat_sessions(db_path)

        assert len(conversations) == 1
        mock_query.get_data_from_db.assert_called_once_with(
            db_path, WINDSURF_KEY_CHAT_SESSION_STORE
        )

    def test_extract_from_database_keys(self):
        """Test extraction from database keys."""
        db_path = self.temp_dir / "keys_test.db"
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """
            )

            # Add conversation-like data
            conv_data = {
                "content": "This is a conversation about programming",
                "messages": [{"text": "Hello"}],
            }

            cursor.execute(
                "INSERT INTO ItemTable (key, value) VALUES (?, ?)",
                ("conversation.test", json.dumps(conv_data)),
            )
            conn.commit()

        conversations = self.extractor.extract_from_database_keys(db_path)
        assert isinstance(conversations, list)

    def test_extract_from_data_structure_dict(self):
        """Test extraction from dictionary data structure."""
        data = {
            "entries": {
                "conv1": {
                    "messages": [{"content": "test message"}],
                    "text": "conversation content",
                }
            }
        }

        conversations = self.extractor._extract_from_data_structure(
            "test_key", data, Path("test")
        )
        assert len(conversations) == 1
        assert conversations[0]["id"] == "conv1"

    def test_extract_from_data_structure_list(self):
        """Test extraction from list data structure."""
        data = [
            {
                "id": "conv1",
                "content": "conversation content",
                "messages": [{"text": "hello"}],
            }
        ]

        conversations = self.extractor._extract_from_data_structure(
            "test_key", data, Path("test")
        )
        assert len(conversations) == 1
        assert conversations[0]["id"] == "conv1"

    def test_extract_from_data_structure_error_handling(self):
        """Test extraction with errors in data structure."""
        # Test with data that will cause errors
        invalid_data = {"invalid": None}

        # Should handle errors gracefully
        conversations = self.extractor._extract_from_data_structure(
            "test_key", invalid_data, Path("test")
        )
        assert isinstance(conversations, list)

    def test_extract_from_dict_entries_pattern(self):
        """Test extraction from dict with entries pattern."""
        data = {
            "entries": {
                "entry1": {
                    "content": "meaningful conversation content",
                    "messages": [{"text": "hello"}],
                }
            }
        }

        conversations = self.extractor._extract_from_dict(
            "test_key", data, Path("test")
        )
        assert len(conversations) == 1
        assert conversations[0]["source"] == "windsurf_db_entry"

    def test_extract_from_dict_direct_conversation(self):
        """Test extraction from dict as direct conversation."""
        data = {
            "content": "This is meaningful conversation content",
            "messages": [{"text": "hello"}],
        }

        conversations = self.extractor._extract_from_dict(
            "test_key", data, Path("test")
        )
        assert len(conversations) == 1
        assert conversations[0]["source"] == "windsurf_db_direct"

    def test_extract_from_dict_nested_data(self):
        """Test extraction from nested dict data."""
        data = {
            "conversations": [
                {
                    "content": "conversation content",
                    "messages": [{"text": "hello"}],
                }
            ],
            "session_data": {
                "content": "session conversation content",
                "messages": [{"text": "session message"}],
            },
        }

        conversations = self.extractor._extract_from_dict(
            "test_key", data, Path("test")
        )
        assert len(conversations) >= 1

    def test_extract_from_list(self):
        """Test extraction from list data."""
        data = [
            {
                "id": "conv1",
                "content": "conversation content",
                "messages": [{"text": "hello"}],
            },
            {
                "content": "another conversation",
                "messages": [{"text": "world"}],
            },
        ]

        conversations = self.extractor._extract_from_list(
            "test_key", data, Path("test")
        )
        assert len(conversations) == 2
        assert conversations[0]["id"] == "conv1"
        assert conversations[1]["id"] == "test_key_1"

    def test_create_conversation_entry(self):
        """Test conversation entry creation."""
        data = {"content": "test content"}

        entry = self.extractor._create_conversation_entry(
            "test_id",
            data,
            "test_source",
            Path("/test/path"),
            extra_field="extra_value",
        )

        assert entry["id"] == "test_id"
        assert entry["source"] == "test_source"
        assert entry["data"] == data
        assert entry["database_path"] == "/test/path"
        assert entry["workspace_id"] == "test"
        assert entry["extra_field"] == "extra_value"

    def test_create_conversation_entry_chat_session(self):
        """Test conversation entry creation for chat session."""
        data = {"messages": [{"content": "test"}]}

        entry = self.extractor._create_conversation_entry(
            "session_id", data, "windsurf_chat_session", Path("/test/path")
        )

        assert entry["session_data"] == data
        assert entry["source"] == "windsurf_chat_session"


class TestWindsurfQueryMethods:
    """Test additional WindsurfQuery methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.query = WindsurfQuery(silent=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_db_response(self):
        """Test _create_db_response method."""
        conversations = [
            {"id": "conv1", "content": "test"},
            {"id": "conv2", "content": "test2"},
        ]

        # Mock the get_data call for chat sessions
        with patch.object(self.query.db_reader, "get_data") as mock_get_data:
            mock_get_data.return_value = {"entries": {"session1": {}}}

            response = self.query._create_db_response(conversations, Path("/test/path"))

            assert response["conversations"] == conversations
            assert response["total_conversations"] == 2
            assert response["database_path"] == "/test/path"
            assert "query_timestamp" in response
            assert response["has_chat_sessions"] is True
            assert response["chat_session_empty"] is False

    def test_create_db_response_empty_chat_sessions(self):
        """Test _create_db_response with empty chat sessions."""
        conversations = []

        with patch.object(self.query.db_reader, "get_data") as mock_get_data:
            mock_get_data.return_value = {"entries": {}}

            response = self.query._create_db_response(conversations, Path("/test/path"))

            assert response["has_chat_sessions"] is False
            assert response["chat_session_empty"] is True

    def test_search_in_conversations(self):
        """Test _search_in_conversations method."""
        conversations = [
            {
                "id": "conv1",
                "session_data": {"messages": [{"content": "python programming"}]},
                "title": "Python Help",
            },
            {
                "id": "conv2",
                "session_data": {"messages": [{"content": "javascript coding"}]},
                "title": "JS Help",
            },
        ]

        results = self.query._search_in_conversations(conversations, "python", 10)
        assert len(results) == 1
        assert results[0]["conversation"]["id"] == "conv1"
        assert results[0]["match_count"] > 0

    def test_find_matches_in_conversation(self):
        """Test _find_matches_in_conversation method."""
        conv = {
            "id": "test_conv",
            "session_data": {"messages": [{"content": "python programming help"}]},
            "title": "Python Tutorial",
            "content": "Learn python basics",
        }

        matches = self.query._find_matches_in_conversation(conv, "python")
        assert len(matches) >= 2  # Should find in session_data and title/content

    def test_search_in_field_string(self):
        """Test _search_in_field with string field."""
        matches = self.query._search_in_field("python programming", "title", "python")
        assert len(matches) == 1
        assert matches[0]["type"] == "title"

    def test_search_in_field_dict(self):
        """Test _search_in_field with dict field."""
        field_value = {"messages": [{"content": "python help"}]}
        matches = self.query._search_in_field(field_value, "messages", "python")
        assert len(matches) == 1
        assert matches[0]["type"] == "messages"

    def test_search_in_field_no_match(self):
        """Test _search_in_field with no matches."""
        matches = self.query._search_in_field("javascript code", "content", "python")
        assert len(matches) == 0

    def test_truncate_content(self):
        """Test _truncate_content static method."""
        short_content = "short"
        result = WindsurfQuery._truncate_content(short_content, 10)
        assert result == "short"

        long_content = "a" * 100
        result = WindsurfQuery._truncate_content(long_content, 10)
        assert result == "a" * 10 + "..."
        assert len(result) == 13

    def test_find_workspace_databases_permission_error(self):
        """Test _find_workspace_databases with permission errors."""
        # Mock paths that will cause permission errors
        with patch.object(self.query, "workspace_storage", self.temp_dir):
            with patch.object(self.query, "global_storage", self.temp_dir):
                # Mock iterdir to raise PermissionError
                with patch.object(
                    Path,
                    "iterdir",
                    side_effect=PermissionError("Access denied"),
                ):
                    databases = self.query._find_workspace_databases()
                    # Should handle error gracefully and return empty list
                    assert isinstance(databases, list)


class TestConstants:
    """Test module constants."""

    def test_constants_exist(self):
        """Test that all required constants are defined."""
        assert WINDSURF_KEY_CHAT_SESSION_STORE is not None
        assert isinstance(WINDSURF_CONVERSATION_PATTERNS, set)
        assert isinstance(WINDSURF_STRONG_CONVERSATION_INDICATORS, set)
        assert isinstance(WINDSURF_FALSE_POSITIVE_INDICATORS, set)
        assert isinstance(WINDSURF_CONTENT_KEYS, set)
        assert isinstance(WINDSURF_MESSAGE_INDICATORS, set)

    def test_constant_values(self):
        """Test that constants have reasonable values."""
        assert CONVERSATION_MIN_CONTENT_LENGTH > 0
        assert CONVERSATION_MAX_ANALYSIS_LENGTH > CONVERSATION_MIN_CONTENT_LENGTH
        assert CONVERSATION_FALSE_POSITIVE_RATIO_THRESHOLD > 0
        assert CONVERSATION_MAX_LIST_ITEMS_TO_CHECK > 0

    def test_pattern_sets_not_empty(self):
        """Test that pattern sets are not empty."""
        assert len(WINDSURF_CONVERSATION_PATTERNS) > 0
        assert len(WINDSURF_STRONG_CONVERSATION_INDICATORS) > 0
        assert len(WINDSURF_FALSE_POSITIVE_INDICATORS) > 0
        assert len(WINDSURF_CONTENT_KEYS) > 0
        assert len(WINDSURF_MESSAGE_INDICATORS) > 0
