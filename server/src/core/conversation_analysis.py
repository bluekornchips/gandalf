"""
Conversation analysis and relevance scoring for Claude Code conversations.

This module provides the main interface for conversation analysis, keyword extraction,
and relevance scoring across different conversation formats and IDEs.
"""

from pathlib import Path
from typing import Any

from src.core.content_extractor import (
    extract_conversation_content,
    extract_conversation_metadata,
    extract_conversation_summary,
    filter_conversations_by_date,
    get_conversation_statistics,
    normalize_conversation_format,
    sort_conversations_by_relevance,
)
from src.core.conversation_scorer import (
    analyze_session_relevance,
    calculate_composite_score,
    classify_conversation_type,
    get_conversation_type_bonus,
    get_scoring_explanation,
    score_file_references,
    score_keyword_matches,
    score_session_recency,
)
from src.core.keyword_extractor import (
    extract_keywords_from_file,
    extract_tech_keywords_from_files,
    generate_shared_context_keywords,
    get_project_summary,
)

# Export key functions
__all__ = [
    # Main analysis functions
    "generate_shared_context_keywords",
    "analyze_session_relevance",
    "extract_conversation_content",
    "classify_conversation_type",
    # Scoring functions
    "score_keyword_matches",
    "score_file_references",
    "score_session_recency",
    "get_conversation_type_bonus",
    "calculate_composite_score",
    # Content processing
    "extract_conversation_metadata",
    "extract_conversation_summary",
    "normalize_conversation_format",
    "filter_conversations_by_date",
    "sort_conversations_by_relevance",
    # Keyword extraction
    "extract_keywords_from_file",
    "extract_tech_keywords_from_files",
    # Utilities
    "get_project_summary",
    "get_conversation_statistics",
    "get_scoring_explanation",
]


def analyze_conversation_batch(
    conversations: list[dict[str, Any]],
    project_root: Path,
    include_detailed_analysis: bool = False,
    weights_config: Any | None = None,
) -> list[dict[str, Any]]:
    """Analyze a batch of conversations for relevance scoring."""
    if not conversations:
        return []

    # Generate context keywords once for the batch
    context_keywords = generate_shared_context_keywords(project_root)

    analyzed_conversations = []

    for conversation in conversations:
        try:
            # Extract content and metadata
            content = extract_conversation_content(conversation)
            metadata = extract_conversation_metadata(conversation)

            # Analyze relevance
            relevance_score, analysis = analyze_session_relevance(
                content,
                context_keywords,
                metadata,
                include_detailed_analysis,
                weights_config,
            )

            # Create analyzed conversation entry
            analyzed_conv = {
                "conversation": conversation,
                "relevance_score": relevance_score,
                "content": content,
                "metadata": metadata,
                "analysis": analysis,
            }

            if include_detailed_analysis:
                analyzed_conv["summary"] = extract_conversation_summary(conversation)
                analyzed_conv["scoring_explanation"] = get_scoring_explanation(analysis)

            analyzed_conversations.append(analyzed_conv)

        except Exception:
            # Include conversation with zero score if analysis fails
            analyzed_conversations.append(
                {
                    "conversation": conversation,
                    "relevance_score": 0.0,
                    "content": "",
                    "metadata": {},
                    "analysis": {"conversation_type": "general"},
                }
            )

    return analyzed_conversations


def get_conversation_insights(
    conversations: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    """Get comprehensive insights about a collection of conversations."""
    if not conversations:
        return {
            "total_conversations": 0,
            "insights": {},
            "recommendations": [],
        }

    # Analyze conversations
    analyzed = analyze_conversation_batch(
        conversations, project_root, include_detailed_analysis=True
    )

    # Calculate statistics
    stats = get_conversation_statistics(conversations)

    # Group by conversation type
    type_distribution: dict[str, int] = {}
    score_distribution = {"high": 0, "medium": 0, "low": 0}
    keyword_frequency: dict[str, int] = {}

    for conv in analyzed:
        # Conversation type distribution
        conv_type = conv["analysis"].get("conversation_type", "general")
        type_distribution[conv_type] = type_distribution.get(conv_type, 0) + 1

        # Score distribution
        score = conv["relevance_score"]
        if score >= 3.0:
            score_distribution["high"] += 1
        elif score >= 1.0:
            score_distribution["medium"] += 1
        else:
            score_distribution["low"] += 1

        # Keyword frequency
        keywords = conv["analysis"].get("keyword_matches", [])
        for keyword in keywords:
            keyword_frequency[keyword] = keyword_frequency.get(keyword, 0) + 1

    # Generate recommendations
    recommendations = []

    if score_distribution["low"] > len(conversations) * 0.7:
        recommendations.append(
            "Consider reviewing conversation selection criteria - many conversations have low relevance scores"
        )

    if type_distribution.get("debugging", 0) > len(conversations) * 0.5:
        recommendations.append(
            "High proportion of debugging conversations - consider focusing on architectural discussions"
        )

    if not keyword_frequency:
        recommendations.append(
            "Few keyword matches found - consider updating project context keywords"
        )

    return {
        "total_conversations": len(conversations),
        "statistics": stats,
        "type_distribution": type_distribution,
        "score_distribution": score_distribution,
        "top_keywords": sorted(
            keyword_frequency.items(), key=lambda x: x[1], reverse=True
        )[:10],
        "insights": {
            "average_relevance": sum(c["relevance_score"] for c in analyzed)
            / len(analyzed),
            "most_common_type": max(type_distribution.items(), key=lambda x: x[1])[0]
            if type_distribution
            else "general",
            "high_relevance_count": score_distribution["high"],
        },
        "recommendations": recommendations,
    }
