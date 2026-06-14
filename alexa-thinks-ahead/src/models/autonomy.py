"""Autonomy tier and trust data models."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.models.device import DeviceCategory, DeviceCommand


class ActionType(Enum):
    """Types of autonomous actions based on confidence level."""

    AUTO_EXECUTE = "auto_execute"
    RECOMMEND = "recommend"
    INFORM = "inform"


@dataclass
class TrustScore:
    """Trust score per family member per device category.

    Requirement 5.1: TrustScore per member per category, range 0-100.
    Requirement 5.2: Tier mapping 0-20=1, 21-45=2, 46-70=3, 71-90=4, 91-100=5.
    """

    member: str
    category: DeviceCategory
    score: float  # 0 to 100
    current_tier: int  # 1 to 5
    last_interaction: datetime
    consecutive_acceptances: int = 0
    override_count_30d: int = 0


@dataclass
class TierDecision:
    """Result of checking whether an action is permitted at a given tier."""

    action: DeviceCommand
    permitted: bool
    current_tier: int
    required_tier: int
    requires_confirmation: bool
    reason: str
