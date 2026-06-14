"""Daikin AC adapter for climate control.

Requirement 1.1: Unified interface for climate device.
Requirement 1.2: Translate commands to device-specific protocol.
Requirement 1.3: Mark device as stale when unreachable.
Requirement 1.5: Normalize to DeviceState dataclass.
"""

from datetime import datetime, timezone
from typing import Callable, Dict, List
from uuid import uuid4

from src.devices.base import DeviceAdapter
from src.models.device import (
    CommandResult,
    DeviceCategory,
    DeviceCommand,
    DeviceState,
)


class DaikinACAdapter(DeviceAdapter):
    """Adapter for Daikin Living Room AC.

    Controls temperature (16-30), mode (cool/heat/auto/dry),
    fan speed (low/medium/high/auto), and power state.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "temperature": 24,
            "mode": "cool",
            "fan_speed": "auto",
            "power": True,
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current AC state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.CLIMATE,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a climate control command."""
        command_id = command.command_id
        action = command.action
        params = command.parameters

        if not self._reachable:
            return CommandResult(
                command_id=command_id,
                success=False,
                device_id=self.device_id,
                error_message="Device unreachable",
            )

        success = True
        error_message = None

        if action == "set_temperature":
            temp = params.get("temperature", params.get("target_temp"))
            if temp is not None and 16 <= temp <= 30:
                self._state["temperature"] = temp
            else:
                success = False
                error_message = "Temperature must be between 16 and 30"

        elif action == "set_mode":
            mode = params.get("mode")
            if mode in ("cool", "heat", "auto", "dry"):
                self._state["mode"] = mode
            else:
                success = False
                error_message = "Mode must be cool, heat, auto, or dry"

        elif action == "set_fan_speed":
            speed = params.get("fan_speed", params.get("speed"))
            if speed in ("low", "medium", "high", "auto"):
                self._state["fan_speed"] = speed
            else:
                success = False
                error_message = "Fan speed must be low, medium, high, or auto"

        elif action == "power_on":
            self._state["power"] = True

        elif action == "power_off":
            self._state["power"] = False

        else:
            success = False
            error_message = f"Unknown command: {action}"

        if success:
            self._last_updated = datetime.now(timezone.utc)

        return CommandResult(
            command_id=command_id,
            success=success,
            device_id=self.device_id,
            new_state=self.get_state() if success else None,
            error_message=error_message,
        )

    def subscribe_events(self, callback: Callable) -> str:
        """Register callback for AC events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return AC capabilities."""
        return ["set_temperature", "set_mode", "set_fan_speed", "power_on", "power_off"]
