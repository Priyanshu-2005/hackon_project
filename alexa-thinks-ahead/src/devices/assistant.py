"""Amazon Echo adapter for assistant device control.

Requirement 1.1: Unified interface for assistant device.
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


class EchoAdapter(DeviceAdapter):
    """Adapter for Amazon Echo Devices.

    Controls announcements, notifications, music playback,
    reminders, and volume.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "power": True,
            "volume": 50,
            "last_announcement": "",
            "active": True,
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current Echo state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.ASSISTANT,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute an Echo command."""
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

        if action == "announce":
            message = params.get("message", params.get("text", ""))
            if message and isinstance(message, str):
                self._state["last_announcement"] = message
                self._state["active"] = True
            else:
                success = False
                error_message = "Announcement message must be a non-empty string"

        elif action == "notify":
            message = params.get("message", params.get("text", ""))
            if message and isinstance(message, str):
                self._state["last_announcement"] = f"[Notification] {message}"
                self._state["active"] = True
            else:
                success = False
                error_message = "Notification message must be a non-empty string"

        elif action == "play_music":
            track = params.get("track", params.get("query", ""))
            if track and isinstance(track, str):
                self._state["active"] = True
                self._state["last_announcement"] = f"[Playing] {track}"
            else:
                success = False
                error_message = "Music track/query must be a non-empty string"

        elif action == "set_reminder":
            reminder = params.get("reminder", params.get("message", ""))
            if reminder and isinstance(reminder, str):
                self._state["last_announcement"] = f"[Reminder set] {reminder}"
            else:
                success = False
                error_message = "Reminder must be a non-empty string"

        elif action == "get_status":
            # Returns current state, no mutation needed
            pass

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
        """Register callback for Echo events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return Echo capabilities."""
        return ["announce", "notify", "play_music", "set_reminder", "get_status"]
