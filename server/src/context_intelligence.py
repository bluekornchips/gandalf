import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import subprocess

from config.load_weights import (
    ENABLE_CONTEXT_INTELLIGENCE, 
    CONTEXT_WEIGHTS,
    CONTEXT_MIN_SCORE,
    CONTEXT_GIT_CACHE_TTL,
    CONTEXT_GIT_LOOKBACK_DAYS,
    CONTEXT_GIT_TIMEOUT,
    CONTEXT_FILE_SIZE_OPTIMAL_MIN,
    CONTEXT_FILE_SIZE_OPTIMAL_MAX,
    CONTEXT_FILE_SIZE_ACCEPTABLE_MAX,
    CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER,
    CONTEXT_FILE_SIZE_LARGE_MULTIPLIER,
    CONTEXT_RECENT_HOUR_THRESHOLD,
    CONTEXT_RECENT_DAY_THRESHOLD,
    CONTEXT_RECENT_WEEK_THRESHOLD,
    CONTEXT_RECENT_DAY_MULTIPLIER,
    CONTEXT_RECENT_WEEK_MULTIPLIER,
    CONTEXT_PRIORITY_EXTENSIONS,
    CONTEXT_IMPORTANT_DIRS,
    CONTEXT_HIGH_PRIORITY_THRESHOLD,
    CONTEXT_MEDIUM_PRIORITY_THRESHOLD,
    CONTEXT_TOP_FILES_COUNT
)
from src.utils import log_info, debug_log


class ContextIntelligence:
    """Intelligent context scoring and prioritization system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._git_activity_cache = {}
        self._import_cache = {}
        self._cache_time = 0
        
        # Use configurable weights and parameters from constants
        self.weights = CONTEXT_WEIGHTS.copy()
        self.min_score = CONTEXT_MIN_SCORE
        self.git_cache_ttl = CONTEXT_GIT_CACHE_TTL
        self.git_lookback_days = CONTEXT_GIT_LOOKBACK_DAYS
        self.git_timeout = CONTEXT_GIT_TIMEOUT
        
        # Score thresholds for categorization
        self.high_priority_threshold = CONTEXT_HIGH_PRIORITY_THRESHOLD
        self.medium_priority_threshold = CONTEXT_MEDIUM_PRIORITY_THRESHOLD
        self.top_files_count = CONTEXT_TOP_FILES_COUNT
        
        # File size scoring parameters
        self.file_size_optimal_min = CONTEXT_FILE_SIZE_OPTIMAL_MIN
        self.file_size_optimal_max = CONTEXT_FILE_SIZE_OPTIMAL_MAX
        self.file_size_acceptable_max = CONTEXT_FILE_SIZE_ACCEPTABLE_MAX
        self.file_size_acceptable_multiplier = CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER
        self.file_size_large_multiplier = CONTEXT_FILE_SIZE_LARGE_MULTIPLIER
        
        # Recent modification time parameters
        self.recent_hour_threshold = CONTEXT_RECENT_HOUR_THRESHOLD
        self.recent_day_threshold = CONTEXT_RECENT_DAY_THRESHOLD
        self.recent_week_threshold = CONTEXT_RECENT_WEEK_THRESHOLD
        self.recent_day_multiplier = CONTEXT_RECENT_DAY_MULTIPLIER
        self.recent_week_multiplier = CONTEXT_RECENT_WEEK_MULTIPLIER
        
        # Priority mappings from configuration
        self.priority_extensions = {f'.{k}': v for k, v in CONTEXT_PRIORITY_EXTENSIONS.items()}
        self.important_dirs = CONTEXT_IMPORTANT_DIRS
        
        debug_log(f"Context intelligence initialized with weights: {self.weights}")
        debug_log(f"Score thresholds - High: {self.high_priority_threshold}, Medium: {self.medium_priority_threshold}")
        debug_log(f"Top files count: {self.top_files_count}")
        debug_log(f"File extension priorities: {self.priority_extensions}")
        debug_log(f"Directory importance: {self.important_dirs}")
    
    def score_file_relevance(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> float:
        """Calculate relevance score for a file."""
        if not ENABLE_CONTEXT_INTELLIGENCE:
            return 1.0  # Equal weight if intelligence disabled
            
        try:
            full_path = self.project_root / file_path
            if not full_path.exists():
                return 0.0
            
            score = 0.0
            
            score += self._score_recent_modification(full_path)
            score += self._score_file_size(full_path)
            score += self._score_file_type(file_path)
            score += self._score_directory_importance(file_path)
            score += self._score_git_activity(file_path)
            
            if context and 'active_files' in context:
                score += self._score_import_relationships(file_path, context['active_files'])
            
            debug_log(f"File {file_path} scored {score:.2f}")
            return max(score, self.min_score)  # Use configurable minimum score
            
        except Exception as e:
            debug_log(f"Error scoring file {file_path}: {e}")
            return self.min_score
    
    def _score_recent_modification(self, full_path: Path) -> float:
        """Score based on recent file modifications."""
        try:
            mod_time = full_path.stat().st_mtime
            now = time.time()
            hours_ago = (now - mod_time) / 3600
            
            if hours_ago < self.recent_hour_threshold:
                return self.weights['recent_modification']
            elif hours_ago < self.recent_day_threshold:
                return self.weights['recent_modification'] * self.recent_day_multiplier
            elif hours_ago < self.recent_week_threshold:
                return self.weights['recent_modification'] * self.recent_week_multiplier
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _score_file_size(self, full_path: Path) -> float:
        """Score based on optimal file size for analysis."""
        try:
            size = full_path.stat().st_size
            
            # Optimal range: configurable min-max (good for AI analysis)
            if self.file_size_optimal_min <= size <= self.file_size_optimal_max:
                return self.weights['file_size_optimal']
            # Acceptable range: larger files with reduced score
            elif self.file_size_optimal_max < size <= self.file_size_acceptable_max:
                return self.weights['file_size_optimal'] * self.file_size_acceptable_multiplier
            # Large files get lower priority
            elif size > self.file_size_acceptable_max:
                return self.weights['file_size_optimal'] * self.file_size_large_multiplier
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _score_file_type(self, file_path: str) -> float:
        """Score based on file extension priority."""
        suffix = Path(file_path).suffix.lower()
        extension_score = self.priority_extensions.get(suffix, 0.0)
        return extension_score * self.weights['file_type_priority']
    
    def _score_directory_importance(self, file_path: str) -> float:
        """Score based on directory importance."""
        parts = Path(file_path).parts
        score = 0.0
        
        for part in parts[:-1]:  # Exclude filename
            dir_score = self.important_dirs.get(part.lower(), 0.0)
            score += dir_score * self.weights['directory_importance']
        
        return score
    
    def _score_git_activity(self, file_path: str) -> float:
        """Score based on recent git activity."""
        try:
            if time.time() - self._cache_time > self.git_cache_ttl:
                self._load_git_cache()
            
            activity_score = self._git_activity_cache.get(file_path, 0.0)
            return activity_score * self.weights['git_activity']
            
        except Exception:
            return 0.0
    
    def _load_git_cache(self):
        """Load git activity cache."""
        try:
            # Get files changed in last N days (configurable)
            result = subprocess.run([
                'git', 'log', f'--since={self.git_lookback_days} days ago', '--name-only', '--pretty=format:', '--'
            ], cwd=self.project_root, capture_output=True, text=True, timeout=self.git_timeout)
            
            if result.returncode == 0:
                files = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                file_counts = {}
                
                for file in files:
                    file_counts[file] = file_counts.get(file, 0) + 1
                
                # Normalize scores
                max_count = max(file_counts.values()) if file_counts else 1
                for file, count in file_counts.items():
                    self._git_activity_cache[file] = count / max_count
                
                self._cache_time = time.time()
                debug_log(f"Loaded git activity cache with {len(file_counts)} files")
            
        except Exception as e:
            debug_log(f"Error loading git cache: {e}")
    
    def _score_import_relationships(self, file_path: str, active_files: List[str]) -> float:
        """Score based on import relationships with active files."""
        # Simplified import relationship scoring
        # In a full implementation, this would parse import statements
        try:
            file_stem = Path(file_path).stem
            score = 0.0
            
            for active_file in active_files:
                active_stem = Path(active_file).stem
                
                # Simple heuristic: files with similar names might be related
                if file_stem in active_stem or active_stem in file_stem:
                    score += 0.5
                
                # Files in same directory are likely related
                if Path(file_path).parent == Path(active_file).parent:
                    score += 0.3
            
            return min(score * self.weights['import_relationship'], self.weights['import_relationship'])
            
        except Exception:
            return 0.0
    
    def rank_files(self, files: List[str], context: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[Tuple[str, float]]:
        """Rank files by relevance score."""
        scored_files = [(file, self.score_file_relevance(file, context)) for file in files]
        scored_files.sort(key=lambda x: x[1], reverse=True)
        
        if limit:
            scored_files = scored_files[:limit]
        
        log_info(f"Ranked {len(scored_files)} files by relevance")
        return scored_files
    
    def get_context_summary(self, files: List[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate intelligent context summary."""
        ranked_files = self.rank_files(files, context)
        
        # Categorize by score ranges
        high_priority = [f for f, s in ranked_files if s >= self.high_priority_threshold]
        medium_priority = [f for f, s in ranked_files if self.medium_priority_threshold <= s < self.high_priority_threshold]
        low_priority = [f for f, s in ranked_files if self.min_score <= s < self.medium_priority_threshold]
        
        return {
            'total_files': len(files),
            'high_priority_files': high_priority,
            'medium_priority_files': medium_priority,
            'low_priority_files': low_priority,
            'top_X_files': [f for f, s in ranked_files[:self.top_files_count]],
            'scoring_weights': self.weights,
            'intelligence_enabled': ENABLE_CONTEXT_INTELLIGENCE,
            'scoring_parameters': {
                'min_score': self.min_score,
                'git_cache_ttl': self.git_cache_ttl,
                'git_lookback_days': self.git_lookback_days,
                'thresholds': {
                    'high_priority': self.high_priority_threshold,
                    'medium_priority': self.medium_priority_threshold,
                    'top_files_count': self.top_files_count
                },
                'file_size_ranges': {
                    'optimal_min': self.file_size_optimal_min,
                    'optimal_max': self.file_size_optimal_max,
                    'acceptable_max': self.file_size_acceptable_max
                }
            }
        }


# Global context intelligence instance
_context_intelligence: Optional[ContextIntelligence] = None


def get_context_intelligence(project_root: Path) -> ContextIntelligence:
    """Get or create context intelligence instance."""
    global _context_intelligence
    
    if _context_intelligence is None or _context_intelligence.project_root != project_root:
        _context_intelligence = ContextIntelligence(project_root)
    
    return _context_intelligence 