"""Unit tests for ConflictResolver.

Tests priority ordering: safety > elder_comfort > child_needs > efficiency
Requirements: 3.4, 12.4
"""

from datetime import datetime, timezone

import pytest

from src.context.conflicts import ConflictResolver
from src.models.context import FamilyActivity
from src.utils.constants import PRIORITY_ORDER


@pytest.fixture
def resolver():
    """Create a ConflictResolver instance."""
    return ConflictResolver()


def _make_activity(
    member_name: str,
    activity: str,
    devices: list,
    location: str = "home",
) -> FamilyActivity:
    """Helper to create a FamilyActivity for testing."""
    now = datetime.now(timezone.utc)
    return FamilyActivity(
        member_name=member_name,
        activity=activity,
        location=location,
        start_time=now,
        estimated_end=None,
        devices_in_use=devices,
    )


class TestResolveActivityConflicts:
    """Tests for resolve_activity_conflicts."""

    def test_empty_input_returns_empty(self, resolver):
        """Empty activity list should return empty result."""
        result = resolver.resolve_activity_conflicts([])
        assert result == []

    def test_safety_wins_over_elder_comfort(self, resolver):
        """Safety priority (security devices) wins over elder comfort on shared device."""
        # Security activity uses smart_lock AND smart_lights (safety due to smart_lock)
        safety_activity = _make_activity(
            "rajesh", "lock_check", ["smart_lock", "smart_lights"]
        )
        # Elder activity wants smart_lights (elder_comfort, no security device)
        elder_activity = _make_activity(
            "dadaji", "rest", ["smart_lights", "living_room_ac"]
        )

        result = resolver.resolve_activity_conflicts(
            [elder_activity, safety_activity]
        )

        # Safety should win the smart_lights device (conflict point)
        safety_result = next(
            a for a in result if a.member_name == "rajesh"
        )
        assert "smart_lights" in safety_result.devices_in_use

        # Elder keeps living_room_ac but not smart_lights
        elder_result = next(
            (a for a in result if a.member_name == "dadaji"), None
        )
        if elder_result:
            assert "smart_lights" not in elder_result.devices_in_use
            assert "living_room_ac" in elder_result.devices_in_use

    def test_safety_wins_over_child_needs(self, resolver):
        """Safety priority wins over child needs on shared device."""
        # Security camera activity gets safety priority
        safety_activity = _make_activity(
            "priya", "security_check", ["security_camera", "smart_lights"]
        )
        # Child wants smart_lights (no security device, so child_needs priority)
        child_activity = _make_activity(
            "arjun", "study", ["smart_lights", "smart_tv"]
        )

        result = resolver.resolve_activity_conflicts(
            [child_activity, safety_activity]
        )

        # Safety gets smart_lights (the conflict point)
        safety_result = next(
            a for a in result if a.member_name == "priya"
        )
        assert "smart_lights" in safety_result.devices_in_use

        # Child keeps smart_tv but not smart_lights
        child_result = next(
            (a for a in result if a.member_name == "arjun"), None
        )
        if child_result:
            assert "smart_lights" not in child_result.devices_in_use
            assert "smart_tv" in child_result.devices_in_use

    def test_safety_wins_over_efficiency(self, resolver):
        """Safety priority wins over efficiency (parent) on shared device."""
        # Safety activity uses smart_lock (safety due to security device)
        safety_activity = _make_activity(
            "rajesh", "arm_system", ["smart_lock", "echo_devices"]
        )
        # Efficiency activity wants echo_devices (no security device, parent=efficiency)
        efficiency_activity = _make_activity(
            "priya", "leaving", ["echo_devices"]
        )

        result = resolver.resolve_activity_conflicts(
            [efficiency_activity, safety_activity]
        )

        # Safety wins echo_devices
        winners = [a for a in result if "echo_devices" in a.devices_in_use]
        assert len(winners) == 1
        assert winners[0].member_name == "rajesh"

    def test_elder_comfort_wins_over_child_needs(self, resolver):
        """Elder comfort wins over child needs on shared non-security device."""
        elder_activity = _make_activity(
            "dadaji", "rest", ["living_room_ac", "smart_lights"]
        )
        child_activity = _make_activity(
            "ananya", "homework", ["smart_lights", "echo_devices"]
        )

        result = resolver.resolve_activity_conflicts(
            [child_activity, elder_activity]
        )

        # Elder gets smart_lights
        elder_result = next(
            a for a in result if a.member_name == "dadaji"
        )
        assert "smart_lights" in elder_result.devices_in_use
        assert "living_room_ac" in elder_result.devices_in_use

        # Child keeps echo_devices but not smart_lights
        child_result = next(
            (a for a in result if a.member_name == "ananya"), None
        )
        if child_result:
            assert "smart_lights" not in child_result.devices_in_use
            assert "echo_devices" in child_result.devices_in_use

    def test_elder_comfort_wins_over_efficiency(self, resolver):
        """Elder comfort wins over parent efficiency on shared device."""
        elder_activity = _make_activity(
            "dadiji", "rest", ["living_room_ac"]
        )
        parent_activity = _make_activity(
            "rajesh", "energy_saving", ["living_room_ac"]
        )

        result = resolver.resolve_activity_conflicts(
            [parent_activity, elder_activity]
        )

        # Elder wins the AC
        winners = [a for a in result if "living_room_ac" in a.devices_in_use]
        assert len(winners) == 1
        assert winners[0].member_name == "dadiji"

    def test_non_conflicting_activities_all_kept(self, resolver):
        """Activities using different devices should all be preserved."""
        activity1 = _make_activity("dadaji", "rest", ["living_room_ac"])
        activity2 = _make_activity("arjun", "study", ["smart_lights"])
        activity3 = _make_activity("priya", "cooking", ["kitchen_hub"])

        result = resolver.resolve_activity_conflicts(
            [activity1, activity2, activity3]
        )

        # All three activities should be in the result
        assert len(result) == 3
        names = {a.member_name for a in result}
        assert names == {"dadaji", "arjun", "priya"}

    def test_activity_with_no_remaining_devices_excluded(self, resolver):
        """An activity that loses all its devices is excluded from results."""
        # Elder gets the only device
        elder_activity = _make_activity(
            "dadaji", "rest", ["living_room_ac"]
        )
        # Parent also wants just that device
        parent_activity = _make_activity(
            "rajesh", "cool_down", ["living_room_ac"]
        )

        result = resolver.resolve_activity_conflicts(
            [parent_activity, elder_activity]
        )

        # Only elder remains since parent loses its only device
        assert len(result) == 1
        assert result[0].member_name == "dadaji"


class TestResolveCommandConflicts:
    """Tests for resolve_command_conflicts."""

    def test_empty_input_returns_empty(self, resolver):
        """Empty command list should return empty result."""
        result = resolver.resolve_command_conflicts([])
        assert result == []

    def test_safety_command_wins_over_others(self, resolver):
        """Safety-priority command wins over lower priority on same device."""
        commands = [
            {
                "device_id": "smart_lock",
                "action": "lock",
                "parameters": {},
                "priority_category": "safety",
            },
            {
                "device_id": "smart_lock",
                "action": "unlock",
                "parameters": {},
                "priority_category": "child_needs",
            },
        ]

        result = resolver.resolve_command_conflicts(commands)

        assert len(result) == 1
        assert result[0]["action"] == "lock"
        assert result[0]["priority_category"] == "safety"

    def test_elder_comfort_wins_over_efficiency(self, resolver):
        """Elder comfort command wins over efficiency on same device."""
        commands = [
            {
                "device_id": "living_room_ac",
                "action": "set_temp",
                "parameters": {"temp": 22},
                "priority_category": "elder_comfort",
            },
            {
                "device_id": "living_room_ac",
                "action": "set_temp",
                "parameters": {"temp": 28},
                "priority_category": "efficiency",
            },
        ]

        result = resolver.resolve_command_conflicts(commands)

        assert len(result) == 1
        assert result[0]["parameters"]["temp"] == 22
        assert result[0]["priority_category"] == "elder_comfort"

    def test_non_conflicting_commands_all_kept(self, resolver):
        """Commands targeting different devices are all kept."""
        commands = [
            {
                "device_id": "smart_lock",
                "action": "lock",
                "parameters": {},
                "priority_category": "safety",
            },
            {
                "device_id": "living_room_ac",
                "action": "set_temp",
                "parameters": {"temp": 24},
                "priority_category": "elder_comfort",
            },
            {
                "device_id": "smart_lights",
                "action": "dim",
                "parameters": {"brightness": 50},
                "priority_category": "child_needs",
            },
        ]

        result = resolver.resolve_command_conflicts(commands)

        assert len(result) == 3

    def test_unknown_priority_treated_as_lowest(self, resolver):
        """Unknown priority category gets lowest priority (score=99)."""
        commands = [
            {
                "device_id": "smart_tv",
                "action": "off",
                "parameters": {},
                "priority_category": "unknown_category",
            },
            {
                "device_id": "smart_tv",
                "action": "on",
                "parameters": {},
                "priority_category": "efficiency",
            },
        ]

        result = resolver.resolve_command_conflicts(commands)

        assert len(result) == 1
        # Efficiency (score=3) beats unknown (score=99)
        assert result[0]["action"] == "on"
        assert result[0]["priority_category"] == "efficiency"


class TestPriorityScoring:
    """Tests for internal priority scoring logic."""

    def test_priority_order_matches_constants(self, resolver):
        """Priority scoring order matches PRIORITY_ORDER constant."""
        scores = [resolver._get_priority_score(cat) for cat in PRIORITY_ORDER]
        # Scores should be strictly increasing (lower score = higher priority)
        assert scores == sorted(scores)
        assert len(set(scores)) == len(scores)  # All distinct

    def test_unknown_category_gets_lowest_score(self, resolver):
        """Unknown categories get score 99 (lowest priority)."""
        assert resolver._get_priority_score("unknown") == 99
        assert resolver._get_priority_score("") == 99

    def test_safety_has_lowest_score(self, resolver):
        """Safety has the lowest (highest priority) score."""
        safety_score = resolver._get_priority_score("safety")
        for category in ["elder_comfort", "child_needs", "efficiency"]:
            assert safety_score < resolver._get_priority_score(category)


class TestInferPriorityCategory:
    """Tests for priority category inference from activities."""

    def test_security_device_implies_safety(self, resolver):
        """Activities using security devices get safety priority."""
        activity = _make_activity("rajesh", "check", ["security_camera"])
        assert resolver._infer_priority_category(activity) == "safety"

        activity2 = _make_activity("priya", "lock", ["smart_lock"])
        assert resolver._infer_priority_category(activity2) == "safety"

    def test_elder_member_gets_elder_comfort(self, resolver):
        """Elder family members get elder_comfort priority."""
        activity = _make_activity("dadaji", "rest", ["living_room_ac"])
        assert resolver._infer_priority_category(activity) == "elder_comfort"

        activity2 = _make_activity("dadiji", "rest", ["smart_lights"])
        assert resolver._infer_priority_category(activity2) == "elder_comfort"

    def test_child_member_gets_child_needs(self, resolver):
        """Child family members get child_needs priority."""
        activity = _make_activity("arjun", "study", ["smart_lights"])
        assert resolver._infer_priority_category(activity) == "child_needs"

        activity2 = _make_activity("ananya", "homework", ["echo_devices"])
        assert resolver._infer_priority_category(activity2) == "child_needs"

    def test_parent_member_gets_efficiency(self, resolver):
        """Parent family members get efficiency priority."""
        activity = _make_activity("rajesh", "work", ["smart_lights"])
        assert resolver._infer_priority_category(activity) == "efficiency"

        activity2 = _make_activity("priya", "cooking", ["kitchen_hub"])
        assert resolver._infer_priority_category(activity2) == "efficiency"

    def test_security_device_overrides_role(self, resolver):
        """Security device gives safety priority regardless of member role."""
        # Even a child using a security device gets safety priority
        activity = _make_activity("arjun", "play", ["smart_lock", "smart_tv"])
        assert resolver._infer_priority_category(activity) == "safety"
