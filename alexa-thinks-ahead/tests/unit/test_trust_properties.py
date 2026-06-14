"""Property-based tests for trust score operations.

Uses hypothesis to verify universal properties that must hold
regardless of input values.

**Validates: Requirements 5.1, 5.3, 5.4, 5.7**
"""

import pytest
from hypothesis import given, settings
from hypothesis.strategies import floats, lists, booleans

from src.autonomy.trust import TrustScoreManager


class TestTrustScoreProperties:
    """Property tests for trust score operations."""

    @given(
        initial_score=floats(min_value=0.0, max_value=100.0, allow_nan=False),
        operations=lists(booleans(), min_size=1, max_size=20),
    )
    @settings(max_examples=200)
    def test_score_always_in_bounds_after_any_sequence(self, initial_score, operations):
        """Property 1: After any sequence of acceptances/overrides, score is in [0, 100].

        **Validates: Requirements 1.2**
        """
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = initial_score

        for is_acceptance in operations:
            if is_acceptance:
                manager.record_acceptance("rajesh", "climate")
            else:
                manager.record_override("rajesh", "climate")

        final = manager.get_score("rajesh", "climate")
        assert 0 <= final <= 100

    @given(score=floats(min_value=0.0, max_value=100.0, allow_nan=False))
    @settings(max_examples=200)
    def test_override_never_increases_score(self, score):
        """Property 3: Override always decreases or maintains score (at 0).

        **Validates: Requirements 5.4**
        """
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = score
        new_score = manager.record_override("rajesh", "climate")
        assert new_score <= score

    @given(score=floats(min_value=0.0, max_value=100.0, allow_nan=False))
    @settings(max_examples=200)
    def test_acceptance_never_decreases_score(self, score):
        """Property 4: Acceptance always increases or maintains score (at 100).

        **Validates: Requirements 5.3**
        """
        manager = TrustScoreManager()
        manager._scores[("rajesh", "climate")] = score
        new_score = manager.record_acceptance("rajesh", "climate")
        assert new_score >= score
