"""Property-based tests for confidence-based action routing.

Validates: Requirements 4.2, 4.3, 4.4, 4.5
"""

from hypothesis import given, settings
from hypothesis.strategies import floats

from src.intelligence.routing import route_action
from src.models.autonomy import ActionType


class TestActionRoutingConsistency:
    """Property 7: Action Routing Consistency.

    For any confidence C:
    - C >= 0.85 → AUTO_EXECUTE
    - 0.60 <= C < 0.85 → RECOMMEND
    - 0.40 <= C < 0.60 → INFORM
    - C < 0.40 → None (discard)
    """

    @given(confidence=floats(min_value=0.85, max_value=1.0, allow_nan=False))
    @settings(max_examples=100)
    def test_high_confidence_always_auto_execute(self, confidence):
        """**Validates: Requirements 4.2**"""
        assert route_action(confidence) == ActionType.AUTO_EXECUTE

    @given(confidence=floats(min_value=0.60, max_value=0.8499, allow_nan=False))
    @settings(max_examples=100)
    def test_medium_confidence_always_recommend(self, confidence):
        """**Validates: Requirements 4.3**"""
        assert route_action(confidence) == ActionType.RECOMMEND

    @given(confidence=floats(min_value=0.40, max_value=0.5999, allow_nan=False))
    @settings(max_examples=100)
    def test_low_confidence_always_inform(self, confidence):
        """**Validates: Requirements 4.4**"""
        assert route_action(confidence) == ActionType.INFORM

    @given(confidence=floats(min_value=0.0, max_value=0.3999, allow_nan=False))
    @settings(max_examples=100)
    def test_very_low_confidence_always_discards(self, confidence):
        """**Validates: Requirements 4.5**"""
        assert route_action(confidence) is None
