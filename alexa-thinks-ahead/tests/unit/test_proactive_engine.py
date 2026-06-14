"""Unit tests for the ProactiveEngine class."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.intelligence.engine import ProactiveEngine
from src.models.autonomy import ActionType
from src.models.context import ContextSnapshot
from src.models.intelligence import ActionPlan, ReasoningResponse


class TestProactiveEngine:
    """Tests for ProactiveEngine."""

    def _make_snapshot(self) -> ContextSnapshot:
        """Create a minimal valid ContextSnapshot for testing."""
        return ContextSnapshot(
            snapshot_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            device_states={},
            active_activities=[],
            detected_patterns=[],
            resource_levels={},
            environmental={},
            confidence=0.8,
        )

    def _make_reasoning_response(self, actions=None, confidence=0.7) -> ReasoningResponse:
        """Create a ReasoningResponse with given actions."""
        if actions is None:
            actions = [
                {
                    "strategy": "pre_cooling",
                    "confidence": 0.90,
                    "target_devices": ["living_room_ac"],
                    "reasoning": "Temperature will rise before Dadaji's rest",
                    "benefit": "Comfortable temperature ready",
                },
                {
                    "strategy": "geyser_preheat",
                    "confidence": 0.70,
                    "target_devices": ["smart_geyser"],
                    "reasoning": "Morning alarm in 45 minutes",
                    "benefit": "Hot water ready for bath",
                },
                {
                    "strategy": "comfort_lighting",
                    "confidence": 0.50,
                    "target_devices": ["smart_lights"],
                    "reasoning": "Sunset approaching",
                    "benefit": "Smooth lighting transition",
                },
            ]
        return ReasoningResponse(
            actions=actions,
            reasoning_chain="Analyzed context and generated plan",
            confidence=confidence,
            explanation="Actions recommended based on current context",
            latency_ms=150,
        )

    def _build_engine(self) -> tuple:
        """Build a ProactiveEngine with mocked dependencies."""
        mock_context = MagicMock()
        mock_reasoner = MagicMock()
        engine = ProactiveEngine(
            context_engine=mock_context,
            reasoning_client=mock_reasoner,
        )
        return engine, mock_context, mock_reasoner

    def test_evaluate_context_returns_action_plan(self):
        """evaluate_context should return an ActionPlan instance."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response()

        result = engine.evaluate_context()

        assert isinstance(result, ActionPlan)
        assert result.plan_id is not None
        assert result.event_id is None
        assert result.context_snapshot_id == snapshot.snapshot_id
        assert result.reasoning_chain == "Analyzed context and generated plan"

    def test_evaluate_context_uses_provided_snapshot(self):
        """When a snapshot is provided, context_engine.build_snapshot is not called."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response()

        result = engine.evaluate_context(snapshot=snapshot)

        mock_context.build_snapshot.assert_not_called()
        assert result.context_snapshot_id == snapshot.snapshot_id

    def test_predictions_sorted_by_confidence_descending(self):
        """Predictions should be sorted highest confidence first."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response()

        result = engine.evaluate_context()

        # All three predictions have confidence >= 0.40 so none are discarded
        assert len(result.predictions) == 3
        confidences = [p.confidence for p in result.predictions]
        assert confidences == sorted(confidences, reverse=True)
        assert confidences[0] == 0.90
        assert confidences[1] == 0.70
        assert confidences[2] == 0.50

    def test_handle_event_includes_event_id(self):
        """handle_event should set event_id from the provided event dict."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response(actions=[])

        event = {"event_id": "power-cut-001", "type": "power_cut"}
        result = engine.handle_event(event)

        assert isinstance(result, ActionPlan)
        assert result.event_id == "power-cut-001"

    def test_handle_event_generates_event_id_if_missing(self):
        """handle_event should generate a UUID event_id if not provided."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response(actions=[])

        event = {"type": "temperature_spike"}
        result = engine.handle_event(event)

        assert result.event_id is not None
        assert len(result.event_id) > 0

    def test_handle_event_force_refreshes_context(self):
        """handle_event should call build_snapshot with force_refresh=True."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response(actions=[])

        engine.handle_event({"event_id": "test", "type": "test"})

        mock_context.build_snapshot.assert_called_once_with(force_refresh=True)

    def test_low_confidence_predictions_are_discarded(self):
        """Predictions below 0.40 confidence should be filtered out."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot

        actions = [
            {"strategy": "pre_cooling", "confidence": 0.90, "target_devices": ["ac"]},
            {"strategy": "security_arm", "confidence": 0.30, "target_devices": ["lock"]},
            {"strategy": "energy_optimization", "confidence": 0.10, "target_devices": ["inverter"]},
        ]
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response(actions=actions)

        result = engine.evaluate_context()

        # Only the 0.90 prediction should survive routing (>= 0.40)
        assert len(result.predictions) == 1
        assert result.predictions[0].confidence == 0.90

    def test_action_types_set_by_routing(self):
        """Predictions should have correct action_type set by routing."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response()

        result = engine.evaluate_context()

        action_types = {p.confidence: p.action_type for p in result.predictions}
        assert action_types[0.90] == ActionType.AUTO_EXECUTE  # >= 0.85
        assert action_types[0.70] == ActionType.RECOMMEND  # >= 0.60
        assert action_types[0.50] == ActionType.INFORM  # >= 0.40

    def test_empty_response_produces_empty_plan(self):
        """An empty reasoning response should produce an ActionPlan with no predictions."""
        engine, mock_context, mock_reasoner = self._build_engine()
        snapshot = self._make_snapshot()
        mock_context.build_snapshot.return_value = snapshot
        mock_reasoner.invoke_reasoning.return_value = self._make_reasoning_response(actions=[])

        result = engine.evaluate_context()

        assert isinstance(result, ActionPlan)
        assert len(result.predictions) == 0
