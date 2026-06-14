"""Device-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class DeviceCategory(Enum):
    """Categories of smart home devices."""

    CLIMATE = "climate"
    LIGHTING = "lighting"
    SECURITY = "security"
    KITCHEN = "kitchen"
    UTILITY = "utility"
    POWER = "power"
    ENTERTAINMENT = "entertainment"
    ASSISTANT = "assistant"


@dataclass
class DeviceState:
    """Represents the current state of a smart home device.

    Requirement 1.5: DeviceState with device_id, device_type, category,
    status, properties, last_updated.
    """

    device_id: str
    device_type: str
    category: DeviceCategory
    status: str  # "online", "offline", "error"
    properties: Dict[str, Any]
    last_updated: datetime
    battery_level: Optional[float] = None


@dataclass
class DeviceCommand:
    """A command to be sent to a device."""

    command_id: str
    device_id: str
    action: str
    parameters: Dict[str, Any]
    source: str  # "autonomy", "user", "schedule"
    tier_required: int
    reversible: bool


@dataclass
class CommandResult:
    """Result of executing a device command."""

    command_id: str
    success: bool
    device_id: str
    new_state: Optional[DeviceState] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
