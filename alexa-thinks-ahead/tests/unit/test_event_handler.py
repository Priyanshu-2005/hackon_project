"""Unit tests for ContextualEventHandler.

Tests the event-driven contextual handler covering:
- handle_event returns expected structure
- Critical events force context refresh
- Non-critical events don't force refresh
- Actions from plan are included in result
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.intelligence.event_handler import (
    CRITICAL_EVENTS,
    ContextualEventHandler,
)
from src.models.autonomy import ActionType
from src.models.intelligence import ActionPlan, Prediction


@pytest.fixture
def mock_context_engine():
    """Mock ContextEngine with build_snapshot returning a minimal snapshot."""
    engine = MagicMock()
    snapshot = MagicMock()
    snapshot.snapshot_id = "snap-001"
    engine.build_snapshot.return_value = snapshot
    return engine


@pytest.fixture
def mock_proactive_engine():
    """Mock ProactiveEngine with handle_event returning a minimal plan."""
    engine = MagicMock()
    plan = ActionPlan(
        plan_id="plan-001",
        event_id="evt-001",
        predictions=[
            Prediction(
                prediction_id="pred-001",
                strategy="energy_optimization",
                target_devices=["inverter_ups", "living_room_ac"],
                actions=[],
                confidence=0.9,
                action_type=ActionType.AUTO_EXECUTE,
                reasoning="Load shedding needed to preserve battery",
                estimated_benefit="Extended inverter life by 2 hours",
            ),
            Prediction(
                prediction_id="pred-002",
                strategy="comfort_lighting",
                target_devices=["smart_lights"],
                actions=[],
                confidence=0.7,
                action_type=ActionType.RECOMMEND,
                reasoning="Low light detected in study room",
                estimated_benefit="Better visibility for tuition",
            ),
        ],
        reasoning_chain="Power cut detected. Prioritizing Wi-Fi and study room.",
        context_snapshot_id="snap-001",
        created_at=datetime.now(timezone.utc),
    )
    engine.handle_event.return_value = plan
    return engine


@pytest.fixture
def handler(mock_context_engine, mock_proactive_engine):
    """Instantiate ContextualEventHandler with mocked dependencies."""
    return ContextualEventHandler(
        context_engine=mock_context_engine,
        proactive_engine=mock_proactive_engine,
        device_adapters={},
    )


class TestHandleEventStructure:
    """Test that handle_event returns the expected result structure."""

    def test_result_contains_all_required_keys(self, handler):
        """Verify the result dict has all expected keys."""
        event = {"event_type": "power_cut", "source": "smart_meter"}
        result = handler.handle_event(event)

        assert "event_type" in result
        assert "is_critical" in result
        assert "plan" in result
        assert "actions_executed" in result
        assert "explanation" in result
        assert "timestamp" in result

    def test_result_event_type_matches_input(self, handler):
        """Verify event_type in result matches the input event."""
        event = {"event_type": "temperature_change"}
        result = handler.handle_event(event)

        assert result["event_type"] == "temperature_change"

    def test_result_timestamp_is_valid_iso(self, handler):
        """Verify timestamp in result is a valid ISO format string."""
        event = {"event_type": "motion_detected"}
        result = handler.handle_event(event)

        # Should not raise
        parsed = datetime.fromisoformat(result["timestamp"])
        assert parsed.tzinfo is not None

    def test_result_plan_is_action_plan(self, handler):
        """Verify the plan in result is an ActionPlan instance."""
        event = {"event_type": "door_opened"}
        result = handler.handle_event(event)

        assert isinstance(result["plan"], ActionPlan)

    def test_result_explanation_is_reasoning_chain(self, handler):
        """Verify explanation comes from the plan's reasoning chain."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        assert result["explanation"] == "Power cut detected. Prioritizing Wi-Fi and study room."

    def test_unknown_event_type_defaults_gracefully(self, handler):
        """Verify events without event_type default to 'unknown'."""
        event = {}
        result = handler.handle_event(event)

        assert result["event_type"] == "unknown"
        assert result["is_critical"] is False


class TestCriticalEventHandling:
    """Test that critical events force context refresh."""

    @pytest.mark.parametrize("event_type", list(CRITICAL_EVENTS))
    def test_critical_event_forces_refresh(
        self, mock_context_engine, mock_proactive_engine, event_type
    ):
        """Critical events should call build_snapshot with force_refresh=True."""
        handler = ContextualEventHandler(
            context_engine=mock_context_engine,
            proactive_engine=mock_proactive_engine,
        )
        event = {"event_type": event_type}
        handler.handle_event(event)

        mock_context_engine.build_snapshot.assert_called_once_with(force_refresh=True)

    @pytest.mark.parametrize("event_type", list(CRITICAL_EVENTS))
    def test_critical_event_is_flagged(self, handler, event_type):
        """Critical events should be flagged in the result."""
        event = {"event_type": event_type}
        result = handler.handle_event(event)

        assert result["is_critical"] is True


class TestNonCriticalEventHandling:
    """Test that non-critical events don't force context refresh."""

    @pytest.mark.parametrize(
        "event_type",
        ["temperature_change", "motion_detected", "door_opened", "schedule_event", "unknown"],
    )
    def test_non_critical_event_no_force_refresh(
        self, mock_context_engine, mock_proactive_engine, event_type
    ):
        """Non-critical events should call build_snapshot with force_refresh=False."""
        handler = ContextualEventHandler(
            context_engine=mock_context_engine,
            proactive_engine=mock_proactive_engine,
        )
        event = {"event_type": event_type}
        handler.handle_event(event)

        mock_context_engine.build_snapshot.assert_called_once_with(force_refresh=False)

    @pytest.mark.parametrize(
        "event_type",
        ["temperature_change", "motion_detected", "routine_trigger"],
    )
    def test_non_critical_event_is_not_flagged(self, handler, event_type):
        """Non-critical events should not be flagged as critical."""
        event = {"event_type": event_type}
        result = handler.handle_event(event)

        assert result["is_critical"] is False


class TestActionsFromPlan:
    """Test that actions from the plan are correctly extracted into the result."""

    def test_all_predictions_become_actions(self, handler):
        """All predictions from the plan should appear in actions_executed."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        assert len(result["actions_executed"]) == 2

    def test_action_contains_strategy(self, handler):
        """Each action should include the strategy from the prediction."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        strategies = [a["strategy"] for a in result["actions_executed"]]
        assert "energy_optimization" in strategies
        assert "comfort_lighting" in strategies

    def test_action_contains_target_devices(self, handler):
        """Each action should include the target devices."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        first_action = result["actions_executed"][0]
        assert "target_devices" in first_action
        assert isinstance(first_action["target_devices"], list)

    def test_action_contains_action_type(self, handler):
        """Each action should include the action type as a string value."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        action_types = [a["action_type"] for a in result["actions_executed"]]
        assert ActionType.AUTO_EXECUTE.value in action_types
        assert ActionType.RECOMMEND.value in action_types

    def test_action_contains_confidence(self, handler):
        """Each action should include the confidence score."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        confidences = [a["confidence"] for a in result["actions_executed"]]
        assert 0.9 in confidences
        assert 0.7 in confidences

    def test_action_contains_prediction_id(self, handler):
        """Each action should include the prediction_id for tracing."""
        event = {"event_type": "power_cut"}
        result = handler.handle_event(event)

        assert result["actions_executed"][0]["prediction_id"] == "pred-001"
        assert result["actions_executed"][1]["prediction_id"] == "pred-002"

    def test_empty_plan_returns_no_actions(
        self, mock_context_engine, mock_proactive_engine
    ):
        """An empty action plan should result in no actions executed."""
        empty_plan = ActionPlan(
            plan_id="plan-empty",
            event_id=None,
            predictions=[],
            reasoning_chain="No action needed.",
            context_snapshot_id="snap-001",
            created_at=datetime.now(timezone.utc),
        )
        mock_proactive_engine.handle_event.return_value = empty_plan

        handler = ContextualEventHandler(
            context_engine=mock_context_engine,
            proactive_engine=mock_proactive_engine,
        )
        event = {"event_type": "routine_trigger"}
        result = handler.handle_event(event)

        assert result["actions_executed"] == []
        assert result["explanation"] == "No action needed."


class TestIsCriticalEvent:
    """Test the is_critical_event classification method."""

    def test_all_known_critical_events(self, handler):
        """All events in CRITICAL_EVENTS set should be classified as critical."""
        for event_type in CRITICAL_EVENTS:
            assert handler.is_critical_event({"event_type": event_type}) is True

    def test_non_critical_events(self, handler):
        """Events not in the critical set should return False."""
        non_critical = ["motion", "temperature_change", "door_bell", "schedule"]
        for event_type in non_critical:
            assert handler.is_critical_event({"event_type": event_type}) is False

    def test_missing_event_type(self, handler):
        """Events without event_type key should not be critical."""
        assert handler.is_critical_event({}) is False

    def test_empty_event_type(self, handler):
        """Events with empty event_type should not be critical."""
        assert handler.is_critical_event({"event_type": ""}) is False
