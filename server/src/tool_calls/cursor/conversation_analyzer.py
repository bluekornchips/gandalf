"""
Conversation analysis and scoring utilities for Cursor IDE conversations.

This module provides relevance scoring, keyword matching, and conversation analysis
functionality.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.constants.context import (
    ACTIVITY_SCORE_MAX_DURATION,
    CONTEXT_KEYWORDS_QUICK_LIMIT,
)
from src.config.constants.conversation import (
    CONVERSATION_KEYWORD_MATCHES_LIMIT,
    CONVERSATION_PATTERN_MATCHES_LIMIT,
)
from src.config.weights import WeightsManager
from src.core.conversation_analysis import (
    classify_conversation_type,
)
from src.core.conversation_analysis import (
    score_file_references as _score_file_references,
)
from src.core.conversation_scorer import (
    score_keyword_matches,
)
from src.tool_calls.cursor.conversation_utils import (
    extract_conversation_text_lazy,
    extract_keywords_from_content,
)
from src.utils.common import log_debug


def score_keyword_matches_optimized(
    text: str,
    context_keywords: list[str],
    limit: int = CONVERSATION_KEYWORD_MATCHES_LIMIT,
) -> float:
    """Optimized keyword matching with early termination."""
    if not context_keywords or not text:
        return 0.0

    # Use only top keywords for performance
    top_keywords = context_keywords[:CONTEXT_KEYWORDS_QUICK_LIMIT]
    text_lower = text.lower()

    score = 0.0
    matches_found = 0

    for keyword in top_keywords:
        if matches_found >= limit:
            break

        keyword_lower = keyword.lower()
        if keyword_lower in text_lower:
            score += 0.1
            matches_found += 1

    return min(score, 1.0)


def analyze_conversation_relevance_optimized(
    conversation: dict[str, Any],
    context_keywords: list[str],
    project_root: Path,
) -> dict[str, Any]:
    """Analyze conversation relevance with performance optimizations."""
    text, message_count = extract_conversation_text_lazy(conversation)

    # Quick scoring
    keyword_score = score_keyword_matches_optimized(text, context_keywords)
    recency_score = score_recency(conversation)

    # File reference scoring (lightweight)
    file_score = 0.0
    file_refs: list[str] = []
    if text:
        file_score, file_refs = score_file_references(text, project_root)

    # Pattern matching (simplified)
    pattern_score = score_pattern_matches(text, context_keywords[:5])

    # Weighted total
    weights = WeightsManager.get_default()
    total_score = (
        keyword_score * weights.get("scoring.conversation_keyword_score", 0.4)
        + recency_score * weights.get("scoring.conversation_recency_score", 0.2)
        + file_score * weights.get("scoring.conversation_file_ref_score", 0.2)
        + pattern_score * weights.get("scoring.conversation_pattern_score", 0.2)
    )

    return {
        "conversation": conversation,
        "relevance_score": round(total_score, 3),
        "message_count": message_count,
        "analysis": {
            "keyword_score": round(keyword_score, 3),
            "recency_score": round(recency_score, 3),
            "file_score": round(file_score, 3),
            "pattern_score": round(pattern_score, 3),
            "file_references": file_refs[:5],  # Limit references
        },
    }


def analyze_conversation_relevance(
    conversation: dict[str, Any],
    context_keywords: list[str],
    project_root: Path,
    include_analysis: bool = False,
) -> dict[str, Any]:
    """Analyze conversation relevance with full scoring."""
    text, message_count = extract_conversation_text_lazy(conversation)

    # Keyword scoring
    keyword_score, keyword_matches = score_keyword_matches(text, context_keywords)

    # Recency scoring
    recency_score = score_recency(conversation)

    # File reference scoring
    file_score, file_refs = score_file_references(text, project_root)

    # Pattern matching
    pattern_score = score_pattern_matches(text, context_keywords)

    # Conversation type classification
    conv_type = classify_conversation_type(text, context_keywords, file_refs)

    # Weighted total
    weights = WeightsManager.get_default()
    total_score = (
        keyword_score * weights.get("scoring.conversation_keyword_score", 0.4)
        + recency_score * weights.get("scoring.conversation_recency_score", 0.2)
        + file_score * weights.get("scoring.conversation_file_ref_score", 0.2)
        + pattern_score * weights.get("scoring.conversation_pattern_score", 0.2)
    )

    result = {
        "conversation": conversation,
        "relevance_score": round(total_score, 3),
        "message_count": message_count,
        "conversation_type": conv_type,
    }

    if include_analysis:
        result["analysis"] = {
            "keyword_score": round(keyword_score, 3),
            "recency_score": round(recency_score, 3),
            "file_score": round(file_score, 3),
            "pattern_score": round(pattern_score, 3),
            "file_references": file_refs,
            "detected_keywords": extract_keywords_from_content("", text),
        }

    return result


def score_recency(conversation: dict[str, Any]) -> float:
    """Score conversation based on how recent it is."""
    created_at = conversation.get("created_at")
    if not created_at:
        return 0.0

    try:
        if isinstance(created_at, str):
            conv_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, int | float):
            conv_time = datetime.fromtimestamp(created_at)
        else:
            return 0.0

        # Calculate age in hours
        now = datetime.now(conv_time.tzinfo) if conv_time.tzinfo else datetime.now()
        age_hours = (now - conv_time).total_seconds() / 3600

        # Score based on recency (1.0 for very recent, decaying over time)
        if age_hours <= 24:
            return 1.0
        elif age_hours <= 168:  # 1 week
            return max(0.5, 1.0 - (age_hours - 24) / (168 - 24) * 0.5)
        else:
            return max(0.1, 0.5 - (age_hours - 168) / ACTIVITY_SCORE_MAX_DURATION * 0.4)

    except (ValueError, TypeError, OverflowError):
        log_debug(f"Failed to parse date for recency scoring: {created_at}")
        return 0.0


def score_pattern_matches(
    text: str,
    context_keywords: list[str],
    limit: int = CONVERSATION_PATTERN_MATCHES_LIMIT,
) -> float:
    """Score based on pattern matches in conversation text."""
    if not text or not context_keywords:
        return 0.0

    score = 0.0
    patterns_found = 0

    # Common development patterns
    patterns = {
        "error_handling": r"\b(error|exception|try|catch|throw)\b",
        "debugging": r"\b(debug|log|console|print)\b",
        "testing": r"\b(test|spec|assert|mock)\b",
        "config": r"\b(config|setting|environment|env)\b",
        "performance": r"\b(performance|speed|optimize|slow)\b",
    }

    text_lower = text.lower()

    for pattern_name, pattern in patterns.items():
        if patterns_found >= limit:
            break

        if re.search(pattern, text_lower):
            score += 0.1
            patterns_found += 1

    # Bonus for keyword context
    for keyword in context_keywords[:5]:
        if patterns_found >= limit:
            break

        if keyword.lower() in text_lower:
            score += 0.05
            patterns_found += 1

    return min(score, 1.0)


def score_file_references(text: str, project_root: Path) -> tuple[float, list[str]]:
    """Score based on file references that exist in current project."""
    # Use the core function but add project root validation
    score, refs = _score_file_references(text)

    # Filter references to only include files that exist in the current project
    validated_refs = []
    validated_score = 0.0

    weights = WeightsManager.get_default()
    file_ref_score = weights.get("scoring.conversation_file_ref_score", 0.1)

    for ref in refs:
        potential_path = project_root / ref
        if potential_path.exists():
            validated_refs.append(ref)
            validated_score += file_ref_score

    return min(validated_score, 1.0), validated_refs
