"""Luminous Inverter/UPS adapter for power management.

Requirement 1.1: Unified interface for power device.
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


class LuminousInverterAdapter(DeviceAdapter):
    """Adapter for Luminous Inverter/UPS.

    Manages battery level, load allocation, mode (normal/eco/ups),
    and grid status.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "battery_level": 80,
            "load_watts": 450,
            "mode": "normal",
            "grid_status": "online",
            "allocated_devices": [],
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current inverter state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.POWER,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
            battery_level=self._state["battery_level"],
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute an inverter command."""
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

        if action == "get_battery_level":
            # Returns current state with battery info, no mutation
            pass

        elif action == "get_load":
            # Returns current state with load info, no mutation
            pass

        elif action == "set_mode":
            mode = params.get("mode")
            if mode in ("normal", "eco", "ups"):
                self._state["mode"] = mode
            else:
                success = False
                error_message = "Mode must be normal, eco, or ups"

        elif action == "allocate_load":
            devices = params.get("devices", params.get("allocated_devices"))
            if devices is not None and isinstance(devices, list):
                self._state["allocated_devices"] = devices
                # Simulate load calculation: each device ~100W
                self._state["load_watts"] = len(devices) * 100
            else:
                success = False
                error_message = "Devices must be a list of device identifiers"

        elif action == "get_backup_time":
            # Calculate estimated backup time based on battery and load
            # Returns current state; calculation is in properties
            load = self._state["load_watts"] if self._state["load_watts"] > 0 else 1
            battery_wh = self._state["battery_level"] * 10  # Simplified: 1000Wh at 100%
            backup_minutes = int((battery_wh / load) * 60)
            self._state["estimated_backup_minutes"] = backup_minutes

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
        """Register callback for inverter events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return inverter capabilities."""
        return ["get_battery_level", "get_load", "set_mode", "allocate_load", "get_backup_time"]
