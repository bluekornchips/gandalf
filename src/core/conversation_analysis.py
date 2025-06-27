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
from typing import Any, Dict, List, Tuple

from src.config.constants.system import (
    CONVERSATION_RECENCY_THRESHOLDS,
    CONVERSATION_KEYWORD_WEIGHT,
    CONVERSATION_FILE_REF_SCORE,
)
from src.config.weights import CONVERSATION_WEIGHTS
from src.config.constants.technology import TECHNOLOGY_KEYWORD_MAPPING
from src.config.constants.conversations import (
    CONTEXT_KEYWORD_MAX_COUNT,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
)
from src.utils.common import log_debug, log_error

# Global cache for context keywords
_context_keywords_cache = {}
_context_keywords_cache_time = {}

# Cache TTL constant
CONTEXT_CACHE_TTL_SECONDS = 300  # 5 minutes

# File reference patterns for detecting code files in conversations
FILE_REFERENCE_PATTERNS = [
    r"[\w/.-]+\.py\b",
    r"[\w/.-]+\.js\b",
    r"[\w/.-]+\.ts\b",
    r"[\w/.-]+\.tsx\b",
    r"[\w/.-]+\.json\b",
    r"[\w/.-]+\.yaml\b",
    r"[\w/.-]+\.yml\b",
    r"[\w/.-]+\.md\b",
    r"[\w/.-]+\.sh\b",
    r"[\w/.-]+\.txt\b",
]


def generate_shared_context_keywords(project_root: Path) -> List[str]:
    """Generate context keywords with intelligent caching and weighting."""
    project_root_str = str(project_root)

    # Simple cache key based on project path and modification time
    cache_key = f"{project_root_str}"
    current_time = time.time()

    # Check cache
    if (
        cache_key in _context_keywords_cache
        and cache_key in _context_keywords_cache_time
        and current_time - _context_keywords_cache_time[cache_key]
        < CONTEXT_CACHE_TTL_SECONDS
    ):
        return _context_keywords_cache[cache_key]

    # Generate keywords
    keywords = _extract_project_keywords(project_root)

    # Cache results
    _context_keywords_cache[cache_key] = keywords
    _context_keywords_cache_time[cache_key] = current_time

    # Clean old cache entries
    for key in list(_context_keywords_cache_time.keys()):
        if (
            current_time - _context_keywords_cache_time[key]
            > CONTEXT_CACHE_TTL_SECONDS
        ):
            _context_keywords_cache.pop(key, None)
            _context_keywords_cache_time.pop(key, None)

    return keywords


def _extract_project_keywords(project_root: Path) -> List[str]:
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
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "README.md",
            "CLAUDE.md",
            "requirements.txt",
            "Gemfile",
            "composer.json",
        ]

        for file_name in common_files:
            file_path = project_root / file_name
            if file_path.exists():
                try:
                    # Use a larger limit for keyword extraction to ensure we can read small config files
                    content = file_path.read_text(encoding="utf-8")[
                        :2000
                    ]  # Increased from CONTEXT_KEYWORDS_FILE_LIMIT
                    keywords.extend(
                        _extract_keywords_from_file(file_name, content)
                    )
                except (OSError, UnicodeDecodeError):
                    continue

        # Add technology keywords based on file extensions
        keywords.extend(_extract_tech_keywords_from_files(project_root))

        # Remove duplicates, filter, and limit
        keywords = list(set(keywords))
        keywords = [
            k for k in keywords if len(k) > 1
        ]  # Filter out single chars
        keywords = keywords[:CONTEXT_KEYWORD_MAX_COUNT]

        log_debug(f"Generated {len(keywords)} context keywords")
        return keywords

    except Exception as e:
        log_error(e, "extracting project keywords")
        return [project_name] if "project_name" in locals() else []


def _extract_keywords_from_file(file_name: str, content: str) -> List[str]:
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

        elif file_name == "Cargo.toml":
            keywords.append("rust")

        elif file_name == "go.mod":
            keywords.append("go")

        elif file_name == "pom.xml":
            keywords.append("java")
            content_lower = content.lower()
            if "spring" in content_lower:
                keywords.append("spring")

    except Exception as e:
        log_debug(f"Error extracting keywords from {file_name}: {e}")

    return keywords


def _extract_tech_keywords_from_files(project_root: Path) -> List[str]:
    """Extract technology keywords based on file extensions in project."""
    keywords = []

    try:
        # Sample some files to determine tech stack
        file_extensions = set()
        for file_path in project_root.rglob("*"):
            if file_path.is_file() and len(file_extensions) < 20:
                ext = file_path.suffix.lower()
                if ext:
                    file_extensions.add(ext)

        # Map extensions to technologies
        ext_mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "react",
            ".tsx": "react",
            ".vue": "vue",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".cpp": "cpp",
            ".c": "c",
            ".swift": "swift",
            ".kt": "kotlin",
        }

        for ext in file_extensions:
            if ext in ext_mapping:
                keywords.append(ext_mapping[ext])

    except Exception as e:
        log_debug(f"Error extracting tech keywords: {e}")

    return keywords


def analyze_session_relevance(
    session_content: str,
    context_keywords: List[str],
    session_metadata: Dict[str, Any],
    include_detailed_analysis: bool = False,
) -> Tuple[float, Dict[str, Any]]:
    """Analyze relevance of a conversation session using multi-factor scoring."""
    try:
        score = 0.0
        analysis = {
            "keyword_matches": [],
            "file_references": [],
            "recency_score": 0.0,
            "conversation_type": "general",
        }

        if not session_content:
            return 0.0, analysis

        text_content = session_content.lower()

        # Score keyword matches
        keyword_score, matched_keywords = score_keyword_matches(
            text_content, context_keywords
        )
        analysis["keyword_matches"] = matched_keywords
        score += keyword_score * CONVERSATION_WEIGHTS["keyword_match"]

        # Score recency
        recency_score = score_session_recency(session_metadata)
        analysis["recency_score"] = recency_score
        score += recency_score * CONVERSATION_WEIGHTS["recency"]

        # Score file references if detailed analysis requested
        if include_detailed_analysis:
            file_score, file_refs = score_file_references(text_content)
            analysis["file_references"] = file_refs
            score += file_score * CONVERSATION_WEIGHTS["file_reference"]

        # Classify conversation type
        analysis["conversation_type"] = classify_conversation_type(
            text_content, matched_keywords, analysis.get("file_references", [])
        )

        # Add type-specific scoring bonuses
        type_bonus = get_conversation_type_bonus(analysis["conversation_type"])
        score += type_bonus

        return min(score, 5.0), analysis

    except Exception as e:
        log_error(e, "analyzing session relevance")
        return 0.0, analysis


def score_keyword_matches(
    text: str, keywords: List[str]
) -> Tuple[float, List[str]]:
    """Score based on keyword matches with intelligent weighting."""
    matches = []
    score = 0.0

    for keyword in keywords:
        if keyword.lower() in text:
            matches.append(keyword)
            # Weight longer keywords more heavily
            score += len(keyword) * CONVERSATION_KEYWORD_WEIGHT

    return min(score, 1.0), matches[:8]  # Limit matches returned


def score_file_references(text: str) -> Tuple[float, List[str]]:
    """Score based on file references using standardized patterns."""
    refs = []
    score = 0.0

    # Use shared file reference patterns
    for pattern in FILE_REFERENCE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            refs.append(match)
            score += CONVERSATION_FILE_REF_SCORE

    return min(score, 1.0), refs[:5]  # Limit references returned


def score_session_recency(session_metadata: Dict[str, Any]) -> float:
    """Score based on session recency using standardized thresholds."""
    try:
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
            return CONVERSATION_RECENCY_THRESHOLDS["days_1"]
        elif days_ago <= 7:
            return CONVERSATION_RECENCY_THRESHOLDS["days_7"]
        elif days_ago <= 30:
            return CONVERSATION_RECENCY_THRESHOLDS["days_30"]
        elif days_ago <= 90:
            return CONVERSATION_RECENCY_THRESHOLDS["days_90"]
        else:
            return CONVERSATION_RECENCY_THRESHOLDS["default"]

    except (ValueError, TypeError, OSError):
        return 0.0


def classify_conversation_type(
    text_content: str, keyword_matches: List[str], file_references: List[str]
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


def get_conversation_type_bonus(conversation_type: str) -> float:
    """Get scoring bonus based on conversation type."""
    type_bonuses = {
        "debugging": 0.25,
        "architecture": 0.2,
        "testing": 0.15,
        "code_discussion": 0.1,
        "problem_solving": 0.1,
        "general": 0.0,
    }

    return type_bonuses.get(conversation_type, 0.0)


def extract_conversation_content(
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
                            if (
                                isinstance(item, dict)
                                and item.get("type") == "text"
                            ):
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
                    content = message.get("content", "") or message.get(
                        "text", ""
                    )
                    if content:
                        remaining = max_chars - total_chars
                        if len(content) > remaining:
                            content = content[:remaining]
                        text_parts.append(str(content))
                        total_chars += len(str(content))

    except Exception as e:
        log_debug(f"Error extracting conversation content: {e}")

    return " ".join(text_parts)


def filter_conversations_by_date(
    conversations: List[Dict[str, Any]],
    days_lookback: int,
    date_field_mappings: Dict[str, str] = None,
) -> List[Dict[str, Any]]:
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
                timestamp = datetime.fromtimestamp(
                    conv["lastUpdatedAt"] / 1000
                )

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
                if isinstance(ts, (int, float)):
                    timestamp = datetime.fromtimestamp(ts)
                elif isinstance(ts, str):
                    timestamp = datetime.fromisoformat(
                        ts.replace("Z", "+00:00")
                    )

            # Include if timestamp is recent enough or if no timestamp available
            if timestamp is None or timestamp >= cutoff_date:
                filtered.append(conv)

        except (ValueError, TypeError, KeyError):
            # Include conversations with invalid/missing timestamps
            filtered.append(conv)

    return filtered


def sort_conversations_by_relevance(
    conversations: List[Dict[str, Any]], relevance_key: str = "relevance_score"
) -> List[Dict[str, Any]]:
    """Sort conversations by relevance score in descending order."""
    try:
        return sorted(
            conversations,
            key=lambda x: x.get(relevance_key, 0.0),
            reverse=True,
        )
    except (TypeError, KeyError):
        return conversations
