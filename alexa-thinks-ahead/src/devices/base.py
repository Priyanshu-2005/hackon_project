"""Base device adapter abstract class.

Requirement 1.1: Unified interface (get_state, execute_command,
subscribe_events, get_capabilities) for each of the 10 registered devices.

Requirement 1.5: Normalize device state into DeviceState dataclass.
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, List

from src.models.device import CommandResult, DeviceCommand, DeviceState


class DeviceAdapter(ABC):
    """Abstract base for all device adapters.

    Each concrete adapter implements communication with a specific
    smart home device brand/protocol and normalizes state into the
    unified DeviceState dataclass.
    """

    def __init__(self, device_id: str, device_type: str, config: Dict):
        """Initialize the adapter with device metadata and configuration.

        Args:
            device_id: Unique identifier for this device instance.
            device_type: Type string (e.g. "ac", "lights", "camera").
            config: Device-specific configuration (brand, endpoint, etc.).
        """
        self.device_id = device_id
        self.device_type = device_type
        self.config = config

    @abstractmethod
    def get_state(self) -> DeviceState:
        """Query current device state, normalized into DeviceState.

        Returns:
            DeviceState with current properties and status.
        """
        ...

    @abstractmethod
    def execute_command(self, command: DeviceCommand) -> CommandResult:
        """Send a command to the device and return the result.

        Args:
            command: The DeviceCommand to execute.

        Returns:
            CommandResult with success status and optional new state.
        """
        ...

    @abstractmethod
    def subscribe_events(self, callback: Callable) -> str:
        """Register a callback for real-time device events.

        Args:
            callback: Function to invoke when device emits an event.

        Returns:
            Subscription ID that can be used to unsubscribe.
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return the list of capabilities this device supports.

        Returns:
            List of capability strings (e.g. ["set_temperature", "set_mode"]).
        """
        ...
