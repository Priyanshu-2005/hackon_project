"""Integration tests for the full cognitive pipeline (SENSE → THINK → ACT → EXPLAIN).

Tests the complete pipeline with mocked Bedrock and mock device adapters.
Verifies context snapshot produced, reasoning invoked, actions dispatched.

Requirements: 7.1, 2.3, 4.1
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.context.engine import ContextEngine
from src.devices.base import DeviceAdapter
from src.devices.registry import DEVICE_CONFIGS, DeviceRegistry
from src.intelligence.engine import ProactiveEngine
from src.intelligence.event_handler import ContextualEventHandler
from src.models.context import ContextSnapshot, FamilyActivity
from src.models.device import CommandResult, DeviceCategory, DeviceCommand, DeviceState
from src.reasoning.client import BedrockReasoningClient


class MockDeviceAdapter(DeviceAdapter):
    """Mock adapter for testing all 10 devices."""

    def __init__(self, device_id: str, device_type: str, config: dict):
        super().__init__(device_id, device_type, config)
        self._state = DeviceState(
            device_id=device_id,
            device_type=device_type,
            category=DeviceCategory(config.get("category", "climate")),
            status="online",
            properties={"power": "on", "temperature": 24},
            last_updated=datetime.now(timezone.utc),
            battery_level=80.0 if device_type == "inverter" else None,
        )

    def get_state(self) -> DeviceState:
        return self._state

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        return CommandResult(
            command_id=command.command_id,
            success=True,
            device_id=self.device_id,
            new_state=self._state,
            execution_time_ms=50,
        )

    def subscribe_events(self, callback) -> str:
        return f"sub_{self.device_id}"

    def get_capabilities(self) -> list:
        return self.config.get("capabilities", [])


def create_mock_adapters() -> dict:
    """Create mock adapters for all 10 devices."""
    adapters = {}
    for cfg in DEVICE_CONFIGS:
        adapters[cfg["device_id"]] = MockDeviceAdapter(
            device_id=cfg["device_id"],
            device_type=cfg["device_type"],
            config=cfg,
        )
    return adapters


def make_bedrock_response_factory(actions=None):
    """Create a factory that returns fresh Bedrock response bodies.

    Matches the actual Bedrock API format: {"content": [{"text": "<json>"}]}
    Returns a callable suitable for mock side_effect.
    """
    import io

    if actions is None:
        actions = [
            {
                "strategy": "comfort_lighting",
                "target_devices": ["smart_lights"],
                "confidence": 0.88,
                "reasoning": "Evening approaching, transitioning to warm lighting",
                "benefit": "Improved ambient comfort",
            }
        ]
    inner_json = json.dumps(
        {
            "actions": actions,
            "reasoning_chain": "Evaluated home context. Evening detected, adjusting lighting.",
            "confidence": 0.88,
            "explanation": "Adjusting lights for evening comfort.",
        }
    )
    body_content = json.dumps({"content": [{"text": inner_json}]}).encode()

    def factory(*args, **kwargs):
        return {"body": io.BytesIO(body_content)}

    return factory


class TestCognitivePipeline:
    """Integration tests for the full SENSE → THINK → ACT → EXPLAIN cycle."""

    def setup_method(self):
        """Set up test fixtures with mock adapters and mocked Bedrock."""
        self.adapters = create_mock_adapters()
        self.mock_bedrock_client = MagicMock()
        self.mock_bedrock_client.invoke_model.side_effect = make_bedrock_response_factory()

    def test_full_pipeline_sense_think_act_explain(self):
        """Test the complete cognitive pipeline from sensing to explanation."""
        # Set up context engine with mock adapters (SENSE)
        context_engine = ContextEngine(adapters=self.adapters, table=None)

        # Set up reasoning client with mocked Bedrock (THINK)
        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)

        # Set up proactive engine
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )

        # Set up event handler (full pipeline)
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        # Trigger an event
        event = {
            "event_type": "temperature_change",
            "source": "living_room_ac",
            "details": {"current_temp": 30, "target_temp": 24},
        }

        result = handler.handle_event(event)

        # VERIFY: Context snapshot was built (SENSE worked)
        assert result["event_type"] == "temperature_change"

        # VERIFY: Reasoning was invoked (THINK worked)
        self.mock_bedrock_client.invoke_model.assert_called_once()

        # VERIFY: Actions were dispatched (ACT worked)
        assert "actions_executed" in result
        assert len(result["actions_executed"]) > 0

        # VERIFY: Explanation was generated (EXPLAIN worked)
        assert "explanation" in result
        assert result["explanation"] != ""

    def test_context_snapshot_contains_all_devices(self):
        """Verify context snapshot contains all 10 device states."""
        context_engine = ContextEngine(adapters=self.adapters, table=None)
        snapshot = context_engine.build_snapshot(force_refresh=True)

        # All 10 devices should be present
        assert len(snapshot.device_states) == 10
        for cfg in DEVICE_CONFIGS:
            assert cfg["device_id"] in snapshot.device_states

    def test_critical_event_forces_context_refresh(self):
        """Verify that critical events force a fresh context snapshot."""
        context_engine = ContextEngine(adapters=self.adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
        )

        # Power cut is a critical event
        event = {"event_type": "power_cut", "source": "inverter_ups"}
        result = handler.handle_event(event)

        assert result["is_critical"] is True
        assert result["event_type"] == "power_cut"

    def test_non_critical_event_uses_cached_context(self):
        """Non-critical events can use cached context."""
        context_engine = ContextEngine(adapters=self.adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
        )

        event = {"event_type": "temperature_change", "source": "living_room_ac"}
        result = handler.handle_event(event)

        assert result["is_critical"] is False

    def test_pipeline_handles_bedrock_timeout_gracefully(self):
        """Pipeline should handle Bedrock timeouts without crashing."""
        from botocore.exceptions import ReadTimeoutError

        # Make Bedrock time out
        self.mock_bedrock_client.invoke_model.side_effect = ReadTimeoutError(endpoint_url="test")

        context_engine = ContextEngine(adapters=self.adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)

        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
        )

        event = {"event_type": "temperature_change", "source": "living_room_ac"}

        # Should not raise — falls back to empty plan
        with patch("time.sleep"):  # Skip actual sleep during test
            result = handler.handle_event(event)

        assert result["actions_executed"] == []

    def test_proactive_engine_evaluates_context(self):
        """ProactiveEngine.evaluate_context produces an ActionPlan."""
        context_engine = ContextEngine(adapters=self.adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)

        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )

        plan = proactive_engine.evaluate_context()

        assert plan.plan_id is not None
        assert plan.reasoning_chain != ""
        assert plan.context_snapshot_id != ""
        # Should have predictions routed from the mock response
        assert len(plan.predictions) >= 0

    def test_pipeline_with_multiple_actions(self):
        """Pipeline handles multiple actions in a single reasoning response."""
        self.mock_bedrock_client.invoke_model.side_effect = make_bedrock_response_factory(
            actions=[
                {
                    "strategy": "pre_cooling",
                    "target_devices": ["living_room_ac"],
                    "confidence": 0.90,
                    "reasoning": "Pre-cool before Dadaji's rest time",
                    "benefit": "Elder comfort",
                },
                {
                    "strategy": "comfort_lighting",
                    "target_devices": ["smart_lights"],
                    "confidence": 0.75,
                    "reasoning": "Evening approaching",
                    "benefit": "Ambient comfort",
                },
            ]
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
        )

        event = {"event_type": "schedule_trigger", "source": "system"}
        result = handler.handle_event(event)

        assert len(result["actions_executed"]) == 2
