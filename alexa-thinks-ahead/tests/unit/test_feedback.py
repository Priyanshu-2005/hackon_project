"""Unit tests for FeedbackCollector."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.learning.feedback import FeedbackCollector
from src.models.learning import FeedbackEvent


class TestNormalization:
    """Tests for feedback signal normalization."""

    def setup_method(self):
        """Create a FeedbackCollector without DynamoDB dependency."""
        self.collector = FeedbackCollector(table_name="test-table")

    def test_explicit_rating_1_maps_to_negative_one(self):
        """Rating 1 should normalize to -1.0."""
        result = self.collector.normalize_signal("explicit_rating", 1)
        assert result == pytest.approx(-1.0)

    def test_explicit_rating_3_maps_to_zero(self):
        """Rating 3 should normalize to 0.0."""
        result = self.collector.normalize_signal("explicit_rating", 3)
        assert result == pytest.approx(0.0)

    def test_explicit_rating_5_maps_to_positive_one(self):
        """Rating 5 should normalize to 1.0."""
        result = self.collector.normalize_signal("explicit_rating", 5)
        assert result == pytest.approx(1.0)

    def test_explicit_rating_2_maps_to_negative_half(self):
        """Rating 2 should normalize to -0.5."""
        result = self.collector.normalize_signal("explicit_rating", 2)
        assert result == pytest.approx(-0.5)

    def test_explicit_rating_4_maps_to_positive_half(self):
        """Rating 4 should normalize to 0.5."""
        result = self.collector.normalize_signal("explicit_rating", 4)
        assert result == pytest.approx(0.5)

    def test_override_always_negative_one(self):
        """Override signal should always be -1.0."""
        result = self.collector.normalize_signal("override")
        assert result == -1.0

    def test_acceptance_always_positive_one(self):
        """Acceptance signal should always be +1.0."""
        result = self.collector.normalize_signal("acceptance")
        assert result == 1.0

    def test_adjustment_passes_through(self):
        """Adjustment signal passes through as-is."""
        result = self.collector.normalize_signal("adjustment", 0.5)
        assert result == pytest.approx(0.5)

    def test_adjustment_negative_value(self):
        """Adjustment with negative value passes through."""
        result = self.collector.normalize_signal("adjustment", -0.7)
        assert result == pytest.approx(-0.7)

    def test_adjustment_zero(self):
        """Adjustment with zero value."""
        result = self.collector.normalize_signal("adjustment", 0.0)
        assert result == pytest.approx(0.0)

    def test_invalid_feedback_type_raises(self):
        """Invalid feedback type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid feedback_type"):
            self.collector.normalize_signal("invalid_type", 3)

    def test_explicit_rating_below_1_raises(self):
        """Rating below 1 should raise ValueError."""
        with pytest.raises(ValueError, match="explicit_rating must be between 1 and 5"):
            self.collector.normalize_signal("explicit_rating", 0)

    def test_explicit_rating_above_5_raises(self):
        """Rating above 5 should raise ValueError."""
        with pytest.raises(ValueError, match="explicit_rating must be between 1 and 5"):
            self.collector.normalize_signal("explicit_rating", 6)

    def test_adjustment_below_negative_one_raises(self):
        """Adjustment below -1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="adjustment signal must be between"):
            self.collector.normalize_signal("adjustment", -1.5)

    def test_adjustment_above_positive_one_raises(self):
        """Adjustment above 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="adjustment signal must be between"):
            self.collector.normalize_signal("adjustment", 1.5)


class TestCollectFeedback:
    """Tests for collect_feedback creating FeedbackEvent objects."""

    def setup_method(self):
        """Create a FeedbackCollector that doesn't store to DynamoDB."""
        self.collector = FeedbackCollector(table_name="test-table")

    def test_collect_explicit_rating_creates_event(self):
        """Collecting explicit rating creates a FeedbackEvent with normalized signal."""
        event = self.collector.collect_feedback(
            member="rajesh",
            feedback_type="explicit_rating",
            context={"device": "living_room_ac", "action": "set_temperature"},
            raw_value=4,
            store=False,
        )

        assert isinstance(event, FeedbackEvent)
        assert event.member == "rajesh"
        assert event.feedback_type == "explicit_rating"
        assert event.signal_value == pytest.approx(0.5)
        assert event.context == {"device": "living_room_ac", "action": "set_temperature"}
        assert event.event_id  # UUID should be set

    def test_collect_override_creates_event(self):
        """Collecting override creates event with signal -1.0."""
        event = self.collector.collect_feedback(
            member="priya",
            feedback_type="override",
            context={"device": "smart_geyser"},
            store=False,
        )

        assert event.member == "priya"
        assert event.feedback_type == "override"
        assert event.signal_value == -1.0

    def test_collect_acceptance_creates_event(self):
        """Collecting acceptance creates event with signal +1.0."""
        event = self.collector.collect_feedback(
            member="rajesh",
            feedback_type="acceptance",
            context={"action_plan_id": "plan-123"},
            store=False,
        )

        assert event.signal_value == 1.0
        assert event.feedback_type == "acceptance"

    def test_collect_adjustment_creates_event(self):
        """Collecting adjustment creates event with partial signal."""
        event = self.collector.collect_feedback(
            member="priya",
            feedback_type="adjustment",
            context={"device": "smart_lights", "adjusted_from": 80, "adjusted_to": 60},
            raw_value=-0.3,
            store=False,
        )

        assert event.signal_value == pytest.approx(-0.3)
        assert event.feedback_type == "adjustment"

    def test_collect_feedback_sets_timestamp(self):
        """FeedbackEvent should have a timestamp set to approximately now."""
        before = datetime.now(timezone.utc)
        event = self.collector.collect_feedback(
            member="rajesh",
            feedback_type="acceptance",
            context={},
            store=False,
        )
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_collect_feedback_generates_unique_ids(self):
        """Each FeedbackEvent should have a unique event_id."""
        event1 = self.collector.collect_feedback(
            member="rajesh", feedback_type="acceptance", context={}, store=False
        )
        event2 = self.collector.collect_feedback(
            member="rajesh", feedback_type="acceptance", context={}, store=False
        )

        assert event1.event_id != event2.event_id


class TestGetRecentFeedback:
    """Tests for get_recent_feedback retrieval."""

    def setup_method(self):
        """Create a FeedbackCollector with mocked DynamoDB table."""
        self.mock_table = MagicMock()
        self.mock_dynamodb = MagicMock()
        self.mock_dynamodb.Table.return_value = self.mock_table
        self.collector = FeedbackCollector(
            table_name="test-table", dynamodb_resource=self.mock_dynamodb
        )

    def test_get_recent_feedback_returns_events(self):
        """get_recent_feedback should return a list of FeedbackEvent objects."""
        self.mock_table.query.return_value = {
            "Items": [
                {
                    "event_id": "evt-1",
                    "member": "rajesh",
                    "feedback_type": "acceptance",
                    "context": {"device": "ac"},
                    "signal_value": Decimal("1.0"),
                    "timestamp": "2024-06-15T10:00:00+00:00",
                },
                {
                    "event_id": "evt-2",
                    "member": "rajesh",
                    "feedback_type": "override",
                    "context": {"device": "lights"},
                    "signal_value": Decimal("-1.0"),
                    "timestamp": "2024-06-15T09:00:00+00:00",
                },
            ]
        }

        events = self.collector.get_recent_feedback("rajesh")

        assert len(events) == 2
        assert events[0].event_id == "evt-1"
        assert events[0].signal_value == 1.0
        assert events[1].event_id == "evt-2"
        assert events[1].signal_value == -1.0

    def test_get_recent_feedback_empty_results(self):
        """get_recent_feedback returns empty list when no events exist."""
        self.mock_table.query.return_value = {"Items": []}

        events = self.collector.get_recent_feedback("ananya")

        assert events == []

    def test_get_recent_feedback_respects_limit(self):
        """get_recent_feedback passes the limit to DynamoDB query."""
        self.mock_table.query.return_value = {"Items": []}

        self.collector.get_recent_feedback("rajesh", limit=10)

        call_kwargs = self.mock_table.query.call_args[1]
        assert call_kwargs["Limit"] == 10
