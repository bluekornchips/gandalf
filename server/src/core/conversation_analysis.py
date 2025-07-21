"""
Conversation analysis and relevance scoring for Claude Code conversations.

Provides intelligent analysis of conversation content, keyword matching,
and relevance scoring for conversation recall and search functionality.
"""

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.config.config_data import (
    CONTEXT_SKIP_DIRECTORIES,
    FILE_REFERENCE_PATTERNS,
    TECHNOLOGY_KEYWORD_MAPPING,
)
from src.config.constants.cache import (
    CONTEXT_CACHE_TTL_SECONDS,
)
from src.config.constants.context import (
    CONTEXT_KEYWORD_MAX_COUNT,
    CONTEXT_MAX_FILES_TO_CHECK,
    CONTEXT_MIN_EXTENSIONS_BEFORE_DEEP_SCAN,
)
from src.config.constants.conversation import (
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
)
from src.config.weights import WeightsManager
from src.utils.common import log_debug, log_error

# Global cache for context keywords
_context_keywords_cache = {}
_context_keywords_cache_time = {}


def generate_shared_context_keywords(project_root: Path) -> list[str]:
    """Generate context keywords with intelligent caching and weighting."""
    project_root_str = str(project_root)

    # More specific cache key that includes project modification info
    # for better cache hits
    cache_key = f"{project_root_str}"

    # Add project file modification time to cache key for better invalidation
    try:
        common_files = [
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "README.md",
        ]
        latest_mtime = 0
        for file_name in common_files:
            file_path = project_root / file_name
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                latest_mtime = max(latest_mtime, mtime)
        if latest_mtime > 0:
            cache_key += f"_{int(latest_mtime)}"
    except (OSError, ValueError):
        pass

    current_time = time.time()

    # Check cache
    if (
        cache_key in _context_keywords_cache
        and cache_key in _context_keywords_cache_time
        and current_time - _context_keywords_cache_time[cache_key]
        < CONTEXT_CACHE_TTL_SECONDS
    ):
        log_debug(f"Using cached context keywords for {project_root.name}")
        return _context_keywords_cache[cache_key]

    # Generate keywords
    log_debug(f"Generating fresh context keywords for {project_root.name}")
    keywords = _extract_project_keywords(project_root)

    # Cache results
    _context_keywords_cache[cache_key] = keywords
    _context_keywords_cache_time[cache_key] = current_time

    # Clean old cache entries
    for key in list(_context_keywords_cache_time.keys()):
        if current_time - _context_keywords_cache_time[key] > CONTEXT_CACHE_TTL_SECONDS:
            _context_keywords_cache.pop(key, None)
            _context_keywords_cache_time.pop(key, None)

    return keywords


def _extract_project_keywords(project_root: Path) -> list[str]:
    """Extract keywords from project files and structure."""
    keywords = []

    try:
        # Add project name
        project_name = project_root.name.lower()
        keywords.append(project_name)

        # Check for common project files and extract keywords
        common_files = [
            "package.json",
            "pyproject.toml",
            "README.md",
            "CLAUDE.md",
            "requirements.txt",
        ]

        for file_name in common_files:
            file_path = project_root / file_name
            if file_path.exists():
                try:
                    # Use a larger limit for keyword extraction to ensure
                    # we can read small config files
                    content = file_path.read_text(encoding="utf-8")[
                        :2000
                    ]  # Increased from CONTEXT_KEYWORDS_FILE_LIMIT
                    keywords.extend(_extract_keywords_from_file(file_name, content))
                except (OSError, UnicodeDecodeError):
                    continue

        # Add technology keywords based on file extensions
        keywords.extend(_extract_tech_keywords_from_files(project_root))

        # Remove duplicates, filter, and limit
        keywords = list(set(keywords))
        keywords = [k for k in keywords if len(k) > 1]  # Filter out single chars
        keywords = keywords[:CONTEXT_KEYWORD_MAX_COUNT]

        log_debug(f"Generated {len(keywords)} context keywords")
        return keywords

    except (OSError, ValueError, AttributeError, UnicodeDecodeError) as e:
        log_error(e, "extracting project keywords")
        return [project_name] if "project_name" in locals() else []


def _extract_keywords_from_file(file_name: str, content: str) -> list[str]:
    """Extract keywords from specific file types."""
    keywords = []

    try:
        if file_name == "package.json":
            # Extract npm package keywords
            try:
                data = json.loads(content)
                if "name" in data:
                    keywords.append(data["name"])
                if "keywords" in data:
                    keywords.extend(data["keywords"][:5])
                if "dependencies" in data:
                    # Add major framework names
                    deps = data["dependencies"].keys()
                    for dep in deps:
                        if dep in [
                            "react",
                            "vue",
                            "angular",
                            "express",
                            "next",
                            "nuxt",
                        ]:
                            keywords.append(dep)
            except json.JSONDecodeError:
                pass

        elif file_name in ["README.md", "CLAUDE.md"]:
            # Extract common tech terms from markdown
            content_lower = content.lower()
            # Flatten the technology keyword mapping to get all terms
            all_tech_terms = []
            for (
                tech_category,
                tech_terms,
            ) in TECHNOLOGY_KEYWORD_MAPPING.items():
                all_tech_terms.extend(tech_terms)

            for term in all_tech_terms:
                if term.lower() in content_lower:
                    keywords.append(term)

        elif file_name == "pyproject.toml":
            # Extract Python project info
            content_lower = content.lower()
            if "django" in content_lower:
                keywords.append("django")
            if "flask" in content_lower:
                keywords.append("flask")
            if "fastapi" in content_lower:
                keywords.append("fastapi")

    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
        log_debug(f"Error extracting keywords from {file_name}: {e}")

    return keywords


def _extract_tech_keywords_from_files(project_root: Path) -> list[str]:
    """Extract technology keywords based on file extensions in project."""
    keywords = []

    try:
        # Fast sampling approach: only check top-level directories and limit depth
        file_extensions = set()
        files_checked = 0

        # Check top-level files first (most likely to indicate tech stack)
        for file_path in project_root.iterdir():
            if files_checked >= CONTEXT_MAX_FILES_TO_CHECK:
                break
            if file_path.is_file():
                ext = file_path.suffix.lower()
                if ext:
                    file_extensions.add(ext)
                files_checked += 1

        # If we haven't found enough variety, check one level deeper but with limits
        if (
            len(file_extensions) < CONTEXT_MIN_EXTENSIONS_BEFORE_DEEP_SCAN
            and files_checked < CONTEXT_MAX_FILES_TO_CHECK
        ):
            for subdir in project_root.iterdir():
                if files_checked >= CONTEXT_MAX_FILES_TO_CHECK:
                    break
                if subdir.is_dir() and not subdir.name.startswith("."):
                    # Skip common directories that don't indicate tech stack
                    if subdir.name in CONTEXT_SKIP_DIRECTORIES:
                        continue

                    try:
                        for file_path in subdir.iterdir():
                            if files_checked >= CONTEXT_MAX_FILES_TO_CHECK:
                                break
                            if file_path.is_file():
                                ext = file_path.suffix.lower()
                                if ext:
                                    file_extensions.add(ext)
                                files_checked += 1
                    except (OSError, PermissionError):
                        continue

        # Map extensions to technologies (only supported languages)
        ext_mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".vue": "vue",
        }

        for ext in file_extensions:
            if ext in ext_mapping:
                keywords.append(ext_mapping[ext])

    except (OSError, PermissionError, ValueError, AttributeError) as e:
        log_debug(f"Error extracting tech keywords: {e}")

    return keywords


def analyze_session_relevance(
    session_content: str,
    context_keywords: list[str],
    session_metadata: dict[str, Any],
    include_detailed_analysis: bool = False,
    weights_config: Any | None = None,
) -> tuple[float, dict[str, Any]]:
    """Analyze session relevance with configurable weights."""
    try:
        # Return 0 score for empty content
        if not session_content or not session_content.strip():
            return 0.0, {
                "keyword_matches": [],
                "file_references": [],
                "recency_score": 0.0,
                "conversation_type": "general",
            }

        weights = weights_config or WeightsManager.get_default()
        conversation_weights = weights.get_dict("conversation")

        keyword_score, keyword_matches = score_keyword_matches(
            session_content, context_keywords, weights
        )
        file_score, file_references = score_file_references(session_content, weights)
        recency_score = score_session_recency(session_metadata, weights)

        total_score = 0.0
        total_score += keyword_score * conversation_weights.get("keyword_match", 1.0)
        total_score += recency_score * conversation_weights.get("recency", 1.0)
        total_score += file_score * conversation_weights.get("file_reference", 1.0)

        conversation_type = classify_conversation_type(
            session_content, keyword_matches, file_references
        )

        # Add type-specific scoring bonuses
        type_bonus = get_conversation_type_bonus(conversation_type, weights)
        total_score += type_bonus

        analysis = {
            "keyword_matches": keyword_matches,
            "file_references": file_references,
            "recency_score": recency_score,
            "conversation_type": conversation_type,
        }

        return (
            min(total_score, 5.0),
            analysis,
        )  # should be a constant for the max score

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        log_error(e, "analyzing session relevance")
        return 0.0, {"conversation_type": "general"}


def score_keyword_matches(
    text: str, keywords: list[str], weights_config: Any | None = None
) -> tuple[float, list[str]]:
    """Score text based on keyword matches with configurable weights."""
    matches = []
    score = 0.0

    weights = weights_config or WeightsManager.get_default()
    conversation_weights = weights.get_dict("conversation")

    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            matches.append(keyword)
            # Weight longer keywords more heavily
            score += len(keyword) * conversation_weights.get("keyword_weight", 1.0)

    return min(score, 1.0), matches[:8]  # Limit matches returned


def score_file_references(
    text: str, weights_config: Any | None = None
) -> tuple[float, list[str]]:
    """Score based on file references using standardized patterns."""
    refs = []
    score = 0.0

    weights = weights_config or WeightsManager.get_default()
    conversation_weights = weights.get_dict("conversation")

    # Use shared file reference patterns
    for pattern in FILE_REFERENCE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            refs.append(match)
            score += conversation_weights.get("file_reference_score", 1.0)

    return min(score, 1.0), refs[:5]  # Limit references returned


def score_session_recency(
    session_metadata: dict[str, Any], weights_config: Any | None = None
) -> float:
    """Score based on session recency using standardized thresholds."""
    try:
        weights = weights_config or WeightsManager.get_default()
        recency_thresholds = weights.get_dict("recency_thresholds")

        # Try different timestamp fields based on IDE
        timestamp = None

        # Cursor format with milliseconds timestamp
        if "lastUpdatedAt" in session_metadata:
            timestamp = session_metadata["lastUpdatedAt"] / 1000

        # Claude Code format with ISO string
        elif "start_time" in session_metadata:
            start_time_str = session_metadata["start_time"]
            if start_time_str:
                try:
                    session_time = datetime.fromisoformat(
                        start_time_str.replace("Z", "+00:00")
                    )
                    timestamp = session_time.timestamp()
                except (ValueError, TypeError):
                    pass

        if not timestamp:
            return 0.0

        last_updated_dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        days_ago = (now - last_updated_dt).days

        # Use standardized recency thresholds
        if days_ago <= 1:
            return recency_thresholds.get("days_1", 0.0)
        elif days_ago <= 7:
            return recency_thresholds.get("days_7", 0.0)
        elif days_ago <= 30:
            return recency_thresholds.get("days_30", 0.0)
        elif days_ago <= 90:
            return recency_thresholds.get("days_90", 0.0)
        else:
            return recency_thresholds.get("default", 0.0)

    except (ValueError, TypeError, OSError):
        return 0.0


def classify_conversation_type(
    text_content: str, keyword_matches: list[str], file_references: list[str]
) -> str:
    """Classify conversation type using standardized patterns."""

    # Check for debugging indicators
    debug_terms = [
        "error",
        "bug",
        "fix",
        "debug",
        "issue",
        "exception",
        "traceback",
    ]
    if any(term in text_content for term in debug_terms):
        return "debugging"

    # Check for testing indicators
    test_terms = ["test", "testing", "pytest", "spec", "unit", "integration"]
    if any(term in text_content for term in test_terms):
        return "testing"

    # Check for architecture indicators
    arch_terms = ["refactor", "architecture", "design", "structure", "pattern"]
    if any(term in text_content for term in arch_terms):
        return "architecture"

    # Check for technical discussion indicators
    if len(keyword_matches) > 3 or len(file_references) > 2:
        return "code_discussion"

    # Check for problem solving indicators
    problem_terms = ["how", "help", "problem", "solve", "implement"]
    if any(term in text_content for term in problem_terms):
        return "problem_solving"

    return "general"


def get_conversation_type_bonus(
    conversation_type: str, weights_config: Any | None = None
) -> float:
    """Get scoring bonus based on conversation type."""
    weights = weights_config or WeightsManager.get_default()
    conversation_weights = weights.get_dict("conversation")

    # Default type bonuses if not configured
    default_bonuses = {
        "debugging": 0.25,
        "architecture": 0.2,
        "testing": 0.15,
        "code_discussion": 0.1,
        "problem_solving": 0.1,
        "general": 0.0,
    }

    type_bonuses = conversation_weights.get("type_bonuses", default_bonuses)
    return type_bonuses.get(conversation_type, 0.0)


def extract_conversation_content(  # noqa: C901
    conversation_data: Any, max_chars: int = CONVERSATION_TEXT_EXTRACTION_LIMIT
) -> str:
    """Extract text content from conversation data (IDE-agnostic)."""
    text_parts = []
    total_chars = 0

    try:
        # Handle different conversation data formats
        if isinstance(conversation_data, dict):
            # Cursor format
            if "name" in conversation_data:
                name = conversation_data.get("name", "")
                if name and name != "Untitled":
                    text_parts.append(name)
                    total_chars += len(name)

            # Claude Code format - messages array
            if "messages" in conversation_data:
                messages = conversation_data["messages"]
                for message in messages[:10]:  # Limit messages processed
                    if total_chars >= max_chars:
                        break

                    content = message.get("content", "")
                    if isinstance(content, str):
                        remaining = max_chars - total_chars
                        if len(content) > remaining:
                            content = content[:remaining]
                        text_parts.append(content)
                        total_chars += len(content)
                    elif isinstance(content, list):
                        # Handle structured content
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text", "")
                                remaining = max_chars - total_chars
                                if len(text) > remaining:
                                    text = text[:remaining]
                                text_parts.append(text)
                                total_chars += len(text)
                                if total_chars >= max_chars:
                                    break

        elif isinstance(conversation_data, list):
            # Handle message arrays directly
            for message in conversation_data[:10]:
                if total_chars >= max_chars:
                    break

                if isinstance(message, dict):
                    content = message.get("content", "") or message.get("text", "")
                    if content:
                        remaining = max_chars - total_chars
                        if len(content) > remaining:
                            content = content[:remaining]
                        text_parts.append(str(content))
                        total_chars += len(str(content))

    except (KeyError, TypeError, ValueError, AttributeError) as e:
        log_debug(f"Error extracting conversation content: {e}")

    return " ".join(text_parts)


def filter_conversations_by_date(
    conversations: list[dict[str, Any]],
    days_lookback: int,
    date_field_mappings: dict[str, str] = None,
) -> list[dict[str, Any]]:
    """Filter conversations by date with IDE-agnostic date field handling."""
    if not conversations or days_lookback <= 0:
        return conversations

    cutoff_date = datetime.now() - timedelta(days=days_lookback)
    filtered = []

    # Default date field mappings
    if date_field_mappings is None:
        date_field_mappings = {
            "cursor": "lastUpdatedAt",
            "claude_code": "start_time",
        }

    for conv in conversations:
        try:
            # Try different date field formats
            timestamp = None

            # Cursor format (milliseconds timestamp)
            if "lastUpdatedAt" in conv:
                timestamp = datetime.fromtimestamp(conv["lastUpdatedAt"] / 1000)

            # Claude Code format (ISO string)
            elif "session_metadata" in conv:
                session_meta = conv["session_metadata"]
                if "start_time" in session_meta:
                    start_time_str = session_meta["start_time"]
                    if start_time_str:
                        timestamp = datetime.fromisoformat(
                            start_time_str.replace("Z", "+00:00")
                        )

            # Direct timestamp field
            elif "timestamp" in conv:
                ts = conv["timestamp"]
                if isinstance(ts, int | float):
                    timestamp = datetime.fromtimestamp(ts)
                elif isinstance(ts, str):
                    timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))

            # Include if timestamp is recent enough or if no timestamp available
            if timestamp is None or timestamp >= cutoff_date:
                filtered.append(conv)

        except (ValueError, TypeError, KeyError):
            # Include conversations with invalid/missing timestamps
            filtered.append(conv)

    return filtered


def sort_conversations_by_relevance(
    conversations: list[dict[str, Any]], relevance_key: str = "relevance_score"
) -> list[dict[str, Any]]:
    """Sort conversations by relevance score in descending order."""
    try:
        return sorted(
            conversations,
            key=lambda x: x.get(relevance_key, 0.0),
            reverse=True,
        )
    except (TypeError, KeyError):
        return conversations
