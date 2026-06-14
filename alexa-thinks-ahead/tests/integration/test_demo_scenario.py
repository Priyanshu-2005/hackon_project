"""Integration test for the demo scenario: Power cut at 5:40pm.

Simulates the full demo flow:
  power cut event → context gathering → Bedrock reasoning → load shedding
  → announcements → power restore → recovery

Verifies:
  - Wi-Fi and study room prioritized
  - AC/geyser shed
  - Announcements sent
  - Graceful recovery on power restore

Uses mocked Bedrock with realistic response for demo rehearsal.

Requirements: 13.1, 13.2, 13.3, 13.4
"""

import json
from datetime import datetime, time, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.context.engine import ContextEngine
from src.devices.base import DeviceAdapter
from src.devices.registry import DEVICE_CONFIGS
from src.intelligence.engine import ProactiveEngine
from src.intelligence.event_handler import ContextualEventHandler
from src.models.context import FamilyActivity
from src.models.device import CommandResult, DeviceCategory, DeviceCommand, DeviceState


class DemoMockAdapter(DeviceAdapter):
    """Mock adapter with demo-realistic state for the power cut scenario."""

    def __init__(self, device_id: str, device_type: str, config: dict):
        super().__init__(device_id, device_type, config)
        self._properties = self._get_demo_properties(device_id)
        self._state = DeviceState(
            device_id=device_id,
            device_type=device_type,
            category=DeviceCategory(config.get("category", "climate")),
            status="online",
            properties=self._properties,
            last_updated=datetime(2024, 3, 14, 17, 40, tzinfo=timezone.utc),
            battery_level=80.0 if device_type == "inverter" else None,
        )
        self.commands_received = []

    def _get_demo_properties(self, device_id: str) -> dict:
        """Return realistic properties for the 5:40pm demo scenario."""
        props = {
            "living_room_ac": {"power": "on", "temperature": 24, "mode": "cool"},
            "smart_lights": {"power": "on", "brightness": 80, "scene": "default"},
            "security_camera": {"armed": True, "motion_detected": False},
            "smart_lock": {"locked": True, "auto_lock": True},
            "kitchen_hub": {"active_appliance": "none", "timer": None},
            "water_purifier": {"power": "on", "filter_life_pct": 75},
            "smart_geyser": {"power": "on", "temperature": 55},
            "inverter_ups": {
                "battery_level": 80,
                "mode": "standby",
                "load_watts": 200,
                "backup_time_minutes": 150,
            },
            "smart_tv": {"power": "off", "volume": 0},
            "echo_devices": {"status": "active", "last_announcement": None},
        }
        return props.get(device_id, {"power": "off"})

    def get_state(self) -> DeviceState:
        return self._state

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        self.commands_received.append(command)
        return CommandResult(
            command_id=command.command_id,
            success=True,
            device_id=self.device_id,
            new_state=self._state,
            execution_time_ms=30,
        )

    def subscribe_events(self, callback) -> str:
        return f"sub_{self.device_id}"

    def get_capabilities(self) -> list:
        return self.config.get("capabilities", [])


def create_demo_adapters() -> dict:
    """Create demo-configured mock adapters for all 10 devices."""
    adapters = {}
    for cfg in DEVICE_CONFIGS:
        adapters[cfg["device_id"]] = DemoMockAdapter(
            device_id=cfg["device_id"],
            device_type=cfg["device_type"],
            config=cfg,
        )
    return adapters


def create_power_cut_bedrock_response():
    """Create a factory for the mocked Bedrock response for the power cut scenario.

    The model should return a plan that:
    - Prioritizes Wi-Fi and study room (Arjun's tuition)
    - Sheds AC and geyser
    - Announces to family members
    """
    import io

    inner_json = json.dumps(
        {
            "actions": [
                {
                    "strategy": "energy_optimization",
                    "target_devices": ["inverter_ups"],
                    "confidence": 0.95,
                    "reasoning": "Power cut detected. Arjun is in online tuition. "
                    "Prioritizing Wi-Fi and study room power from inverter. "
                    "Shedding non-essential loads.",
                    "benefit": "Continuous internet for Arjun's tuition class",
                    "devices": ["inverter_ups"],
                },
                {
                    "strategy": "energy_optimization",
                    "target_devices": ["living_room_ac", "smart_geyser"],
                    "confidence": 0.93,
                    "reasoning": "Shedding AC and geyser to conserve inverter battery. "
                    "These can be restored when grid power returns.",
                    "benefit": "Extended inverter backup time from 90min to 150min",
                    "devices": ["living_room_ac", "smart_geyser"],
                },
                {
                    "strategy": "comfort_lighting",
                    "target_devices": ["smart_lights"],
                    "confidence": 0.88,
                    "reasoning": "Switching study room to battery-powered warm mode at 70% "
                    "brightness for Arjun's comfort during tuition.",
                    "benefit": "Adequate lighting for study without grid power",
                    "devices": ["smart_lights"],
                },
                {
                    "strategy": "storm_preparation",
                    "target_devices": ["echo_devices"],
                    "confidence": 0.92,
                    "reasoning": "Announcing power cut status and actions to family. "
                    "Reassuring that Wi-Fi and study room are prioritized.",
                    "benefit": "Family awareness and reduced anxiety",
                    "devices": ["echo_devices"],
                },
            ],
            "reasoning_chain": (
                "SENSE: Power grid failure detected via inverter switchover. "
                "Arjun's online tuition is active (calendar: 5:00-6:30pm). "
                "Inverter battery at 80%. "
                "THINK: Priority is internet continuity for tuition. "
                "Shed AC (non-essential comfort) and geyser (not needed now). "
                "Allocate inverter to Wi-Fi router and study room outlets. "
                "Estimate 2.5 hours backup at reduced load — sufficient for tuition end. "
                "ACT: Execute load shedding, adjust lighting, announce to family. "
                "EXPLAIN: Notify household about actions and estimated backup time."
            ),
            "confidence": 0.93,
            "explanation": (
                "Power cut detected. Inverter is keeping Wi-Fi and study room "
                "running for Arjun's tuition. AC and geyser paused to conserve "
                "battery. Estimated backup: 2.5 hours."
            ),
        }
    )
    body_content = json.dumps({"content": [{"text": inner_json}]}).encode()

    def factory(*args, **kwargs):
        return {"body": io.BytesIO(body_content)}

    return factory


def create_power_restore_bedrock_response():
    """Create a factory for the mocked Bedrock response for power restoration."""
    import io

    inner_json = json.dumps(
        {
            "actions": [
                {
                    "strategy": "energy_optimization",
                    "target_devices": ["living_room_ac", "smart_geyser", "inverter_ups"],
                    "confidence": 0.95,
                    "reasoning": "Grid power restored. Resuming normal operation. "
                    "Re-enabling AC and geyser. Switching inverter to recharge mode.",
                    "benefit": "Full comfort restored, inverter recharging",
                    "devices": ["living_room_ac", "smart_geyser", "inverter_ups"],
                },
                {
                    "strategy": "comfort_lighting",
                    "target_devices": ["echo_devices"],
                    "confidence": 0.90,
                    "reasoning": "Announcing power restoration to family.",
                    "benefit": "Family reassurance",
                    "devices": ["echo_devices"],
                },
            ],
            "reasoning_chain": (
                "Grid power restored. Gracefully transitioning all devices back "
                "to grid. Re-enabling AC and geyser. Inverter switching to recharge mode."
            ),
            "confidence": 0.92,
            "explanation": (
                "Power is back. Resuming normal operation and recharging the inverter."
            ),
        }
    )
    body_content = json.dumps({"content": [{"text": inner_json}]}).encode()

    def factory(*args, **kwargs):
        return {"body": io.BytesIO(body_content)}

    return factory


class TestDemoPowerCutScenario:
    """Integration test for the key demo scenario: power cut at 5:40pm."""

    def setup_method(self):
        """Set up demo environment."""
        self.adapters = create_demo_adapters()
        self.mock_bedrock_client = MagicMock()

    def test_power_cut_triggers_load_shedding(self):
        """Power cut event triggers intelligent load shedding."""
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_cut_bedrock_response()
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)

        from src.reasoning.client import BedrockReasoningClient

        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        # Simulate power cut event at 5:40pm
        power_cut_event = {
            "event_type": "power_cut",
            "event_id": "evt_powercut_001",
            "source": "inverter_ups",
            "details": {
                "grid_status": "offline",
                "inverter_battery_pct": 80,
                "timestamp": "2024-03-14T17:40:00Z",
            },
        }

        result = handler.handle_event(power_cut_event)

        # Verify it's treated as critical
        assert result["is_critical"] is True

        # Verify actions were planned
        actions = result["actions_executed"]
        assert len(actions) >= 3  # load shed, lighting, announcement

        # Verify reasoning chain mentions priority devices
        assert "Wi-Fi" in result["explanation"] or "tuition" in result["explanation"]

    def test_wifi_and_study_room_prioritized(self):
        """The plan should prioritize Wi-Fi and study room for Arjun's tuition."""
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_cut_bedrock_response()
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)

        from src.reasoning.client import BedrockReasoningClient

        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        event = {"event_type": "power_cut", "source": "inverter_ups"}
        result = handler.handle_event(event)

        # The reasoning chain from mock should mention Wi-Fi and study room
        reasoning = result["explanation"]
        assert "Wi-Fi" in reasoning or "study" in reasoning or "tuition" in reasoning

    def test_ac_and_geyser_are_shed(self):
        """AC and geyser should be in the shedding action targets."""
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_cut_bedrock_response()
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)

        from src.reasoning.client import BedrockReasoningClient

        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        event = {"event_type": "power_cut", "source": "inverter_ups"}
        result = handler.handle_event(event)

        # Check that AC and geyser appear in shed actions
        all_targets = []
        for action in result["actions_executed"]:
            all_targets.extend(action.get("target_devices", []))

        assert "living_room_ac" in all_targets
        assert "smart_geyser" in all_targets

    def test_announcements_sent_to_echo(self):
        """Echo devices should be targeted for announcements."""
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_cut_bedrock_response()
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)

        from src.reasoning.client import BedrockReasoningClient

        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        event = {"event_type": "power_cut", "source": "inverter_ups"}
        result = handler.handle_event(event)

        # Echo should be in at least one action's targets
        all_targets = []
        for action in result["actions_executed"]:
            all_targets.extend(action.get("target_devices", []))

        assert "echo_devices" in all_targets

    def test_power_restore_triggers_graceful_recovery(self):
        """Power restoration should re-enable shed devices gracefully."""
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_restore_bedrock_response()
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)

        from src.reasoning.client import BedrockReasoningClient

        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        # Simulate power restore event
        restore_event = {
            "event_type": "power_restored",
            "event_id": "evt_restore_001",
            "source": "inverter_ups",
            "details": {"grid_status": "online"},
        }

        result = handler.handle_event(restore_event)

        # Verify recovery actions include AC and geyser re-enablement
        all_targets = []
        for action in result["actions_executed"]:
            all_targets.extend(action.get("target_devices", []))

        assert "living_room_ac" in all_targets
        assert "smart_geyser" in all_targets
        assert "inverter_ups" in all_targets

    def test_full_power_cut_and_restore_cycle(self):
        """Test the complete cycle: power cut → handling → restore → recovery."""
        # Phase 1: Power cut
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_cut_bedrock_response()
        )

        context_engine = ContextEngine(adapters=self.adapters, table=None)

        from src.reasoning.client import BedrockReasoningClient

        reasoning_client = BedrockReasoningClient(client=self.mock_bedrock_client)
        proactive_engine = ProactiveEngine(
            context_engine=context_engine,
            reasoning_client=reasoning_client,
        )
        handler = ContextualEventHandler(
            context_engine=context_engine,
            proactive_engine=proactive_engine,
            device_adapters=self.adapters,
        )

        cut_event = {"event_type": "power_cut", "source": "inverter_ups"}
        cut_result = handler.handle_event(cut_event)
        assert cut_result["is_critical"] is True
        assert len(cut_result["actions_executed"]) >= 3

        # Phase 2: Power restore
        self.mock_bedrock_client.invoke_model.side_effect = (
            create_power_restore_bedrock_response()
        )

        restore_event = {"event_type": "power_restored", "source": "inverter_ups"}
        restore_result = handler.handle_event(restore_event)

        assert len(restore_result["actions_executed"]) >= 1
        # Recovery explanation should mention restoration
        explanation = restore_result["explanation"]
        assert "restored" in explanation.lower() or "back" in explanation.lower()

    def test_inverter_battery_in_context(self):
        """Verify the context engine captures inverter battery level."""
        context_engine = ContextEngine(adapters=self.adapters, table=None)
        snapshot = context_engine.build_snapshot(force_refresh=True)

        # Inverter should report battery level
        inverter_state = snapshot.device_states.get("inverter_ups")
        assert inverter_state is not None
        assert inverter_state.properties["battery_level"] == 80
