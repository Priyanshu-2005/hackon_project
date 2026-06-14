"""Context-related data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.device import DeviceState


@dataclass
class FamilyActivity:
    """Tracks a family member's current activity."""

    member_name: str
    activity: str
    location: str
    start_time: datetime
    estimated_end: Optional[datetime] = None
    devices_in_use: List[str] = field(default_factory=list)


@dataclass
class TemporalPattern:
    """A detected recurring temporal pattern in device usage."""

    pattern_id: str
    pattern_type: str  # "daily", "weekly", "seasonal"
    confidence: float  # 0.0 to 1.0
    devices_involved: List[str] = field(default_factory=list)
    schedule: Dict[str, Any] = field(default_factory=dict)
    last_observed: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContextSnapshot:
    """A complete snapshot of the home context at a point in time.

    Requirement 2.3: Contains device_states, active_activities,
    detected_patterns, resource_levels, environmental data.
    """

    snapshot_id: str
    timestamp: datetime
    device_states: Dict[str, DeviceState] = field(default_factory=dict)
    active_activities: List[FamilyActivity] = field(default_factory=list)
    detected_patterns: List[TemporalPattern] = field(default_factory=list)
    resource_levels: Dict[str, float] = field(default_factory=dict)  # battery, water, etc.
    environmental: Dict[str, Any] = field(default_factory=dict)  # weather, time_of_day, season
    confidence: float = 0.0
