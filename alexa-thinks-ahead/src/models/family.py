"""Family member and profile data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FamilyMember:
    """Profile for a single family member."""

    name: str
    role: str  # "parent", "child", "elder"
    preferred_echo: str
    routines: List[Dict[str, Any]] = field(default_factory=list)
    autonomy_preferences: Dict[str, int] = field(default_factory=dict)


@dataclass
class FamilyProfile:
    """A family profile with all members."""

    family_id: str
    members: List[FamilyMember] = field(default_factory=list)


# Sharma Family Configuration - Pre-configured with default routines and preferences
SHARMA_FAMILY = FamilyProfile(
    family_id="sharma_family_001",
    members=[
        FamilyMember(
            name="Rajesh",
            role="parent",
            preferred_echo="master_bedroom_echo",
            routines=[
                {"activity": "wake_up", "time": "06:30", "days": "weekdays"},
                {"activity": "leave_for_work", "time": "08:30", "days": "weekdays"},
                {"activity": "return_home", "time": "18:30", "days": "weekdays"},
                {"activity": "dinner", "time": "20:30", "days": "daily"},
                {"activity": "sleep", "time": "23:00", "days": "daily"},
            ],
            autonomy_preferences={
                "climate": 3,
                "lighting": 4,
                "security": 2,
                "kitchen": 3,
                "utility": 4,
                "power": 3,
                "entertainment": 4,
                "assistant": 5,
            },
        ),
        FamilyMember(
            name="Priya",
            role="parent",
            preferred_echo="kitchen_echo",
            routines=[
                {"activity": "wake_up", "time": "06:00", "days": "daily"},
                {"activity": "leave_for_work", "time": "09:00", "days": "weekdays"},
                {"activity": "return_home", "time": "17:30", "days": "weekdays"},
                {"activity": "cooking", "time": "19:00", "days": "daily"},
                {"activity": "dinner", "time": "20:30", "days": "daily"},
                {"activity": "sleep", "time": "22:30", "days": "daily"},
            ],
            autonomy_preferences={
                "climate": 3,
                "lighting": 4,
                "security": 3,
                "kitchen": 5,
                "utility": 4,
                "power": 3,
                "entertainment": 3,
                "assistant": 5,
            },
        ),
        FamilyMember(
            name="Arjun",
            role="child",
            preferred_echo="study_room_echo",
            routines=[
                {"activity": "wake_up", "time": "07:00", "days": "weekdays"},
                {"activity": "school", "time": "08:00", "days": "weekdays"},
                {"activity": "return_home", "time": "14:30", "days": "weekdays"},
                {"activity": "tuition_online", "time": "16:00", "days": "weekdays"},
                {"activity": "study", "time": "19:00", "days": "weekdays"},
                {"activity": "sleep", "time": "22:00", "days": "weekdays"},
            ],
            autonomy_preferences={
                "climate": 2,
                "lighting": 3,
                "security": 1,
                "kitchen": 1,
                "utility": 2,
                "power": 1,
                "entertainment": 3,
                "assistant": 4,
            },
        ),
        FamilyMember(
            name="Ananya",
            role="child",
            preferred_echo="living_room_echo",
            routines=[
                {"activity": "wake_up", "time": "07:00", "days": "weekdays"},
                {"activity": "school", "time": "08:00", "days": "weekdays"},
                {"activity": "return_home", "time": "13:30", "days": "weekdays"},
                {"activity": "extracurricular", "time": "15:00", "days": "mon,wed,fri"},
                {"activity": "homework", "time": "17:00", "days": "weekdays"},
                {"activity": "sleep", "time": "21:00", "days": "daily"},
            ],
            autonomy_preferences={
                "climate": 2,
                "lighting": 2,
                "security": 1,
                "kitchen": 1,
                "utility": 1,
                "power": 1,
                "entertainment": 3,
                "assistant": 4,
            },
        ),
        FamilyMember(
            name="Dadaji",
            role="elder",
            preferred_echo="living_room_echo",
            routines=[
                {"activity": "wake_up", "time": "05:30", "days": "daily"},
                {"activity": "morning_walk", "time": "06:00", "days": "daily"},
                {"activity": "puja", "time": "07:00", "days": "daily"},
                {"activity": "rest", "time": "13:00", "days": "daily"},
                {"activity": "evening_walk", "time": "17:00", "days": "daily"},
                {"activity": "tv_time", "time": "19:30", "days": "daily"},
                {"activity": "sleep", "time": "21:30", "days": "daily"},
            ],
            autonomy_preferences={
                "climate": 4,
                "lighting": 3,
                "security": 2,
                "kitchen": 2,
                "utility": 3,
                "power": 2,
                "entertainment": 3,
                "assistant": 3,
            },
        ),
        FamilyMember(
            name="Dadiji",
            role="elder",
            preferred_echo="living_room_echo",
            routines=[
                {"activity": "wake_up", "time": "05:30", "days": "daily"},
                {"activity": "puja", "time": "06:30", "days": "daily"},
                {"activity": "cooking_assist", "time": "10:00", "days": "daily"},
                {"activity": "rest", "time": "14:00", "days": "daily"},
                {"activity": "tv_time", "time": "16:00", "days": "daily"},
                {"activity": "sleep", "time": "21:00", "days": "daily"},
            ],
            autonomy_preferences={
                "climate": 4,
                "lighting": 3,
                "security": 2,
                "kitchen": 3,
                "utility": 3,
                "power": 2,
                "entertainment": 3,
                "assistant": 3,
            },
        ),
    ],
)
