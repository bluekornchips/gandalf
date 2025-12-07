"""
Tests for recency_scorer module.
"""

from datetime import datetime, timedelta, timezone

from src.database_management.recency_scorer import RecencyScorer
from src.config.constants import RECENCY_DECAY_RATE


class TestRecencyScorer:
    """Test suite for RecencyScorer class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.scorer = RecencyScorer()

    def test_init_default_decay_rate(self) -> None:
        """Test RecencyScorer initialization with default decay rate."""
        scorer = RecencyScorer()
        assert scorer.decay_rate == RECENCY_DECAY_RATE

    def test_init_custom_decay_rate(self) -> None:
        """Test RecencyScorer initialization with custom decay rate."""
        custom_rate = 0.5
        scorer = RecencyScorer(decay_rate=custom_rate)
        assert scorer.decay_rate == custom_rate

    def test_extract_timestamp_timestamp_field(self) -> None:
        """Test extract_timestamp with timestamp field."""
        now = datetime.now(timezone.utc)
        timestamp_seconds = int(now.timestamp())
        conversation = {"timestamp": timestamp_seconds}

        result = self.scorer.extract_timestamp(conversation)
        assert result is not None
        assert isinstance(result, datetime)

    def test_extract_timestamp_timestamp_milliseconds(self) -> None:
        """Test extract_timestamp with timestamp in milliseconds."""
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)
        conversation = {"timestamp": timestamp_ms}

        result = self.scorer.extract_timestamp(conversation)
        assert result is not None
        assert isinstance(result, datetime)

    def test_extract_timestamp_created_at_field(self) -> None:
        """Test extract_timestamp with createdAt field."""
        now = datetime.now(timezone.utc)
        conversation = {"createdAt": int(now.timestamp())}

        result = self.scorer.extract_timestamp(conversation)
        assert result is not None

    def test_extract_timestamp_iso_string(self) -> None:
        """Test extract_timestamp with ISO format string."""
        now = datetime.now(timezone.utc)
        iso_string = now.isoformat()
        conversation = {"created_at": iso_string}

        result = self.scorer.extract_timestamp(conversation)
        assert result is not None

    def test_extract_timestamp_nested_metadata(self) -> None:
        """Test extract_timestamp in nested metadata structure."""
        now = datetime.now(timezone.utc)
        conversation = {"metadata": {"timestamp": int(now.timestamp())}}

        result = self.scorer.extract_timestamp(conversation)
        assert result is not None

    def test_extract_timestamp_not_found(self) -> None:
        """Test extract_timestamp when no timestamp field exists."""
        conversation = {"text": "some conversation", "other": "data"}

        result = self.scorer.extract_timestamp(conversation)
        assert result is None

    def test_extract_timestamp_non_dict(self) -> None:
        """Test extract_timestamp with non-dict input."""
        result = self.scorer.extract_timestamp({"invalid": "no timestamp"})
        assert result is None

    def test_calculate_recency_score_recent_conversation(self) -> None:
        """Test calculate_recency_score with recent conversation."""
        now = datetime.now(timezone.utc)
        conversation = {"timestamp": int(now.timestamp())}

        score = self.scorer.calculate_recency_score(conversation)
        # Recent conversations should have higher recency score
        assert score > 0.9

    def test_calculate_recency_score_old_conversation(self) -> None:
        """Test calculate_recency_score with old conversation."""
        old_time = datetime.now(timezone.utc) - timedelta(days=100)
        conversation = {"timestamp": int(old_time.timestamp())}

        score = self.scorer.calculate_recency_score(conversation)
        # Older conversations should have lower recency score
        assert score < 0.5

    def test_calculate_recency_score_no_timestamp(self) -> None:
        """Test calculate_recency_score when no timestamp available."""
        conversation = {"text": "no timestamp here"}

        score = self.scorer.calculate_recency_score(conversation)
        # Should return neutral score  when no timestamp
        assert score == 0.5

    def test_calculate_recency_score_range(self) -> None:
        """Test calculate_recency_score returns values in valid range."""
        now = datetime.now(timezone.utc)
        conversation = {"timestamp": int(now.timestamp())}

        score = self.scorer.calculate_recency_score(conversation)
        assert 0.0 <= score <= 1.0

    def test_calculate_recency_score_decay_progression(self) -> None:
        """Test calculate_recency_score shows proper decay over time."""
        base_time = datetime.now(timezone.utc)

        # Very recen
        recent = {"timestamp": int((base_time - timedelta(hours=1)).timestamp())}
        score_recent = self.scorer.calculate_recency_score(recent)

        # Medium age
        medium = {"timestamp": int((base_time - timedelta(days=1)).timestamp())}
        score_medium = self.scorer.calculate_recency_score(medium)

        # Old
        old = {"timestamp": int((base_time - timedelta(days=10)).timestamp())}
        score_old = self.scorer.calculate_recency_score(old)

        # Scores should decrease with age
        assert score_recent > score_medium > score_old

    def test_calculate_recency_score_exception_handling(self) -> None:
        """Test calculate_recency_score handles exceptions gracefully."""
        # Invalid timestamp format that might cause exception
        conversation = {"timestamp": "invalid format"}

        score = self.scorer.calculate_recency_score(conversation)
        # Should return neutral score on exception
        assert score == 0.5
