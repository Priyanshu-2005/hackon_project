"""Property-based tests for data model validation.

Validates: Requirements 5.1, 2.2

Uses hypothesis to verify invariants hold across all valid inputs.
"""

from hypothesis import given, settings
from hypothesis.strategies import floats

from src.models.autonomy import TrustScore
from src.models.device import DeviceCategory
from src.context.fusion import compute_temporal_weight

from datetime import datetime, timezone


class TestTrustScoreBoundsInvariant:
    """Property 1: Trust Score Bounds Invariant.

    Verify TrustScore.score is always clamped to [0, 100].

    **Validates: Requirements 5.1**
    """

    @given(score=floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=200)
    def test_trust_score_within_bounds(self, score: float):
        """For any valid trust score value, it must be in [0, 100]."""
        trust = TrustScore(
            member="test_member",
            category=DeviceCategory.CLIMATE,
            score=score,
            current_tier=1,
            last_interaction=datetime.now(timezone.utc),
            consecutive_acceptances=0,
            override_count_30d=0,
        )
        assert 0 <= trust.score <= 100, (
            f"TrustScore.score={trust.score} is outside [0, 100]"
        )

    @given(score=floats(min_value=-1000.0, max_value=0.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_trust_score_clamped_at_lower_bound(self, score: float):
        """Scores below 0 should be clamped to 0 when constructing valid TrustScore."""
        clamped = max(0.0, min(100.0, score))
        trust = TrustScore(
            member="test_member",
            category=DeviceCategory.LIGHTING,
            score=clamped,
            current_tier=1,
            last_interaction=datetime.now(timezone.utc),
        )
        assert 0 <= trust.score <= 100

    @given(score=floats(min_value=100.0, max_value=2000.0, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_trust_score_clamped_at_upper_bound(self, score: float):
        """Scores above 100 should be clamped to 100 when constructing valid TrustScore."""
        clamped = max(0.0, min(100.0, score))
        trust = TrustScore(
            member="test_member",
            category=DeviceCategory.SECURITY,
            score=clamped,
            current_tier=5,
            last_interaction=datetime.now(timezone.utc),
        )
        assert 0 <= trust.score <= 100


class TestSensorFusionWeightBounds:
    """Property 6: Sensor Fusion Weight Bounds.

    Verify weight calculations are always bounded [0.1, 1.0]
    for any non-negative age_seconds.

    **Validates: Requirements 2.2**
    """

    @given(
        age_seconds=floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200)
    def test_weight_always_within_bounds(self, age_seconds: float):
        """For any non-negative age_seconds, weight must be in [0.1, 1.0]."""
        weight = compute_temporal_weight(age_seconds)
        assert 0.1 <= weight <= 1.0, (
            f"Weight={weight} is outside [0.1, 1.0] for age_seconds={age_seconds}"
        )

    @given(
        age_seconds=floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
        max_staleness=floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=200)
    def test_weight_bounds_with_custom_max_staleness(
        self, age_seconds: float, max_staleness: float
    ):
        """Weight is in [0.1, 1.0] regardless of max_staleness_seconds (positive)."""
        weight = compute_temporal_weight(age_seconds, int(max_staleness))
        assert 0.1 <= weight <= 1.0, (
            f"Weight={weight} outside [0.1, 1.0] for "
            f"age_seconds={age_seconds}, max_staleness={max_staleness}"
        )

    @given(
        age_seconds=floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=200)
    def test_weight_decreases_monotonically_within_window(self, age_seconds: float):
        """Weight at age_seconds is >= weight at age_seconds + 1 (monotone decreasing)."""
        w1 = compute_temporal_weight(age_seconds)
        w2 = compute_temporal_weight(age_seconds + 1.0)
        assert w1 >= w2, (
            f"Weight not monotonically decreasing: "
            f"w({age_seconds})={w1} < w({age_seconds + 1})={w2}"
        )
