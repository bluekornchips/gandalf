"""
Conversation threading to pair prompts with corresponding generations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConversationThreader:
    """Threads conversations by matching prompts with corresponding generations."""

    def _extract_timestamp(self, entry: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from conversation entry.

        Args:
            entry: Conversation entry dictionary.

        Returns:
            Datetime object if found, None otherwise.
        """
        if not isinstance(entry, dict):
            return None

        timestamp_fields = ["timestamp", "createdAt", "date", "time", "created_at"]

        for field in timestamp_fields:
            if field in entry:
                value = entry[field]
                if isinstance(value, (int, float)):
                    if value > 1e10:  # Milliseconds
                        value = value / 1000
                    return datetime.fromtimestamp(value, tz=timezone.utc)
                elif isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

        return None

    def _time_window_match(
        self, prompt_time: Optional[datetime], gen_time: Optional[datetime]
    ) -> bool:
        """Check if generation is within reasonable time window of prompt.

        Args:
            prompt_time: Prompt timestamp.
            gen_time: Generation timestamp.

        Returns:
            True if within 5 minute window, False otherwise.
        """
        if prompt_time is None or gen_time is None:
            return False

        time_diff = abs((gen_time - prompt_time).total_seconds())
        return time_diff <= 300  # 5 minutes

    def thread_conversations(
        self,
        prompts: List[Dict[str, Any]],
        generations: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Thread conversations by pairing prompts with generations.

        Matching strategy:
        1. Sequence matching: prompt[i] pairs with generation[i] or generation[i+1]
        2. Timestamp matching: generation within 5 minutes of prompt
        3. Proximity: prefer closer generations

        Args:
            prompts: List of prompt dictionaries.
            generations: List of generation dictionaries.

        Returns:
            List of threaded conversation dictionaries with structure:
            {
                "prompt": {...},
                "generation": {...},
                "timestamp": datetime,
                "unpaired": False
            }
            Also includes unpaired entries.
        """
        if not prompts and not generations:
            return []

        threaded: List[Dict[str, Any]] = []
        used_generations = set()

        prompt_times = [self._extract_timestamp(p) for p in prompts]
        gen_times = [self._extract_timestamp(g) for g in generations]

        for i, prompt in enumerate(prompts):
            prompt_time = prompt_times[i]
            best_match_idx = None
            best_match_score = -1

            # Find best matching generation
            for j, generation in enumerate(generations):
                if j in used_generations:
                    continue

                gen_time = gen_times[j]
                score = 0.0

                if j == i:
                    score += 2.0
                elif j == i + 1:
                    score += 1.5
                elif abs(j - i) <= 2:
                    score += 1.0
                else:
                    score += 0.5 / abs(j - i)

                if self._time_window_match(prompt_time, gen_time):
                    score += 1.0

                if score > best_match_score:
                    best_match_score = int(score)
                    best_match_idx = j

            if best_match_idx is not None and best_match_score > 0.5:
                generation = generations[best_match_idx]
                used_generations.add(best_match_idx)

                thread_time = prompt_time or gen_times[best_match_idx]

                threaded.append(
                    {
                        "prompt": prompt,
                        "generation": generation,
                        "timestamp": thread_time,
                        "unpaired": False,
                    }
                )
            else:
                threaded.append(
                    {
                        "prompt": prompt,
                        "generation": None,
                        "timestamp": prompt_time,
                        "unpaired": True,
                    }
                )

        for j, generation in enumerate(generations):
            if j not in used_generations:
                threaded.append(
                    {
                        "prompt": None,
                        "generation": generation,
                        "timestamp": gen_times[j],
                        "unpaired": True,
                    }
                )

        threaded.sort(
            key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min,
            reverse=True,
        )

        return threaded
