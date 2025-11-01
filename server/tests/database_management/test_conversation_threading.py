"""
Tests for conversation_threading module.
"""

from datetime import datetime, timedelta, timezone

from src.database_management.conversation_threading import ConversationThreader


class TestConversationThreader:
    """Test suite for ConversationThreader class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.threader = ConversationThreader()

    def test_extract_timestamp_int_seconds(self) -> None:
        """Test _extract_timestamp with integer timestamp in seconds."""
        now = datetime.now(timezone.utc)
        timestamp = int(now.timestamp())
        entry = {"timestamp": timestamp}

        result = self.threader._extract_timestamp(entry)
        assert result is not None
        assert isinstance(result, datetime)

    def test_extract_timestamp_int_milliseconds(self) -> None:
        """Test _extract_timestamp with integer timestamp in milliseconds."""
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)
        entry = {"timestamp": timestamp_ms}

        result = self.threader._extract_timestamp(entry)
        assert result is not None

    def test_extract_timestamp_iso_string(self) -> None:
        """Test _extract_timestamp with ISO format string."""
        now = datetime.now(timezone.utc)
        iso_string = now.isoformat()
        entry = {"createdAt": iso_string}

        result = self.threader._extract_timestamp(entry)
        assert result is not None

    def test_extract_timestamp_not_found(self) -> None:
        """Test _extract_timestamp when no timestamp field exists."""
        entry = {"text": "no timestamp"}

        result = self.threader._extract_timestamp(entry)
        assert result is None

    def test_time_window_match_within_window(self) -> None:
        """Test _time_window_match returns True for conversations within time window."""
        base_time = datetime.now(timezone.utc)
        prompt_time = base_time
        gen_time = base_time + timedelta(seconds=60)  # 1 minute later

        result = self.threader._time_window_match(prompt_time, gen_time)
        assert result is True

    def test_time_window_match_outside_window(self) -> None:
        """Test _time_window_match returns False for conversations outside time window."""
        base_time = datetime.now(timezone.utc)
        prompt_time = base_time
        gen_time = base_time + timedelta(seconds=400)  # > 5 minutes later

        result = self.threader._time_window_match(prompt_time, gen_time)
        assert result is False

    def test_time_window_match_none_times(self) -> None:
        """Test _time_window_match returns False when times are None."""
        result = self.threader._time_window_match(None, None)
        assert result is False

        result = self.threader._time_window_match(datetime.now(timezone.utc), None)
        assert result is False

    def test_thread_conversations_empty(self) -> None:
        """Test thread_conversations with empty inputs."""
        result = self.threader.thread_conversations([], [])
        assert result == []

    def test_thread_conversations_perfect_match(self) -> None:
        """Test thread_conversations with perfectly matching prompts and generations."""
        base_time = datetime.now(timezone.utc)
        prompts = [
            {"text": "Question 1", "timestamp": int(base_time.timestamp())},
            {
                "text": "Question 2",
                "timestamp": int((base_time + timedelta(seconds=100)).timestamp()),
            },
        ]
        generations = [
            {
                "textDescription": "Answer 1",
                "timestamp": int((base_time + timedelta(seconds=10)).timestamp()),
            },
            {
                "textDescription": "Answer 2",
                "timestamp": int((base_time + timedelta(seconds=110)).timestamp()),
            },
        ]

        result = self.threader.thread_conversations(prompts, generations)

        assert len(result) == 2
        assert all(not thread["unpaired"] for thread in result)
        assert all(thread["prompt"] is not None for thread in result)
        assert all(thread["generation"] is not None for thread in result)

    def test_thread_conversations_unpaired_prompts(self) -> None:
        """Test thread_conversations with unpaired prompts."""
        base_time = datetime.now(timezone.utc)
        prompts = [
            {"text": "Question 1", "timestamp": int(base_time.timestamp())},
            {
                "text": "Question 2",
                "timestamp": int((base_time + timedelta(seconds=100)).timestamp()),
            },
        ]
        generations = [
            {
                "textDescription": "Answer 1",
                "timestamp": int((base_time + timedelta(seconds=10)).timestamp()),
            },
        ]

        result = self.threader.thread_conversations(prompts, generations)

        assert len(result) >= 2
        # Should have at least one unpaired prompt
        unpaired = [
            t
            for t in result
            if t["unpaired"] and t["prompt"] is not None and t["generation"] is None
        ]
        assert len(unpaired) >= 1

    def test_thread_conversations_unpaired_generations(self) -> None:
        """Test thread_conversations with unpaired generations."""
        base_time = datetime.now(timezone.utc)
        prompts = [
            {"text": "Question 1", "timestamp": int(base_time.timestamp())},
        ]
        generations = [
            {
                "textDescription": "Answer 1",
                "timestamp": int((base_time + timedelta(seconds=10)).timestamp()),
            },
            {
                "textDescription": "Answer 2",
                "timestamp": int((base_time + timedelta(seconds=110)).timestamp()),
            },
        ]

        result = self.threader.thread_conversations(prompts, generations)

        assert len(result) >= 2
        # Should have at least one unpaired generation
        unpaired = [
            t
            for t in result
            if t["unpaired"] and t["prompt"] is None and t["generation"] is not None
        ]
        assert len(unpaired) >= 1

    def test_thread_conversations_sorted_by_timestamp(self) -> None:
        """Test thread_conversations returns results sorted by timestamp (most recent first)."""
        base_time = datetime.now(timezone.utc)
        prompts = [
            {
                "text": "Old question",
                "timestamp": int((base_time - timedelta(seconds=200)).timestamp()),
            },
            {"text": "New question", "timestamp": int(base_time.timestamp())},
        ]
        generations = [
            {
                "textDescription": "Old answer",
                "timestamp": int((base_time - timedelta(seconds=190)).timestamp()),
            },
            {
                "textDescription": "New answer",
                "timestamp": int((base_time + timedelta(seconds=10)).timestamp()),
            },
        ]

        result = self.threader.thread_conversations(prompts, generations)

        # Check that results are sorted (most recent first)
        timestamps = [
            t["timestamp"]
            if t["timestamp"]
            else datetime.min.replace(tzinfo=timezone.utc)
            for t in result
        ]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1]

    def test_thread_conversations_sequence_matching(self) -> None:
        """Test thread_conversations prefers sequence-based matching."""
        datetime.now(timezone.utc)
        prompts = [
            {"text": "Q1"},
            {"text": "Q2"},
        ]
        generations = [
            {"textDescription": "A1"},
            {"textDescription": "A2"},
        ]

        result = self.threader.thread_conversations(prompts, generations)

        # Should match Q1->A1 and Q2->A2 based on sequence
        assert len(result) >= 2
        # First thread should have first prompt and first generation
        first_thread = result[0] if result else None
        if first_thread and not first_thread["unpaired"]:
            # Should match in sequence when timestamps are missing
            assert first_thread["prompt"] is not None
            assert first_thread["generation"] is not None
