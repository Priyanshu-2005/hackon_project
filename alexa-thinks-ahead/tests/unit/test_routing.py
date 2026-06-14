"""Unit tests for confidence-based action routing."""

import pytest

from src.intelligence.routing import route_action, route_action_plan
from src.models.autonomy import ActionType
from src.models.intelligence import Prediction


class TestRouteAction:
    """Tests for route_action() function."""

    def test_high_confidence_auto_executes(self):
        """Confidence >= 0.85 should return AUTO_EXECUTE."""
        assert route_action(0.85) == ActionType.AUTO_EXECUTE
        assert route_action(0.90) == ActionType.AUTO_EXECUTE
        assert route_action(1.0) == ActionType.AUTO_EXECUTE

    def test_medium_confidence_recommends(self):
        """Confidence >= 0.60 but < 0.85 should return RECOMMEND."""
        assert route_action(0.60) == ActionType.RECOMMEND
        assert route_action(0.70) == ActionType.RECOMMEND
        assert route_action(0.84) == ActionType.RECOMMEND

    def test_low_confidence_informs(self):
        """Confidence >= 0.40 but < 0.60 should return INFORM."""
        assert route_action(0.40) == ActionType.INFORM
        assert route_action(0.50) == ActionType.INFORM
        assert route_action(0.59) == ActionType.INFORM

    def test_very_low_confidence_discards(self):
        """Confidence < 0.40 should return None (discard)."""
        assert route_action(0.39) is None
        assert route_action(0.20) is None
        assert route_action(0.0) is None

    def test_exact_boundary_values(self):
        """Test exact boundary values between tiers."""
        assert route_action(0.85) == ActionType.AUTO_EXECUTE
        assert route_action(0.60) == ActionType.RECOMMEND
        assert route_action(0.40) == ActionType.INFORM
        # Just below boundaries
        assert route_action(0.8499) == ActionType.RECOMMEND
        assert route_action(0.5999) == ActionType.INFORM
        assert route_action(0.3999) is None


class TestRouteActionPlan:
    """Tests for route_action_plan() function."""

    def _make_prediction(self, confidence: float) -> Prediction:
        """Helper to create a Prediction with a given confidence."""
        return Prediction(
            prediction_id="test-pred",
            strategy="pre_cooling",
            target_devices=["living_room_ac"],
            actions=[],
            confidence=confidence,
            action_type=ActionType.INFORM,  # placeholder, will be overwritten
            reasoning="Test reasoning",
            estimated_benefit="Test benefit",
        )

    def test_routes_all_predictions_above_threshold(self):
        """Predictions above 0.40 should be routed and returned."""
        predictions = [
            self._make_prediction(0.90),
            self._make_prediction(0.70),
            self._make_prediction(0.50),
        ]
        routed = route_action_plan(predictions)
        assert len(routed) == 3
        assert routed[0].action_type == ActionType.AUTO_EXECUTE
        assert routed[1].action_type == ActionType.RECOMMEND
        assert routed[2].action_type == ActionType.INFORM

    def test_discards_predictions_below_threshold(self):
        """Predictions below 0.40 should be discarded."""
        predictions = [
            self._make_prediction(0.90),
            self._make_prediction(0.30),
            self._make_prediction(0.10),
        ]
        routed = route_action_plan(predictions)
        assert len(routed) == 1
        assert routed[0].action_type == ActionType.AUTO_EXECUTE

    def test_empty_predictions_list(self):
        """Empty input should return empty output."""
        assert route_action_plan([]) == []

    def test_all_discarded(self):
        """All predictions below threshold should result in empty list."""
        predictions = [
            self._make_prediction(0.10),
            self._make_prediction(0.20),
            self._make_prediction(0.39),
        ]
        routed = route_action_plan(predictions)
        assert len(routed) == 0
