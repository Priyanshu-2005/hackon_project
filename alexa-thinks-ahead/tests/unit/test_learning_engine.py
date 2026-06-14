"""Unit tests for the LearningEngine orchestrator."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.learning.engine import LearningEngine
from src.models.learning import FeedbackEvent


def _make_feedback_event(
    member: str = "rajesh",
    feedback_type: str = "explicit_rating",
    signal_value: float = 0.5,
    timestamp: datetime = None,
) -> FeedbackEvent:
    """Helper to create a FeedbackEvent for testing."""
    return FeedbackEvent(
        event_id=str(uuid.uuid4()),
        member=member,
        feedback_type=feedback_type,
        context={"device": "living_room_ac", "action": "set_temperature"},
        signal_value=signal_value,
        timestamp=timestamp or datetime.now(timezone.utc),
    )


class TestProcessFeedback:
    """Tests for process_feedback creating and updating distributions."""

    def test_process_feedback_creates_new_distribution(self):
        """First feedback for a key creates a new preference distribution."""
        engine = LearningEngine()

        event = _make_feedback_event(member="rajesh", feedback_type="acceptance")
        engine.process_feedback(event)

        key = "rajesh#acceptance"
        assert key in engine._preferences
        dist = engine._preferences[key]
        assert dist.sample_count == 1
        assert dist.key == key

    def test_process_feedback_updates_existing_distribution(self):
        """Subsequent feedback for same key updates the distribution."""
        engine = LearningEngine()

        event1 = _make_feedback_event(signal_value=0.8)
        event2 = _make_feedback_event(signal_value=0.6)

        engine.process_feedback(event1)
        engine.process_feedback(event2)

        key = "rajesh#explicit_rating"
        dist = engine._preferences[key]
        assert dist.sample_count == 2

    def test_process_feedback_variance_decreases(self):
        """Variance should decrease with more observations (more certainty)."""
        engine = LearningEngine()

        event1 = _make_feedback_event(signal_value=0.5)
        engine.process_feedback(event1)
        variance_after_one = engine._preferences["rajesh#explicit_rating"].variance

        event2 = _make_feedback_event(signal_value=0.5)
        engine.process_feedback(event2)
        variance_after_two = engine._preferences["rajesh#explicit_rating"].variance

        assert variance_after_two < variance_after_one

    def test_process_feedback_updates_seasonal_model(self):
        """Feedback should also update the seasonal model."""
        engine = LearningEngine()

        event = _make_feedback_event(signal_value=0.7)
        engine.process_feedback(event)

        # The seasonal model should have recorded this observation
        key = "rajesh#explicit_rating"
        seasonal_dist = engine._seasonal.get_distribution(key)
        assert seasonal_dist is not None
        assert seasonal_dist.sample_count >= 1

    def test_process_feedback_case_insensitive_member(self):
        """Member names should be handled case-insensitively."""
        engine = LearningEngine()

        event = _make_feedback_event(member="Rajesh", signal_value=0.5)
        engine.process_feedback(event)

        assert "rajesh#explicit_rating" in engine._preferences

    def test_process_feedback_multiple_members(self):
        """Feedback from different members creates separate distributions."""
        engine = LearningEngine()

        event_rajesh = _make_feedback_event(member="rajesh", signal_value=0.5)
        event_priya = _make_feedback_event(member="priya", signal_value=-0.3)

        engine.process_feedback(event_rajesh)
        engine.process_feedback(event_priya)

        assert "rajesh#explicit_rating" in engine._preferences
        assert "priya#explicit_rating" in engine._preferences


class TestPredictPreference:
    """Tests for predict_preference returning blended values."""

    def test_predict_preference_returns_dict(self):
        """predict_preference should return a dict of key -> float."""
        engine = LearningEngine()

        event = _make_feedback_event(signal_value=0.8)
        engine.process_feedback(event)

        predictions = engine.predict_preference({})
        assert isinstance(predictions, dict)
        assert len(predictions) > 0

    def test_predict_preference_contains_known_keys(self):
        """Predictions should contain keys for all processed feedback."""
        engine = LearningEngine()

        engine.process_feedback(_make_feedback_event(member="rajesh", signal_value=0.5))
        engine.process_feedback(
            _make_feedback_event(member="priya", feedback_type="override", signal_value=-1.0)
        )

        predictions = engine.predict_preference({})
        assert "rajesh#explicit_rating" in predictions
        assert "priya#override" in predictions

    def test_predict_preference_returns_blended_value(self):
        """Blended predictions should combine overall and seasonal data."""
        engine = LearningEngine()

        # Add several observations so the mean moves toward a known value
        for _ in range(10):
            engine.process_feedback(_make_feedback_event(signal_value=0.8))

        predictions = engine.predict_preference({})
        # The prediction should be influenced by the 0.8 signal
        key = "rajesh#explicit_rating"
        assert key in predictions
        # After many 0.8 observations, the prediction should be close to 0.8
        assert predictions[key] > 0.5

    def test_predict_preference_empty_when_no_data(self):
        """predict_preference returns empty dict when no feedback processed."""
        engine = LearningEngine()
        predictions = engine.predict_preference({})
        assert predictions == {}


class TestPersonalizationIndex:
    """Tests for personalization index tracking."""

    def test_initial_personalization_index_is_zero(self):
        """All members start with personalization index 0.0."""
        engine = LearningEngine()

        for member in ["rajesh", "priya", "arjun", "ananya", "dadaji", "dadiji"]:
            assert engine.get_personalization_index(member) == 0.0

    def test_personalization_index_increases_with_feedback(self):
        """Personalization index should increase as more feedback arrives."""
        engine = LearningEngine()

        # Add some feedback
        for i in range(10):
            event = _make_feedback_event(member="rajesh", signal_value=0.5)
            engine.process_feedback(event)

        index = engine.get_personalization_index("rajesh")
        assert index > 0.0

    def test_personalization_index_capped_at_one(self):
        """Personalization index should not exceed 1.0."""
        engine = LearningEngine()

        # Add way more than 100 samples
        for i in range(150):
            event = _make_feedback_event(member="rajesh", signal_value=0.5)
            engine.process_feedback(event)

        index = engine.get_personalization_index("rajesh")
        assert index == 1.0

    def test_personalization_index_scales_with_samples(self):
        """More feedback should yield proportionally higher index."""
        engine = LearningEngine()

        # 10 samples → should be 0.1
        for i in range(10):
            engine.process_feedback(_make_feedback_event(member="priya", signal_value=0.3))

        index_10 = engine.get_personalization_index("priya")

        # Add 20 more (30 total) → should be 0.3
        for i in range(20):
            engine.process_feedback(_make_feedback_event(member="priya", signal_value=0.3))

        index_30 = engine.get_personalization_index("priya")

        assert index_30 > index_10

    def test_personalization_index_case_insensitive(self):
        """Member lookup should be case-insensitive."""
        engine = LearningEngine()
        engine.process_feedback(_make_feedback_event(member="Rajesh", signal_value=0.5))

        assert engine.get_personalization_index("rajesh") > 0.0
        assert engine.get_personalization_index("Rajesh") > 0.0

    def test_personalization_index_unknown_member_returns_zero(self):
        """Unknown member names should return 0.0."""
        engine = LearningEngine()
        assert engine.get_personalization_index("unknown_person") == 0.0


class TestRollingWindowDecay:
    """Tests for 90-day rolling window observation decay."""

    def test_recent_observations_not_decayed(self):
        """Observations within 90 days should not be affected."""
        engine = LearningEngine()

        event = _make_feedback_event(signal_value=0.5)
        engine.process_feedback(event)

        key = "rajesh#explicit_rating"
        # Should have 1 valid observation
        assert len(engine._observation_timestamps[key]) == 1
        assert engine._preferences[key].sample_count == 1

    def test_old_observations_are_pruned(self):
        """Observations older than 90 days should be pruned from timestamps."""
        engine = LearningEngine()

        # Create an event with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(days=100)
        event = _make_feedback_event(signal_value=0.5, timestamp=old_time)
        engine.process_feedback(event)

        key = "rajesh#explicit_rating"
        # The old timestamp should be pruned during decay
        assert len(engine._observation_timestamps[key]) == 0


class TestGetPreference:
    """Tests for get_preference method."""

    def test_get_preference_returns_distribution(self):
        """get_preference returns the distribution for a known key."""
        engine = LearningEngine()
        engine.process_feedback(_make_feedback_event(signal_value=0.6))

        dist = engine.get_preference("rajesh#explicit_rating")
        assert dist is not None
        assert dist.key == "rajesh#explicit_rating"

    def test_get_preference_returns_none_for_unknown(self):
        """get_preference returns None for an unknown key."""
        engine = LearningEngine()
        assert engine.get_preference("unknown#key") is None


class TestGetSeasonalModel:
    """Tests for get_seasonal_model method."""

    def test_get_seasonal_model_returns_data_after_feedback(self):
        """Seasonal model should have data after processing feedback."""
        engine = LearningEngine()
        engine.process_feedback(_make_feedback_event(signal_value=0.7))

        from src.utils.time_utils import get_current_season

        current_season = get_current_season()
        model = engine.get_seasonal_model(current_season)
        assert len(model) > 0

    def test_get_seasonal_model_empty_for_unused_season(self):
        """Seasonal model should be empty for a season with no data."""
        engine = LearningEngine()
        engine.process_feedback(_make_feedback_event(signal_value=0.7))

        # Pick a season that is NOT current
        from src.utils.time_utils import get_current_season

        current = get_current_season()
        other_seasons = [s for s in ["summer", "monsoon", "autumn", "winter"] if s != current]
        other_season = other_seasons[0]

        model = engine.get_seasonal_model(other_season)
        assert len(model) == 0
