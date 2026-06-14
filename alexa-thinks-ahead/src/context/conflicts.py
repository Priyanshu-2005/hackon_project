"""Conflict resolver for overlapping device needs between family members.

Resolves conflicts using priority ordering: safety > elder_comfort > child_needs > efficiency.
When two activities need the same device with conflicting settings, the higher-priority need wins.

Requirements:
    3.4: Resolve conflicts using priority rules (safety > elder comfort > child needs > efficiency)
    12.4: If two action plans conflict on same device, resolve using priority ordering
"""

from typing import Any, Dict, List

from src.models.context import FamilyActivity
from src.utils.constants import PRIORITY_ORDER
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ConflictResolver:
    """Resolves conflicting device needs between family members.

    Uses priority ordering: safety > elder_comfort > child_needs > efficiency
    When two activities need the same device with conflicting settings,
    the higher-priority need wins.
    """

    ROLE_PRIORITY: Dict[str, int] = {
        "safety": 0,  # Highest priority (e.g., security actions)
        "elder_comfort": 1,
        "child_needs": 2,
        "efficiency": 3,  # Lowest priority
    }

    # Map family roles to priority categories
    ROLE_TO_PRIORITY_CATEGORY: Dict[str, str] = {
        "elder": "elder_comfort",
        "child": "child_needs",
        "parent": "efficiency",
    }

    # Devices that imply safety priority
    SAFETY_DEVICES = {"security_camera", "smart_lock"}

    def resolve_activity_conflicts(
        self, activities: List[FamilyActivity]
    ) -> List[FamilyActivity]:
        """Resolve conflicts between overlapping activities on shared devices.

        When multiple activities need the same device, the higher-priority
        activity wins. Returns the resolved list of activities with conflicting
        device references removed from lower-priority activities.

        Args:
            activities: List of active FamilyActivity objects.

        Returns:
            Resolved list of activities where device conflicts are settled.
            Activities that lose all devices are excluded from the result.
        """
        if not activities:
            return []

        # Assign priority categories to each activity
        activity_priorities: List[tuple] = []
        for activity in activities:
            category = self._infer_priority_category(activity)
            score = self._get_priority_score(category)
            activity_priorities.append((activity, category, score))

        # Sort by priority score (lower = higher priority)
        activity_priorities.sort(key=lambda x: x[2])

        # Track which devices have been claimed
        claimed_devices: Dict[str, FamilyActivity] = {}
        resolved_activities: List[FamilyActivity] = []

        for activity, category, score in activity_priorities:
            # Determine which devices this activity can keep
            remaining_devices: List[str] = []
            for device in activity.devices_in_use:
                if device not in claimed_devices:
                    # Device is unclaimed, this activity gets it
                    claimed_devices[device] = activity
                    remaining_devices.append(device)
                else:
                    # Device already claimed by a higher-priority activity
                    logger.info(
                        f"Conflict on '{device}': '{activity.member_name}/{activity.activity}' "
                        f"(priority={category}) loses to "
                        f"'{claimed_devices[device].member_name}/{claimed_devices[device].activity}'"
                    )

            # Create a resolved copy of the activity with remaining devices
            if remaining_devices:
                resolved_activity = FamilyActivity(
                    member_name=activity.member_name,
                    activity=activity.activity,
                    location=activity.location,
                    start_time=activity.start_time,
                    estimated_end=activity.estimated_end,
                    devices_in_use=remaining_devices,
                )
                resolved_activities.append(resolved_activity)

        logger.info(
            f"Resolved {len(activities)} activities to {len(resolved_activities)} "
            f"(claimed {len(claimed_devices)} devices)"
        )
        return resolved_activities

    def resolve_command_conflicts(
        self, commands: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve conflicting device commands.

        Each command dict has: device_id, action, parameters, priority_category.
        When multiple commands target the same device, the highest-priority
        command is kept.

        Args:
            commands: List of command dicts with priority_category field.

        Returns:
            Deduplicated list with one command per device (highest priority wins).
        """
        if not commands:
            return []

        # Sort commands by priority score (lower = higher priority)
        sorted_commands = sorted(
            commands,
            key=lambda cmd: self._get_priority_score(
                cmd.get("priority_category", "efficiency")
            ),
        )

        # Keep only the first (highest priority) command per device
        device_winners: Dict[str, Dict[str, Any]] = {}
        for cmd in sorted_commands:
            device_id = cmd.get("device_id", "")
            if device_id not in device_winners:
                device_winners[device_id] = cmd
            else:
                existing = device_winners[device_id]
                logger.info(
                    f"Command conflict on '{device_id}': "
                    f"'{cmd.get('priority_category')}' loses to "
                    f"'{existing.get('priority_category')}'"
                )

        resolved = list(device_winners.values())
        logger.info(
            f"Resolved {len(commands)} commands to {len(resolved)} "
            f"(one per device, highest priority wins)"
        )
        return resolved

    def _get_priority_score(self, category: str) -> int:
        """Get the numeric priority score for a category.

        Lower score = higher priority.

        Args:
            category: Priority category name.

        Returns:
            Integer score (0=highest, 99=unknown).
        """
        return self.ROLE_PRIORITY.get(category, 99)

    def _infer_priority_category(self, activity: FamilyActivity) -> str:
        """Infer priority category from activity context.

        Security-related devices always get 'safety' priority.
        Otherwise, the category is inferred from the member name and known roles.

        Args:
            activity: The FamilyActivity to categorize.

        Returns:
            Priority category string.
        """
        # Security activities always get "safety" priority
        if any(d in self.SAFETY_DEVICES for d in activity.devices_in_use):
            return "safety"

        # Infer role from member name using known Sharma family mapping
        member_role = self._get_member_role(activity.member_name)
        return self.ROLE_TO_PRIORITY_CATEGORY.get(member_role, "efficiency")

    def _get_member_role(self, member_name: str) -> str:
        """Get the role of a family member by name.

        Uses the Sharma family mapping. Falls back to 'parent' for unknown members.

        Args:
            member_name: Name of the family member.

        Returns:
            Role string ('elder', 'child', or 'parent').
        """
        # Sharma family role mapping
        member_roles: Dict[str, str] = {
            "dadaji": "elder",
            "dadiji": "elder",
            "rajesh": "parent",
            "priya": "parent",
            "arjun": "child",
            "ananya": "child",
        }
        return member_roles.get(member_name.lower(), "parent")
