"""Continuous learning data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class PreferenceDistribution:
    """A Bayesian preference distribution for a single preference key."""

    key: str
    mean: float
    variance: float
    sample_count: int
    last_updated: datetime
    seasonal_bias: Dict[str, float] = field(default_factory=dict)


@dataclass
class FeedbackEvent:
    """A feedback event from a family member."""

    event_id: str
    member: str
    feedback_type: str  # "explicit_rating", "override", "acceptance", "adjustment"
    context: Dict[str, Any]
    signal_value: float  # -1.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
