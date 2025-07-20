"""
Memory-efficient LRU cache with size limits and memory pressure detection.

Provides intelligent caching with 100MB memory limits, automatic eviction,
and TTL management to prevent memory exhaustion while maintaining high
performance. See src/utils/README.md for comprehensive documentation.
"""

import gc
import json
import sys
import threading
import time
from collections import OrderedDict
from typing import Any

from src.utils.common import log_debug, log_info


class MemoryAwareLRUCache:
    """LRU cache with memory size limits and automatic eviction."""

    def __init__(
        self,
        max_memory_mb: int = 100,
        max_items: int = 1000,
        ttl_seconds: int = 3600,
        check_interval: int = 30,
    ):
        """Initialize memory-aware LRU cache."""
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self.check_interval = check_interval

        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._access_times: dict[str, float] = {}
        self._cache_sizes: dict[str, int] = {}
        self._lock = threading.RLock()
        self._last_memory_check = 0
        self._current_memory = 0

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of a value in bytes.

        Provides memory size estimation for different data types to enable
        accurate memory tracking. Uses optimized size calculation methods
        for common data types with fallback for complex objects.

        Args:
            value: The value to estimate size for

        Returns:
            Estimated size in bytes

        Size Estimation Methods:
            - String/bytes: Use len() for direct character/byte count
            - Dict: JSON serialization size as approximation
            - Other objects: sys.getsizeof() for Python object size
            - Fallback: 1KB default for complex objects
        """
        try:
            if isinstance(value, str | bytes):
                return len(value)
            elif isinstance(value, dict):
                # Rough estimation for dict serialization
                return len(json.dumps(value, default=str))
            else:
                return sys.getsizeof(value)
        except Exception:
            # Fallback estimation
            return 1024

    def _check_memory_pressure(self) -> bool:
        """Check if we're under memory pressure and need to evict entries.

        Performs periodic memory pressure checks to determine if cache cleanup
        is needed. Uses garbage collection to get accurate memory readings
        and compares against configured limits.

        Returns:
            True if memory pressure detected and eviction needed

        Memory Pressure Detection:
            - Only checks at specified intervals to avoid overhead
            - Forces garbage collection for accurate memory readings
            - Compares current cache memory against max_memory_bytes limit
        """
        now = time.time()
        if now - self._last_memory_check < self.check_interval:
            return False

        self._last_memory_check = now

        # Force garbage collection to get accurate memory reading
        gc.collect()

        # Check if current cache size exceeds limit
        return self._current_memory > self.max_memory_bytes

    def _evict_expired(self) -> None:
        """Remove expired entries based on TTL.

        Scans all cache entries and removes those that have exceeded their
        time-to-live. This is the first eviction strategy applied when
        memory pressure is detected.

        Expiration Logic:
            - Compares current time against entry access time
            - Removes entries older than ttl_seconds
            - Updates memory tracking and statistics
            - Logs eviction count for monitoring
        """
        now = time.time()
        expired_keys = [
            key
            for key, access_time in self._access_times.items()
            if now - access_time > self.ttl_seconds
        ]

        for key in expired_keys:
            self._remove_key(key)

        if expired_keys:
            log_debug(f"Evicted {len(expired_keys)} expired cache entries")

    def _evict_lru(self, target_count: int = None) -> None:
        """Remove least recently used entries when memory pressure persists.

        Implements LRU (Least Recently Used) eviction policy to remove
        cache entries that haven't been accessed recently. This is applied
        after TTL-based eviction if memory pressure still exists.

        Args:
            target_count: Number of entries to evict (default: 25% of cache)

        LRU Eviction Strategy:
            - Sorts entries by access time (oldest first)
            - Removes specified number of least recently used entries
            - Defaults to removing 25% of cache if no target specified
            - Updates memory tracking and logs eviction statistics
        """
        if target_count is None:
            target_count = max(1, len(self._cache) // 4)  # Remove 25%

        # Sort by access time, oldest first
        lru_keys = sorted(
            self._cache.keys(), key=lambda k: self._access_times.get(k, 0)
        )

        evicted = 0
        for key in lru_keys:
            if evicted >= target_count:
                break
            self._remove_key(key)
            evicted += 1

        if evicted > 0:
            log_debug(f"Evicted {evicted} LRU cache entries")

    def _remove_key(self, key: str) -> None:
        """Remove a key from all internal structures and update memory tracking.

        Safely removes a cache entry from all internal data structures
        and updates memory usage tracking. This is a low-level method
        used by eviction and expiration processes.

        Args:
            key: Cache key to remove

        Cleanup Operations:
            - Removes entry from main cache dictionary
            - Cleans up access time tracking
            - Updates memory usage statistics
            - Removes size tracking information
        """
        if key in self._cache:
            self._current_memory -= self._cache_sizes.get(key, 0)
            del self._cache[key]
            del self._access_times[key]
            del self._cache_sizes[key]

    def get(self, key: str) -> Any | None:
        """Get value from cache, updating access time for LRU tracking."""
        with self._lock:
            if key not in self._cache:
                return None

            # Check if expired
            now = time.time()
            if now - self._access_times[key] > self.ttl_seconds:
                self._remove_key(key)
                return None

            # Update access time and move to end (most recent)
            self._access_times[key] = now
            self._cache.move_to_end(key)

            return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        """Add value to cache with automatic memory management and eviction."""
        with self._lock:
            value_size = self._estimate_size(value)
            now = time.time()

            # Remove existing key if present
            if key in self._cache:
                self._remove_key(key)

            # Check memory pressure before adding
            if self._check_memory_pressure() or len(self._cache) >= self.max_items:
                self._evict_expired()

                # If still over limit, evict LRU entries
                if (
                    self._current_memory + value_size > self.max_memory_bytes
                    or len(self._cache) >= self.max_items
                ):
                    evict_count = max(1, len(self._cache) // 4)
                    self._evict_lru(evict_count)

            # Add new entry
            self._cache[key] = value
            self._access_times[key] = now
            self._cache_sizes[key] = value_size
            self._current_memory += value_size

            log_debug(
                f"Cached {key} ({value_size} bytes, total: {self._current_memory} bytes)"
            )

    def clear(self) -> None:
        """Clear all cache entries and reset memory tracking.

        Removes all cached entries and resets internal tracking structures.
        This provides a clean slate for the cache and frees all memory.

        Operations Performed:
            - Clear main cache dictionary
            - Reset access time tracking
            - Clear memory size tracking
            - Reset total memory counter to zero
        """
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._cache_sizes.clear()
            self._current_memory = 0
            log_debug("Cleared all cache entries")

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics for monitoring and debugging.

        Returns detailed statistics about cache usage, memory consumption,
        and utilization rates. Useful for performance monitoring and tuning.

        Returns:
            Dictionary containing cache statistics:
            - total_items: Current number of cached entries
            - memory_usage_mb: Current memory usage in megabytes
            - memory_limit_mb: Configured memory limit in megabytes
            - items_limit: Maximum number of items allowed
            - memory_utilization: Memory usage as percentage of limit (0.0-1.0)
            - items_utilization: Item count as percentage of limit (0.0-1.0)

        Example:
            stats = cache.get_stats()
            print(f"Memory usage: {stats['memory_usage_mb']:.1f}MB")
            print(f"Cache utilization: {stats['memory_utilization']:.1%}")
        """
        with self._lock:
            return {
                "total_items": len(self._cache),
                "memory_usage_mb": self._current_memory / (1024 * 1024),
                "memory_limit_mb": self.max_memory_bytes / (1024 * 1024),
                "items_limit": self.max_items,
                "memory_utilization": self._current_memory / self.max_memory_bytes,
                "items_utilization": len(self._cache) / self.max_items,
            }

    def cleanup_if_needed(self) -> None:
        """Perform cache cleanup if memory pressure is detected.

        Provides a convenient method to trigger cache cleanup when needed.
        This can be called periodically or when the application detects
        memory pressure to proactively manage cache size.

        Cleanup Strategy:
            1. Check for memory pressure using configured thresholds
            2. Remove expired entries first (TTL-based cleanup)
            3. Apply LRU eviction if memory usage still high (>80% of limit)
            4. Log cleanup actions for monitoring

        Usage:
            Call this method periodically in long-running applications
            or when memory usage warnings are detected.
        """
        with self._lock:
            if self._check_memory_pressure():
                log_info("Memory pressure detected, performing cache cleanup")
                self._evict_expired()
                if self._current_memory > self.max_memory_bytes * 0.8:
                    self._evict_lru()


# Global cache instances
_conversation_cache: MemoryAwareLRUCache | None = None
_keyword_cache: MemoryAwareLRUCache | None = None
_cache_lock = threading.Lock()


def get_conversation_cache() -> MemoryAwareLRUCache:
    """Get the global conversation cache instance with optimized settings.

    Returns a singleton cache instance configured specifically for conversation
    data with appropriate memory limits and TTL settings for conversation content.

    Returns:
        Global conversation cache instance

    Cache Configuration:
        - Memory Limit: 80MB (optimized for conversation data)
        - Item Limit: 500 conversations
        - TTL: 30 minutes (balances freshness and performance)

    Thread Safety:
        Uses double-checked locking pattern to ensure thread-safe
        singleton initialization.
    """
    global _conversation_cache

    if _conversation_cache is None:
        with _cache_lock:
            if _conversation_cache is None:
                _conversation_cache = MemoryAwareLRUCache(
                    max_memory_mb=80,  # 80MB for conversations
                    max_items=500,
                    ttl_seconds=1800,  # 30 minutes
                )
                log_debug("Initialized conversation cache")

    return _conversation_cache


def get_keyword_cache() -> MemoryAwareLRUCache:
    """Get the global keyword cache instance with keyword-optimized settings.

    Returns a singleton cache instance configured specifically for keyword
    and project metadata with settings optimized for smaller, frequently
    accessed data.

    Returns:
        Global keyword cache instance

    Cache Configuration:
        - Memory Limit: 20MB (smaller for keyword data)
        - Item Limit: 200 keyword sets
        - TTL: 1 hour (longer for relatively stable keyword data)

    Thread Safety:
        Uses double-checked locking pattern to ensure thread-safe
        singleton initialization.
    """
    global _keyword_cache

    if _keyword_cache is None:
        with _cache_lock:
            if _keyword_cache is None:
                _keyword_cache = MemoryAwareLRUCache(
                    max_memory_mb=20,  # 20MB for keywords
                    max_items=200,
                    ttl_seconds=3600,  # 1 hour
                )
                log_debug("Initialized keyword cache")

    return _keyword_cache


def clear_all_caches() -> None:
    """Clear all global caches and reset memory usage.

    Provides a convenient way to clear all global cache instances at once.
    Useful for testing, debugging, or when a complete cache reset is needed.

    Operations:
        - Clears conversation cache if initialized
        - Clears keyword cache if initialized
        - Logs cache clearing action for monitoring

    Note:
        This does not destroy the cache instances, just clears their contents.
        The caches will continue to function normally after clearing.
    """
    if _conversation_cache:
        _conversation_cache.clear()
    if _keyword_cache:
        _keyword_cache.clear()
    log_info("Cleared all memory caches")


def get_cache_stats() -> dict[str, Any]:
    """Get comprehensive statistics for all global caches."""
    stats = {}

    if _conversation_cache:
        stats["conversation_cache"] = _conversation_cache.get_stats()

    if _keyword_cache:
        stats["keyword_cache"] = _keyword_cache.get_stats()

    return stats


def cleanup_caches_if_needed() -> None:
    """Perform memory pressure cleanup on all global caches if needed."""
    if _conversation_cache:
        _conversation_cache.cleanup_if_needed()
    if _keyword_cache:
        _keyword_cache.cleanup_if_needed()
