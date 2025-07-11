"""
Tests for Claude Code recall tool functionality.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from src.core.conversation_analysis import (
    analyze_session_relevance,
    generate_shared_context_keywords,
)
from src.tool_calls.claude_code.recall import (
    handle_recall_claude_conversations,
)


class TestClaudeCodeContextKeywords:
    """Test Claude Code context keyword generation using shared functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_context_keywords_basic(self):
        """Test basic context keyword generation."""
        keywords = generate_shared_context_keywords(self.project_root)

        assert "test-project" in keywords
        assert len(keywords) >= 1

    def test_get_context_keywords_with_package_json(self):
        """Test context keyword generation with package.json."""
        package_json = {
            "name": "my-awesome-app",
            "keywords": ["javascript", "web", "api"],
        }

        package_file = self.project_root / "package.json"
        package_file.write_text(json.dumps(package_json))

        keywords = generate_shared_context_keywords(self.project_root)

        assert "my-awesome-app" in keywords
        assert "javascript" in keywords
        assert "web" in keywords
        assert "api" in keywords

    def test_get_context_keywords_with_readme(self):
        """Test context keyword generation with README.md."""
        readme_content = """
        # My Project

        This is a Python project using Django and React.
        It also uses Docker for containerization.
        """

        readme_file = self.project_root / "README.md"
        readme_file.write_text(readme_content)

        keywords = generate_shared_context_keywords(self.project_root)

        assert "python" in keywords
        assert "django" in keywords
        assert "react" in keywords
        assert "docker" in keywords

    def test_get_context_keywords_with_claude_md(self):
        """Test context keyword generation with CLAUDE.md."""
        claude_content = """
        # Claude Instructions

        This project uses TypeScript and Express.
        We also use Kubernetes for deployment.
        """

        claude_file = self.project_root / "CLAUDE.md"
        claude_file.write_text(claude_content)

        keywords = generate_shared_context_keywords(self.project_root)

        assert "typescript" in keywords
        assert "express" in keywords
        assert "kubernetes" in keywords

    def test_get_context_keywords_with_pyproject_toml(self):
        """Test context keyword generation with pyproject.toml."""
        pyproject_content = """
        [tool.poetry]
        name = "my-python-project"
        version = "0.1.0"
        """

        pyproject_file = self.project_root / "pyproject.toml"
        pyproject_file.write_text(pyproject_content)

        keywords = generate_shared_context_keywords(self.project_root)

        assert "test-project" in keywords  # Project directory name always included

    def test_get_context_keywords_invalid_json(self):
        """Test context keyword generation with invalid JSON."""
        package_file = self.project_root / "package.json"
        package_file.write_text("invalid json content")

        # Should not raise exception
        keywords = generate_shared_context_keywords(self.project_root)
        assert "test-project" in keywords

    def test_get_context_keywords_file_read_error(self):
        """Test context keyword generation with file read error."""
        with patch("pathlib.Path.read_text", side_effect=OSError("Permission denied")):
            keywords = generate_shared_context_keywords(self.project_root)
            assert "test-project" in keywords

    def test_get_context_keywords_limit(self):
        """Test that context keywords are limited to reasonable number."""
        # Create a README with many tech terms
        many_terms = " ".join(
            [
                "python",
                "javascript",
                "typescript",
                "react",
                "vue",
                "angular",
                "node",
                "express",
                "django",
                "flask",
                "fastapi",
                "docker",
                "kubernetes",
                "aws",
                "gcp",
                "azure",
                "postgresql",
                "mongodb",
                "redis",
                "elasticsearch",
                "nginx",
            ]
        )

        readme_file = self.project_root / "README.md"
        readme_file.write_text(f"# Project\n\n{many_terms}")

        keywords = generate_shared_context_keywords(self.project_root)

        # Should be limited to reasonable number
        assert len(keywords) <= 30


class TestClaudeCodeSessionRelevance:
    """Test Claude Code session relevance analysis using shared functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir(parents=True)
        self.context_keywords = ["python", "django", "test-project"]

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_session_metadata(self, start_time: str = None) -> dict:
        """Create test session metadata."""
        if start_time is None:
            start_time = datetime.now().isoformat()

        return {
            "session_id": "test-session",
            "start_time": start_time,
            "cwd": str(self.project_root),
            "version": "1.0.0",
        }

    def test_analyze_session_relevance_basic(self):
        """Test basic session relevance analysis."""
        content = "Hello, this is a basic conversation"
        metadata = self.create_test_session_metadata()

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert score >= 0.0
        assert analysis["conversation_type"] == "general"

    def test_analyze_session_relevance_with_keywords(self):
        """Test session relevance analysis with keyword matches."""
        content = "I need help with Python programming and Django development"
        metadata = self.create_test_session_metadata()

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert score > 0.0
        assert "python" in analysis["keyword_matches"]
        assert "django" in analysis["keyword_matches"]

    def test_analyze_session_relevance_debugging_type(self):
        """Test session relevance analysis for debugging conversation."""
        content = "I have a bug in my code that needs to be fixed"
        metadata = self.create_test_session_metadata()

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert analysis["conversation_type"] == "debugging"
        assert score > 0.0  # Debugging gets bonus points

    def test_analyze_session_relevance_testing_type(self):
        """Test session relevance analysis for testing conversation."""
        content = "How do I write unit tests with pytest for this project?"
        metadata = self.create_test_session_metadata()

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert analysis["conversation_type"] == "testing"

    def test_analyze_session_relevance_architecture_type(self):
        """Test session relevance analysis for architecture conversation."""
        content = "Let's refactor the architecture and improve the design patterns"
        metadata = self.create_test_session_metadata()

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert analysis["conversation_type"] == "architecture"

    def test_analyze_session_relevance_recency_score(self):
        """Test session relevance analysis with recency scoring."""
        # Recent session (1 hour ago)
        recent_time = (datetime.now() - timedelta(hours=1)).isoformat()
        content = "Recent message"
        metadata = self.create_test_session_metadata(recent_time)

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert analysis["recency_score"] == 1.0  # Should be max for recent

        # Old session (2 months ago)
        old_time = (datetime.now() - timedelta(days=60)).isoformat()
        metadata = self.create_test_session_metadata(old_time)

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert (
            analysis["recency_score"] == 0.2
        )  # Should be low for old (90-day threshold)

    def test_analyze_session_relevance_empty_content(self):
        """Test session relevance analysis with empty content."""
        content = ""
        metadata = self.create_test_session_metadata()

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert score == 0.0

    def test_analyze_session_relevance_invalid_timestamp(self):
        """Test session relevance analysis with invalid timestamp."""
        content = "Test message"
        metadata = self.create_test_session_metadata("invalid-timestamp")

        # Should not raise exception
        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert score >= 0.0
        assert analysis["recency_score"] == 0.0

    def test_analyze_session_relevance_exception_handling(self):
        """Test session relevance analysis exception handling."""
        content = "Test content"
        # Malformed metadata
        metadata = {"invalid": "data"}

        score, analysis = analyze_session_relevance(
            content, self.context_keywords, metadata
        )

        assert score >= 0.0


class TestClaudeCodeRecallHandlers:
    """Test Claude Code recall handler functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.project_root = self.temp_dir / "test-project"
        self.project_root.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("src.core.conversation_analysis.generate_shared_context_keywords")
    @patch("src.tool_calls.claude_code.recall.ClaudeCodeQuery")
    def test_handle_recall_claude_conversations_success(
        self, mock_query_class, mock_keywords
    ):
        """Test successful conversation recall handler."""
        # Mock context keywords
        mock_keywords.return_value = ["python", "test"]

        # Mock query tool
        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.return_value = {
            "conversations": [
                {
                    "messages": [{"content": "Python code", "role": "user"}],
                    "session_metadata": {
                        "session_id": "test-1",
                        "start_time": datetime.now().isoformat(),
                        "cwd": str(self.project_root),
                    },
                    "last_modified": datetime.now().isoformat(),
                }
            ],
            "claude_home": "/test/claude",
        }

        arguments = {"fast_mode": True, "days_lookback": 7, "limit": 20}

        with patch(
            "src.core.conversation_analysis.analyze_session_relevance"
        ) as mock_analyze:
            mock_analyze.return_value = (
                2.5,
                {
                    "keyword_matches": ["python"],
                    "file_references": [],
                    "recency_score": 1.0,
                    "conversation_type": "general",
                },
            )

            result = handle_recall_claude_conversations(arguments, self.project_root)

        assert "isError" not in result
        data = json.loads(result["content"][0]["text"])
        assert "conversations" in data
        assert data["fast_mode"] is True
        assert len(data["context_keywords"]) > 0

    @patch("src.core.conversation_analysis.generate_shared_context_keywords")
    @patch("src.tool_calls.claude_code.recall.ClaudeCodeQuery")
    def test_handle_recall_claude_conversations_no_conversations(
        self, mock_query_class, mock_keywords
    ):
        """Test conversation recall handler with no conversations."""
        mock_keywords.return_value = ["python"]

        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.return_value = {"conversations": []}

        arguments = {"fast_mode": True}
        result = handle_recall_claude_conversations(arguments, self.project_root)

        assert "isError" not in result
        data = json.loads(result["content"][0]["text"])
        assert data["conversations"] == []
        assert data["total_analyzed"] == 0

    @patch("src.core.conversation_analysis.generate_shared_context_keywords")
    @patch("src.tool_calls.claude_code.recall.ClaudeCodeQuery")
    def test_handle_recall_claude_conversations_with_filters(
        self, mock_query_class, mock_keywords
    ):
        """Test conversation recall handler with type filters."""
        mock_keywords.return_value = ["python"]

        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.return_value = {
            "conversations": [
                {
                    "messages": [{"content": "Debug this error", "role": "user"}],
                    "session_metadata": {
                        "session_id": "debug-session",
                        "start_time": datetime.now().isoformat(),
                        "cwd": str(self.project_root),
                    },
                    "last_modified": datetime.now().isoformat(),
                }
            ],
            "claude_home": "/test/claude",
        }

        arguments = {"conversation_types": ["debugging"], "min_score": 1.0}

        with patch(
            "src.core.conversation_analysis.analyze_session_relevance"
        ) as mock_analyze:
            mock_analyze.return_value = (
                2.0,
                {
                    "keyword_matches": [],
                    "file_references": [],
                    "recency_score": 1.0,
                    "conversation_type": "debugging",
                },
            )

            result = handle_recall_claude_conversations(arguments, self.project_root)

        assert "isError" not in result
        data = json.loads(result["content"][0]["text"])
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["conversation_type"] == "debugging"

    @patch("src.tool_calls.claude_code.recall.ClaudeCodeQuery")
    @patch("src.core.conversation_analysis.generate_shared_context_keywords")
    def test_handle_recall_claude_conversations_exception(
        self, mock_keywords, mock_query_class
    ):
        """Test conversation recall handler with exception."""
        mock_keywords.return_value = ["test-project"]

        # Mock the query tool to raise an exception when called
        mock_query = Mock()
        mock_query_class.return_value = mock_query
        mock_query.query_conversations.side_effect = OSError("Test error")

        arguments = {"fast_mode": True}
        result = handle_recall_claude_conversations(arguments, self.project_root)

        assert "isError" in result
        assert "Error recalling Claude Code conversations" in result["error"]
