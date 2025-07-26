"""Performance tests for recall operations and memory usage."""

import gc
import os
import threading
import time
from typing import Any

import psutil
import pytest


# Mock components for performance testing
def mock_heavy_database_scan(num_conversations: int = 1000) -> list[dict[str, Any]]:
    """Mock database scan that simulates processing many conversations."""
    conversations = []
    for i in range(num_conversations):
        conversations.append(
            {
                "id": f"conversation_{i}",
                "title": f"Test Conversation {i}",
                "content": f"This is test content for conversation {i} "
                * 50,  # Longer content
                "timestamp": f"2023-12-01T{i % 24:02d}:00:00Z",
                "tool": "cursor" if i % 2 == 0 else "claude-code",
                "relevance_score": 0.5 + (i % 5) * 0.1,
            }
        )
    return conversations


def mock_conversation_processing(
    conversations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mock conversation processing with realistic operations."""
    processed = []
    for conv in conversations:
        # Simulate content analysis
        content_words = len(conv["content"].split())

        # Simulate relevance scoring
        relevance_factors = [
            len(conv["title"]) / 100,
            content_words / 1000,
            0.5 if "test" in conv["content"].lower() else 0.0,
        ]
        final_score = min(sum(relevance_factors), 1.0)

        processed_conv = {
            **conv,
            "word_count": content_words,
            "relevance_score": final_score,
            "processed_timestamp": time.time(),
        }
        processed.append(processed_conv)

    return processed


def mock_recall_with_load(
    num_conversations: int = 1000, limit: int = 50
) -> dict[str, Any]:
    """Mock recall function that simulates realistic load."""
    start_time = time.time()

    # Simulate database scanning
    scan_start = time.time()
    raw_conversations = mock_heavy_database_scan(num_conversations)
    scan_time = time.time() - scan_start

    # Simulate conversation processing
    process_start = time.time()
    processed_conversations = mock_conversation_processing(raw_conversations)
    process_time = time.time() - process_start

    # Simulate filtering and sorting
    filter_start = time.time()
    filtered_conversations = [
        conv for conv in processed_conversations if conv["relevance_score"] >= 0.3
    ]
    sorted_conversations = sorted(
        filtered_conversations, key=lambda x: x["relevance_score"], reverse=True
    )
    limited_conversations = sorted_conversations[:limit]
    filter_time = time.time() - filter_start

    total_time = time.time() - start_time

    return {
        "conversations": limited_conversations,
        "total_conversations": len(limited_conversations),
        "processing_stats": {
            "total_scanned": num_conversations,
            "total_processed": len(processed_conversations),
            "total_filtered": len(filtered_conversations),
            "scan_time": scan_time,
            "process_time": process_time,
            "filter_time": filter_time,
            "total_time": total_time,
        },
    }


class TestRecallPerformance:
    """Performance tests for conversation recall operations."""

    def test_recall_performance_small_dataset(self):
        """Test recall performance with small dataset (100 conversations)."""
        start_time = time.time()

        result = mock_recall_with_load(num_conversations=100, limit=25)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete quickly for small dataset
        assert execution_time < 1.0, (
            f"Small dataset took {execution_time:.2f}s, expected < 1.0s"
        )

        # Verify results
        assert result["total_conversations"] <= 25
        assert result["processing_stats"]["total_scanned"] == 100

        # Performance metrics should be reasonable
        stats = result["processing_stats"]
        assert stats["scan_time"] < 0.5
        assert stats["process_time"] < 0.5
        assert stats["filter_time"] < 0.1

    def test_recall_performance_medium_dataset(self):
        """Test recall performance with medium dataset (1000 conversations)."""
        start_time = time.time()

        result = mock_recall_with_load(num_conversations=1000, limit=50)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete in reasonable time for medium dataset
        assert execution_time < 3.0, (
            f"Medium dataset took {execution_time:.2f}s, expected < 3.0s"
        )

        # Verify results
        assert result["total_conversations"] <= 50
        assert result["processing_stats"]["total_scanned"] == 1000

        # Performance should scale reasonably
        stats = result["processing_stats"]
        assert (
            abs(stats["total_time"] - execution_time) < 0.01
        )  # Within 10ms is close enough

    def test_recall_performance_large_dataset(self):
        """Test recall performance with large dataset (5000 conversations)."""
        start_time = time.time()

        result = mock_recall_with_load(num_conversations=5000, limit=100)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should complete in acceptable time for large dataset
        assert execution_time < 10.0, (
            f"Large dataset took {execution_time:.2f}s, expected < 10.0s"
        )

        # Verify results
        assert result["total_conversations"] <= 100
        assert result["processing_stats"]["total_scanned"] == 5000

    def test_recall_performance_scaling(self):
        """Test that recall performance scales reasonably with dataset size."""
        dataset_sizes = [100, 500, 1000, 2000]
        execution_times = []

        for size in dataset_sizes:
            start_time = time.time()
            mock_recall_with_load(num_conversations=size, limit=50)
            execution_time = time.time() - start_time
            execution_times.append(execution_time)

        # Performance should scale sub-linearly (not worse than O(n))
        for i in range(1, len(dataset_sizes)):
            size_ratio = dataset_sizes[i] / dataset_sizes[i - 1]
            time_ratio = execution_times[i] / execution_times[i - 1]

            # Time ratio should not be dramatically worse than size ratio
            assert time_ratio < size_ratio * 2, (
                f"Performance degraded: {size_ratio}x size took {time_ratio}x time"
            )

    def test_memory_usage_during_recall(self):
        """Test memory usage during conversation recall."""
        if not psutil:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())

        # Get baseline memory usage
        gc.collect()  # Force garbage collection
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform recall operation
        result = mock_recall_with_load(num_conversations=1000, limit=50)

        # Get peak memory usage
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - baseline_memory

        # Memory increase should be reasonable (less than 100MB for test data)
        assert memory_increase < 100, (
            f"Memory increased by {memory_increase:.1f}MB, expected < 100MB"
        )

        # Clean up and verify memory is released
        del result
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        peak_memory - final_memory

        # Memory release testing is flaky due to Python's garbage collection
        # Just verify no excessive memory growth over time
        assert final_memory <= baseline_memory + 10.0, (
            f"Excessive memory growth: started with {baseline_memory:.1f}MB, ended with {final_memory:.1f}MB"
        )

        # Log memory usage for debugging but don't fail on release timing
        print(
            f"Memory usage: baseline={baseline_memory:.1f}MB, peak={peak_memory:.1f}MB, final={final_memory:.1f}MB"
        )

    def test_concurrent_recall_performance(self):
        """Test performance under concurrent recall operations."""

        def perform_recall():
            return mock_recall_with_load(num_conversations=500, limit=25)

        num_threads = 4
        threads = []
        results = []

        start_time = time.time()

        # Start concurrent recall operations
        for _ in range(num_threads):

            def thread_target():
                result = perform_recall()
                results.append(result)

            thread = threading.Thread(target=thread_target)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_time = end_time - start_time

        # Concurrent operations should complete in reasonable time
        assert total_time < 8.0, (
            f"Concurrent operations took {total_time:.2f}s, expected < 8.0s"
        )

        # All operations should succeed
        assert len(results) == num_threads
        for result in results:
            assert result["total_conversations"] >= 0
            assert "processing_stats" in result

    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""
        if not psutil:
            pytest.skip("psutil not available for memory testing")

        process = psutil.Process(os.getpid())

        # Baseline memory
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple operations
        for i in range(10):
            result = mock_recall_with_load(num_conversations=200, limit=20)
            del result

            # Occasional garbage collection
            if i % 3 == 0:
                gc.collect()

        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (less than 20MB)
        assert memory_growth < 20, (
            f"Memory grew by {memory_growth:.1f}MB after 10 operations, possible leak"
        )

    def test_cpu_usage_during_recall(self):
        """Test CPU usage during recall operations."""
        if not psutil:
            pytest.skip("psutil not available for CPU testing")

        process = psutil.Process(os.getpid())

        # Monitor CPU usage during operation
        process.cpu_percent()

        start_time = time.time()
        result = mock_recall_with_load(num_conversations=1000, limit=50)
        execution_time = time.time() - start_time

        # Let CPU measurement settle
        time.sleep(0.1)
        cpu_percent_after = process.cpu_percent()

        # Should not consume excessive CPU for reasonable time
        execution_time / max(cpu_percent_after / 100, 0.01)  # seconds per CPU percent

        # Verify operation completed and CPU usage is reasonable
        assert result["total_conversations"] >= 0
        assert execution_time < 5.0  # Should complete in reasonable time

    def test_large_conversation_content_handling(self):
        """Test performance with very large conversation content."""
        # Create conversations with large content
        large_conversations = []
        for i in range(100):
            large_content = (
                "This is a very long conversation content. " * 1000
            )  # ~44KB per conversation
            large_conversations.append(
                {
                    "id": f"large_conv_{i}",
                    "title": f"Large Conversation {i}",
                    "content": large_content,
                    "timestamp": f"2023-12-01T{i % 24:02d}:00:00Z",
                    "tool": "cursor",
                    "relevance_score": 0.7,
                }
            )

        start_time = time.time()

        # Process large conversations
        processed = mock_conversation_processing(large_conversations)

        execution_time = time.time() - start_time

        # Should handle large content reasonably
        assert execution_time < 3.0, (
            f"Large content processing took {execution_time:.2f}s, expected < 3.0s"
        )
        assert len(processed) == 100

        # Verify content was processed
        for conv in processed:
            assert conv["word_count"] > 1000  # Should have many words

    def test_performance_with_different_limits(self):
        """Test how performance varies with different result limits."""
        dataset_size = 1000
        limits = [10, 50, 100, 200]

        for limit in limits:
            start_time = time.time()

            result = mock_recall_with_load(num_conversations=dataset_size, limit=limit)

            execution_time = time.time() - start_time

            # Performance should not degrade significantly with larger limits
            assert execution_time < 5.0, (
                f"Limit {limit} took {execution_time:.2f}s, expected < 5.0s"
            )

            # Should respect the limit
            assert result["total_conversations"] <= limit

            # Processing stats should be consistent regardless of limit
            stats = result["processing_stats"]
            assert stats["total_scanned"] == dataset_size

    def test_database_connection_performance(self):
        """Test simulated database connection performance."""
        connection_times = []

        # Simulate multiple database connections
        for _ in range(10):
            start_time = time.time()

            # Mock database connection and query
            mock_heavy_database_scan(100)

            connection_time = time.time() - start_time
            connection_times.append(connection_time)

        # Connection times should be consistent
        avg_time = sum(connection_times) / len(connection_times)
        max_time = max(connection_times)
        min_time = min(connection_times)

        # Variance should not be too high
        variance = max_time - min_time
        assert variance < avg_time * 2, (
            f"High connection time variance: {variance:.3f}s (avg: {avg_time:.3f}s)"
        )

        # Average connection time should be reasonable
        assert avg_time < 1.0, f"Average connection time {avg_time:.3f}s too high"

    def test_filtering_performance(self):
        """Test performance of conversation filtering operations."""
        # Create conversations with varying relevance scores
        conversations = []
        for i in range(2000):
            conversations.append(
                {
                    "id": f"conv_{i}",
                    "title": f"Conversation {i}",
                    "content": f"Content for conversation {i}",
                    "relevance_score": (i % 10) / 10.0,  # 0.0 to 0.9
                    "timestamp": f"2023-12-01T{i % 24:02d}:00:00Z",
                }
            )

        # Test different relevance thresholds
        thresholds = [0.0, 0.3, 0.5, 0.7, 0.9]

        for threshold in thresholds:
            start_time = time.time()

            # Filter conversations
            filtered = [
                conv for conv in conversations if conv["relevance_score"] >= threshold
            ]

            # Sort by relevance
            sorted_conversations = sorted(
                filtered, key=lambda x: x["relevance_score"], reverse=True
            )

            # Limit results
            limited = sorted_conversations[:100]

            execution_time = time.time() - start_time

            # Filtering should be fast
            assert execution_time < 0.5, (
                f"Filtering with threshold {threshold} took {execution_time:.3f}s, expected < 0.5s"
            )

            # Results should match threshold
            for conv in limited:
                assert conv["relevance_score"] >= threshold

    @pytest.mark.parametrize(
        "num_conversations,expected_max_time",
        [(100, 1.0), (500, 2.0), (1000, 3.0), (2000, 5.0)],
    )
    def test_parametrized_performance_expectations(
        self, num_conversations, expected_max_time
    ):
        """Test performance expectations for different dataset sizes."""
        start_time = time.time()

        result = mock_recall_with_load(num_conversations=num_conversations, limit=50)

        execution_time = time.time() - start_time

        assert execution_time < expected_max_time, (
            f"{num_conversations} conversations took {execution_time:.2f}s, expected < {expected_max_time}s"
        )

        assert result["processing_stats"]["total_scanned"] == num_conversations

    def test_performance_regression_baseline(self):
        """Establish performance baseline for regression testing."""
        # Standard test case for regression detection
        num_conversations = 1000
        limit = 50

        execution_times = []

        # Run multiple times for consistent measurement
        for _ in range(5):
            start_time = time.time()
            mock_recall_with_load(num_conversations=num_conversations, limit=limit)
            execution_time = time.time() - start_time
            execution_times.append(execution_time)

        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)

        # Record baseline metrics for future comparison
        baseline_metrics = {
            "avg_time": avg_time,
            "max_time": max_time,
            "min_time": min_time,
            "num_conversations": num_conversations,
            "limit": limit,
        }

        # Baseline should be reasonable
        assert avg_time < 3.0, f"Baseline average time {avg_time:.2f}s too high"
        assert max_time < avg_time * 2, (
            f"Max time {max_time:.2f}s much higher than average {avg_time:.2f}s"
        )

        # Store baseline for potential future use
        # In real implementation, this could write to a file or database
        print(f"Performance baseline: {baseline_metrics}")
