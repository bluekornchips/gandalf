"""
Enhanced conversation recall and analysis for Gandalf MCP server.

This module provides intelligent conversation recall capabilities for Cursor IDE,
using shared conversation analysis functionality for consistency across IDEs.
"""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.constants import (
    CONVERSATION_CACHE_FILE,
    CONVERSATION_CACHE_METADATA_FILE,
    CONVERSATION_CACHE_MIN_SIZE,
    CONVERSATION_CACHE_TTL_HOURS,
    CONTEXT_KEYWORDS_QUICK_LIMIT,
    CONVERSATION_DEFAULT_RECENT_DAYS,
    CONVERSATION_MAX_LOOKBACK_DAYS,
    CONVERSATION_PROGRESS_LOG_INTERVAL,
    CONVERSATION_TEXT_EXTRACTION_LIMIT,
    CONVERSATION_TYPES,
    DATABASE_STRUCTURE_LIMITATION_NOTE,
    KEYWORD_CHECK_LIMIT,
    KEYWORD_MATCHES_LIMIT,
    KEYWORD_MATCHES_TOP_LIMIT,
    MATCHES_OUTPUT_LIMIT,
    PATTERN_MATCHES_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_LIMIT,
    CONVERSATION_DEFAULT_MIN_SCORE,
    CONVERSATION_MAX_LIMIT,
    CONVERSATION_SNIPPET_CONTEXT_CHARS,
    CONVERSATION_SNIPPET_MAX_LENGTH,
    TECHNOLOGY_KEYWORD_MAPPING,
)
from config.weights import (
    ACTIVITY_SCORE_MAX_DURATION,
    ACTIVITY_SCORE_RECENCY_BOOST,
    CONVERSATION_EARLY_TERMINATION_MULTIPLIER,
    CONVERSATION_FILE_REF_SCORE,
    CONVERSATION_KEYWORD_WEIGHT,
    CONVERSATION_RECENCY_THRESHOLDS,
    CONVERSATION_WEIGHTS,
    EARLY_TERMINATION_LIMIT_MULTIPLIER,
)
from core.conversation_analysis import (
    generate_shared_context_keywords,
    classify_conversation_type,
    score_keyword_matches,
)
from core.conversation_analysis import (
    score_file_references as _score_file_references,
)
from utils.access_control import AccessValidator
from utils.cache import get_cache_directory
from utils.common import log_debug, log_error, log_info
from utils.cursor_chat_query import CursorQuery
from utils.performance import get_duration, log_operation_time, start_timer

# Global cache for context keywords and conversation data
_context_keywords_cache = {}
_context_keywords_cache_time = {}
_conversation_cache = {}
_conversation_cache_time = {}


def get_project_cache_hash(project_root: Path, context_keywords: List[str]) -> str:
    """Generate a cache hash based on project state and keywords."""
    try:
        # Include project path and keywords in hash
        hash_input = str(project_root)

        # Add context keywords
        hash_input += "".join(sorted(context_keywords))

        # Add simple timestamp check instead of git HEAD for speed
        try:
            # Check modification time of common project files for cache invalidation
            common_files = [
                "package.json",
                "pyproject.toml",
                "requirements.txt",
                "Cargo.toml",
            ]
            for file_name in common_files:
                file_path = project_root / file_name
                if file_path.exists():
                    hash_input += str(file_path.stat().st_mtime)
                    break  # Only check first found file for speed
        except (OSError, ValueError):
            pass

        # Simple short md5 hash to avoid bloating the cache
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    except (OSError, ValueError, UnicodeDecodeError):
        return hashlib.md5(f"{project_root}{time.time()}".encode()).hexdigest()[:16]


def is_cache_valid(project_root: Path, context_keywords: List[str]) -> bool:
    """Check if cached conversation data is still valid."""
    try:
        cache_metadata_path = get_cache_directory() / CONVERSATION_CACHE_METADATA_FILE
        if not cache_metadata_path.exists():
            return False

        with open(cache_metadata_path, "r") as f:
            metadata = json.load(f)

        # Check cache age
        cache_age_hours = (time.time() - metadata.get("cached_at", 0)) / 3600
        if cache_age_hours > CONVERSATION_CACHE_TTL_HOURS:
            return False

        # Check project hash
        current_hash = get_project_cache_hash(project_root, context_keywords)
        return metadata.get("project_hash") == current_hash

    except (OSError, ValueError, json.JSONDecodeError):
        return False


def load_cached_conversations(project_root: Path) -> Optional[Dict[str, Any]]:
    """Load cached conversation data if valid."""
    try:
        cache_file_path = get_cache_directory() / CONVERSATION_CACHE_FILE
        if not cache_file_path.exists():
            return None

        with open(cache_file_path, "r") as f:
            return json.load(f)

    except (OSError, ValueError, json.JSONDecodeError):
        return None


def save_conversations_to_cache(
    project_root: Path,
    conversations: List[Dict[str, Any]],
    context_keywords: List[str],
    metadata: Dict[str, Any],
) -> bool:
    """Save conversation data to cache."""
    try:
        cache_dir = get_cache_directory()
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Save conversation data
        cache_data = {
            "conversations": conversations,
            "metadata": metadata,
            "cached_at": time.time(),
        }

        cache_file_path = cache_dir / CONVERSATION_CACHE_FILE
        with open(cache_file_path, "w") as f:
            json.dump(cache_data, f, indent=2)

        # Save cache metadata
        cache_metadata = {
            "project_hash": get_project_cache_hash(project_root, context_keywords),
            "cached_at": time.time(),
            "conversation_count": len(conversations),
        }

        cache_metadata_path = cache_dir / CONVERSATION_CACHE_METADATA_FILE
        with open(cache_metadata_path, "w") as f:
            json.dump(cache_metadata, f, indent=2)

        return True

    except (OSError, ValueError, json.JSONDecodeError):
        return False


# Use shared implementation from conversation_analysis module
generate_context_keywords = generate_shared_context_keywords


def _get_tech_category_from_extension(extension: str) -> Optional[str]:
    """Get technology category from file extension."""
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
    return ext_mapping.get(extension.lower())


def _extract_keywords_from_content(file_name: str, content: str) -> List[str]:
    """Extract keywords from file content."""
    keywords = []

    if file_name == "package.json":
        try:
            data = json.loads(content)
            if "name" in data:
                keywords.append(data["name"])
            if "keywords" in data:
                keywords.extend(data["keywords"][:5])
        except json.JSONDecodeError:
            pass

    elif file_name in ["README.md", "CLAUDE.md"]:
        content_lower = content.lower()
        for tech_category, tech_terms in TECHNOLOGY_KEYWORD_MAPPING.items():
            for term in tech_terms:
                if term.lower() in content_lower:
                    keywords.append(term)

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
    """Quick filter to eliminate obviously irrelevant conversations."""
    try:
        # Check recency first
        created_at = conversation.get("createdAt")
        if created_at:
            try:
                if isinstance(created_at, str):
                    conv_date = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                else:
                    conv_date = datetime.fromtimestamp(created_at / 1000)

                if conv_date < cutoff_date:
                    return False
            except (ValueError, TypeError, OSError):
                pass

        # Check for minimum activity (exchanges)
        exchange_count = conversation.get("numExchanges", 0)
        if exchange_count < min_exchanges:
            return False

        # Quick keyword check in conversation name
        conv_name = conversation.get("name", "").lower()
        if conv_name and conv_name != "untitled":
            for keyword in context_keywords[:CONTEXT_KEYWORDS_QUICK_LIMIT]:
                if keyword.lower() in conv_name:
                    return True

        return True

    except (AttributeError, TypeError, KeyError):
        return False


def analyze_conversation_relevance_optimized(
    conversation: Dict[str, Any],
    prompts: List[Dict[str, Any]],
    generations: List[Dict[str, Any]],
    context_keywords: List[str],
    project_root: Path,
    include_detailed_analysis: bool = False,
) -> Tuple[float, Dict[str, Any]]:
    """Optimized conversation relevance analysis with early termination."""
    try:
        # Quick extraction with limits
        conversation_text = extract_conversation_text_lazy(
            conversation, prompts, generations
        )

        if not conversation_text or len(conversation_text) < 10:
            return 0.0, {"reason": "insufficient_content"}

        # Optimized keyword matching
        keyword_score, keyword_matches = score_keyword_matches_optimized(
            conversation_text, context_keywords
        )

        # Quick recency score
        recency_score = score_recency(conversation)

        # Early termination for low scores
        base_score = keyword_score + recency_score
        if base_score < 0.1 and not include_detailed_analysis:
            return base_score, {
                "keyword_score": keyword_score,
                "recency_score": recency_score,
                "matches": keyword_matches[:KEYWORD_MATCHES_TOP_LIMIT],
            }

        # File reference analysis (more expensive)
        file_score, file_refs = score_file_references(conversation_text, project_root)

        total_score = keyword_score + recency_score + file_score

        analysis = {
            "keyword_score": keyword_score,
            "recency_score": recency_score,
            "file_score": file_score,
            "matches": keyword_matches[:KEYWORD_MATCHES_TOP_LIMIT],
            "file_references": file_refs[:MATCHES_OUTPUT_LIMIT],
            "total_score": min(total_score, 1.0),
        }

        return min(total_score, 1.0), analysis

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_debug(f"Error analyzing conversation relevance: {e}")
        return 0.0, {"error": str(e)}


def extract_conversation_text(
    conversation: Dict[str, Any],
    prompts: List[Dict[str, Any]],
    generations: List[Dict[str, Any]],
) -> str:
    """Extract conversation text for analysis."""
    text_parts = []

    # Add conversation name/title
    conv_name = conversation.get("name", "")
    if conv_name and conv_name != "Untitled":
        text_parts.append(conv_name)

    # Add prompts and generations
    conv_id = conversation.get("composerId", "")
    for prompt in prompts:
        if prompt.get("conversationId") == conv_id:
            text = prompt.get("text", "")
            if text:
                text_parts.append(text)

    for gen in generations:
        if gen.get("conversationId") == conv_id:
            text = gen.get("text", "")
            if text:
                text_parts.append(text)

    return " ".join(text_parts).lower()


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
    matches = []
    score = 0.0

    for pattern in patterns:
        found_matches = re.findall(pattern, text, re.IGNORECASE)
        for match in found_matches[:max_matches]:
            matches.append(match)
            score += score_per_match

    return min(score, 1.0), matches[:max_matches]


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
        keyword_score, matches = score_keyword_matches(conv_text, context_keywords)
        score += keyword_score * CONVERSATION_WEIGHTS["keyword_match"]
        analysis["keyword_matches"] = matches[:KEYWORD_MATCHES_TOP_LIMIT]

    recency_score = score_recency(conversation)
    score += recency_score * CONVERSATION_WEIGHTS["recency"]
    analysis["recency_score"] = recency_score

    # Use the centralized classify_conversation_type function
    analysis["conversation_type"] = classify_conversation_type(
        conv_text, analysis["keyword_matches"], []
    )

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
    """Extract a relevant snippet around the query match."""
    query_lower = query.lower()
    text_lower = text.lower()

    # Find the position of the query in the text
    query_pos = text_lower.find(query_lower)
    if query_pos == -1:
        # If exact query not found, return first part of text
        return (
            text[:CONVERSATION_SNIPPET_MAX_LENGTH] + "..."
            if len(text) > CONVERSATION_SNIPPET_MAX_LENGTH
            else text
        )

    # Calculate snippet bounds
    start = max(0, query_pos - CONVERSATION_SNIPPET_CONTEXT_CHARS)
    end = min(len(text), query_pos + len(query) + CONVERSATION_SNIPPET_CONTEXT_CHARS)

    snippet = text[start:end]

    # Add ellipsis if we're not at the beginning/end
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def handle_recall_cursor_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Recall and analyze relevant conversations with intelligent caching."""
    try:
        limit = arguments.get("limit", CONVERSATION_DEFAULT_LIMIT)
        min_relevance_score = arguments.get(
            "min_relevance_score", CONVERSATION_DEFAULT_MIN_SCORE
        )
        days_lookback = arguments.get("days_lookback", CONVERSATION_DEFAULT_RECENT_DAYS)
        conversation_types = arguments.get("conversation_types", [])
        include_analysis = arguments.get("include_analysis", False)
        fast_mode = arguments.get("fast_mode", True)

        # Validate parameters
        if not isinstance(limit, int) or limit < 1 or limit > CONVERSATION_MAX_LIMIT:
            return AccessValidator.create_error_response(
                f"limit must be an integer between 1 and {CONVERSATION_MAX_LIMIT}"
            )

        if not isinstance(min_relevance_score, (int, float)) or min_relevance_score < 0:
            return AccessValidator.create_error_response(
                "min_relevance_score must be a non-negative number"
            )

        if (
            not isinstance(days_lookback, int)
            or days_lookback < 1
            or days_lookback > CONVERSATION_MAX_LOOKBACK_DAYS
        ):
            return AccessValidator.create_error_response(
                f"days_lookback must be an integer between 1 and {CONVERSATION_MAX_LOOKBACK_DAYS}"
            )

        # Fast mode: Skip expensive keyword generation and cache validation for speed
        if fast_mode:
            # Initialize query tool for fresh data
            query_tool = CursorQuery(silent=True)

            # Query conversations
            log_info("Fast mode: Querying conversations from Cursor databases...")
            start_time = start_timer()
            data = query_tool.query_all_conversations()
            query_time = get_duration(start_time)
            log_operation_time("cursor_conversation_query", start_time, "debug")

            result_data = handle_fast_conversation_extraction(
                data, limit, days_lookback, conversation_types, query_time
            )

            return result_data

        # Enhanced mode: Use caching and context keywords for better relevance
        # Generate context keywords for cache validation
        log_info("Generating intelligent context keywords...")
        context_keywords = generate_context_keywords(project_root)
        log_debug(f"Generated context keywords: {context_keywords[:15]}...")

        # Check cache first
        if is_cache_valid(project_root, context_keywords):
            log_info("Loading conversations from cache...")
            cached_data = load_cached_conversations(project_root)
            if cached_data:
                cached_conversations = cached_data.get("conversations", [])

                # Apply current filters to cached data
                cutoff_date = datetime.now() - timedelta(days=days_lookback)
                filtered_cached = []

                for conv in cached_conversations:
                    # Apply relevance score filter
                    if conv.get("relevance_score", 0) >= min_relevance_score:
                        # Apply conversation type filter
                        if (
                            not conversation_types
                            or conv.get("conversation_type") in conversation_types
                        ):
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
                                (time.time() - cached_data.get("cached_at", 0)) / 3600,
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
                    return AccessValidator.create_success_response(
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
        relevant_conversations.sort(key=lambda x: x["relevance_score"], reverse=True)
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
                "conversation_type": conv_data["analysis"]["conversation_type"],
                "last_updated": conv_data["conversation"].get("lastUpdatedAt", 0),
                "keyword_matches": len(conv_data["analysis"]["keyword_matches"]),
                "file_references": len(conv_data["analysis"]["file_references"]),
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

        return AccessValidator.create_success_response(json.dumps(result, indent=2))

    except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
        log_error(e, "recall_cursor_conversations")
        return AccessValidator.create_error_response(
            f"Error recalling conversations: {str(e)}"
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
                recency_hours = (time.time() * 1000 - last_updated) / (1000 * 3600)

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
                "id": conv_id,
                "title": conv_name or "Untitled",
                "created_at": created_at,
                "updated_at": last_updated,
                "message_count": estimated_exchanges,
                "relevance_score": round(activity_score, 2),
                "snippet": f"Conversation with {estimated_exchanges} exchanges",
                "workspace_id": workspace_hash,
                "conversation_type": "general",
                "ai_model": "",
                "user_query": "",
                "ai_response": "",
                "file_references": [],
                "code_blocks": [],
                "metadata": {
                    "prompt_count": estimated_exchanges,
                    "generation_count": estimated_exchanges,
                    "total_exchanges": estimated_exchanges,
                    "activity_score": round(activity_score, 2),
                    "workspace_stats": {
                        "total_conversations": total_conversations,
                        "total_prompts": total_prompts,
                        "total_generations": total_generations,
                    },
                },
                # Legacy fields for backward compatibility
                "name": conv_name or "Untitled",
                "conversation_id": conv_id,
                "last_updated": last_updated,
                "workspace_hash": workspace_hash,
            }

            conversations.append(conv_data)

            if len(conversations) >= limit * EARLY_TERMINATION_LIMIT_MULTIPLIER:
                break

    # Sort by last updated, most recent first, and limit
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
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
    return AccessValidator.create_success_response(json.dumps(result, indent=2))


def handle_search_cursor_conversations(
    arguments: Dict[str, Any], project_root: Path, **kwargs
) -> Dict[str, Any]:
    """Search conversations for specific context or topics."""
    try:
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        include_content = arguments.get("include_content", False)

        if not query or not isinstance(query, str):
            return AccessValidator.create_error_response(
                "query parameter is required and must be a string"
            )

        if not isinstance(limit, int) or limit < 1 or limit > 50:
            return AccessValidator.create_error_response(
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
                        "id": conv_id,
                        "title": conversation.get("name", "Untitled"),
                        "workspace_id": workspace["workspace_hash"][:8],
                        "updated_at": conversation.get("lastUpdatedAt", 0),
                        "match_type": "title" if name_match else "content",
                        "message_count": len(conv_prompts) + len(conv_generations),
                        "relevance_score": 1.0 if name_match else 0.5,
                        "snippet": matched_content[0] if matched_content else "",
                        # Legacy fields
                        "name": conversation.get("name", "Untitled"),
                        "conversation_id": conv_id,
                        "last_updated": conversation.get("lastUpdatedAt", 0),
                        "workspace_hash": workspace["workspace_hash"][:8],
                        "prompt_count": len(conv_prompts),
                        "generation_count": len(conv_generations),
                    }

                    if include_content and matched_content:
                        match_data["matched_content"] = matched_content

                    matching_conversations.append(match_data)

        # Sort by last updated (most recent first) and limit
        matching_conversations.sort(key=lambda x: x["updated_at"], reverse=True)
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
        return AccessValidator.create_success_response(json.dumps(result, indent=2))

    except (OSError, ValueError, TypeError, KeyError, FileNotFoundError) as e:
        log_error(e, "search_cursor_conversations")
        return AccessValidator.create_error_response(
            f"Error querying conversation context: {str(e)}"
        )


# Tool definitions
TOOL_RECALL_CURSOR_CONVERSATIONS = {
    "name": "recall_cursor_conversations",
    "description": "Recall and analyze relevant conversations from Cursor IDE history with intelligent caching. Defaults to recent 7 days for focused relevance.",
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
        "title": "Recall Relevant Conversations with Smart Caching",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}

TOOL_SEARCH_CURSOR_CONVERSATIONS = {
    "name": "search_cursor_conversations",
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
        "title": "Search Conversation Context",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
}


CONVERSATION_RECALL_TOOL_HANDLERS = {
    "recall_cursor_conversations": handle_recall_cursor_conversations,
    "search_cursor_conversations": handle_search_cursor_conversations,
}

CONVERSATION_RECALL_TOOL_DEFINITIONS = [
    TOOL_RECALL_CURSOR_CONVERSATIONS,
    TOOL_SEARCH_CURSOR_CONVERSATIONS,
]


def score_file_references(text: str, project_root: Path) -> Tuple[float, List[str]]:
    """Score based on file references that exist in current project."""
    # Use the core function but add project root validation
    score, refs = _score_file_references(text)

    # Filter references to only include files that exist in the current project
    validated_refs = []
    validated_score = 0.0

    for ref in refs:
        potential_path = project_root / ref
        if potential_path.exists():
            validated_refs.append(ref)
            validated_score += CONVERSATION_FILE_REF_SCORE

    return min(validated_score, 1.0), validated_refs
