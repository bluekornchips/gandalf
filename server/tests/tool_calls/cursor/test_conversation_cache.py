"""
Tests for cursor conversation caching functionality.

This module tests the caching utilities that improve performance
by storing and retrieving conversation data.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from src.tool_calls.cursor.conversation_cache import (
    clear_cache,
    get_cache_info,
    get_project_cache_hash,
    is_cache_valid,
    load_cached_conversations,
    save_conversations_to_cache,
)


class TestConversationCache:
    """Test conversation caching functionality."""

    @pytest.fixture
    def temp_project_root(self):
        """Create a temporary project root for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            # Create some test files
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "src").mkdir()
            (project_root / "src" / "main.py").write_text("print('hello')")
            yield project_root

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversation data for testing."""
        return [
            {
                "id": "conv_frodo_001",
                "title": "Quest planning discussion",
                "message_count": 15,
                "relevance_score": 0.85,
                "created_at": "2024-03-21T10:30:00Z",
                "snippet": "We need to plan our journey to Mordor...",
            },
            {
                "id": "conv_gandalf_002",
                "title": "Magic system implementation",
                "message_count": 8,
                "relevance_score": 0.92,
                "created_at": "2024-03-21T11:15:00Z",
                "snippet": "The staff requires proper enchantment...",
            },
        ]

    def test_get_project_cache_hash(self, temp_project_root):
        """Test cache hash generation for projects."""
        context_keywords = ["python", "testing", "cache"]

        # Generate hash
        hash1 = get_project_cache_hash(temp_project_root, context_keywords)

        # Should be consistent
        hash2 = get_project_cache_hash(temp_project_root, context_keywords)
        assert hash1 == hash2

        # Should be a 16-character string
        assert len(hash1) == 16
        assert isinstance(hash1, str)

        # Different keywords should produce different hash
        different_keywords = ["javascript", "testing", "cache"]
        hash3 = get_project_cache_hash(temp_project_root, different_keywords)
        assert hash1 != hash3

    def test_get_project_cache_hash_with_nonexistent_path(self):
        """Test cache hash generation with nonexistent path."""
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")
        context_keywords = ["test"]

        # Should still generate a hash
        cache_hash = get_project_cache_hash(nonexistent_path, context_keywords)
        assert len(cache_hash) == 16
        assert isinstance(cache_hash, str)

    def test_is_cache_valid_no_metadata(self, temp_project_root):
        """Test cache validation when metadata file doesn't exist."""
        context_keywords = ["test"]

        # No cache files exist
        is_valid = is_cache_valid(temp_project_root, context_keywords)
        assert not is_valid

    def test_is_cache_valid_expired_cache(self, temp_project_root):
        """Test cache validation with expired cache."""
        context_keywords = ["test"]

        # Create expired metadata
        metadata_file = temp_project_root / "metadata.json"
        cache_file = temp_project_root / "conversations.json"

        # Create metadata with old timestamp (more than TTL hours ago)
        old_timestamp = time.time() - (25 * 3600)  # 25 hours ago
        metadata = {
            "timestamp": old_timestamp,
            "context_hash": get_project_cache_hash(temp_project_root, context_keywords),
            "conversation_count": 5,
        }

        metadata_file.write_text(json.dumps(metadata))
        cache_file.write_text('{"test": "data"}')

        is_valid = is_cache_valid(temp_project_root, context_keywords)
        assert not is_valid

    def test_is_cache_valid_corrupt_metadata(self, temp_project_root):
        """Test cache validation with corrupt metadata file."""
        context_keywords = ["test"]

        metadata_file = temp_project_root / "metadata.json"
        cache_file = temp_project_root / "conversations.json"

        # Create corrupt metadata
        metadata_file.write_text("not valid json")
        cache_file.write_text('{"test": "data"}')

        is_valid = is_cache_valid(temp_project_root, context_keywords)
        assert not is_valid

    def test_load_cached_conversations_no_file(self):
        """Test loading cached conversations when file doesn't exist."""
        # Use a truly nonexistent path
        nonexistent_path = Path("/nonexistent/path/that/does/not/exist")
        result = load_cached_conversations(nonexistent_path)
        assert result is None

    def test_load_cached_conversations_corrupt_file(self, temp_project_root):
        """Test loading cached conversations with corrupt file."""
        cache_file = temp_project_root / "conversations.json"
        cache_file.write_text("not valid json")

        result = load_cached_conversations(temp_project_root)
        assert result is None

    def test_load_cached_conversations_success(
        self, temp_project_root, sample_conversations
    ):
        """Test successful loading of cached conversations."""
        cache_file = temp_project_root / "conversations.json"

        cache_data = {
            "conversations": sample_conversations,
            "total_found": len(sample_conversations),
            "processing_time": 1.5,
            "cached_at": time.time(),
        }

        cache_file.write_text(json.dumps(cache_data))

        result = load_cached_conversations(temp_project_root)
        assert result is not None
        assert "conversations" in result
        assert len(result["conversations"]) == 2
        assert result["conversations"][0]["id"] == "conv_frodo_001"

    def test_save_conversations_to_cache(self, temp_project_root, sample_conversations):
        """Test saving conversations to cache."""
        context_keywords = ["python", "testing"]
        processing_time = 2.3
        total_found = len(sample_conversations)

        # Save to cache
        save_conversations_to_cache(
            temp_project_root,
            sample_conversations,
            context_keywords,
            processing_time,
            total_found,
        )

        # Verify cache file was created
        cache_file = temp_project_root / "conversations.json"
        metadata_file = temp_project_root / "metadata.json"

        assert cache_file.exists()
        assert metadata_file.exists()

        # Verify cache content
        cache_data = json.loads(cache_file.read_text())
        assert "conversations" in cache_data
        assert len(cache_data["conversations"]) == 2
        assert cache_data["processing_time"] == processing_time

        # Verify metadata content
        metadata = json.loads(metadata_file.read_text())
        assert "timestamp" in metadata
        assert "context_hash" in metadata
        assert metadata["conversation_count"] == 2

    def test_clear_cache(self, temp_project_root):
        """Test clearing cache files."""
        # Create cache files
        cache_file = temp_project_root / "conversations.json"
        metadata_file = temp_project_root / "metadata.json"

        cache_file.write_text('{"test": "data"}')
        metadata_file.write_text('{"timestamp": 123}')

        assert cache_file.exists()
        assert metadata_file.exists()

        # Clear cache
        result = clear_cache(temp_project_root)
        assert result is True

        assert not cache_file.exists()
        assert not metadata_file.exists()

    def test_clear_cache_no_files(self, temp_project_root):
        """Test clearing cache when no files exist."""
        result = clear_cache(temp_project_root)
        assert result is False

    def test_get_cache_info(self, temp_project_root, sample_conversations):
        """Test getting cache information."""
        # Test when no cache exists
        info = get_cache_info(temp_project_root)
        assert not info["cache_exists"]
        assert not info["metadata_exists"]
        assert info["cache_size"] == 0

        # Create cache and test
        context_keywords = ["test"]
        save_conversations_to_cache(
            temp_project_root,
            sample_conversations,
            context_keywords,
            1.0,
            len(sample_conversations),
        )

        info = get_cache_info(temp_project_root)
        assert info["cache_exists"]
        assert info["metadata_exists"]
        assert info["cache_size"] > 0
        assert info["conversation_count"] == 2
        assert isinstance(info["cache_age_hours"], float)

    def test_cache_size_validation(self, temp_project_root):
        """Test cache validation based on minimum size."""
        context_keywords = ["test"]

        # Create very small cache file (below minimum)
        cache_file = temp_project_root / "conversations.json"
        metadata_file = temp_project_root / "metadata.json"

        cache_file.write_text("{}")  # Very small file

        metadata = {
            "timestamp": time.time(),
            "context_hash": get_project_cache_hash(temp_project_root, context_keywords),
            "conversation_count": 0,
        }
        metadata_file.write_text(json.dumps(metadata))

        # Should be invalid due to small size
        is_valid = is_cache_valid(temp_project_root, context_keywords)
        assert not is_valid

    def test_cache_context_hash_mismatch(self, temp_project_root):
        """Test cache invalidation when context hash doesn't match."""
        context_keywords = ["test"]
        different_keywords = ["different"]

        cache_file = temp_project_root / "conversations.json"
        metadata_file = temp_project_root / "metadata.json"

        cache_file.write_text('{"conversations": [], "test": "data"}')

        # Create metadata with hash for different keywords
        metadata = {
            "timestamp": time.time(),
            "context_hash": get_project_cache_hash(
                temp_project_root, different_keywords
            ),
            "conversation_count": 1,
        }
        metadata_file.write_text(json.dumps(metadata))

        # Should be invalid due to hash mismatch
        is_valid = is_cache_valid(temp_project_root, context_keywords)
        assert not is_valid
