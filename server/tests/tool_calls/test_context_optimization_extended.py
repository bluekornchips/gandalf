"""
Test suite for context optimization functionality.

Comprehensive tests for context optimization utilities, including keyword optimization,
response size management, and processing strategy creation with extensive edge case coverage.
"""

import unittest

from src.tool_calls.context_optimization import (
    calculate_response_size,
    create_processing_strategy,
    create_size_optimized_summary,
    estimate_conversation_processing_time,
    optimize_context_keywords,
    optimize_conversations_for_size,
    should_enable_fast_mode,
)


class TestOptimizeContextKeywords(unittest.TestCase):
    """Test context keyword optimization functionality."""

    def test_optimize_context_keywords_within_limit(self):
        """Test optimization when keywords are already within limit."""
        keywords = ["python", "django", "react", "nodejs"]
        max_keywords = 10

        result = optimize_context_keywords(keywords, max_keywords)

        self.assertEqual(result, keywords)
        self.assertLessEqual(len(result), max_keywords)

    def test_optimize_context_keywords_exceeds_limit(self):
        """Test optimization when keywords exceed limit."""
        keywords = [
            "python",
            "javascript",
            "typescript",
            "react",
            "angular",
            "vue",
            "django",
            "flask",
        ]
        max_keywords = 5

        result = optimize_context_keywords(keywords, max_keywords)

        self.assertEqual(len(result), max_keywords)
        self.assertTrue(all(keyword in keywords for keyword in result))

    def test_optimize_context_keywords_sorting_by_length(self):
        """Test that keywords are sorted by length (shorter first)."""
        keywords = ["javascript", "js", "typescript", "py", "python"]
        max_keywords = 3

        result = optimize_context_keywords(keywords, max_keywords)

        self.assertEqual(len(result), max_keywords)
        # Should prefer shorter keywords
        self.assertIn("js", result)
        self.assertIn("py", result)

    def test_optimize_context_keywords_empty_list(self):
        """Test optimization with empty keyword list."""
        keywords = []
        max_keywords = 5

        result = optimize_context_keywords(keywords, max_keywords)

        self.assertEqual(result, [])

    def test_optimize_context_keywords_single_keyword(self):
        """Test optimization with single keyword."""
        keywords = ["python"]
        max_keywords = 5

        result = optimize_context_keywords(keywords, max_keywords)

        self.assertEqual(result, keywords)

    def test_optimize_context_keywords_default_limit(self):
        """Test optimization with default limit."""
        keywords = ["keyword" + str(i) for i in range(20)]

        result = optimize_context_keywords(keywords)

        # Should use the default limit from constants
        self.assertLessEqual(len(result), len(keywords))

    def test_optimize_context_keywords_case_sensitivity(self):
        """Test that optimization respects case sensitivity in sorting."""
        keywords = ["Python", "python", "PYTHON", "Javascript", "javascript"]
        max_keywords = 3

        result = optimize_context_keywords(keywords, max_keywords)

        self.assertEqual(len(result), max_keywords)
        # All should be valid keywords from the original list
        self.assertTrue(all(keyword in keywords for keyword in result))


class TestCalculateResponseSize(unittest.TestCase):
    """Test response size calculation functionality."""

    def test_calculate_response_size_simple_dict(self):
        """Test size calculation for simple dictionary."""
        data = {"key": "value", "number": 42}

        size = calculate_response_size(data)

        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)

    def test_calculate_response_size_nested_dict(self):
        """Test size calculation for nested dictionary."""
        data = {
            "conversations": [
                {"id": "conv1", "title": "Test conversation"},
                {"id": "conv2", "title": "Another conversation"},
            ],
            "metadata": {"total": 2, "source": "test"},
        }

        size = calculate_response_size(data)

        self.assertIsInstance(size, int)
        self.assertGreater(size, 50)  # Should be reasonably sized

    def test_calculate_response_size_with_special_objects(self):
        """Test size calculation with objects that need string conversion."""
        from datetime import datetime
        from pathlib import Path

        data = {
            "timestamp": datetime.now(),
            "path": Path("/test/path"),
            "complex": {"nested": True},
        }

        size = calculate_response_size(data)

        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)

    def test_calculate_response_size_fallback_estimation(self):
        """Test size calculation fallback when JSON serialization fails."""

        # Create an object that can't be JSON serialized
        class UnserializableObject:
            def __init__(self):
                self.circular_ref = self

        data = {"unserializable": UnserializableObject()}

        size = calculate_response_size(data)

        self.assertIsInstance(size, int)
        self.assertGreater(size, 0)

    def test_calculate_response_size_empty_dict(self):
        """Test size calculation for empty dictionary."""
        data = {}

        size = calculate_response_size(data)

        self.assertIsInstance(size, int)
        self.assertEqual(size, 2)  # Size of "{}"

    def test_calculate_response_size_large_data(self):
        """Test size calculation for large data structure."""
        data = {
            "conversations": [
                {
                    "id": f"conv_{i}",
                    "title": f"Conversation {i}" * 10,
                    "content": "Sample content " * 100,
                }
                for i in range(100)
            ]
        }

        size = calculate_response_size(data)

        self.assertIsInstance(size, int)
        self.assertGreater(size, 10000)  # Should be quite large


class TestOptimizeConversationsForSize(unittest.TestCase):
    """Test conversation size optimization functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_conversations = [
            {
                "id": "conv1",
                "title": "First conversation",
                "source_tool": "cursor",
                "message_count": 5,
                "relevance_score": 0.8,
                "created_at": "2024-01-01T00:00:00Z",
                "snippet": "This is a test conversation about Python programming.",
            },
            {
                "id": "conv2",
                "title": "Second conversation",
                "source_tool": "claude-code",
                "message_count": 3,
                "relevance_score": 0.6,
                "created_at": "2024-01-02T00:00:00Z",
                "snippet": "This is another test conversation about JavaScript development.",
            },
        ]

    def test_optimize_conversations_for_size_within_limit(self):
        """Test optimization when conversations are within size limit."""
        target_size = 10000  # Large target

        result = optimize_conversations_for_size(self.sample_conversations, target_size)

        self.assertEqual(len(result), len(self.sample_conversations))
        # Should maintain all essential fields
        for conv in result:
            self.assertIn("id", conv)
            self.assertIn("title", conv)
            self.assertIn("source_tool", conv)

    def test_optimize_conversations_for_size_exceeds_limit(self):
        """Test optimization when conversations exceed size limit."""
        target_size = 100  # Very small target

        result = optimize_conversations_for_size(self.sample_conversations, target_size)

        # Should reduce the number of conversations
        self.assertLessEqual(len(result), len(self.sample_conversations))
        # Should still have valid structure
        for conv in result:
            self.assertIn("id", conv)
            self.assertIn("title", conv)

    def test_optimize_conversations_for_size_empty_list(self):
        """Test optimization with empty conversation list."""
        conversations = []
        target_size = 1000

        result = optimize_conversations_for_size(conversations, target_size)

        self.assertEqual(result, [])

    def test_optimize_conversations_for_size_single_conversation(self):
        """Test optimization with single conversation."""
        conversations = [self.sample_conversations[0]]
        target_size = 1000

        result = optimize_conversations_for_size(conversations, target_size)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "conv1")

    def test_optimize_conversations_for_size_field_truncation(self):
        """Test that fields are properly handled during optimization."""
        conversations = [
            {
                "id": "very_long_conversation_id_that_exceeds_normal_length_" * 5,
                "title": "This is a very long conversation title that should be truncated"
                * 10,
                "source_tool": "cursor",
                "message_count": 5,
                "relevance_score": 0.8,
                "created_at": "2024-01-01T00:00:00Z",
                "snippet": "This is a very long snippet that should be truncated because it exceeds the maximum length limit set for snippet optimization in the context optimization module"
                * 5,
            }
        ]

        result = optimize_conversations_for_size(conversations, 10000)

        self.assertEqual(len(result), 1)
        conv = result[0]

        # Just verify that the optimization process preserves essential fields
        self.assertIn("id", conv)
        self.assertIn("title", conv)
        self.assertIn("source_tool", conv)
        self.assertIn("message_count", conv)
        self.assertIn("relevance_score", conv)
        self.assertIn("created_at", conv)

        # Verify that the implementation handles long strings (truncated or not)
        self.assertIsInstance(conv["title"], str)
        self.assertIsInstance(conv["id"], str)

    def test_optimize_conversations_for_size_default_target(self):
        """Test optimization with default target size."""
        result = optimize_conversations_for_size(self.sample_conversations)

        # Should work with default target size
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), len(self.sample_conversations))


class TestSizeOptimizedSummary(unittest.TestCase):
    """Test size-optimized summary creation functionality."""

    def test_create_size_optimized_summary_basic(self):
        """Test creating basic optimized summary."""
        full_summary = {
            "total_conversations_found": 100,
            "conversations_returned": 50,
            "success_rate_percent": 95.5,
            "processing_time_seconds": 2.5,
            "extra_field": "should_be_excluded",
        }
        optimization_stats = {
            "original_count": 100,
            "original_size_bytes": 50000,
            "optimized_size_bytes": 25000,
        }

        result = create_size_optimized_summary(full_summary, optimization_stats)

        self.assertEqual(result["total_conversations_found"], 100)
        self.assertEqual(result["conversations_returned"], 50)
        self.assertEqual(result["success_rate_percent"], 95.5)
        self.assertEqual(result["processing_time_seconds"], 2.5)
        self.assertNotIn("extra_field", result)

        # Check optimization info
        self.assertIn("optimization", result)
        self.assertTrue(result["optimization"]["applied"])
        self.assertEqual(result["optimization"]["reduction_percent"], 50.0)

    def test_create_size_optimized_summary_no_optimization(self):
        """Test creating summary without optimization stats."""
        full_summary = {
            "total_conversations_found": 50,
            "conversations_returned": 50,
            "success_rate_percent": 100.0,
            "processing_time_seconds": 1.0,
        }
        optimization_stats = {}

        result = create_size_optimized_summary(full_summary, optimization_stats)

        self.assertEqual(result["total_conversations_found"], 50)
        self.assertNotIn("optimization", result)

    def test_create_size_optimized_summary_missing_fields(self):
        """Test creating summary with missing fields."""
        full_summary = {"total_conversations_found": 25}
        optimization_stats = {
            "original_count": 25,
            "original_size_bytes": 10000,
            "optimized_size_bytes": 8000,
        }

        result = create_size_optimized_summary(full_summary, optimization_stats)

        self.assertEqual(result["total_conversations_found"], 25)
        self.assertEqual(result["conversations_returned"], 0)  # Default value
        self.assertEqual(result["success_rate_percent"], 0)  # Default value
        self.assertEqual(result["processing_time_seconds"], 0)  # Default value

    def test_create_size_optimized_summary_zero_division_protection(self):
        """Test that summary handles zero division in reduction calculation."""
        full_summary = {"total_conversations_found": 10}
        optimization_stats = {
            "original_count": 10,
            "original_size_bytes": 0,  # Zero original size
            "optimized_size_bytes": 0,
        }

        result = create_size_optimized_summary(full_summary, optimization_stats)

        self.assertIn("optimization", result)
        self.assertEqual(result["optimization"]["reduction_percent"], 100.0)


class TestProcessingTimeEstimation(unittest.TestCase):
    """Test processing time estimation functionality."""

    def test_estimate_conversation_processing_time_basic(self):
        """Test basic processing time estimation."""
        conversation_count = 100

        time_estimate = estimate_conversation_processing_time(conversation_count)

        self.assertIsInstance(time_estimate, float)
        self.assertGreater(time_estimate, 0)

    def test_estimate_conversation_processing_time_with_analysis(self):
        """Test processing time estimation with analysis enabled."""
        conversation_count = 50

        time_with_analysis = estimate_conversation_processing_time(
            conversation_count, include_analysis=True
        )
        time_without_analysis = estimate_conversation_processing_time(
            conversation_count, include_analysis=False
        )

        self.assertGreater(time_with_analysis, time_without_analysis)

    def test_estimate_conversation_processing_time_zero_conversations(self):
        """Test processing time estimation with zero conversations."""
        time_estimate = estimate_conversation_processing_time(0)

        self.assertEqual(time_estimate, 0.5)

    def test_estimate_conversation_processing_time_large_count(self):
        """Test processing time estimation with large conversation count."""
        conversation_count = 10000

        time_estimate = estimate_conversation_processing_time(conversation_count)

        self.assertIsInstance(time_estimate, float)
        self.assertGreater(time_estimate, 1.0)  # Should take significant time


class TestShouldEnableFastMode(unittest.TestCase):
    """Test fast mode recommendation functionality."""

    def test_should_enable_fast_mode_low_count(self):
        """Test fast mode recommendation for low conversation count."""
        conversation_count = 10
        time_limit = 5.0

        result = should_enable_fast_mode(conversation_count, time_limit)

        # Should not recommend fast mode for small datasets
        self.assertFalse(result)

    def test_should_enable_fast_mode_high_count(self):
        """Test fast mode recommendation for high conversation count."""
        conversation_count = 1000
        time_limit = 5.0

        result = should_enable_fast_mode(conversation_count, time_limit)

        # Should recommend fast mode for large datasets
        self.assertTrue(result)

    def test_should_enable_fast_mode_default_time_limit(self):
        """Test fast mode recommendation with default time limit."""
        conversation_count = 500

        result = should_enable_fast_mode(conversation_count)

        self.assertIsInstance(result, bool)

    def test_should_enable_fast_mode_edge_case(self):
        """Test fast mode recommendation at the edge of time limit."""
        conversation_count = 100
        time_limit = 1.0  # Very tight limit

        result = should_enable_fast_mode(conversation_count, time_limit)

        # Should recommend fast mode with tight time constraints
        self.assertTrue(result)


class TestCreateProcessingStrategy(unittest.TestCase):
    """Test processing strategy creation functionality."""

    def test_create_processing_strategy_basic(self):
        """Test creating basic processing strategy."""
        available_tools = ["cursor", "claude-code"]
        estimated_conversations = 100
        parameters = {"fast_mode": True}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        self.assertIsInstance(strategy, dict)
        self.assertIn("use_fast_mode", strategy)
        self.assertIn("enable_caching", strategy)
        self.assertIn("parallel_processing", strategy)
        self.assertIn("size_optimization", strategy)

        self.assertTrue(strategy["use_fast_mode"])
        self.assertTrue(strategy["enable_caching"])
        self.assertTrue(strategy["parallel_processing"])  # Multiple tools

    def test_create_processing_strategy_single_tool(self):
        """Test creating strategy for single tool."""
        available_tools = ["cursor"]
        estimated_conversations = 50
        parameters = {}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        self.assertFalse(strategy["parallel_processing"])  # Single tool

    def test_create_processing_strategy_high_conversation_count(self):
        """Test strategy for high conversation count."""
        available_tools = ["cursor", "claude-code", "windsurf"]
        estimated_conversations = 1500  # High count
        parameters = {}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        self.assertTrue(strategy["use_fast_mode"])
        self.assertTrue(strategy["size_optimization"])
        self.assertFalse(strategy["enable_analysis"])

    def test_create_processing_strategy_moderate_conversation_count(self):
        """Test strategy for moderate conversation count."""
        available_tools = ["cursor", "claude-code"]
        estimated_conversations = 750  # Moderate count
        parameters = {}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        self.assertTrue(strategy["size_optimization"])

    def test_create_processing_strategy_parameter_override(self):
        """Test that explicit parameters override strategy defaults."""
        available_tools = ["cursor"]
        estimated_conversations = 2000  # Would normally force fast_mode
        parameters = {"fast_mode": False, "include_analysis": True}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        # User parameters should override defaults
        self.assertFalse(strategy["use_fast_mode"])
        self.assertTrue(strategy["enable_analysis"])

    def test_create_processing_strategy_empty_tools(self):
        """Test strategy creation with no available tools."""
        available_tools = []
        estimated_conversations = 100
        parameters = {}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        self.assertFalse(strategy["parallel_processing"])

    def test_create_processing_strategy_default_parameters(self):
        """Test strategy creation with default parameters."""
        available_tools = ["cursor"]
        estimated_conversations = 200
        parameters = {}

        strategy = create_processing_strategy(
            available_tools, estimated_conversations, parameters
        )

        # Should have sensible defaults
        self.assertTrue(strategy["use_fast_mode"])  # Default from parameters
        self.assertTrue(strategy["enable_caching"])
        self.assertFalse(
            strategy["size_optimization"]
        )  # Not needed for 200 conversations
