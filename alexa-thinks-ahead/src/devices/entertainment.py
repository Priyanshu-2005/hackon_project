"""Fire TV adapter for entertainment device control.

Requirement 1.1: Unified interface for entertainment device.
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


class FireTVAdapter(DeviceAdapter):
    """Adapter for Fire TV Smart TV.

    Controls power, volume (0-100), input source, and app launching.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "power": True,
            "volume": 30,
            "input_source": "HDMI1",
            "current_app": "home",
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current TV state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.ENTERTAINMENT,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a TV control command."""
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

        if action == "power_on":
            self._state["power"] = True

        elif action == "power_off":
            self._state["power"] = False

        elif action == "set_volume":
            volume = params.get("volume")
            if volume is not None and 0 <= volume <= 100:
                self._state["volume"] = volume
            else:
                success = False
                error_message = "Volume must be between 0 and 100"

        elif action == "set_input":
            input_source = params.get("input_source", params.get("input"))
            if input_source and isinstance(input_source, str):
                self._state["input_source"] = input_source
            else:
                success = False
                error_message = "Input source must be a non-empty string"

        elif action == "launch_app":
            app = params.get("app", params.get("app_name"))
            if app and isinstance(app, str):
                self._state["current_app"] = app
            else:
                success = False
                error_message = "App name must be a non-empty string"

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
        """Register callback for TV events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return TV capabilities."""
        return ["power_on", "power_off", "set_volume", "set_input", "launch_app"]
