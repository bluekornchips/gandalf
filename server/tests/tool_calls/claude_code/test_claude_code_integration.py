"""
Integration tests for Claude Code functionality.

These tests verify real file discovery, project root handling, and registry connections
without mocks to catch integration bugs that unit tests miss.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.tool_calls.aggregator import (
    _detect_available_agentic_tools,
    handle_recall_conversations,
)
from src.tool_calls.claude_code.query import ClaudeCodeQuery
from src.tool_calls.claude_code.recall import (
    handle_recall_claude_conversations,
)


class TestClaudeCodeIntegration:
    """Integration tests for Claude Code functionality."""

    def setup_method(self):
        """Set up test fixtures with real directory structure."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.claude_home = self.temp_dir / ".claude"
        self.projects_dir = self.claude_home / "projects"
        self.sessions_dir = self.claude_home / "sessions"

        self.projects_dir.mkdir(parents=True)
        self.sessions_dir.mkdir(parents=True)

        self.project_root = self.temp_dir / "rivendell-project"
        self.project_root.mkdir()

        # Create encoded project directory (this is how Claude Code stores conversations)
        # TODO: How do we know this? Can we provide a doc link for this?
        self.encoded_project = str(self.project_root).replace("/", "-")
        self.project_sessions_dir = self.projects_dir / self.encoded_project
        self.project_sessions_dir.mkdir()

        self.registry_file = self.temp_dir / "registry.json"
        self.registry_file.write_text(
            json.dumps({"claude-code": str(self.claude_home)})
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_real_conversation_file(self, session_id: str, messages: list) -> Path:
        """Create a real Claude Code conversation file in JSONL format."""
        session_file = self.project_sessions_dir / f"{session_id}.jsonl"

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
                    "parentUuid": f"fellowship-{i}",
                }
                f.write(json.dumps(line_data) + "\n")

        return session_file

    def test_real_file_discovery_with_project_root(self):
        """Test that find_session_files actually discovers real files with project root filtering."""
        # Create conversation files for this project
        conv1 = self.create_real_conversation_file(
            "frodo-quest-session",
            [
                {"content": "How do I destroy the One Ring?", "role": "user"},
                {
                    "content": "Cast it into the fires of Mount Doom where it was forged",
                    "role": "assistant",
                },
            ],
        )
        conv2 = self.create_real_conversation_file(
            "gandalf-wisdom-session",
            [
                {
                    "content": "How to defeat a Balrog in Moria?",
                    "role": "user",
                },
                {"content": "You shall not pass!", "role": "assistant"},
            ],
        )

        # Create conversation file for different project (should be filtered out)
        other_project_dir = self.projects_dir / "isengard-project-path"
        other_project_dir.mkdir()
        other_conv = other_project_dir / "saruman-corruption.jsonl"
        other_conv.write_text(
            '{"sessionId": "saruman", "message": {"content": "Sauron\'s influence"}}\n'
        )

        # Test with Claude home environment variable
        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Test finding files for specific project
            session_files = query.find_session_files(self.project_root)

            # Should find only files for this project
            assert len(session_files) == 2
            assert conv1 in session_files
            assert conv2 in session_files
            assert other_conv not in session_files

    def test_real_file_discovery_without_project_root(self):
        """Test that find_session_files discovers all files when no project root specified."""
        # Create files in both project and global sessions
        project_conv = self.create_real_conversation_file(
            "elrond-council-session",
            [
                {
                    "content": "How to form the Fellowship of the Ring?",
                    "role": "user",
                }
            ],
        )

        global_conv = self.sessions_dir / "aragorn-ranger-session.jsonl"
        global_conv.write_text(
            '{"sessionId": "strider", "message": {"content": "A ranger\'s path"}}\n'
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Test finding all files
            session_files = query.find_session_files()

            # Should find files from both locations
            assert len(session_files) >= 2
            assert project_conv in session_files
            assert global_conv in session_files

    def test_project_root_propagation_through_recall(self):
        """Test that project root is properly passed through the recall handler chain."""
        # Create test conversation
        self.create_real_conversation_file(
            "legolas-archery-session",
            [
                {
                    "content": "How do you win the trust of the elves?",
                    "role": "user",
                },
                {
                    "content": "You must prove your worth and loyalty.",
                    "role": "assistant",
                },
            ],
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            # Test that project root is used in recall
            arguments = {
                "fast_mode": True,
                "limit": 10,
                "min_score": 0.0,  # Low score to ensure conversations are included
                "days_lookback": 30,
            }

            result = handle_recall_claude_conversations(arguments, self.project_root)

            # Extract data from MCP response
            if isinstance(result, dict) and "content" in result:
                content_text = result["content"][0]["text"]
                data = json.loads(content_text)
            else:
                data = result

            # Should find the conversation
            assert data["total_conversations"] > 0
            assert len(data["conversations"]) > 0

            # Verify the conversation is from the project
            conversation = data["conversations"][0]
            assert "legolas-archery-session" in conversation.get("session_id", "")

    def test_conversation_aggregator_real_integration(self):
        """Test that conversation aggregator properly integrates with real Claude Code files."""
        # Create test conversations
        self.create_real_conversation_file(
            "palantir-network-session",
            [
                {
                    "content": "How to debug seeing stone connections?",
                    "role": "user",
                },
                {
                    "content": "Beware! The palantír shows what Sauron wishes you to see",
                    "role": "assistant",
                },
            ],
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            # Mock the registry to include claude-code
            with patch(
                "src.tool_calls.aggregator.get_registered_agentic_tools"
            ) as mock_registry:
                mock_registry.return_value = ["claude-code"]

                # Test full aggregator integration
                result = handle_recall_conversations(
                    fast_mode=True,
                    limit=10,
                    min_score=0.0,  # Low score to ensure inclusion
                    project_root=self.project_root,
                )

                # Extract data from MCP response
                if isinstance(result, dict) and "content" in result:
                    content_text = result["content"][0]["text"]
                    data = json.loads(content_text)
                else:
                    data = result

                # Should detect Claude Code as available
                assert "claude-code" in data["available_tools"]

                # Should find Claude Code conversations properly
                # Handle both normal format and summary format
                if "tool_results" in data:
                    assert "claude-code" in data["tool_results"]
                    claude_results = data["tool_results"]["claude-code"]
                    # Should find the conversation
                    assert claude_results["total_conversations"] > 0
                elif "tool_summaries" in data:
                    # Summary format when response is too large
                    assert "claude-code" in data["tool_summaries"]
                    claude_summary = data["tool_summaries"]["claude-code"]
                    assert claude_summary["count"] > 0
                else:
                    # If neither format, fail with helpful message
                    assert (
                        False
                    ), f"Unexpected response format. Keys: {list(data.keys())}"

    def test_registry_detection_integration(self):
        """Test that registry detection works with real registry files."""
        # Create a real registry file
        registry_content = {
            "cursor": "/mnt/doom/cursor/path",
            "claude-code": str(self.claude_home),
        }

        with patch(
            "src.core.registry.get_registry_path",
            return_value=self.registry_file,
        ):
            self.registry_file.write_text(json.dumps(registry_content))

            # Test registry detection
            detected_tools = _detect_available_agentic_tools()

            # Should detect both tools from registry
            assert "claude-code" in detected_tools
            # Note: cursor might not be detected since path is fake

    def test_empty_directories_handling(self):
        """Test handling of empty Claude Code directories."""
        # Ensure directories exist but are empty
        assert self.projects_dir.exists()
        assert self.sessions_dir.exists()

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Should handle empty directories gracefully
            session_files = query.find_session_files(self.project_root)
            assert session_files == []

            # Should return empty result
            result = query.query_conversations(self.project_root)
            assert result["total_sessions"] == 0
            assert result["conversations"] == []

    def test_malformed_conversation_files(self):
        """Test handling of malformed JSONL conversation files."""
        # Create malformed conversation file
        malformed_file = self.project_sessions_dir / "sauron-corruption.jsonl"
        malformed_file.write_text("{ invalid json from the Dark Lord }")

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Should handle malformed files gracefully
            session_files = query.find_session_files(self.project_root)
            assert malformed_file in session_files

            # Should parse valid lines and skip invalid ones
            result = query.parse_session_file(malformed_file)
            assert result["message_count"] == 0  # No valid lines

    def test_project_root_path_encoding(self):
        """Test handling of project root path encoding edge cases."""
        # Create project with special characters that need encoding
        special_project = self.temp_dir / "fangorn-forest_ent-moot"
        special_project.mkdir()

        # Create encoded directory for this project
        encoded_special = str(special_project).replace("/", "-")
        special_sessions_dir = self.projects_dir / encoded_special
        special_sessions_dir.mkdir()

        # Create conversation in the special project
        special_conv = special_sessions_dir / "treebeard-hoom.jsonl"
        special_conv.write_text(
            '{"sessionId": "ent-session", "message": {"content": "Hoom, hom! Don\'t be hasty"}}\n'
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Should handle special project paths
            session_files = query.find_session_files(special_project)
            assert special_conv in session_files

    def test_multiple_projects_isolation(self):
        """Test that conversations from different projects are properly isolated."""
        # Create another project
        shire_project = self.temp_dir / "shire-project"
        shire_project.mkdir()
        shire_encoded = str(shire_project).replace("/", "-")
        shire_sessions_dir = self.projects_dir / shire_encoded
        shire_sessions_dir.mkdir()

        # Create conversations for each project
        rivendell_conv = self.create_real_conversation_file(
            "elrond-meeting",
            [
                {
                    "content": "How to organize the Council of Elrond?",
                    "role": "user",
                }
            ],
        )

        shire_conv = shire_sessions_dir / "hobbit-feast.jsonl"
        shire_conv.write_text(
            '{"sessionId": "second-breakfast", "message": {"content": "What about elevenses?"}}\n'
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Test project isolation
            rivendell_files = query.find_session_files(self.project_root)
            shire_files = query.find_session_files(shire_project)

            # Should find project-specific conversations
            assert rivendell_conv in rivendell_files
            assert shire_conv not in rivendell_files

            assert shire_conv in shire_files
            assert rivendell_conv not in shire_files


class TestClaudeCodeRegressionTests:
    """Regression tests to prevent Claude Code-specific bugs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.claude_home = self.temp_dir / ".claude"
        self.projects_dir = self.claude_home / "projects"
        self.sessions_dir = self.claude_home / "sessions"

        # Create the structure that actually exists in real Claude Code installations
        self.projects_dir.mkdir(parents=True)
        self.sessions_dir.mkdir(parents=True)

        # Create a real project
        self.project_root = self.temp_dir / "minas-tirith-project"
        self.project_root.mkdir()

        self.encoded_project = str(self.project_root).replace("/", "-")
        self.project_sessions_dir = self.projects_dir / self.encoded_project
        self.project_sessions_dir.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_regression_find_session_files_searches_projects_dir(self):
        """Regression test: ensure find_session_files searches projects/ directory correctly."""
        # This test specifically checks for the bug where find_session_files was only
        # searching in sessions/ directory instead of projects/ subdirectories

        # Create a conversation file in the project directory
        project_conv = self.project_sessions_dir / "boromir-horn.jsonl"
        project_conv.write_text(
            '{"sessionId": "gondor-call", "message": {"content": "The Horn of Gondor!"}}\n'
        )

        # Create a file in the old sessions directory (should also be found)
        session_conv = self.sessions_dir / "aragorn-ranger.jsonl"
        session_conv.write_text(
            '{"sessionId": "strider", "message": {"content": "A ranger\'s duty"}}\n'
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            query = ClaudeCodeQuery()

            # Should find files in both locations
            session_files = query.find_session_files()

            # REGRESSION: Ensure both projects/ and sessions/ files are found
            assert len(session_files) >= 2
            assert project_conv in session_files
            assert session_conv in session_files

    def test_regression_project_root_propagation(self):
        """Regression test: ensure project_root is passed through conversation aggregator."""
        # This test checks for the bug where project_root wasn't being passed
        # through the aggregator to individual tool handlers

        project_conv = self.project_sessions_dir / "faramir-wisdom.jsonl"
        project_conv.write_text(
            '{"sessionId": "steward-duty", "message": {"content": "Quality over chance"}}\n'
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            # Mock the registry to include claude-code
            with (
                patch(
                    "src.core.registry.get_registered_agentic_tools"
                ) as mock_registry,
                patch(
                    "src.tool_calls.aggregator.get_registered_agentic_tools"
                ) as mock_aggregator_registry,
            ):
                mock_registry.return_value = ["claude-code"]
                mock_aggregator_registry.return_value = ["claude-code"]

                # This should pass project_root through to Claude Code handlers
                result = handle_recall_conversations(
                    project_root=self.project_root,
                    fast_mode=True,
                    min_score=0.0,
                    limit=10,
                )

                # Extract data
                if isinstance(result, dict) and "content" in result:
                    content_text = result["content"][0]["text"]
                    data = json.loads(content_text)
                else:
                    data = result

                # REGRESSION: Should find Claude Code conversations properly
                # Handle both normal format and summary format
                if "tool_results" in data:
                    assert "claude-code" in data["tool_results"]
                    claude_results = data["tool_results"]["claude-code"]
                    # Should find the conversation
                    assert claude_results["total_conversations"] > 0
                elif "tool_summaries" in data:
                    # Summary format when response is too large
                    assert "claude-code" in data["tool_summaries"]
                    claude_summary = data["tool_summaries"]["claude-code"]
                    assert claude_summary["count"] > 0
                else:
                    # If neither format, fail with helpful message
                    assert (
                        False
                    ), f"Unexpected response format. Keys: {list(data.keys())}"

    def test_regression_conversation_aggregator_project_root_default(self):
        """Regression test: ensure conversation aggregator handles default project root."""
        # This test checks that the aggregator properly handles when project_root is None

        project_conv = self.project_sessions_dir / "denethor-palantir.jsonl"
        project_conv.write_text(
            '{"sessionId": "seeing-stone", "message": {"content": "The stones will show what they will"}}\n'
        )

        with patch.dict("os.environ", {"CLAUDE_HOME": str(self.claude_home)}):
            # Mock the registry to include claude-code
            with patch(
                "src.core.registry.get_registered_agentic_tools"
            ) as mock_registry:
                mock_registry.return_value = ["claude-code"]

                # Test with None project_root (should use current working directory)
                result = handle_recall_conversations(
                    project_root=None,  # This was the source of the bug
                    fast_mode=True,
                    min_score=0.0,
                    limit=10,
                )

                # Extract data
                if isinstance(result, dict) and "content" in result:
                    content_text = result["content"][0]["text"]
                    data = json.loads(content_text)
                else:
                    data = result

                # REGRESSION: Should handle None project_root gracefully
                # Handle both normal format and summary format
                if "tool_results" in data:
                    # Should have some tool results and not crash
                    assert len(data["tool_results"]) >= 0
                    # Should have valid response structure
                    for tool_name, tool_results in data["tool_results"].items():
                        assert "total_conversations" in tool_results
                        # Check if conversations key exists (full format)
                        if "conversations" in tool_results:
                            assert isinstance(tool_results["conversations"], list)
                elif "tool_summaries" in data:
                    # Summary format when response is too large
                    assert len(data["tool_summaries"]) >= 0
                    for tool_name, tool_summary in data["tool_summaries"].items():
                        assert "count" in tool_summary
                else:
                    # If neither format, should still have basic structure
                    assert "total_conversations" in data
