"""Utility device adapters: Kent Water Purifier and Havells Geyser.

Requirement 1.1: Unified interface for utility devices.
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


class KentPurifierAdapter(DeviceAdapter):
    """Adapter for Kent Water Purifier.

    Controls power state and reports filter life and water quality (TDS).
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "power": True,
            "filter_life_pct": 72,
            "water_quality_tds": 45,
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current purifier state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.UTILITY,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a purifier command."""
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

        elif action == "get_filter_status":
            # Returns current state with filter info, no mutation
            pass

        elif action == "get_water_quality":
            # Returns current state with TDS info, no mutation
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
        """Register callback for purifier events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return purifier capabilities."""
        return ["power_on", "power_off", "get_filter_status", "get_water_quality"]


class HavellsGeyserAdapter(DeviceAdapter):
    """Adapter for Havells Smart Geyser.

    Controls power state and temperature (30-75°C).
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        super().__init__(device_id, device_type, config)
        self._state: Dict = {
            "power": False,
            "temperature": 40,
            "target_temperature": 50,
        }
        self._last_updated = datetime.now(timezone.utc)
        self._reachable = True

    def get_state(self) -> DeviceState:
        """Return current geyser state normalized to DeviceState."""
        status = "online" if self._reachable else "offline"
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.UTILITY,
            status=status,
            properties=dict(self._state),
            last_updated=self._last_updated,
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Execute a geyser command."""
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

        elif action == "set_temperature":
            temp = params.get("temperature", params.get("target_temperature"))
            if temp is not None and 30 <= temp <= 75:
                self._state["target_temperature"] = temp
            else:
                success = False
                error_message = "Temperature must be between 30 and 75"

        elif action == "get_temperature":
            # Returns current state with temperature info, no mutation
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
        """Register callback for geyser events. Returns subscription ID."""
        return str(uuid4())

    def get_capabilities(self) -> List[str]:
        """Return geyser capabilities."""
        return ["power_on", "power_off", "set_temperature", "get_temperature"]
