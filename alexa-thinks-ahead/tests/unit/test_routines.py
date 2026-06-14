"""Unit tests for the FamilyRoutineModeler.

Tests active activity detection, day filtering (weekdays/daily/specific days),
member schedule lookup, and device-to-activity mapping.
"""

import pytest
from datetime import datetime, timezone

from src.context.routines import FamilyRoutineModeler
from src.models.family import FamilyMember, FamilyProfile, SHARMA_FAMILY


class TestFamilyRoutineModeler:
    """Tests for the FamilyRoutineModeler class."""

    def setup_method(self):
        """Set up test fixtures using the Sharma family profile."""
        self.modeler = FamilyRoutineModeler(SHARMA_FAMILY)

    def test_get_active_activities_returns_activities_at_correct_times(self):
        """Activities should be returned when current time falls within their duration."""
        # Arjun's tuition is at 16:00 weekdays, duration 1.5h -> active until 17:30
        # Use a Wednesday at 16:30 (within tuition window)
        wednesday_1630 = datetime(2024, 1, 17, 16, 30, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(wednesday_1630)

        # Arjun's tuition_online should be active
        arjun_tuition = [
            a for a in activities
            if a.member_name == "Arjun" and a.activity == "tuition_online"
        ]
        assert len(arjun_tuition) == 1
        assert arjun_tuition[0].devices_in_use == ["smart_lights", "echo_devices"]
        assert arjun_tuition[0].location == "study_room"

    def test_weekday_only_routines_dont_trigger_on_weekends(self):
        """Routines with days='weekdays' should not be active on Saturday/Sunday."""
        # Arjun's tuition is weekday-only, check on a Saturday at 16:30
        # Jan 20, 2024 is a Saturday
        saturday_1630 = datetime(2024, 1, 20, 16, 30, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(saturday_1630)

        # Arjun's tuition_online should NOT be active on Saturday
        arjun_tuition = [
            a for a in activities
            if a.member_name == "Arjun" and a.activity == "tuition_online"
        ]
        assert len(arjun_tuition) == 0

    def test_daily_routines_trigger_on_weekends(self):
        """Routines with days='daily' should be active on any day including weekends."""
        # Dadaji's rest is daily at 13:00 (duration 2h -> active until 15:00)
        # Check on Saturday at 14:00
        saturday_1400 = datetime(2024, 1, 20, 14, 0, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(saturday_1400)

        # Dadaji's rest should be active
        dadaji_rest = [
            a for a in activities
            if a.member_name == "Dadaji" and a.activity == "rest"
        ]
        assert len(dadaji_rest) == 1
        assert dadaji_rest[0].devices_in_use == ["living_room_ac", "smart_lights"]

    def test_get_member_schedule_returns_correct_schedule(self):
        """get_member_schedule should return all routines for a given member."""
        arjun_schedule = self.modeler.get_member_schedule("Arjun")

        # Arjun has 6 routines in the SHARMA_FAMILY profile
        assert len(arjun_schedule) == 6

        # Verify tuition_online is in the schedule
        activities = [r["activity"] for r in arjun_schedule]
        assert "tuition_online" in activities
        assert "school" in activities
        assert "study" in activities

    def test_get_member_schedule_returns_empty_for_unknown_member(self):
        """get_member_schedule should return empty list for non-existent member."""
        result = self.modeler.get_member_schedule("NonExistentPerson")
        assert result == []

    def test_activity_not_active_outside_duration_window(self):
        """Activity should not be returned when current time is past its end time."""
        # Dadaji's puja is at 07:00 daily, duration 0.5h -> ends at 07:30
        # Check at 08:00 - should not be active
        wednesday_0800 = datetime(2024, 1, 17, 8, 0, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(wednesday_0800)

        dadaji_puja = [
            a for a in activities
            if a.member_name == "Dadaji" and a.activity == "puja"
        ]
        assert len(dadaji_puja) == 0

    def test_specific_day_filter_mon_wed_fri(self):
        """Routines with specific day filters (e.g., mon,wed,fri) should work correctly."""
        # Ananya's extracurricular is at 15:00 on mon,wed,fri (duration 1.5h)
        # Wednesday at 15:30 - should be active
        wednesday_1530 = datetime(2024, 1, 17, 15, 30, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(wednesday_1530)

        ananya_extra = [
            a for a in activities
            if a.member_name == "Ananya" and a.activity == "extracurricular"
        ]
        assert len(ananya_extra) == 1

    def test_specific_day_filter_not_on_wrong_day(self):
        """Routines with specific day filters should not trigger on excluded days."""
        # Ananya's extracurricular is mon,wed,fri only
        # Tuesday at 15:30 - should NOT be active
        # Jan 16, 2024 is a Tuesday
        tuesday_1530 = datetime(2024, 1, 16, 15, 30, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(tuesday_1530)

        ananya_extra = [
            a for a in activities
            if a.member_name == "Ananya" and a.activity == "extracurricular"
        ]
        assert len(ananya_extra) == 0

    def test_multiple_members_active_simultaneously(self):
        """Multiple family members can have active activities at the same time."""
        # At 19:30 daily: Dadaji's tv_time starts; Priya's cooking is active (started at 19:00)
        # Arjun's study is at 19:00 weekdays
        wednesday_1930 = datetime(2024, 1, 17, 19, 30, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(wednesday_1930)

        active_members = {a.member_name for a in activities}
        # Multiple members should be active at this busy evening time
        assert len(active_members) >= 2

    def test_activity_has_estimated_end_time(self):
        """Each returned activity should have a valid estimated_end datetime."""
        wednesday_1630 = datetime(2024, 1, 17, 16, 30, 0, tzinfo=timezone.utc)

        activities = self.modeler.get_active_activities(wednesday_1630)

        for activity in activities:
            assert activity.estimated_end is not None
            assert activity.estimated_end > activity.start_time

    def test_get_active_activities_defaults_to_current_time(self):
        """get_active_activities should work without explicit time argument."""
        # Just verify it doesn't raise an error
        activities = self.modeler.get_active_activities()
        assert isinstance(activities, list)
