"""
Enhanced conversation ingestion and analysis for Gandalf MCP server.
"""

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import cursor_chat_query from scripts directory
scripts_dir = Path(__file__).resolve().parent.parent.parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from src.config.cache import (
    CONVERSATION_CACHE_FILE,
    CONVERSATION_CACHE_MAX_SIZE_MB,
    CONVERSATION_CACHE_METADATA_FILE,
    CONVERSATION_CACHE_MIN_SIZE,
    CONVERSATION_CACHE_TTL_HOURS,
)
from src.config.constants.conversations import (
    ACTIVITY_SCORE_MAX_DURATION,
    ACTIVITY_SCORE_RECENCY_BOOST,
    CONTEXT_CACHE_TTL_SECONDS,
    CONTEXT_KEYWORD_MAX_COUNT,
    CONTEXT_KEYWORD_MIN_RELEVANCE,
    CONTEXT_KEYWORDS_FILE_LIMIT,
    CONTEXT_KEYWORDS_QUICK_LIMIT,
    CONTEXT_PROJECT_WEIGHT_MULTIPLIER,
    CONTEXT_TECH_WEIGHT_MULTIPLIER,
    CONVERSATION_DEFAULT_RECENT_DAYS,
    CONVERSATION_EARLY_TERMINATION_MULTIPLIER,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_PROGRESS_LOG_INTERVAL,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
    CONVERSATION_TYPES,
    DATABASE_STRUCTURE_LIMITATION_NOTE,
    EARLY_TERMINATION_LIMIT_MULTIPLIER,
    FILE_REFERENCE_PATTERNS,
    FIRST_WORDS_ANALYSIS_LIMIT,
    KEYWORD_CHECK_LIMIT,
    KEYWORD_MATCHES_LIMIT,
    KEYWORD_MATCHES_TOP_LIMIT,
    MATCHES_OUTPUT_LIMIT,
    MAX_TECH_WEIGHT,
    PATTERN_MATCHES_DEFAULT_LIMIT,
    PROJECT_NAME_WEIGHT_MULTIPLIER,
    RECENT_ACTIVITY_HOURS,
    TECH_WEIGHT_DIVISOR,
)
from src.config.constants.system import (
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_FILE_REF_SCORE,
    CONVERSATION_KEYWORD_WEIGHT,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_RECENCY_THRESHOLDS,
    CONVERSATION_SNIPPET_CONTEXT_CHARS,
    CONVERSATION_SNIPPET_MAX_LENGTH,
)
from src.config.constants.technology import TECHNOLOGY_KEYWORD_MAPPING
from src.config.weights import CONVERSATION_WEIGHTS
from src.core.file_scoring import get_files_list
from src.utils.common import log_debug, log_error, log_info
from src.utils.cursor_chat_query import CursorQuery
from src.utils.performance import get_duration, log_operation_time, start_timer
from src.utils.security import SecurityValidator
from src.utils.cache import get_cache_directory

# Global cache for context keywords and conversation data
_context_keywords_cache = {}
_context_keywords_cache_time = {}
_conversation_cache = {}
_conversation_cache_time = {}


def get_project_cache_hash(
    project_root: Path, context_keywords: List[str]
) -> str:
    """Generate a cache hash based on project state and keywords."""
    try:
        # Include project path, git state, and keywords in hash
        hash_input = str(project_root)

        # Add git HEAD if available
        git_head = project_root / ".git" / "HEAD"
        if git_head.exists():
            hash_input += git_head.read_text().strip()

        # Add context keywords
        hash_input += "".join(sorted(context_keywords))

        # Simple short md5 hash to avoid bloating the cache. Maybe sha256? Probably overkill.
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    except (OSError, ValueError, UnicodeDecodeError):
        return hashlib.md5(
            f"{project_root}{time.time()}".encode()
        ).hexdigest()[:16]


def is_cache_valid(project_root: Path, context_keywords: List[str]) -> bool:
    """Check if the conversation cache is valid and up to date."""
    try:
        metadata_path = CONVERSATION_CACHE_METADATA_FILE
        cache_file_path = CONVERSATION_CACHE_FILE

        if not metadata_path.exists() or not cache_file_path.exists():
            return False

        cache_size_mb = cache_file_path.stat().st_size / (1024 * 1024)
        if cache_size_mb > CONVERSATION_CACHE_MAX_SIZE_MB:
            log_debug(f"Cache file too large: {cache_size_mb:.1f}MB")
            return False

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        cache_age_hours = (time.time() - metadata.get("timestamp", 0)) / 3600
        if cache_age_hours > CONVERSATION_CACHE_TTL_HOURS:
            log_debug(f"Cache expired: {cache_age_hours:.1f} hours old")
            return False

        current_hash = get_project_cache_hash(project_root, context_keywords)
        if metadata.get("project_hash") != current_hash:
            log_debug("Project state changed, cache invalid")
            return False

        return True

    except (OSError, json.JSONDecodeError, ValueError, KeyError) as e:
        log_debug(f"Cache validation error: {e}")
        return False


def load_cached_conversations(project_root: Path) -> Optional[Dict[str, Any]]:
    """Load conversations from cache if valid."""
    try:
        cache_file_path = CONVERSATION_CACHE_FILE

        if not cache_file_path.exists():
            return None

        with open(cache_file_path, "r") as f:
            cached_data = json.load(f)

        log_info(
            f"Loaded {len(cached_data.get('conversations', []))} "
            f"conversations from cache"
        )
        return cached_data

    except (OSError, json.JSONDecodeError, ValueError) as e:
        log_error(e, "loading cached conversations")
        return None


def save_conversations_to_cache(
    project_root: Path,
    conversations: List[Dict[str, Any]],
    context_keywords: List[str],
    metadata: Dict[str, Any],
) -> bool:
    """Save conversations to local cache with metadata."""
    try:
        if len(conversations) < CONVERSATION_CACHE_MIN_SIZE:
            log_debug(
                f"Not caching - too few conversations: {len(conversations)}"
            )
            return False

        get_cache_directory()

        # Save metadata
        metadata_content = {
            "timestamp": time.time(),
            "conversation_count": len(conversations),
            "context_keywords": context_keywords,
            "project_hash": get_project_cache_hash(
                project_root, context_keywords
            ),
            **metadata,
        }

        with open(CONVERSATION_CACHE_METADATA_FILE, "w") as f:
            json.dump(metadata_content, f, indent=2)

        # Save conversations
        cache_content = {"conversations": conversations, **metadata}
        with open(CONVERSATION_CACHE_FILE, "w") as f:
            json.dump(cache_content, f)

        cache_size_mb = CONVERSATION_CACHE_FILE.stat().st_size / (1024 * 1024)
        log_info(
            f"Cached {len(conversations)} conversations "
            f"({cache_size_mb:.1f}MB)"
        )
        return True

    except (OSError, json.JSONEncodeError) as e:
        log_error(e, "saving conversations to cache")
        return False


def get_project_hash(project_root: Path) -> str:
    """Generate a hash for the project to use in caching."""
    try:
        hash_input = str(project_root)

        git_head = project_root / ".git" / "HEAD"
        if git_head.exists():
            hash_input += git_head.read_text().strip()

        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    except (OSError, UnicodeDecodeError):
        return hashlib.md5(str(project_root).encode()).hexdigest()[:12]


@lru_cache(maxsize=32)
def get_enhanced_context_keywords(
    project_root_str: str, project_hash: str
) -> List[str]:
    """Enhanced context keyword generation with intelligent filtering."""
    project_root = Path(project_root_str)
    keyword_weights = {}

    project_name = project_root.name
    keyword_weights[project_name] = (
        CONTEXT_PROJECT_WEIGHT_MULTIPLIER * PROJECT_NAME_WEIGHT_MULTIPLIER
    )

    try:
        files = get_files_list(project_root)[:CONTEXT_KEYWORDS_FILE_LIMIT]

        extensions = {}
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext:
                clean_ext = ext[1:]
                extensions[clean_ext] = extensions.get(clean_ext, 0) + 1

        for ext, count in extensions.items():
            if ext in TECHNOLOGY_KEYWORD_MAPPING:
                tech_weight = CONTEXT_TECH_WEIGHT_MULTIPLIER * min(
                    count / TECH_WEIGHT_DIVISOR, MAX_TECH_WEIGHT
                )
                for tech_keyword in TECHNOLOGY_KEYWORD_MAPPING[ext]:
                    keyword_weights[tech_keyword] = (
                        keyword_weights.get(tech_keyword, 0) + tech_weight
                    )

    except (OSError, ValueError, AttributeError) as e:
        log_debug(f"Error processing project files: {e}")

    sorted_keywords = sorted(
        keyword_weights.items(), key=lambda x: x[1], reverse=True
    )

    final_keywords = []
    for keyword, weight in sorted_keywords:
        if (
            weight >= CONTEXT_KEYWORD_MIN_RELEVANCE
            and len(final_keywords) < CONTEXT_KEYWORD_MAX_COUNT
        ):
            final_keywords.append(keyword)

    log_debug(
        f"Generated {len(final_keywords)} weighted keywords from {len(keyword_weights)} candidates"
    )
    return final_keywords


def generate_context_keywords(project_root: Path) -> List[str]:
    """Generate context keywords with intelligent caching and weighting."""
    project_root_str = str(project_root)
    project_hash = get_project_hash(project_root)

    cache_key = f"{project_root_str}:{project_hash}"
    current_time = time.time()

    if (
        cache_key in _context_keywords_cache
        and cache_key in _context_keywords_cache_time
        and current_time - _context_keywords_cache_time[cache_key]
        < CONTEXT_CACHE_TTL_SECONDS
    ):
        return _context_keywords_cache[cache_key]

    keywords = get_enhanced_context_keywords(project_root_str, project_hash)

    _context_keywords_cache[cache_key] = keywords
    _context_keywords_cache_time[cache_key] = current_time

    for key in list(_context_keywords_cache_time.keys()):
        if (
            current_time - _context_keywords_cache_time[key]
            > CONTEXT_CACHE_TTL_SECONDS
        ):
            _context_keywords_cache.pop(key, None)
            _context_keywords_cache_time.pop(key, None)

    return keywords


def extract_conversation_text_lazy(
    conversation: Dict[str, Any],
    prompts: List[Dict[str, Any]],
    generations: List[Dict[str, Any]],
    max_chars: int = CONVERSATION_TEXT_EXTRACTION_LIMIT,
) -> str:
    """Extract conversation text with lazy loading and length limits."""
    text_parts = []
    total_chars = 0

    # Add conversation name/title are probably the most relevant...
    conv_name = conversation.get("name", "")
    if conv_name and conv_name != "Untitled":
        text_parts.append(conv_name)
        total_chars += len(conv_name)

    # ...except for the user input, which is almost always the most relevant
    conv_id = conversation.get("composerId", "")
    for prompt in prompts:
        if total_chars >= max_chars:
            break
        if prompt.get("conversationId") == conv_id:
            text = prompt.get("text", "")
            if text:
                remaining_chars = max_chars - total_chars
                if len(text) > remaining_chars:
                    text = text[:remaining_chars]
                text_parts.append(text)
                total_chars += len(text)

    if total_chars < max_chars:
        for gen in generations:
            if total_chars >= max_chars:
                break
            if gen.get("conversationId") == conv_id:
                text = gen.get("text", "")
                if text:
                    remaining_chars = max_chars - total_chars
                    if len(text) > remaining_chars:
                        text = text[:remaining_chars]
                    text_parts.append(text)
                    total_chars += len(text)

    return " ".join(text_parts).lower()


def score_keyword_matches_optimized(
    text: str, keywords: List[str]
) -> Tuple[float, List[str]]:
    """Optimized keyword matching with early termination."""
    matches = []
    score = 0.0
    text_lower = text.lower()

    sorted_keywords = sorted(keywords, key=len, reverse=True)

    for keyword in sorted_keywords[:KEYWORD_CHECK_LIMIT]:
        keyword_lower = keyword.lower()
        if keyword_lower in text_lower:
            matches.append(keyword)
            # Weight longer keywords more heavily
            score += len(keyword) * CONVERSATION_KEYWORD_WEIGHT

            if len(matches) >= KEYWORD_MATCHES_LIMIT:
                break

    return min(score, 1.0), matches


def quick_conversation_filter(
    conversation: Dict[str, Any],
    cutoff_date: datetime,
    context_keywords: List[str],
    min_exchanges: int = 2,
) -> bool:
    """Quick filter to eliminate obviously irrelevant conversations early."""

    # recency
    last_updated = conversation.get("lastUpdatedAt", 0)
    if last_updated:
        conv_date = datetime.fromtimestamp(last_updated / 1000)
        if conv_date < cutoff_date:
            return False

    # Skip untitled conversations with no recent activity
    conv_name = conversation.get("name", "")
    if (not conv_name or conv_name == "Untitled") and last_updated == 0:
        return False

    # keyword check in title
    if conv_name and context_keywords:
        conv_name_lower = conv_name.lower()
        for keyword in context_keywords[:CONTEXT_KEYWORDS_QUICK_LIMIT]:
            if keyword.lower() in conv_name_lower:
                return True

    # Always include recent conversations
    if last_updated > 0:
        hours_ago = (
            datetime.now() - datetime.fromtimestamp(last_updated / 1000)
        ).total_seconds() / 3600
        if hours_ago < RECENT_ACTIVITY_HOURS:
            return True

    return True  # Default operation is to include


def analyze_conversation_relevance_optimized(
    conversation: Dict[str, Any],
    prompts: List[Dict[str, Any]],
    generations: List[Dict[str, Any]],
    context_keywords: List[str],
    project_root: Path,
    include_detailed_analysis: bool = False,
) -> Tuple[float, Dict[str, Any]]:
    """Optimized conversation relevance analysis."""

    score = 0.0
    analysis = {
        "keyword_matches": [],
        "recency_score": 0.0,
        "conversation_type": "general",
    }

    recency_score = score_recency(conversation)
    score += recency_score * CONVERSATION_WEIGHTS["recency"]
    analysis["recency_score"] = recency_score

    conv_text = extract_conversation_text_lazy(
        conversation, prompts, generations
    )

    if not conv_text:
        return score, analysis

    if context_keywords:
        keyword_score, matches = score_keyword_matches_optimized(
            conv_text, context_keywords
        )
        score += keyword_score * CONVERSATION_WEIGHTS["keyword_match"]
        analysis["keyword_matches"] = matches[:MATCHES_OUTPUT_LIMIT]

    conv_name = conversation.get("name", "").lower()
    first_words = conv_text.split()[:FIRST_WORDS_ANALYSIS_LIMIT]

    if any(
        word in ["test", "testing", "pytest"]
        for word in (analysis["keyword_matches"] + [conv_name])
    ):
        analysis["conversation_type"] = "technical"
    elif any(
        word in ["error", "debug", "fix", "issue", "bug"]
        for word in first_words
    ):
        analysis["conversation_type"] = "debugging"
    elif any(
        word in ["architecture", "design", "structure", "refactor"]
        for word in first_words
    ):
        analysis["conversation_type"] = "architecture"
    elif len(analysis["keyword_matches"]) > 3:
        analysis["conversation_type"] = "code_discussion"
    else:
        analysis["conversation_type"] = "general"

    # Add file reference check if detailed analysis requested
    if include_detailed_analysis:
        file_score, refs = score_file_references(conv_text, project_root)
        score += file_score * CONVERSATION_WEIGHTS["file_reference"]
        analysis["file_references"] = refs[:5]
    else:
        analysis["file_references"] = []

    return score, analysis


def extract_conversation_text(
    conversation: Dict[str, Any],
    prompts: List[Dict[str, Any]],
    generations: List[Dict[str, Any]],
) -> str:
    """Extract all text content from a conversation."""
    text_parts = []

    # Add conversation name/title
    conv_name = conversation.get("name", "")
    if conv_name and conv_name != "Untitled":
        text_parts.append(conv_name)

    for prompt in prompts:
        text = prompt.get("text", "")
        if text:
            text_parts.append(text)

    for gen in generations:
        text = gen.get("text", "")
        if text:
            text_parts.append(text)

    return " ".join(text_parts).lower()


def score_keyword_matches(
    text: str, keywords: List[str]
) -> Tuple[float, List[str]]:
    """Score based on keyword matches."""
    matches = []
    score = 0.0

    for keyword in keywords:
        if keyword.lower() in text:
            matches.append(keyword)
            # Weight longer keywords more heavily, pretty subjective but works for now
            score += len(keyword) * CONVERSATION_KEYWORD_WEIGHT

    return min(score, 1.0), matches


def score_file_references(
    text: str, project_root: Path
) -> Tuple[float, List[str]]:
    """Score based on file references that exist in current project."""
    refs = []
    score = 0.0

    for pattern in FILE_REFERENCE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            # Check if file exists in current project, might want to throw a warning or error if it doesn't in the future
            potential_path = project_root / match
            if potential_path.exists():
                refs.append(match)
                score += CONVERSATION_FILE_REF_SCORE

    return min(score, 1.0), refs


def score_recency(conversation: Dict[str, Any]) -> float:
    """Score based on conversation recency."""
    try:
        last_updated = conversation.get("lastUpdatedAt", 0)
        if not last_updated:
            return 0.0

        last_updated_dt = datetime.fromtimestamp(last_updated / 1000)
        now = datetime.now()
        days_ago = (now - last_updated_dt).days

        # We can probably rename these keys and values to be more human readable
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


def score_pattern_matches(
    text: str,
    patterns: List[str],
    score_per_match: float,
    max_matches: int = PATTERN_MATCHES_DEFAULT_LIMIT,
) -> Tuple[float, List[str]]:
    """Score based on pattern matches in text."""
    indicators = []
    score = 0.0
    # Use set to avoid counting duplicates
    unique_matches = set()

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                unique_matches.add(match.lower())
                if len(unique_matches) >= max_matches:
                    break
            score += len(matches) * score_per_match

        # Early termination if we have enough matches
        if len(unique_matches) >= max_matches:
            break

    indicators = list(unique_matches)[:max_matches]
    return min(score, 1.0), indicators


def classify_conversation_type(
    file_references: List[str],
    technical_indicators: List[str],
    arch_score: float,
    debug_score: float,
    problem_score: float,
) -> str:
    """Classify the type of conversation."""
    # Use threshold constants for classification
    if arch_score > 0.5:
        return "architecture"
    elif debug_score > 0.5:
        return "debugging"
    elif problem_score > 0.5:
        return "problem_solving"
    elif file_references:
        return "code_discussion"
    elif technical_indicators:
        return "technical"
    else:
        return "general"


def analyze_conversation_relevance(
    conversation: Dict[str, Any],
    prompts: List[Dict[str, Any]],
    generations: List[Dict[str, Any]],
    context_keywords: List[str],
    project_root: Path,
    include_detailed_analysis: bool = False,
) -> Tuple[float, Dict[str, Any]]:
    """Analyze conversation relevance using only context keywords for fast, targeted scoring."""

    score = 0.0
    analysis = {
        "keyword_matches": [],
        "recency_score": 0.0,
        "conversation_type": "general",
    }

    conv_text = extract_conversation_text(conversation, prompts, generations)

    if not conv_text:
        return 0.0, analysis

    # Context keyword matching, primary scoring mechanism
    if context_keywords:
        keyword_score, matches = score_keyword_matches(
            conv_text, context_keywords
        )
        score += keyword_score * CONVERSATION_WEIGHTS["keyword_match"]
        analysis["keyword_matches"] = matches[:KEYWORD_MATCHES_TOP_LIMIT]

    recency_score = score_recency(conversation)
    score += recency_score * CONVERSATION_WEIGHTS["recency"]
    analysis["recency_score"] = recency_score

    # Simple conversation type classification based on keywords
    if any(
        keyword in ["test", "testing", "pytest"]
        for keyword in analysis["keyword_matches"]
    ):
        analysis["conversation_type"] = "technical"
    elif any(
        keyword in ["error", "debug", "fix", "issue"]
        for keyword in conv_text.split()[:50]
    ):
        analysis["conversation_type"] = "debugging"
    elif any(
        keyword in ["architecture", "design", "structure"]
        for keyword in conv_text.split()[:50]
    ):
        analysis["conversation_type"] = "architecture"
    elif len(analysis["keyword_matches"]) > 3:
        analysis["conversation_type"] = "code_discussion"
    else:
        analysis["conversation_type"] = "general"

    # Optional: Add basic file reference check if requested
    # We should make this the default and only option
    if include_detailed_analysis:
        file_score, refs = score_file_references(conv_text, project_root)
        score += file_score * CONVERSATION_WEIGHTS["file_reference"]
        analysis["file_references"] = refs[:5]
    else:
        analysis["file_references"] = []

    return score, analysis


def extract_snippet(text: str, query: str) -> str:
    """Extract a snippet around the query match."""
    try:
        index = text.find(query)
        if index == -1:
            return (
                text[:CONVERSATION_SNIPPET_MAX_LENGTH] + "..."
                if len(text) > CONVERSATION_SNIPPET_MAX_LENGTH
                else text
            )

        start = max(0, index - CONVERSATION_SNIPPET_CONTEXT_CHARS // 2)
        end = min(
            len(text),
            index + len(query) + CONVERSATION_SNIPPET_CONTEXT_CHARS // 2,
        )

        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet.strip()

    except (ValueError, AttributeError):
        return (
            text[:CONVERSATION_SNIPPET_MAX_LENGTH] + "..."
            if len(text) > CONVERSATION_SNIPPET_MAX_LENGTH
            else text
        )


def handle_ingest_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Ingest and analyze relevant conversations with intelligent caching."""
    try:
        limit = arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)
        min_relevance_score = arguments.get(
            "min_relevance_score", CONVERSATION_DEFAULT_MIN_SCORE
        )
        days_lookback = arguments.get(
            "days_lookback", CONVERSATION_DEFAULT_RECENT_DAYS
        )
        conversation_types = arguments.get("conversation_types", [])
        include_analysis = arguments.get("include_analysis", False)
        fast_mode = arguments.get("fast_mode", True)

        # Validate parameters
        if (
            not isinstance(limit, int)
            or limit < 1
            or limit > CONVERSATION_MAX_LIMIT
        ):
            return SecurityValidator.create_error_response(
                f"limit must be an integer between 1 and {CONVERSATION_MAX_LIMIT}"
            )

        if (
            not isinstance(min_relevance_score, (int, float))
            or min_relevance_score < 0
        ):
            return SecurityValidator.create_error_response(
                "min_relevance_score must be a non-negative number"
            )

        if (
            not isinstance(days_lookback, int)
            or days_lookback < 1
            or days_lookback > CONVERSATION_MAX_LOOKBACK_DAYS
        ):
            return SecurityValidator.create_error_response(
                f"days_lookback must be an integer between 1 and {CONVERSATION_MAX_LOOKBACK_DAYS}"
            )

        # Generate context keywords early for cache validation
        log_info("Generating intelligent context keywords...")
        context_keywords = generate_context_keywords(project_root)
        log_debug(f"Generated context keywords: {context_keywords[:15]}...")

        # Check for valid cache first
        if is_cache_valid(project_root, context_keywords):
            log_info("Loading conversations from valid cache...")
            cached_data = load_cached_conversations(project_root)
            if cached_data:
                # Filter cached results based on current parameters
                cached_conversations = cached_data.get("conversations", [])

                # Apply current filters to cached data
                filtered_cached = []
                for conv in cached_conversations:
                    # Check if it meets current criteria
                    last_updated = conv.get("last_updated", 0)
                    if last_updated:
                        conv_date = datetime.fromtimestamp(last_updated / 1000)
                        cutoff_date = datetime.now() - timedelta(
                            days=days_lookback
                        )
                        if conv_date >= cutoff_date:
                            filtered_cached.append(conv)

                # Return cached results if sufficient
                if len(filtered_cached) >= limit:
                    result = {
                        "mode": "cached_results",
                        "total_conversations": len(filtered_cached[:limit]),
                        "context_keywords": context_keywords[:15],
                        "parameters": {
                            "limit": limit,
                            "min_relevance_score": min_relevance_score,
                            "days_lookback": days_lookback,
                            "conversation_types": conversation_types,
                        },
                        "cache_info": {
                            "cache_age_hours": round(
                                (time.time() - cached_data.get("cached_at", 0))
                                / 3600,
                                1,
                            ),
                            "total_cached": len(cached_conversations),
                            "filtered_count": len(filtered_cached),
                        },
                        "conversations": filtered_cached[:limit],
                    }
                    log_info(
                        f"Returned {len(filtered_cached[:limit])} conversations from cache"
                    )
                    return SecurityValidator.create_success_response(
                        json.dumps(result, indent=2)
                    )

        # Initialize query tool for fresh data
        query_tool = CursorQuery(silent=True)

        # Query conversations
        log_info("Querying conversations from Cursor databases...")
        start_time = start_timer()
        data = query_tool.query_all_conversations()
        query_time = get_duration(start_time)
        log_operation_time("cursor_conversation_query", start_time, "debug")

        # Fast mode: Simple filtering without complex analysis
        if fast_mode:
            result_data = handle_fast_conversation_extraction(
                data, limit, days_lookback, conversation_types, query_time
            )

            # Save fast results to cache if significant
            # Fast mode caching is intentionally disabled to maintain speed, return to this later
            # Complex caching is only available in analysis mode, ensure we need this sometime later too

            return result_data

        log_info("Running enhanced analysis with intelligent filtering...")

        cutoff_date = datetime.now() - timedelta(days=days_lookback)

        log_debug("Basic conversation filtering...")
        filtered_conversations = []
        total_conversations = 0

        for workspace in data["workspaces"]:
            for conversation in workspace["conversations"]:
                total_conversations += 1

                # Apply basic recency filter
                last_updated = conversation.get("lastUpdatedAt", 0)
                if last_updated:
                    conv_date = datetime.fromtimestamp(last_updated / 1000)
                    if conv_date >= cutoff_date:
                        filtered_conversations.append(
                            {
                                "conversation": conversation,
                                "workspace": workspace,
                                "workspace_hash": workspace["workspace_hash"],
                            }
                        )

        log_debug(
            f"Basic filter: {len(filtered_conversations)} / {total_conversations} conversations passed"
        )

        # Relevance analysis on filtered set
        log_debug("Relevance analysis...")
        relevant_conversations = []
        start_analysis_time = start_timer()

        # Sort by recency for better early results
        filtered_conversations.sort(
            key=lambda x: x["conversation"].get("lastUpdatedAt", 0),
            reverse=True,
        )

        processed_count = 0
        for conv_data in filtered_conversations:
            processed_count += 1

            if processed_count % CONVERSATION_PROGRESS_LOG_INTERVAL == 0:
                log_debug(
                    f"Analyzed {processed_count}/{len(filtered_conversations)} conversations..."
                )

            conversation = conv_data["conversation"]
            workspace = conv_data["workspace"]

            # Analyze relevance with optimized analysis
            score, analysis = analyze_conversation_relevance_optimized(
                conversation,
                workspace["prompts"],
                workspace["generations"],
                context_keywords,
                project_root,
                include_detailed_analysis=include_analysis,
            )

            # Filter by minimum score
            if score >= min_relevance_score:
                # Filter by conversation type if specified
                if (
                    not conversation_types
                    or analysis["conversation_type"] in conversation_types
                ):
                    relevant_conversations.append(
                        {
                            "conversation": conversation,
                            "workspace_hash": conv_data["workspace_hash"],
                            "relevance_score": score,
                            "analysis": analysis,
                        }
                    )

                    # Early termination optimization
                    if (
                        len(relevant_conversations)
                        >= limit * CONVERSATION_EARLY_TERMINATION_MULTIPLIER
                    ):
                        log_debug(
                            f"Early termination: found {len(relevant_conversations)} conversations"
                        )
                        break

        analysis_time = get_duration(start_analysis_time)
        log_operation_time(
            "conversation_relevance_analysis", start_analysis_time, "debug"
        )

        # Sort and limit results
        relevant_conversations.sort(
            key=lambda x: x["relevance_score"], reverse=True
        )
        final_conversations = relevant_conversations[:limit]

        result = {
            "mode": "enhanced_analysis_with_caching",
            "total_relevant_conversations": len(final_conversations),
            "context_keywords": context_keywords[:15],
            "parameters": {
                "limit": limit,
                "min_relevance_score": min_relevance_score,
                "days_lookback": days_lookback,
                "conversation_types": conversation_types,
            },
            "processing_stats": {
                "total_conversations": total_conversations,
                "basic_filtered": len(filtered_conversations),
                "analyzed": processed_count,
                "extraction_time_seconds": round(query_time, 2),
                "analysis_time_seconds": round(analysis_time, 2),
                "total_time_seconds": round(query_time + analysis_time, 2),
                "efficiency_percent": (
                    round(processed_count / total_conversations * 100, 1)
                    if total_conversations > 0
                    else 0
                ),
            },
            "conversations": [],
        }

        for conv_data in final_conversations:
            conv_summary = {
                "name": conv_data["conversation"].get("name", "Untitled"),
                "workspace_hash": conv_data["workspace_hash"][:8],
                "relevance_score": round(conv_data["relevance_score"], 2),
                "conversation_type": conv_data["analysis"][
                    "conversation_type"
                ],
                "last_updated": conv_data["conversation"].get(
                    "lastUpdatedAt", 0
                ),
                "keyword_matches": len(
                    conv_data["analysis"]["keyword_matches"]
                ),
                "file_references": len(
                    conv_data["analysis"]["file_references"]
                ),
            }

            # Only include detailed analysis if explicitly requested
            if include_analysis:
                conv_summary["detailed_analysis"] = conv_data["analysis"]

            result["conversations"].append(conv_summary)

        # Save to cache for future use
        if len(final_conversations) >= CONVERSATION_CACHE_MIN_SIZE:
            cache_success = save_conversations_to_cache(
                project_root,
                result["conversations"],
                context_keywords,
                result["processing_stats"],
            )
            result["cache_saved"] = cache_success

        efficiency = (
            (processed_count / total_conversations * 100)
            if total_conversations > 0
            else 0
        )
        log_info(
            f"Enhanced analysis: {len(final_conversations)} relevant conversations in {query_time + analysis_time:.2f}s "
            f"(analyzed {efficiency:.1f}% of conversations)"
        )

        return SecurityValidator.create_success_response(
            json.dumps(result, indent=2)
        )

    except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as e:
        log_error(e, "ingest_conversations")
        return SecurityValidator.create_error_response(
            f"Error ingesting conversations: {str(e)}"
        )


def handle_fast_conversation_extraction(
    data: Dict[str, Any],
    limit: int,
    days_lookback: int,
    conversation_types: List[str],
    extraction_time: float,
) -> Dict[str, Any]:
    """Ultra-fast conversation extraction with minimal processing."""
    start_time = start_timer()

    conversations = []
    cutoff_date = datetime.now() - timedelta(days=days_lookback)
    processed_count = 0
    skipped_count = 0

    for workspace in data["workspaces"]:
        workspace_hash = workspace["workspace_hash"][:8]

        # Calculate workspace-level statistics for context
        total_prompts = len(workspace.get("prompts", []))
        total_generations = len(workspace.get("generations", []))
        total_conversations = len(workspace.get("conversations", []))

        for conversation in workspace["conversations"]:
            processed_count += 1

            last_updated = conversation.get("lastUpdatedAt", 0)
            if last_updated:
                conv_date = datetime.fromtimestamp(last_updated / 1000)
                if conv_date < cutoff_date:
                    skipped_count += 1
                    continue

            # Skip empty/untitled conversations unless very recent
            conv_name = conversation.get("name", "")
            if (not conv_name or conv_name == "Untitled") and last_updated < (
                time.time() - 86400
            ) * 1000:
                skipped_count += 1
                continue

            # Calculate conversation activity score based on available data
            conv_id = conversation.get("composerId", "")
            created_at = conversation.get("createdAt", 0)

            # Estimate conversation activity, based on time span and recency
            activity_score = 0
            if created_at and last_updated:
                duration_hours = (last_updated - created_at) / (1000 * 3600)
                recency_hours = (time.time() * 1000 - last_updated) / (
                    1000 * 3600
                )

                # Score based on conversation duration and recency
                if duration_hours > 0:
                    activity_score = min(
                        duration_hours / 24, ACTIVITY_SCORE_MAX_DURATION
                    )
                if recency_hours < 24:
                    activity_score += ACTIVITY_SCORE_RECENCY_BOOST

            # Use activity score as a proxy for exchange count
            estimated_exchanges = max(1, int(activity_score))

            conv_data = {
                "name": conv_name or "Untitled",
                "workspace_hash": workspace_hash,
                "conversation_id": conv_id,
                "last_updated": last_updated,
                "created_at": created_at,
                "prompt_count": estimated_exchanges,
                "generation_count": estimated_exchanges,
                "total_exchanges": estimated_exchanges,
                "activity_score": round(activity_score, 2),
                "workspace_stats": {
                    "total_conversations": total_conversations,
                    "total_prompts": total_prompts,
                    "total_generations": total_generations,
                },
            }

            conversations.append(conv_data)

            if (
                len(conversations)
                >= limit * EARLY_TERMINATION_LIMIT_MULTIPLIER
            ):
                break

    # Sort by last updated, most recent first, and limit
    conversations.sort(key=lambda x: x["last_updated"], reverse=True)
    conversations = conversations[:limit]

    processing_time = get_duration(start_time)
    log_operation_time("fast_conversation_extraction", start_time, "debug")

    result = {
        "mode": "ultra_fast_extraction",
        "total_conversations": len(conversations),
        "parameters": {
            "limit": limit,
            "days_lookback": days_lookback,
            "conversation_types": conversation_types,
        },
        "processing_stats": {
            "total_processed": processed_count,
            "skipped": skipped_count,
            "efficiency_percent": (
                round(
                    (processed_count - skipped_count) / processed_count * 100,
                    1,
                )
                if processed_count > 0
                else 0
            ),
            "extraction_time_seconds": round(extraction_time, 2),
            "filtering_time_seconds": round(processing_time, 2),
            "total_time_seconds": round(extraction_time + processing_time, 2),
        },
        "conversations": conversations,
        "database_note": DATABASE_STRUCTURE_LIMITATION_NOTE,
    }

    log_info(
        f"Ultra-fast extracted {len(conversations)} conversations in {extraction_time + processing_time:.2f}s "
        f"(processed {processed_count}, skipped {skipped_count})"
    )
    return SecurityValidator.create_success_response(
        json.dumps(result, indent=2)
    )


def handle_query_conversation_context(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Query conversations for specific context or topics."""
    try:
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        include_content = arguments.get("include_content", False)

        if not query or not isinstance(query, str):
            return SecurityValidator.create_error_response(
                "query parameter is required and must be a string"
            )

        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return SecurityValidator.create_error_response(
                "limit must be an integer between 1 and 50"
            )

        # Initialize query tool
        query_tool = CursorQuery(silent=True)

        # Query conversations
        log_info(f"Searching conversations for: '{query}'")
        data = query_tool.query_all_conversations()

        # Search for query in conversations
        matching_conversations = []
        query_lower = query.lower()
        processed_count = 0

        for workspace in data["workspaces"]:
            # Create lookup dictionaries for prompts and generations by conversation ID
            prompts_by_conv = {}
            generations_by_conv = {}

            for prompt in workspace["prompts"]:
                conv_id = prompt.get("conversationId", "")
                if conv_id not in prompts_by_conv:
                    prompts_by_conv[conv_id] = []
                prompts_by_conv[conv_id].append(prompt)

            for generation in workspace["generations"]:
                conv_id = generation.get("conversationId", "")
                if conv_id not in generations_by_conv:
                    generations_by_conv[conv_id] = []
                generations_by_conv[conv_id].append(generation)

            for conversation in workspace["conversations"]:
                processed_count += 1
                conv_id = conversation.get("composerId", "")

                conv_name = conversation.get("name", "").lower()
                name_match = query_lower in conv_name

                # Get related prompts and generations for this conversation
                conv_prompts = prompts_by_conv.get(conv_id, [])
                conv_generations = generations_by_conv.get(conv_id, [])

                # Check prompts and generations for content match
                content_match = False
                matched_content = []

                for prompt in conv_prompts:
                    text = prompt.get("text", "").lower()
                    if query_lower in text:
                        content_match = True
                        if include_content:
                            snippet = extract_snippet(text, query_lower)
                            matched_content.append(f"User: {snippet}")
                            if len(matched_content) >= 2:
                                break

                for generation in conv_generations:
                    text = generation.get("text", "").lower()
                    if query_lower in text:
                        content_match = True
                        if include_content:
                            snippet = extract_snippet(text, query_lower)
                            matched_content.append(f"Assistant: {snippet}")
                            if len(matched_content) >= 2:
                                break

                if name_match or content_match:
                    match_data = {
                        "name": conversation.get("name", "Untitled"),
                        "workspace_hash": workspace["workspace_hash"][:8],
                        "last_updated": conversation.get("lastUpdatedAt", 0),
                        "match_type": "title" if name_match else "content",
                        "conversation_id": conv_id,
                        "prompt_count": len(conv_prompts),
                        "generation_count": len(conv_generations),
                    }

                    if include_content and matched_content:
                        match_data["matched_content"] = matched_content

                    matching_conversations.append(match_data)

        # Sort by last updated (most recent first) and limit
        matching_conversations.sort(
            key=lambda x: x["last_updated"], reverse=True
        )
        matching_conversations = matching_conversations[:limit]

        result = {
            "query": query,
            "total_matches": len(matching_conversations),
            "processed_conversations": processed_count,
            "parameters": {
                "limit": limit,
                "include_content": include_content,
            },
            "conversations": matching_conversations,
        }

        log_info(
            f"Found {len(matching_conversations)} conversations matching '{query}' from {processed_count} total"
        )
        return SecurityValidator.create_success_response(
            json.dumps(result, indent=2)
        )

    except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as e:
        log_error(e, "query_conversation_context")
        return SecurityValidator.create_error_response(
            f"Error querying conversation context: {str(e)}"
        )


# Tool definitions
TOOL_INGEST_CONVERSATIONS = {
    "name": "ingest_conversations",
    "description": "Analyze and ingest relevant conversations from Cursor IDE history with intelligent caching. Defaults to recent 7 days for focused relevance.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LIMIT,
                "default": CONVERSATION_DEFAULT_LIMIT,
                "description": "Maximum number of conversations to return",
            },
            "min_relevance_score": {
                "type": "number",
                "minimum": 0,
                "default": CONVERSATION_DEFAULT_MIN_SCORE,
                "description": "Minimum relevance score threshold (only used when fast_mode=false)",
            },
            "days_lookback": {
                "type": "integer",
                "minimum": 1,
                "maximum": CONVERSATION_MAX_LOOKBACK_DAYS,
                "default": CONVERSATION_DEFAULT_RECENT_DAYS,
                "description": "Number of days to look back for conversations (default: 7 days for recent focus)",
            },
            "conversation_types": {
                "type": "array",
                "items": {"type": "string", "enum": CONVERSATION_TYPES},
                "description": "Filter by conversation types (only used when fast_mode=false)",
            },
            "include_analysis": {
                "type": "boolean",
                "default": False,
                "description": "Include detailed relevance analysis (only used when fast_mode=false)",
            },
            "fast_mode": {
                "type": "boolean",
                "default": True,
                "description": "Use fast extraction (seconds) vs full analysis (minutes). Recommended: true",
            },
        },
        "required": [],
    },
    "annotations": {
        "title": "Ingest Relevant Conversations with Smart Caching",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

TOOL_QUERY_CONVERSATION_CONTEXT = {
    "name": "query_conversation_context",
    "description": "Search conversations for specific topics, keywords, or context",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to find in conversations",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 10,
                "description": "Maximum number of conversations to return",
            },
            "include_content": {
                "type": "boolean",
                "default": False,
                "description": "Include matched content snippets",
            },
        },
        "required": ["query"],
    },
    "annotations": {
        "title": "Query Conversation Context",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


CONVERSATION_INGESTION_TOOL_HANDLERS = {
    "ingest_conversations": handle_ingest_conversations,
    "query_conversation_context": handle_query_conversation_context,
}

CONVERSATION_INGESTION_TOOL_DEFINITIONS = [
    TOOL_INGEST_CONVERSATIONS,
    TOOL_QUERY_CONVERSATION_CONTEXT,
]
