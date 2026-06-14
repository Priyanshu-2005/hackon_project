"""Security device adapters: Ring Camera and Yale Lock.

Requirement 1.1: Unified interface for security devices.
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


class RingCameraAdapter(DeviceAdapter):
    """Adapter for Ring Security Camera.

    Controls armed state, motion detection, night vision, and recording.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "armed": True,
            "motion_detected": False,
            "night_vision": True,
            "recording": True,
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current camera state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.SECURITY,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a camera control command."""
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

        if action == "arm":
            self._state["armed"] = True
            self._state["recording"] = True

        elif action == "disarm":
            self._state["armed"] = False
            self._state["recording"] = False

        elif action == "get_feed":
            # Simulated: returns current state (feed is always available when armed)
            pass

        elif action == "motion_detection":
            enabled = params.get("enabled", True)
            self._state["motion_detected"] = enabled

        elif action == "night_vision":
            enabled = params.get("enabled", True)
            self._state["night_vision"] = enabled

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
        """Register callback for camera events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return camera capabilities."""
        return ["arm", "disarm", "get_feed", "motion_detection", "night_vision"]


class YaleLockAdapter(DeviceAdapter):
    """Adapter for Yale Smart Lock.

    Controls lock state, auto-lock, and reports battery level.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "locked": True,
            "auto_lock": True,
            "battery_level": 85,
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current lock state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.SECURITY,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
            battery_level=self._state["battery_level"],
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a lock control command."""
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

        if action == "lock":
            self._state["locked"] = True

        elif action == "unlock":
            self._state["locked"] = False

        elif action == "get_status":
            # Returns current state, no mutation needed
            pass

        elif action == "set_auto_lock":
            enabled = params.get("enabled", True)
            self._state["auto_lock"] = enabled

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
        """Register callback for lock events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return lock capabilities."""
        return ["lock", "unlock", "get_status", "set_auto_lock"]
