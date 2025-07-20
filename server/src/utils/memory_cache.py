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
        """Estimate memory size of a value in bytes."""
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
        """Check if we're under memory pressure and need to evict entries."""
        now = time.time()
        if now - self._last_memory_check < self.check_interval:
            return False

        self._last_memory_check = now

        # Force garbage collection to get accurate memory reading
        gc.collect()

        # Check if current cache size exceeds limit
        return self._current_memory > self.max_memory_bytes

    def _evict_expired(self) -> None:
        """Remove expired entries based on TTL."""
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

    def _evict_lru(self, target_count: int | None = None) -> None:
        """Remove least recently used entries when memory pressure persists."""
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
        """Remove a key from all internal structures and update memory tracking."""
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
        """Clear all cache entries and reset memory tracking."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._cache_sizes.clear()
            self._current_memory = 0
            log_debug("Cleared all cache entries")

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics for monitoring and debugging."""
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
        """Perform cache cleanup if memory pressure is detected."""
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
    """Get the global conversation cache instance with optimized settings."""
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
    """Get the global keyword cache instance with keyword-optimized settings."""
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
    """Clear all global caches and reset memory usage."""
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
