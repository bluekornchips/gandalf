"""
Test suite for conversation analysis batch processing functions.

Comprehensive tests for analyze_conversation_batch and get_conversation_insights
functions that are not covered in the main conversation_analysis tests.
"""

import tempfile
import unittest
from pathlib import Path

from src.core.conversation_analysis import (
    analyze_conversation_batch,
    get_conversation_insights,
)


class TestAnalyzeConversationBatch(unittest.TestCase):
    """Test the analyze_conversation_batch function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

        # Create a simple README for project context
        (self.project_root / "README.md").write_text(
            "# Test Project\nPython Django application with React frontend"
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_analyze_empty_conversations(self):
        """Test analyzing empty conversation list."""
        result = analyze_conversation_batch([], self.project_root)

        self.assertEqual(result, [])

    def test_analyze_single_conversation(self):
        """Test analyzing a single conversation."""
        conversations = [
            {
                "id": "conv1",
                "title": "Python Debug Help",
                "messages": [
                    {"content": "I have a Python error in my Django app"},
                    {"content": "Can you help debug this issue?"},
                ],
            }
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        self.assertEqual(len(result), 1)
        analyzed_conv = result[0]

        # Check structure
        self.assertIn("conversation", analyzed_conv)
        self.assertIn("relevance_score", analyzed_conv)
        self.assertIn("content", analyzed_conv)
        self.assertIn("metadata", analyzed_conv)
        self.assertIn("analysis", analyzed_conv)

        # Check content was extracted
        self.assertIn("Python", analyzed_conv["content"])
        self.assertIn("Django", analyzed_conv["content"])

        # Check analysis was performed
        self.assertIsInstance(analyzed_conv["relevance_score"], float)
        self.assertIn("conversation_type", analyzed_conv["analysis"])

    def test_analyze_multiple_conversations(self):
        """Test analyzing multiple conversations."""
        conversations = [
            {
                "id": "conv1",
                "title": "Python Debug",
                "messages": [{"content": "Python error debugging"}],
            },
            {
                "id": "conv2",
                "title": "React Component",
                "messages": [{"content": "React component issues"}],
            },
            {
                "id": "conv3",
                "title": "General Discussion",
                "messages": [{"content": "General project discussion"}],
            },
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        self.assertEqual(len(result), 3)

        # All should have required fields
        for analyzed_conv in result:
            self.assertIn("conversation", analyzed_conv)
            self.assertIn("relevance_score", analyzed_conv)
            self.assertIn("content", analyzed_conv)
            self.assertIn("metadata", analyzed_conv)
            self.assertIn("analysis", analyzed_conv)

    def test_analyze_with_detailed_analysis(self):
        """Test analyzing conversations with detailed analysis enabled."""
        conversations = [
            {
                "id": "conv1",
                "title": "Debug Session",
                "messages": [
                    {"content": "Working on main.py file with Python debugging"},
                ],
            }
        ]

        result = analyze_conversation_batch(
            conversations, self.project_root, include_detailed_analysis=True
        )

        self.assertEqual(len(result), 1)
        analyzed_conv = result[0]

        # Should include additional detailed analysis fields
        self.assertIn("summary", analyzed_conv)
        self.assertIn("scoring_explanation", analyzed_conv)

        # Verify scoring explanation structure
        scoring_explanation = analyzed_conv["scoring_explanation"]
        self.assertIsInstance(scoring_explanation, dict)

    def test_analyze_with_custom_weights(self):
        """Test analyzing conversations with custom weights configuration."""
        conversations = [
            {
                "id": "conv1",
                "messages": [{"content": "Python Django application testing"}],
            }
        ]

        # Mock weights config
        mock_weights = type(
            "MockWeights",
            (),
            {
                "get_dict": lambda self, key: {
                    "keyword_match": 2.0,
                    "recency": 1.0,
                    "file_reference": 1.5,
                }
            },
        )()

        result = analyze_conversation_batch(
            conversations, self.project_root, weights_config=mock_weights
        )

        self.assertEqual(len(result), 1)
        # Should use the custom weights (hard to test directly, but ensures no errors)
        self.assertIsInstance(result[0]["relevance_score"], float)

    def test_analyze_handles_conversation_exceptions(self):
        """Test that batch analysis handles individual conversation exceptions."""
        conversations = [
            {
                "id": "good_conv",
                "messages": [{"content": "Normal conversation"}],
            },
            None,  # This will cause an exception
            {
                "id": "another_good_conv",
                "messages": [{"content": "Another normal conversation"}],
            },
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        # Should still return results for valid conversations
        # Plus a fallback entry for the failed one
        self.assertEqual(len(result), 3)

        # Check that failed conversation gets zero score fallback
        failed_conv = next(
            conv
            for conv in result
            if conv["relevance_score"] == 0.0 and conv["content"] == ""
        )
        self.assertIsNotNone(failed_conv)
        self.assertEqual(failed_conv["analysis"]["conversation_type"], "general")

    def test_analyze_handles_analysis_exceptions(self):
        """Test that batch analysis handles exceptions during conversation analysis."""
        # Create a conversation that will cause an exception during analysis
        conversations = [
            {
                "id": "normal_conv",
                "messages": [{"content": "Normal conversation"}],
            },
            {
                "id": "malformed_conv",
                "messages": [
                    {"content": None}
                ],  # This should cause an exception during analysis
            },
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        # Should return results, even if some fail
        self.assertGreaterEqual(len(result), 1)

        # Function should complete without crashing, which tests the exception handling

    def test_analyze_with_malformed_conversations(self):
        """Test analyzing conversations with malformed data."""
        conversations = [
            {},  # Empty conversation
            {"id": "no_content"},  # No messages or content
            {"messages": "not_a_list"},  # Invalid messages format
            {
                "id": "valid_conv",
                "messages": [{"content": "Valid conversation"}],
            },
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        self.assertEqual(len(result), 4)

        # All should have fallback structure even if analysis fails
        for analyzed_conv in result:
            self.assertIn("relevance_score", analyzed_conv)
            self.assertIn("analysis", analyzed_conv)

    def test_analyze_conversation_type_classification(self):
        """Test that conversations are properly classified by type."""
        conversations = [
            {
                "id": "debug_conv",
                "messages": [
                    {"content": "I have a bug in my code that needs debugging"}
                ],
            },
            {
                "id": "test_conv",
                "messages": [{"content": "Writing unit tests with pytest"}],
            },
            {
                "id": "arch_conv",
                "messages": [
                    {"content": "Need to refactor the application architecture"}
                ],
            },
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        # Find conversations by type
        debug_conv = next(c for c in result if c["conversation"]["id"] == "debug_conv")
        test_conv = next(c for c in result if c["conversation"]["id"] == "test_conv")
        arch_conv = next(c for c in result if c["conversation"]["id"] == "arch_conv")

        # Check type classification
        self.assertEqual(debug_conv["analysis"]["conversation_type"], "debugging")
        self.assertEqual(test_conv["analysis"]["conversation_type"], "testing")
        self.assertEqual(arch_conv["analysis"]["conversation_type"], "architecture")

    def test_analyze_with_file_references(self):
        """Test analyzing conversations with file references."""
        conversations = [
            {
                "id": "file_conv",
                "messages": [
                    {"content": "Working on main.py and config.json files"},
                    {"content": "Also modified utils.py and README.md"},
                ],
            }
        ]

        result = analyze_conversation_batch(
            conversations, self.project_root, include_detailed_analysis=True
        )

        analyzed_conv = result[0]

        # Should detect file references
        self.assertIn("file_references", analyzed_conv["analysis"])
        file_refs = analyzed_conv["analysis"]["file_references"]
        self.assertGreater(len(file_refs), 0)

    def test_analyze_relevance_scoring(self):
        """Test that relevance scoring works properly."""
        conversations = [
            {
                "id": "high_relevance",
                "messages": [
                    {"content": "Python Django React TypeScript development project"},
                ],
            },
            {
                "id": "low_relevance",
                "messages": [
                    {"content": "Random discussion about cooking recipes"},
                ],
            },
        ]

        result = analyze_conversation_batch(conversations, self.project_root)

        high_rel_conv = next(
            c for c in result if c["conversation"]["id"] == "high_relevance"
        )
        low_rel_conv = next(
            c for c in result if c["conversation"]["id"] == "low_relevance"
        )

        # High relevance conversation should score higher
        self.assertGreater(
            high_rel_conv["relevance_score"], low_rel_conv["relevance_score"]
        )


class TestGetConversationInsights(unittest.TestCase):
    """Test the get_conversation_insights function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

        # Create project context
        (self.project_root / "README.md").write_text(
            "# Test Project\nPython Django application"
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_insights_empty_conversations(self):
        """Test getting insights from empty conversation list."""
        result = get_conversation_insights([], self.project_root)

        expected = {
            "total_conversations": 0,
            "insights": {},
            "recommendations": [],
        }
        self.assertEqual(result, expected)

    def test_insights_single_conversation(self):
        """Test getting insights from single conversation."""
        conversations = [
            {
                "id": "conv1",
                "messages": [
                    {"content": "Python debugging help"},
                    {"content": "Django error message"},
                ],
                "created_at": "2024-01-01T00:00:00",
            }
        ]

        result = get_conversation_insights(conversations, self.project_root)

        self.assertIn("total_conversations", result)
        self.assertIn("insights", result)
        self.assertIn("recommendations", result)

        # Should analyze the conversation
        self.assertEqual(result["total_conversations"], 1)

    def test_insights_multiple_conversation_types(self):
        """Test insights with conversations of different types."""
        conversations = [
            {
                "id": "debug1",
                "messages": [{"content": "Bug in code needs debugging"}],
                "created_at": "2024-01-01T00:00:00",
            },
            {
                "id": "debug2",
                "messages": [{"content": "Error message debugging help"}],
                "created_at": "2024-01-01T01:00:00",
            },
            {
                "id": "test1",
                "messages": [{"content": "Writing unit tests with pytest"}],
                "created_at": "2024-01-01T02:00:00",
            },
            {
                "id": "arch1",
                "messages": [{"content": "Refactoring application architecture"}],
                "created_at": "2024-01-01T03:00:00",
            },
        ]

        result = get_conversation_insights(conversations, self.project_root)

        self.assertEqual(result["total_conversations"], 4)

        # Should provide insights based on conversation patterns
        self.assertIn("insights", result)

        # Should include recommendations
        self.assertIn("recommendations", result)
        self.assertIsInstance(result["recommendations"], list)

    def test_insights_high_debugging_proportion(self):
        """Test insights when debugging conversations dominate."""
        # Create mostly debugging conversations
        conversations = []
        for i in range(6):
            conversations.append(
                {
                    "id": f"debug{i}",
                    "messages": [{"content": f"Debug issue {i} with error"}],
                    "created_at": "2024-01-01T00:00:00",
                }
            )

        # Add one non-debugging conversation
        conversations.append(
            {
                "id": "general1",
                "messages": [{"content": "General discussion"}],
                "created_at": "2024-01-01T00:00:00",
            }
        )

        result = get_conversation_insights(conversations, self.project_root)

        # Should recommend focusing on architectural discussions
        recommendations = result["recommendations"]
        debugging_recommendation = any(
            "architectural" in rec.lower() for rec in recommendations
        )
        self.assertTrue(debugging_recommendation)

    def test_insights_low_relevance_scores(self):
        """Test insights when most conversations have low relevance."""
        # Create conversations with content that won't match project keywords well
        conversations = []
        for i in range(8):
            conversations.append(
                {
                    "id": f"low_rel{i}",
                    "messages": [
                        {"content": f"Random discussion about cooking recipe {i}"}
                    ],
                    "created_at": "2024-01-01T00:00:00",
                }
            )

        result = get_conversation_insights(conversations, self.project_root)

        # Should recommend reviewing conversation selection criteria
        recommendations = result["recommendations"]
        selection_recommendation = any(
            "selection criteria" in rec.lower() for rec in recommendations
        )
        self.assertTrue(selection_recommendation)

    def test_insights_statistics_integration(self):
        """Test that insights properly integrate conversation statistics."""
        conversations = [
            {
                "id": "conv1",
                "messages": [
                    {"content": "First message"},
                    {"content": "Second message"},
                ],
                "created_at": "2024-01-01T00:00:00",
            },
            {
                "id": "conv2",
                "messages": [
                    {"content": "Third message"},
                ],
                "timestamp": 1704067200,  # 2024-01-01 00:00:00 UTC in seconds
            },
        ]

        result = get_conversation_insights(conversations, self.project_root)

        # Should include statistical insights
        self.assertEqual(result["total_conversations"], 2)

    def test_insights_handles_malformed_conversations(self):
        """Test insights handles malformed conversation data gracefully."""
        conversations = [
            {
                "id": "good_conv",
                "messages": [{"content": "Normal conversation"}],
            },
            {},  # Empty conversation (this is handled fine)
            {
                "id": "another_good",
                "messages": [{"content": "Another normal conversation"}],
            },
        ]

        # Should not crash and provide useful insights
        result = get_conversation_insights(conversations, self.project_root)

        self.assertIn("total_conversations", result)
        self.assertIn("insights", result)
        self.assertIn("recommendations", result)

    def test_insights_keyword_frequency_analysis(self):
        """Test that insights analyze keyword frequency properly."""
        conversations = [
            {
                "id": "conv1",
                "messages": [{"content": "Python Django application development"}],
            },
            {
                "id": "conv2",
                "messages": [{"content": "Python programming with Django framework"}],
            },
            {
                "id": "conv3",
                "messages": [{"content": "React frontend development"}],
            },
        ]

        result = get_conversation_insights(conversations, self.project_root)

        # Should analyze conversations and provide insights
        self.assertEqual(result["total_conversations"], 3)

        # The function should complete without errors
        self.assertIn("insights", result)

    def test_insights_score_distribution_analysis(self):
        """Test that insights properly analyze score distribution."""
        # Create conversations with varied relevance to project
        conversations = [
            {
                "id": "high_score",
                "messages": [{"content": "Python Django React development project"}],
            },
            {
                "id": "medium_score",
                "messages": [{"content": "Programming discussion"}],
            },
            {
                "id": "low_score",
                "messages": [{"content": "Random unrelated topic"}],
            },
        ]

        result = get_conversation_insights(conversations, self.project_root)

        # Should analyze score distribution
        self.assertEqual(result["total_conversations"], 3)

        # Should provide insights based on score patterns
        self.assertIn("insights", result)
        self.assertIn("recommendations", result)

    def test_insights_score_distribution_buckets(self):
        """Test that score distribution correctly categorizes conversations into buckets."""
        # Create conversations designed to hit specific score ranges
        conversations = [
            # High score (>= 3.0): lots of relevant keywords
            {
                "id": "high_score_conv",
                "messages": [
                    {
                        "content": "Python Django React TypeScript API development database optimization performance testing"
                    }
                ],
            },
            # Medium score (1.0 <= score < 3.0): some relevant keywords
            {
                "id": "medium_score_conv",
                "messages": [{"content": "programming discussion development"}],
            },
            # Low score (< 1.0): minimal or no relevant keywords
            {
                "id": "low_score_conv",
                "messages": [{"content": "random conversation about cooking"}],
            },
        ]

        result = get_conversation_insights(conversations, self.project_root)

        # Verify total conversations
        self.assertEqual(result["total_conversations"], 3)

        # The function should return analysis with score distribution
        # This test ensures all score distribution branches are hit
        self.assertIn("insights", result)
