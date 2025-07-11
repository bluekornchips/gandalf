"""Test Windsurf conversation recall functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.tool_calls.windsurf.recall import handle_recall_windsurf_conversations


class TestWindsurfRecall:
    """Test Windsurf conversation recall functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_root = Path("/test/minas_tirith")
        self.context_keywords = [
            "fellowship",
            "ring",
            "quest",
            "python",
            "javascript",
            "mithril",
            "palantír",
        ]

        self.sample_conversations = [
            {
                "id": "frodo_ring_bearer",
                "workspace_id": "shire_workspace",
                "source": "windsurf_chat_session",
                "database_path": "/path/to/windsurf/bag_end.vscdb",
                "session_data": {
                    "title": "The Ring Bearer's Journey",
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
            },
            {
                "id": "gandalf_balrog_encounter",
                "workspace_id": "moria_workspace",
                "source": "windsurf_chat_session",
                "database_path": "/path/to/windsurf/khazad_dum.vscdb",
                "session_data": {
                    "title": "The Bridge of Khazad-dûm",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Even the very wise cannot see all ends. What about the shadow and flame?",
                        },
                        {
                            "role": "assistant",
                            "content": "You shall not pass! This foe is beyond any of you. Run! Fly, you fools! I am a servant of the Secret Fire, wielder of the flame of Anor.",
                        },
                    ],
                    "timestamp": "2024-01-01T11:00:00Z",
                },
            },
            {
                "id": "aragorn_king_return",
                "workspace_id": "gondor_workspace",
                "source": "windsurf_chat_session",
                "database_path": "/path/to/windsurf/minas_tirith.vscdb",
                "session_data": {
                    "title": "The Return of the King",
                    "messages": [
                        {
                            "role": "user",
                            "content": "A day may come when the courage of men fails, but how do I lead them?",
                        },
                        {
                            "role": "assistant",
                            "content": "I am Aragorn, son of Arathorn. The hands of the king are the hands of a healer. This day does not belong to one man, but to all. You bow to no one.",
                        },
                    ],
                    "timestamp": "2024-01-01T12:00:00Z",
                },
            },
            {
                "id": "sam_loyalty_devotion",
                "workspace_id": "shire_workspace",
                "source": "windsurf_chat_session",
                "database_path": "/path/to/windsurf/hobbiton.vscdb",
                "session_data": {
                    "title": "The Gardener's Unwavering Loyalty",
                    "messages": [
                        {
                            "role": "user",
                            "content": "There's some good in this world, Mr. Frodo, and it's worth fighting for. How do I help?",
                        },
                        {
                            "role": "assistant",
                            "content": "I can't carry it for you, but I can carry you! By rights we shouldn't even be here. But we are. Share and enjoy, Mr. Frodo.",
                        },
                    ],
                    "timestamp": "2024-01-01T13:00:00Z",
                },
            },
            {
                "id": "galadriel_mirror_wisdom",
                "workspace_id": "lothlorien_workspace",
                "source": "windsurf_chat_session",
                "database_path": "/path/to/windsurf/caras_galadhon.vscdb",
                "session_data": {
                    "title": "The Mirror of Galadriel",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Even the smallest person can change the course of the future. What do you see?",
                        },
                        {
                            "role": "assistant",
                            "content": "I give you the light of Eärendil, our most beloved star. May it be a light for you in dark places, when all other lights go out.",
                        },
                    ],
                    "timestamp": "2024-01-01T14:00:00Z",
                },
            },
        ]

        self.mock_query_response = {
            "conversations": self.sample_conversations,
            "total_conversations": len(self.sample_conversations),
            "total_databases": 1,
            "query_timestamp": "2024-01-01T14:00:00Z",
        }

    def test_handle_recall_windsurf_conversations_basic(self):
        """Test basic Windsurf conversation recall."""
        arguments = {
            "fast_mode": True,
            "days_lookback": 7,
            "limit": 20,
            "min_score": 2.0,
            "conversation_types": ["technical", "code_discussion"],
        }

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            # Mock relevance analysis to return good scores
            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                return {
                    "relevance_score": 5.0,
                    "snippet": f"Snippet for {conv.get('id', 'unknown')}",
                    "keyword_matches": ["fellowship", "ring"],
                    "context_analysis": {"score": 5.0},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            assert "content" in result
            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            assert "conversations" in data
            assert "total_conversations" in data
            assert "total_analyzed" in data
            assert "processing_time" in data
            assert data["total_analyzed"] == 5

    def test_handle_recall_windsurf_conversations_no_conversations(self):
        """Test recall when no conversations are found."""
        arguments = {"fast_mode": True, "limit": 10}

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = {
                "conversations": [],
                "total_conversations": 0,
            }
            mock_keywords.return_value = self.context_keywords

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            assert data["total_conversations"] == 0
            assert data["total_analyzed"] == 0
            assert len(data["conversations"]) == 0

    def test_handle_recall_windsurf_conversations_with_relevance_filtering(
        self,
    ):
        """Test recall with relevance score filtering."""
        arguments = {
            "fast_mode": True,
            "limit": 10,
            "min_score": 4.0,
        }  # High threshold

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                conv_id = conv.get("id", "unknown")
                if conv_id == "frodo_ring_bearer":
                    score = 5.0  # above
                elif conv_id == "gandalf_balrog_encounter":
                    score = 3.0  # below
                else:
                    score = 4.5  # above

                return {
                    "relevance_score": score,
                    "snippet": f"Snippet for {conv_id}",
                    "keyword_matches": ["fellowship", "ring"],
                    "context_analysis": {"score": score},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            assert len(data["conversations"]) == 4  # 4 conversations have scores >= 4.0
            assert data["total_analyzed"] == 5

            for conv in data["conversations"]:
                assert conv["relevance_score"] >= 4.0

    def test_handle_recall_windsurf_conversations_with_limit(self):
        """Test recall with conversation limit."""
        arguments = {
            "fast_mode": True,
            "limit": 2,  # lower than total conversations
            "min_score": 1.0,
        }

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            # All conversations get good scores
            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                return {
                    "relevance_score": 5.0,
                    "snippet": f"Snippet for {conv.get('id', 'unknown')}",
                    "keyword_matches": ["fellowship"],
                    "context_analysis": {"score": 5.0},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            assert len(data["conversations"]) == 2
            assert data["total_analyzed"] == 5

    def test_handle_recall_windsurf_conversations_conversation_standardization(
        self,
    ):
        """Test that conversations are properly standardized."""
        arguments = {"fast_mode": True, "limit": 10, "min_score": 1.0}

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                return {
                    "relevance_score": 5.0,
                    "snippet": f"Snippet for {conv.get('id', 'unknown')}",
                    "keyword_matches": ["fellowship"],
                    "context_analysis": {"score": 5.0},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            for conv in data["conversations"]:
                assert "id" in conv
                assert "title" in conv
                assert "source" in conv
                assert "workspace_id" in conv
                assert "database_path" in conv
                assert "session_data" in conv
                assert "relevance_score" in conv
                assert "snippet" in conv
                assert "keyword_matches" in conv
                assert "created_at" in conv
                assert "updated_at" in conv
                assert conv["title"].startswith("Windsurf Chat")

    def test_handle_recall_windsurf_conversations_fast_mode(self):
        """Test recall in fast mode vs comprehensive mode."""
        for fast_mode in [True, False]:
            arguments = {"fast_mode": fast_mode, "limit": 10, "min_score": 1.0}

            with (
                patch(
                    "src.tool_calls.windsurf.recall.WindsurfQuery"
                ) as mock_query_class,
                patch(
                    "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
                ) as mock_keywords,
                patch(
                    "src.tool_calls.windsurf.recall.analyze_session_relevance"
                ) as mock_analyze,
            ):

                mock_instance = Mock()
                mock_query_class.return_value = mock_instance
                mock_instance.query_all_conversations.return_value = (
                    self.mock_query_response
                )
                mock_keywords.return_value = self.context_keywords

                def mock_analyze_side_effect(
                    conv, keywords, project_root, _fast_mode_param=True
                ):
                    return {
                        "relevance_score": 5.0,
                        "snippet": f"Snippet for {conv.get('id', 'unknown')}",
                        "keyword_matches": ["fellowship"],
                        "context_analysis": {"score": 5.0},
                    }

                mock_analyze.side_effect = mock_analyze_side_effect

                result = handle_recall_windsurf_conversations(
                    arguments, self.project_root
                )

                content_text = result["content"][0]["text"]
                data = json.loads(content_text)

                assert data["parameters"]["fast_mode"] == fast_mode
                assert len(data["conversations"]) > 0

    def test_handle_recall_windsurf_conversations_parameter_validation(self):
        """Test parameter validation and defaults."""
        test_cases = [
            {"days_lookback": 0, "limit": 0, "min_score": -1},
            {"days_lookback": 100, "limit": 200, "min_score": 10},
            {},
            {"conversation_types": "invalid"},
        ]

        for arguments in test_cases:
            with (
                patch(
                    "src.tool_calls.windsurf.recall.WindsurfQuery"
                ) as mock_query_class,
                patch(
                    "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
                ) as mock_keywords,
            ):

                mock_instance = Mock()
                mock_query_class.return_value = mock_instance
                mock_instance.query_all_conversations.return_value = {
                    "conversations": [],
                    "total_conversations": 0,
                }
                mock_keywords.return_value = self.context_keywords

                result = handle_recall_windsurf_conversations(
                    arguments, self.project_root
                )

                content_text = result["content"][0]["text"]
                data = json.loads(content_text)

                assert "parameters" in data
                params = data["parameters"]

                assert 1 <= params["days_lookback"] <= 60
                assert 1 <= params["limit"] <= 100
                assert params["min_score"] >= 0.0

    def test_handle_recall_windsurf_conversations_error_handling(self):
        """Test error handling during conversation analysis."""
        arguments = {"fast_mode": True, "limit": 10}

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                conv_id = conv.get("id", "unknown")
                if conv_id == "gandalf_balrog_encounter":
                    raise OSError("Analysis failed")
                return {
                    "relevance_score": 5.0,
                    "snippet": f"Snippet for {conv_id}",
                    "keyword_matches": ["fellowship"],
                    "context_analysis": {"score": 5.0},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            assert len(data["conversations"]) >= 4  # at least 4 should succeed
            assert data["total_analyzed"] == 5

    def test_handle_recall_windsurf_conversations_query_error(self):
        """Test handling of query errors."""
        arguments = {"fast_mode": True, "limit": 10}

        with patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class:
            mock_query_class.side_effect = OSError("Database connection failed")

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            assert "content" in result or "isError" in result

    def test_handle_recall_windsurf_conversations_context_keywords(self):
        """Test context keyword generation and usage."""
        arguments = {"fast_mode": True, "limit": 10, "min_score": 1.0}

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                assert keywords == self.context_keywords
                return {
                    "relevance_score": 5.0,
                    "snippet": f"Snippet for {conv.get('id', 'unknown')}",
                    "keyword_matches": keywords[:2],  # Use some keywords
                    "context_analysis": {"score": 5.0},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            assert data["context_keywords"] == self.context_keywords
            mock_keywords.assert_called_once_with(self.project_root)

    def test_handle_recall_windsurf_conversations_date_filtering(self):
        """Test conversation filtering by date."""
        arguments = {
            "fast_mode": True,
            "days_lookback": 1,  # Very recent only
            "limit": 10,
            "min_score": 1.0,
        }

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.filter_conversations_by_date"
            ) as mock_filter,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            # Mock date filtering to return subset
            filtered_conversations = self.sample_conversations[:2]  # Only first 2
            mock_filter.return_value = filtered_conversations

            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                return {
                    "relevance_score": 5.0,
                    "snippet": f"Snippet for {conv.get('id', 'unknown')}",
                    "keyword_matches": ["fellowship"],
                    "context_analysis": {"score": 5.0},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            # Should only process filtered conversations
            assert data["total_filtered"] == 2
            mock_filter.assert_called_once()

    def test_handle_recall_windsurf_conversations_sorting(self):
        """Test conversation sorting by relevance."""
        arguments = {"fast_mode": True, "limit": 10, "min_score": 1.0}

        with (
            patch("src.tool_calls.windsurf.recall.WindsurfQuery") as mock_query_class,
            patch(
                "src.tool_calls.windsurf.recall.generate_shared_context_keywords"
            ) as mock_keywords,
            patch(
                "src.tool_calls.windsurf.recall.analyze_session_relevance"
            ) as mock_analyze,
        ):

            mock_instance = Mock()
            mock_query_class.return_value = mock_instance
            mock_instance.query_all_conversations.return_value = (
                self.mock_query_response
            )
            mock_keywords.return_value = self.context_keywords

            # Mock different relevance scores to test sorting
            def mock_analyze_side_effect(conv, keywords, project_root, fast_mode=True):
                conv_id = conv.get("id", "unknown")
                scores = {
                    "frodo_ring_bearer": 3.0,
                    "gandalf_balrog_encounter": 5.0,
                    "aragorn_king_return": 4.0,
                    "sam_loyalty_devotion": 2.0,
                    "galadriel_mirror_wisdom": 4.5,
                }
                score = scores.get(conv_id, 1.0)

                return {
                    "relevance_score": score,
                    "snippet": f"Snippet for {conv_id}",
                    "keyword_matches": ["fellowship"],
                    "context_analysis": {"score": score},
                }

            mock_analyze.side_effect = mock_analyze_side_effect

            result = handle_recall_windsurf_conversations(arguments, self.project_root)

            content_text = result["content"][0]["text"]
            data = json.loads(content_text)

            # Should be sorted by relevance score (highest first)
            scores = [conv["relevance_score"] for conv in data["conversations"]]
            assert scores == sorted(scores, reverse=True)
            assert scores[0] == 5.0  # gandalf_balrog_encounter should be first

    @patch("src.tool_calls.windsurf.recall.WindsurfQuery")
    @patch("src.core.conversation_analysis.generate_shared_context_keywords")
    def test_handle_recall_windsurf_conversations_exception(
        self, mock_keywords, mock_query_class
    ):
        """Test conversation recall handler with exception."""
        mock_keywords.return_value = ["test-project"]
        mock_query_class.side_effect = OSError("Test error")

        arguments = {"fast_mode": True}
        result = handle_recall_windsurf_conversations(arguments, self.project_root)

        assert result["isError"] is True
        assert "Error recalling Windsurf conversations" in result["error"]
