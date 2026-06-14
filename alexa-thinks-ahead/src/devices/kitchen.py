"""Samsung Kitchen Hub adapter for kitchen appliance control.

Requirement 1.1: Unified interface for kitchen device.
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


class SamsungKitchenAdapter(DeviceAdapter):
    """Adapter for Samsung Kitchen Appliance Hub.

    Controls appliance status, timers, and start/stop operations.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "active_appliance": "none",
            "timer_minutes": 0,
            "status": "idle",
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current kitchen hub state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.KITCHEN,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a kitchen hub command."""
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

        if action == "get_status":
            # Returns current state, no mutation needed
            pass

        elif action == "set_timer":
            minutes = params.get("minutes", params.get("timer_minutes"))
            if minutes is not None and isinstance(minutes, (int, float)) and minutes >= 0:
                self._state["timer_minutes"] = int(minutes)
            else:
                success = False
                error_message = "Timer minutes must be a non-negative number"

        elif action == "start_appliance":
            appliance = params.get("appliance", params.get("active_appliance"))
            if appliance and isinstance(appliance, str):
                self._state["active_appliance"] = appliance
                self._state["status"] = "running"
            else:
                success = False
                error_message = "Appliance name must be a non-empty string"

        elif action == "stop_appliance":
            self._state["active_appliance"] = "none"
            self._state["status"] = "idle"
            self._state["timer_minutes"] = 0

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
        """Register callback for kitchen events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return kitchen hub capabilities."""
        return ["get_status", "set_timer", "start_appliance", "stop_appliance"]
