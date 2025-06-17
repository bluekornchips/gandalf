"""
Loads weights from weights.yaml and provides all AI constants.
"""

from pathlib import Path
import os
import json
from typing import Any, Dict, Optional, Callable


class WeightsLoader:
    """Handles loading AI weights from YAML with environment variable fallbacks."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the weights loader.
        
        Args:
            config_dir: Directory containing weights.yaml. Defaults to gandalf root.
        """
        if config_dir is None:
            # Default to gandalf directory (parent of server directory)
            config_dir = Path(__file__).parent.parent.parent
        
        self.config_dir = config_dir
        self._yaml_available = self._check_yaml_availability()
        self._weights_config = None
        self._weights_loaded = False
    
    def _check_yaml_availability(self) -> bool:
        """Check if PyYAML is available for direct YAML loading."""
        try:
            import yaml
            return True
        except ImportError:
            return False
    
    def _load_weights_yaml(self) -> Optional[Dict[str, Any]]:
        """Load weights.yaml if PyYAML is available."""
        if not self._yaml_available:
            return None
        
        try:
            import yaml
            weights_file = self.config_dir / "weights.yaml"
            if weights_file.exists():
                with open(weights_file, 'r') as f:
                    return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError):
            pass
        
        return None
    
    def get_value(self, yaml_path: str, env_var: str, default: Any, convert_func: Callable = str) -> Any:
        """Get a weight value from YAML file or environment variable.
        
        Args:
            yaml_path: Dot-separated path in YAML (e.g., 'weights.recent_modification')
            env_var: Environment variable name
            default: Default value if not found
            convert_func: Function to convert the value (str, int, float, bool)
            
        Returns:
            The configuration value, converted to the appropriate type
        """
        # Ensure weights are loaded
        if not self._weights_loaded:
            self._weights_config = self._load_weights_yaml()
            self._weights_loaded = True
        
        config = self._weights_config
        if config:
            # Navigate YAML path like 'weights.recent_modification' -> config['weights']['recent_modification']
            value = config
            for key in yaml_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    value = None
                    break
            
            if value is not None:
                return convert_func(value) if convert_func != bool else value
        
        # Fall back to environment variable
        env_value = os.getenv(env_var, str(default))
        if convert_func == bool:
            return env_value.lower() in ('true', '1', 'yes', 'on')
        return convert_func(env_value)
    
    def get_extensions_dict(self, env_var: str = 'CONTEXT_PRIORITY_EXTENSIONS') -> Dict[str, float]:
        """Get file extension priorities as a dictionary."""
        # Ensure weights are loaded
        if not self._weights_loaded:
            self._weights_config = self._load_weights_yaml()
            self._weights_loaded = True
        
        # Try from weights config first
        if self._weights_config and 'file_extensions' in self._weights_config:
            extensions = self._weights_config['file_extensions']
            # Ensure extensions have dots
            return {f'.{k}' if not k.startswith('.') else k: float(v) 
                    for k, v in extensions.items()}
        
        # Fall back to environment variable (JSON format)
        try:
            extensions = json.loads(os.getenv(env_var, '{}'))
            return {f'.{k}' if not k.startswith('.') else k: float(v) 
                    for k, v in extensions.items()}
        except (json.JSONDecodeError, ValueError):
            # Return sensible defaults
            return {
                '.py': 3.0, '.js': 2.5, '.ts': 2.5, '.jsx': 2.0, '.tsx': 2.0,
                '.java': 2.0, '.cpp': 2.0, '.c': 2.0, '.go': 2.0, '.rs': 2.0,
                '.md': 1.5, '.yml': 1.0, '.yaml': 1.0, '.json': 1.0, '.toml': 1.0
            }
    
    def get_directories_dict(self, env_var: str = 'CONTEXT_IMPORTANT_DIRS') -> Dict[str, float]:
        """Get directory importance scores as a dictionary."""
        # Ensure weights are loaded
        if not self._weights_loaded:
            self._weights_config = self._load_weights_yaml()
            self._weights_loaded = True
        
        # Try from weights config first
        if self._weights_config and 'directories' in self._weights_config:
            return {k: float(v) for k, v in self._weights_config['directories'].items()}
        
        # Fall back to environment variable (JSON format)
        try:
            return {k: float(v) for k, v in json.loads(os.getenv(env_var, '{}')).items()}
        except (json.JSONDecodeError, ValueError):
            # Return sensible defaults
            return {
                'src': 3.0, 'lib': 2.5, 'components': 2.0, 'utils': 2.0, 
                'api': 2.0, 'services': 2.0, 'models': 2.0, 'views': 1.5, 
                'tests': 1.0, 'docs': 0.5
            }


# Global weights loader instance
_weights_loader = WeightsLoader()

########################################################
# AI Context Intelligence Constants
########################################################

# Enable/disable context intelligence features
ENABLE_CONTEXT_INTELLIGENCE = _weights_loader.get_value('enabled', 'ENABLE_CONTEXT_INTELLIGENCE', True, bool)

# Context weights - loaded from weights.yaml or environment variables
CONTEXT_WEIGHTS = {
    'recent_modification': _weights_loader.get_value('weights.recent_modification', 'WEIGHT_RECENT_MODIFICATION', 5.0, float),
    'file_size_optimal': _weights_loader.get_value('weights.file_size_optimal', 'WEIGHT_FILE_SIZE_OPTIMAL', 2.0, float),
    'import_relationship': _weights_loader.get_value('weights.import_relationship', 'WEIGHT_IMPORT_RELATIONSHIP', 4.0, float),
    'conversation_mention': _weights_loader.get_value('weights.conversation_mention', 'WEIGHT_CONVERSATION_MENTION', 3.0, float),
    'git_activity': _weights_loader.get_value('weights.git_activity', 'WEIGHT_GIT_ACTIVITY', 3.5, float),
    'file_type_priority': _weights_loader.get_value('weights.file_type_priority', 'WEIGHT_FILE_TYPE_PRIORITY', 1.5, float),
    'directory_importance': _weights_loader.get_value('weights.directory_importance', 'WEIGHT_DIRECTORY_IMPORTANCE', 1.0, float),
}

# Context intelligence display limits
MAX_HIGH_PRIORITY_DISPLAY = _weights_loader.get_value('display.max_high_priority', 'MAX_HIGH_PRIORITY_DISPLAY', 5, int)
MAX_MEDIUM_PRIORITY_DISPLAY = _weights_loader.get_value('display.max_medium_priority', 'MAX_MEDIUM_PRIORITY_DISPLAY', 10, int)
MAX_TOP_FILES_DISPLAY = _weights_loader.get_value('display.max_top_files', 'MAX_TOP_FILES_DISPLAY', 10, int)

# Score thresholds for categorization
CONTEXT_HIGH_PRIORITY_THRESHOLD = _weights_loader.get_value('thresholds.high_priority', 'CONTEXT_HIGH_PRIORITY_THRESHOLD', 5.0, float)
CONTEXT_MEDIUM_PRIORITY_THRESHOLD = _weights_loader.get_value('thresholds.medium_priority', 'CONTEXT_MEDIUM_PRIORITY_THRESHOLD', 2.0, float)
CONTEXT_TOP_FILES_COUNT = _weights_loader.get_value('thresholds.top_files_count', 'CONTEXT_TOP_FILES_COUNT', 10, int)

# Context intelligence scoring parameters
CONTEXT_MIN_SCORE = _weights_loader.get_value('scoring.min_score', 'CONTEXT_MIN_SCORE', 0.1, float)
CONTEXT_GIT_CACHE_TTL = _weights_loader.get_value('scoring.git_cache_ttl', 'CONTEXT_GIT_CACHE_TTL', 300, int)
CONTEXT_GIT_LOOKBACK_DAYS = _weights_loader.get_value('scoring.git_lookback_days', 'CONTEXT_GIT_LOOKBACK_DAYS', 7, int)
CONTEXT_GIT_TIMEOUT = _weights_loader.get_value('scoring.git_timeout', 'CONTEXT_GIT_TIMEOUT', 10, int)

# File size scoring thresholds and multipliers
CONTEXT_FILE_SIZE_OPTIMAL_MIN = _weights_loader.get_value('scoring.file_size.optimal_min', 'CONTEXT_FILE_SIZE_OPTIMAL_MIN', 1000, int)
CONTEXT_FILE_SIZE_OPTIMAL_MAX = _weights_loader.get_value('scoring.file_size.optimal_max', 'CONTEXT_FILE_SIZE_OPTIMAL_MAX', 50000, int)
CONTEXT_FILE_SIZE_ACCEPTABLE_MAX = _weights_loader.get_value('scoring.file_size.acceptable_max', 'CONTEXT_FILE_SIZE_ACCEPTABLE_MAX', 200000, int)
CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER = _weights_loader.get_value('scoring.file_size.acceptable_multiplier', 'CONTEXT_FILE_SIZE_ACCEPTABLE_MULTIPLIER', 0.6, float)
CONTEXT_FILE_SIZE_LARGE_MULTIPLIER = _weights_loader.get_value('scoring.file_size.large_multiplier', 'CONTEXT_FILE_SIZE_LARGE_MULTIPLIER', 0.2, float)

# Recent modification time thresholds and multipliers
CONTEXT_RECENT_HOUR_THRESHOLD = _weights_loader.get_value('scoring.recent_modifications.hour_threshold', 'CONTEXT_RECENT_HOUR_THRESHOLD', 1, int)
CONTEXT_RECENT_DAY_THRESHOLD = _weights_loader.get_value('scoring.recent_modifications.day_threshold', 'CONTEXT_RECENT_DAY_THRESHOLD', 24, int)
CONTEXT_RECENT_WEEK_THRESHOLD = _weights_loader.get_value('scoring.recent_modifications.week_threshold', 'CONTEXT_RECENT_WEEK_THRESHOLD', 168, int)
CONTEXT_RECENT_DAY_MULTIPLIER = _weights_loader.get_value('scoring.recent_modifications.day_multiplier', 'CONTEXT_RECENT_DAY_MULTIPLIER', 0.7, float)
CONTEXT_RECENT_WEEK_MULTIPLIER = _weights_loader.get_value('scoring.recent_modifications.week_multiplier', 'CONTEXT_RECENT_WEEK_MULTIPLIER', 0.4, float)

# File extension and directory priorities (loaded from weights.yaml or environment)
CONTEXT_PRIORITY_EXTENSIONS = _weights_loader.get_extensions_dict()
CONTEXT_IMPORTANT_DIRS = _weights_loader.get_directories_dict() 