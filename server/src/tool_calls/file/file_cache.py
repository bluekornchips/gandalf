"""File caching system for MCP server to improve performance."""

import json
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict
import hashlib

from config.constants import (
    MCP_CACHE_TTL, 
    MAX_PROJECT_FILES,
    CACHE_FILE_NAME,
)
from src.ignored_files import filter_files
from src.utils import debug_log, log_error


class FileCache:
    """Cache for project file listings to improve MCP server performance."""
    
    def __init__(self, project_root: Path, cache_ttl: int = MCP_CACHE_TTL):
        """Initialize file cache."""
        self.project_root = project_root
        self.cache_ttl = cache_ttl
        # Store cache file in GANDALF_HOME with project-specific name
        project_hash = hashlib.md5(str(project_root).encode()).hexdigest()[:8]
        cache_filename = f"mcp_cache_{project_hash}.json"
        self.cache_file = CACHE_FILE_NAME.parent / cache_filename
        self._cache_data: Optional[dict] = None
        self._cache_lock = threading.Lock()
        
    def get_files(self, max_files: int = MAX_PROJECT_FILES) -> List[str]:
        """Get cached file list or generate if cache is stale."""
        with self._cache_lock:
            # Try to load from cache first
            if self._is_cache_valid() and self._cache_data is not None:
                cached_files = self._cache_data.get("files", [])
                debug_log(f"Using cached file list ({len(cached_files)} files)")
                return cached_files[:max_files]
            
            # Cache is stale or doesn't exist, generate new list
            debug_log("Cache is stale, generating new file list")
            files = filter_files(self.project_root, max_files)
            
            # Update cache
            self._update_cache(files)
            
            return files
    
    def preload_cache(self, max_files: int = MAX_PROJECT_FILES) -> None:
        """Preload the cache synchronously."""
        try:
            debug_log("Preloading file cache")
            files = filter_files(self.project_root, max_files)
            with self._cache_lock:
                self._update_cache(files)
            debug_log(f"Cache preload complete ({len(files)} files)")
        except Exception as e:
            log_error(e, "cache preload")
    
    def invalidate_cache(self) -> None:
        """Invalidate the current cache."""
        with self._cache_lock:
            self._cache_data = None
            if self.cache_file.exists():
                try:
                    self.cache_file.unlink()
                    debug_log("Cache file deleted")
                except Exception as e:
                    log_error(e, "deleting cache file")
    
    def _is_cache_valid(self) -> bool:
        """Check if the current cache is valid."""
        if self._cache_data is None:
            self._load_cache_from_disk()
        
        if self._cache_data is None:
            return False
        
        cache_time = self._cache_data.get("timestamp", 0)
        return (time.time() - cache_time) < self.cache_ttl
    
    def _load_cache_from_disk(self) -> None:
        """Load cache from disk if it exists."""
        if not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self._cache_data = json.load(f)
            debug_log("Loaded cache from disk")
        except Exception as e:
            log_error(e, "loading cache from disk")
            self._cache_data = None
    
    def _update_cache(self, files: List[str]) -> None:
        """Update the cache with new file list."""
        self._cache_data = {
            "timestamp": time.time(),
            "files": files,
            "project_root": str(self.project_root),
            "file_count": len(files)
        }
        
        # Save to disk
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache_data, f, indent=2)
            debug_log(f"Cache updated with {len(files)} files")
        except Exception as e:
            log_error(e, "saving cache to disk")


# Global cache instances (one per project)
_file_caches: Dict[str, FileCache] = {}
_cache_lock = threading.Lock()


def get_file_cache(project_root: Path) -> FileCache:
    """Get or create the file cache instance for a project."""
    project_key = str(project_root.resolve())
    
    with _cache_lock:
        if project_key not in _file_caches:
            # Create new cache instance
            _file_caches[project_key] = FileCache(project_root, MCP_CACHE_TTL)
            
            # Preload cache
            _file_caches[project_key].preload_cache()
    
    return _file_caches[project_key]


def get_cached_files(project_root: Path, max_files: int = MAX_PROJECT_FILES) -> List[str]:
    """Get cached file list for the project. Use instead of filter_files() for better performance."""
    cache = get_file_cache(project_root)
    return cache.get_files(max_files) 