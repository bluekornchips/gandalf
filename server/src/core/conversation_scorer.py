"""
Conversation scoring and relevance analysis utilities.

This module provides scoring mechanisms for analyzing conversation relevance
based on keywords, file references, recency, and conversation type classification.
"""

import re
from datetime import datetime
from typing import Any

from src.config.config_data import FILE_REFERENCE_PATTERNS
from src.config.weights import WeightsManager
from src.utils.common import log_error


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
            "keyword_score": keyword_score,
            "file_score": file_score,
            "type_bonus": type_bonus,
        }

        if include_detailed_analysis:
            analysis.update(
                {
                    "content_length": len(session_content),
                    "keyword_density": len(keyword_matches) / len(context_keywords)
                    if context_keywords
                    else 0,
                    "file_reference_count": len(file_references),
                }
            )

        return (
            min(total_score, 5.0),  # Cap at maximum score
            analysis,
        )

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
            keyword_weight = conversation_weights.get("keyword_weight", 1.0)
            score += (
                len(keyword) * keyword_weight * 0.01
            )  # Scale down to prevent huge scores

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
            score += conversation_weights.get("file_reference_score", 0.1)

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

        # Generic timestamp field
        elif "timestamp" in session_metadata:
            ts = session_metadata["timestamp"]
            if isinstance(ts, int | float):
                timestamp = ts
            elif isinstance(ts, str):
                try:
                    session_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
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
            return float(recency_thresholds.get("days_1", 1.0))
        elif days_ago <= 7:
            return float(recency_thresholds.get("days_7", 0.8))
        elif days_ago <= 30:
            return float(recency_thresholds.get("days_30", 0.5))
        elif days_ago <= 90:
            return float(recency_thresholds.get("days_90", 0.2))
        else:
            return float(recency_thresholds.get("default", 0.1))

    except (ValueError, TypeError, OSError):
        return 0.0


def classify_conversation_type(
    text_content: str, keyword_matches: list[str], file_references: list[str]
) -> str:
    """Classify conversation type using standardized patterns."""
    text_lower = text_content.lower()

    # Check for debugging indicators
    debug_terms = [
        "error",
        "bug",
        "fix",
        "debug",
        "issue",
        "exception",
        "traceback",
        "stack trace",
        "crash",
        "fail",
    ]
    if any(term in text_lower for term in debug_terms):
        return "debugging"

    # Check for testing indicators
    test_terms = [
        "test",
        "testing",
        "pytest",
        "spec",
        "unit",
        "integration",
        "mock",
        "assert",
        "coverage",
    ]
    if any(term in text_lower for term in test_terms):
        return "testing"

    # Check for architecture indicators
    arch_terms = [
        "refactor",
        "architecture",
        "design",
        "structure",
        "pattern",
        "organize",
        "restructure",
        "modular",
    ]
    if any(term in text_lower for term in arch_terms):
        return "architecture"

    # Check for technical discussion indicators
    if len(keyword_matches) > 3 or len(file_references) > 2:
        return "code_discussion"

    # Check for problem solving indicators
    problem_terms = [
        "how",
        "help",
        "problem",
        "solve",
        "implement",
        "create",
        "build",
        "make",
    ]
    if any(term in text_lower for term in problem_terms):
        return "problem_solving"

    # Check for documentation indicators
    doc_terms = [
        "document",
        "explain",
        "describe",
        "comment",
        "readme",
        "documentation",
        "guide",
        "tutorial",
    ]
    if any(term in text_lower for term in doc_terms):
        return "documentation"

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
        "documentation": 0.05,
        "general": 0.0,
    }

    type_bonuses = conversation_weights.get("type_bonuses", default_bonuses)
    return float(type_bonuses.get(conversation_type, 0.0))


def calculate_composite_score(
    keyword_score: float,
    file_score: float,
    recency_score: float,
    type_bonus: float,
    weights_config: Any | None = None,
) -> float:
    """Calculate composite relevance score from individual components."""
    weights = weights_config or WeightsManager.get_default()
    conversation_weights = weights.get_dict("conversation")

    total_score = 0.0
    total_score += keyword_score * float(conversation_weights.get("keyword_match", 0.4))
    total_score += recency_score * float(conversation_weights.get("recency", 0.2))
    total_score += file_score * float(conversation_weights.get("file_reference", 0.2))
    total_score += type_bonus * float(
        conversation_weights.get("type_bonus_weight", 1.0)
    )

    return min(total_score, 5.0)


def get_scoring_explanation(analysis: dict[str, Any]) -> dict[str, str]:
    """Generate human-readable explanation of scoring decisions."""
    explanations = {}

    # Keyword matching explanation
    keyword_matches = analysis.get("keyword_matches", [])
    if keyword_matches:
        explanations["keywords"] = (
            f"Matched {len(keyword_matches)} keywords: {', '.join(keyword_matches[:3])}"
        )
    else:
        explanations["keywords"] = "No keyword matches found"

    # File reference explanation
    file_refs = analysis.get("file_references", [])
    if file_refs:
        explanations["files"] = (
            f"References {len(file_refs)} files: {', '.join(file_refs[:2])}"
        )
    else:
        explanations["files"] = "No file references found"

    # Recency explanation
    recency_score = analysis.get("recency_score", 0.0)
    if recency_score > 0.8:
        explanations["recency"] = "Very recent conversation"
    elif recency_score > 0.5:
        explanations["recency"] = "Recent conversation"
    elif recency_score > 0.2:
        explanations["recency"] = "Moderately recent conversation"
    else:
        explanations["recency"] = "Older conversation"

    # Type explanation
    conv_type = analysis.get("conversation_type", "general")
    type_descriptions = {
        "debugging": "Debugging/troubleshooting conversation",
        "architecture": "Software architecture discussion",
        "testing": "Testing-related conversation",
        "code_discussion": "Technical code discussion",
        "problem_solving": "Problem-solving conversation",
        "documentation": "Documentation-related conversation",
        "general": "General conversation",
    }
    explanations["type"] = type_descriptions.get(conv_type, "Unknown conversation type")

    return explanations
