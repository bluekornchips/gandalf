"""
Tests for Claude Code query tool functionality.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.claude_code.query import (
    ClaudeCodeQuery,
    handle_query_claude_conversations,
)


class TestClaudeCodeQuery:
    """Test Claude Code query functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.claude_home = self.temp_dir / ".claude"
        self.projects_dir = self.claude_home / "projects"
        self.sessions_dir = self.claude_home / "sessions"

        # Create directory structure
        self.projects_dir.mkdir(parents=True)
        self.sessions_dir.mkdir(parents=True)

        # Create test project
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir()

        # Create encoded project directory
        self.encoded_project = str(self.project_root).replace("/", "-")
        self.project_sessions_dir = self.projects_dir / self.encoded_project
        self.project_sessions_dir.mkdir()

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

    def create_test_session_file(
        self, session_dir: Path, session_id: str, messages: list
    ) -> Path:
        """Create a test session file with given messages."""
        session_file = session_dir / f"{session_id}.jsonl"

        with open(session_file, "w") as f:
            for i, message in enumerate(messages):
                line_data = {
                    "type": message.get("type", "user"),
                    "message": {
                        "role": message.get("role", "user"),
                        "content": message.get("content", ""),
                    },
                    "timestamp": message.get("timestamp", datetime.now().isoformat()),
                    "sessionId": session_id,
                    "cwd": str(self.project_root),
                    "version": "1.0.0",
                    "parentUuid": f"parent-{i}",
                }
                f.write(json.dumps(line_data) + "\n")

        return session_file

    @patch.dict("os.environ", {"CLAUDE_HOME": ""})
    def test_get_claude_home_default(self):
        """Test getting Claude home directory with default location."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = self.temp_dir

            query = ClaudeCodeQuery()
            self.temp_dir / ".claude"

            # Since we're mocking, we need to check the logic
            assert query.claude_home.name == ".claude"

    def test_get_claude_home_environment(self):
        """Test getting Claude home directory from environment variable."""
        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()
            assert query.claude_home == self.claude_home

    def test_find_session_files_with_project(self):
        """Test finding session files for a specific project."""
        # Create test session files
        session1 = self.create_test_session_file(
            self.project_sessions_dir,
            "session-1",
            [{"content": "Hello", "role": "user"}],
        )
        session2 = self.create_test_session_file(
            self.project_sessions_dir,
            "session-2",
            [{"content": "World", "role": "assistant"}],
        )

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            session_files = query.find_session_files(self.project_root)

            assert len(session_files) == 2
            assert session1 in session_files
            assert session2 in session_files

    def test_find_session_files_without_project(self):
        """Test finding session files without specifying a project."""
        # Create test session file in global sessions directory
        session_file = self.create_test_session_file(
            self.sessions_dir,
            "global-session",
            [{"content": "Global message", "role": "user"}],
        )

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            session_files = query.find_session_files()

            assert len(session_files) == 1
            assert session_file in session_files

    def test_parse_session_file_valid(self):
        """Test parsing a valid session file."""
        messages = [
            {"content": "Hello", "role": "user", "type": "user"},
            {"content": "Hi there!", "role": "assistant", "type": "assistant"},
        ]

        session_file = self.create_test_session_file(
            self.project_sessions_dir, "test-session", messages
        )

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            result = query.parse_session_file(session_file)

            assert result["file_path"] == str(session_file)
            assert result["message_count"] == 2
            assert len(result["messages"]) == 2
            assert result["session_metadata"]["session_id"] == "test-session"
            assert result["session_metadata"]["cwd"] == str(self.project_root)

    def test_parse_session_file_invalid_json(self):
        """Test parsing a session file with invalid JSON."""
        session_file = self.project_sessions_dir / "invalid.jsonl"

        with open(session_file, "w") as f:
            f.write("invalid json line\n")
            f.write('{"valid": "json"}\n')

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            result = query.parse_session_file(session_file)

            # Should handle invalid JSON gracefully
            assert result["message_count"] == 1  # Only valid line counted

    def test_parse_session_file_nonexistent(self):
        """Test parsing a non-existent session file."""
        nonexistent_file = self.project_sessions_dir / "nonexistent.jsonl"

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            result = query.parse_session_file(nonexistent_file)

            assert result == {}

    def test_query_conversations_success(self):
        """Test successful conversation querying."""
        # Create test session
        messages = [
            {"content": "Test message", "role": "user"},
            {"content": "Test response", "role": "assistant"},
        ]

        self.create_test_session_file(
            self.project_sessions_dir, "test-conversation", messages
        )

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            result = query.query_conversations(self.project_root)

            assert "conversations" in result
            assert len(result["conversations"]) == 1
            assert result["total_sessions"] == 1
            assert result["claude_home"] == str(self.claude_home)

    def test_query_conversations_no_sessions(self):
        """Test querying conversations when no sessions exist."""
        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            result = query.query_conversations(self.project_root)

            assert result["conversations"] == []
            assert result["total_sessions"] == 0

    def test_search_conversations_found(self):
        """Test searching conversations with matches."""
        messages = [
            {"content": "This is about Python programming", "role": "user"},
            {"content": "Python is a great language", "role": "assistant"},
        ]

        self.create_test_session_file(
            self.project_sessions_dir, "python-session", messages
        )

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            results = query.search_conversations("Python", self.project_root)

            assert len(results) == 1
            assert results[0]["match_count"] == 2  # Both messages contain "Python"

    def test_search_conversations_no_matches(self):
        """Test searching conversations with no matches."""
        messages = [
            {"content": "This is about JavaScript", "role": "user"},
            {"content": "JavaScript is also good", "role": "assistant"},
        ]

        self.create_test_session_file(self.project_sessions_dir, "js-session", messages)

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            results = query.search_conversations("Python", self.project_root)

            assert len(results) == 0

    def test_extract_snippet(self):
        """Test snippet extraction around query matches."""
        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()

            text = "This is a long text with the word Python in the middle of it"
            # Use the exact case as in the text since find() is case-sensitive
            snippet = query._extract_snippet(text, "Python", 20)

            assert "Python" in snippet
            assert len(snippet) <= 50  # Should be around context_chars * 2

    def test_format_as_markdown(self):
        """Test formatting conversation data as markdown."""
        data = {
            "query_timestamp": "2024-01-01T00:00:00",
            "total_sessions": 1,
            "claude_home": str(self.claude_home),
            "conversations": [
                {
                    "session_metadata": {
                        "session_id": "test-session",
                        "cwd": str(self.project_root),
                        "start_time": "2024-01-01T00:00:00",
                    },
                    "message_count": 2,
                    "last_modified": "2024-01-01T00:00:00",
                    "messages": [
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"},
                    ],
                }
            ],
        }

        with patch.object(
            ClaudeCodeQuery, "_get_claude_home", return_value=self.claude_home
        ):
            query = ClaudeCodeQuery()
            markdown = query.format_as_markdown(data)

            assert "# Claude Code Conversations" in markdown
            assert "test-session" in markdown
            assert "Hello" in markdown


class TestClaudeCodeQueryHandlers:
    """Test Claude Code query handler functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir(parents=True)

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

    def test_handle_query_claude_conversations_success(self, mock_query_class):
        """Test successful conversation querying handler."""
        # Mock the query tool
        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.return_value = {
            "conversations": [{"test": "data"}],
            "total_sessions": 1,
            "query_timestamp": "2024-01-01T00:00:00",
            "claude_home": "/test/claude",
        }

        arguments = {"format": "json", "summary": False, "limit": 50}
        result = handle_query_claude_conversations(arguments, self.project_root)

        # New MCP format uses content array instead of success field
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        content_text = result["content"][0]["text"]
        mcp_response = json.loads(content_text)
        data = json.loads(mcp_response["content"][0]["text"])
        assert "conversations" in data
        assert data["total_sessions"] == 1

    @patch("src.tool_calls.claude_code.query.ClaudeCodeQuery")
    def test_handle_query_claude_conversations_summary(self, mock_query_class):
        """Test conversation querying handler with summary mode."""
        # Mock the query tool
        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.return_value = {
            "conversations": [
                {
                    "message_count": 5,
                    "session_metadata": {"session_id": "test-1"},
                },
                {
                    "message_count": 3,
                    "session_metadata": {"session_id": "test-2"},
                },
            ],
            "total_sessions": 2,
            "query_timestamp": "2024-01-01T00:00:00",
            "claude_home": "/test/claude",
        }

        arguments = {"format": "json", "summary": True}
        result = handle_query_claude_conversations(arguments, self.project_root)

        # New MCP format uses content array instead of success field
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        content_text = result["content"][0]["text"]
        mcp_response = json.loads(content_text)
        data = json.loads(mcp_response["content"][0]["text"])
        assert data["total_conversations"] == 2
        assert data["total_messages"] == 8  # 5 + 3

    def test_handle_query_claude_conversations_invalid_format(self):
        """Test conversation querying handler with invalid format."""
        arguments = {"format": "invalid"}
        result = handle_query_claude_conversations(arguments, self.project_root)

        # New MCP format uses isError instead of success field
        assert result["isError"] is True
        assert "format must be one of" in result["error"]

    @patch("src.tool_calls.claude_code.query.ClaudeCodeQuery")
    def test_handle_query_claude_conversations_markdown(self, mock_query_class):
        """Test conversation querying handler with markdown format."""
        # Mock the query tool
        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.return_value = {"conversations": []}
        mock_query.format_as_markdown.return_value = "# Test Markdown"

        arguments = {"format": "markdown"}
        result = handle_query_claude_conversations(arguments, self.project_root)

        # Parse the nested MCP response
        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        content_text = result["content"][0]["text"]
        mcp_response = json.loads(content_text)
        actual_content = mcp_response["content"][0]["text"]
        assert actual_content == "# Test Markdown"

    @patch("src.tool_calls.claude_code.query.ClaudeCodeQuery")
    def test_handle_query_claude_conversations_exception(self, mock_query_class):
        """Test conversation querying handler with exception."""
        mock_query_class.side_effect = OSError("Test error")

        arguments = {"format": "json"}
        result = handle_query_claude_conversations(arguments, self.project_root)

        # New MCP format uses isError instead of success field
        assert result["isError"] is True
        assert "Error querying Claude Code conversations" in result["error"]
