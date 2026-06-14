"""Philips Hue adapter for smart lighting control.

Requirement 1.1: Unified interface for lighting device.
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


class PhilipsHueAdapter(DeviceAdapter):
    """Adapter for Philips Hue Smart Lights.

    Controls brightness (0-100), color (hex string), scene,
    zone, and power state.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "brightness": 80,
            "color": "#FFFFFF",
            "scene": "default",
            "power": True,
            "zone": "living_room",
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current lighting state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.LIGHTING,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a lighting control command."""
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

        if action == "set_brightness":
            brightness = params.get("brightness")
            if brightness is not None and 0 <= brightness <= 100:
                self._state["brightness"] = brightness
            else:
                success = False
                error_message = "Brightness must be between 0 and 100"

        elif action == "set_color":
            color = params.get("color")
            if color and isinstance(color, str):
                self._state["color"] = color
            else:
                success = False
                error_message = "Color must be a valid hex string"

        elif action == "set_scene":
            scene = params.get("scene")
            if scene and isinstance(scene, str):
                self._state["scene"] = scene
            else:
                success = False
                error_message = "Scene must be a non-empty string"

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
        """Register callback for lighting events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return lighting capabilities."""
        return ["set_brightness", "set_color", "set_scene", "power_on", "power_off"]
