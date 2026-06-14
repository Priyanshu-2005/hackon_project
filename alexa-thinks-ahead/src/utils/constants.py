"""Immutable constants for the Alexa Thinks Ahead system."""

from typing import Dict, List

# Tier thresholds - trust score boundaries for each autonomy tier.
# Index corresponds to tier number (tier 1 starts at 0, tier 2 at 21, etc.)
TIER_THRESHOLDS: List[int] = [0, 21, 46, 71, 91]

# Human-readable tier names
TIER_NAMES: Dict[int, str] = {
    1: "Inform",
    2: "Suggest",
    3: "Auto-Act (Reversible)",
    4: "Auto-Act (Irreversible)",
    5: "Full Autonomy",
}

# Confidence thresholds for action routing
CONFIDENCE_AUTO_EXECUTE: float = 0.85
CONFIDENCE_RECOMMEND: float = 0.60
CONFIDENCE_INFORM: float = 0.40

# Device categories supported by the system
DEVICE_CATEGORIES: List[str] = [
    "climate",
    "lighting",
    "security",
    "kitchen",
    "utility",
    "power",
    "entertainment",
    "assistant",
]

# Sharma family members
FAMILY_MEMBERS: List[str] = [
    "rajesh",
    "priya",
    "arjun",
    "ananya",
    "dadaji",
    "dadiji",
]

# Indian seasons mapped to months
SEASONS: Dict[str, List[int]] = {
    "summer": [3, 4, 5, 6],
    "monsoon": [7, 8, 9],
    "autumn": [10, 11],
    "winter": [12, 1, 2],
}

# Conflict resolution priority (highest priority first)
PRIORITY_ORDER: List[str] = [
    "safety",
    "elder_comfort",
    "child_needs",
    "efficiency",
]

# Intelligence strategies for proactive actions
INTELLIGENCE_STRATEGIES: List[str] = [
    "pre_cooling",
    "geyser_preheat",
    "security_arm",
    "energy_optimization",
    "comfort_lighting",
    "storm_preparation",
]
