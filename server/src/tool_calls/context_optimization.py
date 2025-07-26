"""
Context optimization utilities for conversation aggregation.

This module handles token optimization, response size management,
and context-aware processing for large conversation datasets.
"""

# Use common imports for frequently used utilities
from src.common_imports import (
    TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
    Any,
    json,
    log_debug,
    log_info,
)

# Specific imports not in common_imports
from src.config.conversation_config import (
    TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE,
    TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD,
)


def optimize_context_keywords(
    keywords: list[str],
    max_keywords: int = TOKEN_OPTIMIZATION_MAX_CONTEXT_KEYWORDS,
) -> list[str]:
    """Optimize context keywords for performance and relevance."""
    if len(keywords) <= max_keywords:
        return keywords

    # Sort by length and frequency heuristics
    # Prefer shorter, more specific keywords
    sorted_keywords = sorted(
        keywords,
        key=lambda k: (len(k), k.lower()),
    )

    optimized = sorted_keywords[:max_keywords]

    log_debug(f"Optimized context keywords: {len(keywords)} -> {len(optimized)}")

    return optimized


def calculate_response_size(data: dict[str, Any]) -> int:
    """Calculate the approximate size of a response in bytes."""
    try:
        json_str = json.dumps(data, default=str)
        return len(json_str.encode("utf-8"))
    except (TypeError, ValueError):
        # Fallback estimation
        return len(str(data).encode("utf-8"))


def should_use_summary_mode(
    conversations: list[dict[str, Any]],
    threshold: int = TOKEN_OPTIMIZATION_SUMMARY_MODE_THRESHOLD,
) -> bool:
    """Determine if summary mode should be used based on response size."""
    test_data = {"conversations": conversations}
    size = calculate_response_size(test_data)

    should_summarize = size > threshold

    if should_summarize:
        log_info(
            f"Large response detected ({size:,} bytes > {threshold:,}), "
            "recommending summary mode"
        )

    return should_summarize


def optimize_conversations_for_size(
    conversations: list[dict[str, Any]],
    target_size: int = TOKEN_OPTIMIZATION_MAX_RESPONSE_SIZE,
) -> list[dict[str, Any]]:
    """Optimize conversations to fit within target response size."""
    if not conversations:
        return conversations

    current_size = calculate_response_size({"conversations": conversations})

    if current_size <= target_size:
        log_debug(f"Response size OK: {current_size:,} <= {target_size:,} bytes")
        return conversations

    log_info(f"Optimizing {len(conversations)} conversations ({current_size:,} bytes)")

    optimized_conversations: list[dict[str, Any]] = []
    running_size = 0

    for conversation in conversations:
        # Create optimized version of conversation
        optimized_conv = _optimize_single_conversation(conversation)
        conv_size = calculate_response_size(optimized_conv)

        # Check if adding this conversation would exceed target
        if running_size + conv_size > target_size:
            log_debug(
                f"Stopping at {len(optimized_conversations)} conversations to fit size limit"
            )
            break

        optimized_conversations.append(optimized_conv)
        running_size += conv_size

    final_size = calculate_response_size({"conversations": optimized_conversations})
    log_info(
        f"Optimization complete: {len(conversations)} -> {len(optimized_conversations)} "
        f"conversations, {current_size:,} -> {final_size:,} bytes"
    )

    return optimized_conversations


def _optimize_single_conversation(conversation: dict[str, Any]) -> dict[str, Any]:
    """Optimize a single conversation for size."""
    optimized = {}

    # Keep essential fields
    essential_fields = [
        "id",
        "title",
        "source_tool",
        "message_count",
        "relevance_score",
        "created_at",
    ]

    for field in essential_fields:
        if field in conversation:
            value = conversation[field]

            # Truncate string fields
            if isinstance(value, str) and field in ["title", "id"]:
                if field == "title":
                    optimized[field] = (
                        value[:100] + "..." if len(value) > 100 else value
                    )
                elif field == "id":
                    optimized[field] = value[:50] + "..." if len(value) > 50 else value
                else:
                    optimized[field] = value
            else:
                optimized[field] = value

    # Add snippet if available, but truncated
    if "snippet" in conversation:
        snippet = str(conversation["snippet"])
        optimized["snippet"] = snippet[:150] + "..." if len(snippet) > 150 else snippet

    return optimized


def create_size_optimized_summary(
    full_summary: dict[str, Any],
    optimization_stats: dict[str, Any],
) -> dict[str, Any]:
    """Create a size-optimized version of the summary."""
    optimized_summary = {
        "total_conversations_found": full_summary.get("total_conversations_found", 0),
        "conversations_returned": full_summary.get("conversations_returned", 0),
        "success_rate_percent": full_summary.get("success_rate_percent", 0),
        "processing_time_seconds": full_summary.get("processing_time_seconds", 0),
    }

    # Add optimization info
    if optimization_stats:
        optimized_summary["optimization"] = {
            "applied": True,
            "original_count": optimization_stats.get("original_count", 0),
            "original_size_bytes": optimization_stats.get("original_size_bytes", 0),
            "optimized_size_bytes": optimization_stats.get("optimized_size_bytes", 0),
            "reduction_percent": round(
                (
                    1
                    - optimization_stats.get("optimized_size_bytes", 0)
                    / max(optimization_stats.get("original_size_bytes", 1), 1)
                )
                * 100,
                1,
            ),
        }

    return optimized_summary


def estimate_conversation_processing_time(
    conversation_count: int,
    include_analysis: bool = False,
) -> float:
    """Estimate processing time for a given number of conversations."""
    # Base processing time per conversation
    base_time_per_conv = 0.01  # 10ms per conversation for basic processing

    if include_analysis:
        # Analysis adds significant overhead
        analysis_time_per_conv = 0.05  # 50ms per conversation for analysis
        total_time = conversation_count * (base_time_per_conv + analysis_time_per_conv)
    else:
        total_time = conversation_count * base_time_per_conv

    # Add base overhead
    overhead = 0.5  # 500ms base overhead

    return total_time + overhead


def should_enable_fast_mode(
    conversation_count: int,
    time_limit_seconds: float = 10.0,
) -> bool:
    """Determine if fast mode should be enabled based on conversation count."""
    estimated_time = estimate_conversation_processing_time(
        conversation_count, include_analysis=True
    )

    should_use_fast = estimated_time > time_limit_seconds

    if should_use_fast:
        log_info(
            f"Recommending fast mode: estimated {estimated_time:.1f}s > {time_limit_seconds}s limit"
        )

    return should_use_fast


def create_processing_strategy(
    available_tools: list[str],
    estimated_conversations: int,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Create an optimal processing strategy based on available data."""
    strategy = {
        "use_fast_mode": parameters.get("fast_mode", True),
        "enable_caching": True,
        "parallel_processing": len(available_tools) > 1,
        "size_optimization": False,
    }

    # Adjust strategy based on estimated workload
    if estimated_conversations > 1000:
        strategy["use_fast_mode"] = True
        strategy["size_optimization"] = True
        strategy["enable_analysis"] = False
        log_info("High conversation count: enabling aggressive optimizations")
    elif estimated_conversations > 500:
        strategy["size_optimization"] = True
        log_info("Moderate conversation count: enabling size optimization")

    # Override with explicit user parameters
    if "fast_mode" in parameters:
        strategy["use_fast_mode"] = parameters["fast_mode"]

    if "include_analysis" in parameters:
        strategy["enable_analysis"] = parameters["include_analysis"]

    return strategy
