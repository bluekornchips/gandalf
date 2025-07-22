"""
Tests for memory-aware LRU cache functionality.
"""

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest

from src.utils.memory_cache import (
    MemoryAwareLRUCache,
    cleanup_caches_if_needed,
    clear_all_caches,
    get_cache_stats,
    get_conversation_cache,
    get_keyword_cache,
)


class TestMemoryAwareLRUCache:
    """Test the MemoryAwareLRUCache class."""

    def test_cache_initialization(self):
        """Test cache initialization with default and custom parameters."""
        cache = MemoryAwareLRUCache()
        assert cache.max_memory_bytes == 100 * 1024 * 1024  # 100MB
        assert cache.max_items == 1000
        assert cache.ttl_seconds == 3600
        assert cache.check_interval == 30

        # Custom initialization
        cache = MemoryAwareLRUCache(
            max_memory_mb=50, max_items=500, ttl_seconds=1800, check_interval=60
        )
        assert cache.max_memory_bytes == 50 * 1024 * 1024  # 50MB
        assert cache.max_items == 500
        assert cache.ttl_seconds == 1800
        assert cache.check_interval == 60

    def test_estimate_size(self):
        """Test size estimation for different data types."""
        cache = MemoryAwareLRUCache()

        # String
        size = cache._estimate_size("hello world")
        assert size == len("hello world")

        # Bytes
        size = cache._estimate_size(b"hello world")
        assert size == len(b"hello world")

        data = {"key": "value", "number": 42}
        size = cache._estimate_size(data)
        expected_size = len(json.dumps(data, default=str))
        assert size == expected_size

        size = cache._estimate_size(42)
        assert size > 0

    def test_estimate_size_exception_handling(self):
        """Test size estimation when JSON serialization fails."""
        cache = MemoryAwareLRUCache()

        with patch("json.dumps", side_effect=Exception("JSON error")):
            size = cache._estimate_size({"complex": "object"})
            assert size == 1024

    def test_basic_get_put_operations(self):
        """Test basic cache get and put operations."""
        cache = MemoryAwareLRUCache()

        cache.put("ring_bearer", "frodo_baggins")
        assert cache.get("ring_bearer") == "frodo_baggins"

        assert cache.get("sauron_location") is None

    def test_lru_behavior(self):
        """Test LRU (Least Recently Used) eviction behavior."""
        cache = MemoryAwareLRUCache(max_items=3)

        cache.put("gandalf", "grey_wizard")
        cache.put("frodo", "hobbit_ring_bearer")
        cache.put("aragorn", "future_king")

        assert cache.get("gandalf") == "grey_wizard"
        assert cache.get("frodo") == "hobbit_ring_bearer"
        assert cache.get("aragorn") == "future_king"

        cache.get("gandalf")
        cache.put("legolas", "elf_archer")

        assert cache.get("gandalf") == "grey_wizard"
        assert cache.get("frodo") is None
        assert cache.get("aragorn") == "future_king"
        assert cache.get("legolas") == "elf_archer"

    @patch("src.utils.memory_cache.time.time")
    def test_ttl_expiration(self, mock_time):
        """Test TTL (Time To Live) expiration."""
        cache = MemoryAwareLRUCache(ttl_seconds=1)

        mock_time.return_value = 0.0
        cache.put("one_ring", "precious_ring")
        assert cache.get("one_ring") == "precious_ring"

        # fastforward time to 1.2 seconds
        mock_time.return_value = 1.2

        cache._evict_expired()
        assert cache.get("one_ring") is None

    def test_memory_pressure_detection(self):
        """Test memory pressure detection mechanism."""
        cache = MemoryAwareLRUCache(max_memory_mb=1, check_interval=0)

        assert not cache._check_memory_pressure()

        large_data = "x" * (1024 * 1024 + 1)
        cache.put("palantir", large_data)
        assert cache._check_memory_pressure()

    def test_memory_pressure_check_interval(self):
        """Test that memory pressure check respects interval."""
        cache = MemoryAwareLRUCache(check_interval=3600)

        result1 = cache._check_memory_pressure()
        result2 = cache._check_memory_pressure()
        assert not result1
        assert not result2

    def test_concurrent_access(self):
        """Test thread-safe concurrent access."""
        cache = MemoryAwareLRUCache()
        results = []
        errors = []

        def worker(thread_id):
            try:
                key = f"thread_{thread_id}"
                value = f"value_{thread_id}"
                cache.put(key, value)
                retrieved = cache.get(key)
                results.append((thread_id, retrieved))
            except (RuntimeError, ValueError, OSError) as e:
                errors.append(e)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 5

        for thread_id, value in results:
            assert value == f"value_{thread_id}"

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryAwareLRUCache()

        stats = cache.get_stats()
        assert stats["total_items"] == 0
        assert stats["memory_usage_mb"] == 0
        assert stats["memory_utilization"] == 0
        assert stats["items_utilization"] == 0

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        stats = cache.get_stats()
        assert stats["total_items"] == 2
        assert stats["memory_usage_mb"] > 0
        assert stats["memory_utilization"] > 0
        assert stats["items_utilization"] > 0

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = MemoryAwareLRUCache()

        cache.put("key1", "value1")
        cache.put("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

        stats = cache.get_stats()
        assert stats["total_items"] == 0
        assert stats["memory_usage_mb"] == 0

    def test_evict_lru_with_target_count(self):
        """Test LRU eviction with specific target count."""
        cache = MemoryAwareLRUCache(max_items=10)

        # Add items
        for i in range(5):
            cache.put(f"key{i}", f"value{i}")

        # Access some items to change LRU order
        cache.get("key2")  # Make key2 more recent
        cache.get("key4")  # Make key4 more recent

        # Manually trigger LRU eviction of 2 items
        cache._evict_lru(target_count=2)

        # key0 and key1 should be evicted (least recently used)
        assert cache.get("key0") is None
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"  # Still present
        assert cache.get("key3") == "value3"  # Still present
        assert cache.get("key4") == "value4"  # Still present

    def test_remove_key_internal(self):
        """Test internal key removal."""
        cache = MemoryAwareLRUCache()

        cache.put("shire", "hobbit_homeland")
        assert cache.get("shire") == "hobbit_homeland"

        cache._remove_key("shire")
        assert cache.get("shire") is None

    def test_cleanup_if_needed(self):
        """Test cleanup_if_needed method."""
        cache = MemoryAwareLRUCache(max_memory_mb=1, ttl_seconds=1)

        large_data = "x" * (1024 * 1024 + 100)
        cache.put("large_key", large_data)

        cache.cleanup_if_needed()
        assert cache.get("large_key") is not None


class TestGlobalCacheFunctions:
    """Test global cache management functions."""

    def test_get_conversation_cache(self):
        """Test getting conversation cache instance."""
        cache1 = get_conversation_cache()
        assert isinstance(cache1, MemoryAwareLRUCache)

        # Should return the same instance (singleton)
        cache2 = get_conversation_cache()
        assert cache1 is cache2

        # Check configuration
        assert cache1.max_memory_bytes == 80 * 1024 * 1024  # 80MB
        assert cache1.max_items == 500
        assert cache1.ttl_seconds == 1800  # 30 minutes

    def test_get_keyword_cache(self):
        """Test getting keyword cache instance."""
        cache1 = get_keyword_cache()
        assert isinstance(cache1, MemoryAwareLRUCache)

        # Should return the same instance (singleton)
        cache2 = get_keyword_cache()
        assert cache1 is cache2

        # Check configuration
        assert cache1.max_memory_bytes == 20 * 1024 * 1024  # 20MB
        assert cache1.max_items == 200
        assert cache1.ttl_seconds == 3600  # 1 hour

    def test_clear_all_caches(self):
        """Test clearing all global caches."""
        # Get caches and add data
        conv_cache = get_conversation_cache()
        keyword_cache = get_keyword_cache()

        conv_cache.put("conv_key", "conv_value")
        keyword_cache.put("keyword_key", "keyword_value")

        assert conv_cache.get("conv_key") == "conv_value"
        assert keyword_cache.get("keyword_key") == "keyword_value"

        # Clear all caches
        clear_all_caches()

        # Should be cleared
        assert conv_cache.get("conv_key") is None
        assert keyword_cache.get("keyword_key") is None

    def test_get_cache_stats_empty(self):
        """Test getting cache statistics when empty."""
        # Clear first to ensure clean state
        clear_all_caches()

        stats = get_cache_stats()
        assert isinstance(stats, dict)

        # Should be empty initially or have empty stats
        if "conversation_cache" in stats:
            assert stats["conversation_cache"]["total_items"] == 0
        if "keyword_cache" in stats:
            assert stats["keyword_cache"]["total_items"] == 0

    def test_get_cache_stats_with_data(self):
        """Test getting cache statistics with data."""
        # Get caches and add data
        conv_cache = get_conversation_cache()
        keyword_cache = get_keyword_cache()

        conv_cache.put("conv_key", "conv_value")
        keyword_cache.put("keyword_key", "keyword_value")

        stats = get_cache_stats()

        assert "conversation_cache" in stats
        assert "keyword_cache" in stats
        assert stats["conversation_cache"]["total_items"] >= 1
        assert stats["keyword_cache"]["total_items"] >= 1

    def test_cleanup_caches_if_needed(self):
        """Test cleanup_caches_if_needed function."""
        # Get caches and add some data
        conv_cache = get_conversation_cache()
        keyword_cache = get_keyword_cache()

        conv_cache.put("fellowship", "nine_companions")
        keyword_cache.put("my_precious", "gollum_phrase")

        # This should not raise an exception
        cleanup_caches_if_needed()

        # Data might still be there (cleanup is conditional)
        # Just verify the function doesn't crash
        assert True


class TestCacheIntegration:
    """Test cache integration scenarios."""

    def test_memory_pressure_eviction_workflow(self):
        """Test complete memory pressure detection and eviction workflow."""
        # Small cache to trigger eviction
        cache = MemoryAwareLRUCache(max_memory_mb=1, max_items=100, check_interval=0)

        # Add data that should exceed memory limit
        for i in range(10):
            large_data = "x" * (200 * 1024)  # 200KB each
            cache.put(f"key_{i}", large_data)

        # Should have triggered automatic eviction
        stats = cache.get_stats()
        assert stats["total_items"] < 10  # Some items should have been evicted
        assert (
            stats["memory_usage_mb"] < 10 * 0.2
        )  # Memory should be reduced (0.2 MB per item)

    @patch("src.utils.memory_cache.time.time")
    def test_ttl_and_lru_interaction(self, mock_time):
        """Test interaction between TTL and LRU eviction policies."""
        cache = MemoryAwareLRUCache(ttl_seconds=1, max_items=5)

        mock_time.return_value = 0.0

        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")

        # All should be present initially
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

        mock_time.return_value = 1.2

        # Check expiration via get() method which checks TTL automatically
        # The get() method should detect expiration and return None
        result1 = cache.get("key1")
        result2 = cache.get("key2")
        result3 = cache.get("key3")

        # All should be expired due to TTL
        assert result1 is None
        assert result2 is None
        assert result3 is None

    @patch("src.utils.memory_cache.log_debug")
    @patch("src.utils.memory_cache.time.time")
    def test_logging_during_eviction(self, mock_time, mock_log):
        """Test that eviction operations are properly logged."""
        cache = MemoryAwareLRUCache(ttl_seconds=1)

        mock_time.return_value = 0.0

        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")

        mock_time.return_value = 1.1

        # Trigger eviction (should log)
        cache._evict_expired()

        # Check that logging occurred
        mock_log.assert_called_with("Evicted 2 expired cache entries")
