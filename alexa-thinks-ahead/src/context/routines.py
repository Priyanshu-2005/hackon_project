"""Family routine modeler for tracking per-member schedules and active activities.

Models each family member's routines independently using the FamilyProfile configuration.
Correlates scheduled activities with expected device usage and provides current activity
lookups for the context engine.

Requirement 3.3: Model per-member routines by correlating calendar events with device usage.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.models.context import FamilyActivity
from src.models.family import FamilyMember, FamilyProfile
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Default durations for activities (in hours)
ACTIVITY_DURATIONS: Dict[str, float] = {
    "wake_up": 0.5,
    "morning_walk": 1.0,
    "evening_walk": 1.0,
    "puja": 0.5,
    "cooking": 1.0,
    "cooking_assist": 1.5,
    "rest": 2.0,
    "sleep": 8.0,
    "tuition_online": 1.5,
    "study": 1.5,
    "homework": 1.5,
    "tv_time": 1.5,
    "dinner": 1.0,
    "school": 6.0,
    "extracurricular": 1.5,
    "leave_for_work": 0.5,
    "return_home": 0.5,
}

# Activity-to-device mapping: which devices are typically in use during an activity
ACTIVITY_DEVICES: Dict[str, List[str]] = {
    "tuition_online": ["smart_lights", "echo_devices"],
    "sleep": ["living_room_ac", "smart_lights"],
    "cooking": ["kitchen_hub", "smart_lights"],
    "cooking_assist": ["kitchen_hub", "smart_lights"],
    "rest": ["living_room_ac", "smart_lights"],
    "tv_time": ["smart_tv", "smart_lights"],
    "puja": ["smart_lights"],
    "study": ["smart_lights", "echo_devices"],
    "homework": ["smart_lights", "echo_devices"],
    "morning_walk": [],
    "evening_walk": [],
    "school": [],
    "extracurricular": [],
    "leave_for_work": ["smart_lock"],
    "return_home": ["smart_lock"],
    "wake_up": ["smart_lights"],
    "dinner": ["smart_lights", "kitchen_hub"],
}

# Day name abbreviations for parsing specific day lists
DAY_ABBREVIATIONS = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


class FamilyRoutineModeler:
    """Models per-member family routines and provides active activity lookups.

    Uses the FamilyProfile (e.g., SHARMA_FAMILY) to determine which activities
    are active at any given time, based on scheduled routines and day filters.
    """

    def __init__(self, family_profile: FamilyProfile):
        """Initialize the routine modeler with a family profile.

        Args:
            family_profile: The family profile containing members and their routines.
        """
        self.family_profile = family_profile

    def get_active_activities(
        self, current_time: Optional[datetime] = None
    ) -> List[FamilyActivity]:
        """Get all currently active family activities.

        Checks the current time against each member's routines and returns
        FamilyActivity objects for members who should be active right now.

        Args:
            current_time: The time to check against. Defaults to current UTC time.

        Returns:
            List of FamilyActivity objects for currently active routines.
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        active_activities: List[FamilyActivity] = []

        for member in self.family_profile.members:
            for routine in member.routines:
                activity = routine.get("activity", "")
                time_str = routine.get("time", "")
                days = routine.get("days", "daily")

                if not activity or not time_str:
                    continue

                # Check if the routine is active on the current day
                if not self._is_active_day(current_time, days):
                    continue

                # Parse routine start time and compute end time
                start_time = self._parse_routine_time(current_time, time_str)
                if start_time is None:
                    continue

                duration_hours = ACTIVITY_DURATIONS.get(activity, 1.0)
                end_time = start_time + timedelta(hours=duration_hours)

                # Check if current_time falls within [start, end)
                if start_time <= current_time < end_time:
                    devices = ACTIVITY_DEVICES.get(activity, [])
                    family_activity = FamilyActivity(
                        member_name=member.name,
                        activity=activity,
                        location=self._infer_location(activity, member),
                        start_time=start_time,
                        estimated_end=end_time,
                        devices_in_use=list(devices),
                    )
                    active_activities.append(family_activity)

        logger.info(f"Found {len(active_activities)} active activities at {current_time}")
        return active_activities

    def get_member_schedule(self, member_name: str) -> List[Dict]:
        """Get the full routine schedule for a specific family member.

        Args:
            member_name: Name of the family member.

        Returns:
            List of routine dictionaries for the member.
            Returns empty list if member not found.
        """
        for member in self.family_profile.members:
            if member.name == member_name:
                return list(member.routines)
        return []

    def _is_active_day(self, current_time: datetime, days: str) -> bool:
        """Check if the routine is active on the given day.

        Args:
            current_time: The datetime to check.
            days: Day specification - "daily", "weekdays", or comma-separated day names.

        Returns:
            True if the routine is active on the current day.
        """
        if days == "daily":
            return True

        current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday

        if days == "weekdays":
            return current_weekday < 5  # Monday to Friday

        if days == "weekends":
            return current_weekday >= 5

        # Comma-separated day abbreviations (e.g., "mon,wed,fri")
        day_list = [d.strip().lower() for d in days.split(",")]
        for day_abbr in day_list:
            if day_abbr in DAY_ABBREVIATIONS:
                if DAY_ABBREVIATIONS[day_abbr] == current_weekday:
                    return True

        return False

    def _parse_routine_time(
        self, current_time: datetime, time_str: str
    ) -> Optional[datetime]:
        """Parse a routine time string into a datetime on the current date.

        Args:
            current_time: The reference datetime (used for date and timezone).
            time_str: Time in "HH:MM" format.

        Returns:
            A datetime combining current date with the routine time, or None if invalid.
        """
        try:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return current_time.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
        except (ValueError, IndexError):
            logger.warning(f"Invalid time format: {time_str}")
            return None

    def _infer_location(self, activity: str, member: FamilyMember) -> str:
        """Infer the location of an activity based on activity type.

        Args:
            activity: The activity name.
            member: The family member performing the activity.

        Returns:
            Inferred location string.
        """
        location_map = {
            "sleep": "bedroom",
            "cooking": "kitchen",
            "cooking_assist": "kitchen",
            "dinner": "dining_room",
            "tv_time": "living_room",
            "rest": "living_room",
            "puja": "puja_room",
            "morning_walk": "outside",
            "evening_walk": "outside",
            "school": "outside",
            "extracurricular": "outside",
            "leave_for_work": "outside",
            "return_home": "entrance",
            "tuition_online": "study_room",
            "study": "study_room",
            "homework": "study_room",
            "wake_up": "bedroom",
        }
        return location_map.get(activity, "home")
