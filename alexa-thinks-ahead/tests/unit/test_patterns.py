"""Unit tests for the TemporalPatternAnalyzer.

Tests daily pattern detection, weekly pattern detection,
confidence filtering, and edge cases.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.context.patterns import TemporalPatternAnalyzer


class TestTemporalPatternAnalyzer:
    """Tests for TemporalPatternAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a low threshold for tests to see all patterns
        self.analyzer = TemporalPatternAnalyzer(table=None, confidence_threshold=0.75)

    def test_empty_history_returns_empty_list(self):
        """Empty history should produce no patterns."""
        result = self.analyzer.detect_patterns([])
        assert result == []

    def test_daily_patterns_detected_from_consistent_usage(self):
        """Device used at the same hour every day should produce a daily pattern."""
        base = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        # Same device used at 8am for 4 consecutive days
        history = []
        for day_offset in range(4):
            history.append({
                "device_id": "living_room_ac",
                "timestamp": (base + timedelta(days=day_offset)).isoformat(),
            })

        # With 4 days and usage every day, confidence = 4/4 = 1.0
        result = self.analyzer.detect_patterns(history)

        daily_patterns = [p for p in result if p.pattern_type == "daily"]
        assert len(daily_patterns) >= 1

        # Find the specific pattern for hour 8
        ac_pattern = next(
            (p for p in daily_patterns if "living_room_ac" in p.devices_involved),
            None,
        )
        assert ac_pattern is not None
        assert ac_pattern.confidence == 1.0
        assert ac_pattern.schedule["hour"] == 8
        assert ac_pattern.schedule["frequency"] == "daily"

    def test_patterns_below_confidence_threshold_are_filtered(self):
        """Patterns with confidence < threshold should not be included."""
        # Use high threshold
        analyzer = TemporalPatternAnalyzer(table=None, confidence_threshold=0.75)

        base = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        # Device used at 10am on only 1 out of 4 different days
        history = [
            {"device_id": "smart_geyser", "timestamp": base.isoformat()},
            # Other device events on different days to establish total_days count
            {"device_id": "other_device", "timestamp": (base + timedelta(days=1)).isoformat()},
            {"device_id": "other_device", "timestamp": (base + timedelta(days=2)).isoformat()},
            {"device_id": "other_device", "timestamp": (base + timedelta(days=3)).isoformat()},
        ]

        result = analyzer.detect_patterns(history)

        # smart_geyser at hour 10: confidence = 1/4 = 0.25 (below 0.75 threshold)
        geyser_patterns = [
            p for p in result
            if "smart_geyser" in p.devices_involved and p.pattern_type == "daily"
        ]
        assert len(geyser_patterns) == 0

    def test_weekly_patterns_detect_weekday_skew(self):
        """Device used only on weekdays should produce a weekly pattern."""
        # Use a low threshold to see the weekly pattern
        analyzer = TemporalPatternAnalyzer(table=None, confidence_threshold=0.3)

        # Monday to Friday usage only (Jan 15, 2024 is a Monday)
        history = []
        monday = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        for day_offset in range(5):  # Mon-Fri
            history.append({
                "device_id": "office_light",
                "timestamp": (monday + timedelta(days=day_offset)).isoformat(),
            })

        result = analyzer.detect_patterns(history)

        weekly_patterns = [p for p in result if p.pattern_type == "weekly"]
        office_weekly = next(
            (p for p in weekly_patterns if "office_light" in p.devices_involved),
            None,
        )
        assert office_weekly is not None
        # All usage on weekdays: ratio = 1.0, expected = 0.714, skew = 0.286
        # confidence = 0.286 * 3 = 0.857
        assert office_weekly.confidence > 0.5
        assert office_weekly.schedule["dominant_period"] == "weekdays"

    def test_weekly_patterns_detect_weekend_skew(self):
        """Device used only on weekends should produce a weekend-dominant pattern."""
        analyzer = TemporalPatternAnalyzer(table=None, confidence_threshold=0.3)

        # Saturday and Sunday usage only (Jan 20, 2024 is a Saturday)
        saturday = datetime(2024, 1, 20, 14, 0, 0, tzinfo=timezone.utc)
        sunday = datetime(2024, 1, 21, 14, 0, 0, tzinfo=timezone.utc)
        history = [
            {"device_id": "smart_tv", "timestamp": saturday.isoformat()},
            {"device_id": "smart_tv", "timestamp": sunday.isoformat()},
        ]

        result = analyzer.detect_patterns(history)

        weekly_patterns = [p for p in result if p.pattern_type == "weekly"]
        tv_weekly = next(
            (p for p in weekly_patterns if "smart_tv" in p.devices_involved),
            None,
        )
        assert tv_weekly is not None
        # All usage on weekends: weekday_ratio = 0.0, expected = 0.714
        # skew = 0.714, confidence = min(0.714 * 3, 1.0) = 1.0
        assert tv_weekly.confidence == 1.0
        assert tv_weekly.schedule["dominant_period"] == "weekends"

    def test_invalid_timestamps_are_skipped(self):
        """Records with invalid timestamps should be gracefully skipped."""
        history = [
            {"device_id": "sensor_a", "timestamp": "not-a-date"},
            {"device_id": "sensor_b", "timestamp": ""},
            {"device_id": "sensor_c"},  # missing timestamp
            {"device_id": "", "timestamp": "2024-01-15T08:00:00+00:00"},  # empty device_id
        ]

        result = self.analyzer.detect_patterns(history)
        assert result == []

    def test_query_history_returns_empty_without_table(self):
        """query_history should return empty list when no DynamoDB table is configured."""
        analyzer = TemporalPatternAnalyzer(table=None)
        result = analyzer.query_history()
        assert result == []

    def test_confidence_scores_bounded_zero_to_one(self):
        """All pattern confidence scores should be between 0.0 and 1.0."""
        # Use zero threshold to see all patterns
        analyzer = TemporalPatternAnalyzer(table=None, confidence_threshold=0.0)

        base = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        history = []
        for day_offset in range(7):
            for hour_offset in range(3):
                history.append({
                    "device_id": f"device_{hour_offset}",
                    "timestamp": (base + timedelta(days=day_offset, hours=hour_offset)).isoformat(),
                })

        result = analyzer.detect_patterns(history)

        assert len(result) > 0
        for pattern in result:
            assert 0.0 <= pattern.confidence <= 1.0

    def test_pattern_ids_are_unique(self):
        """Each detected pattern should have a unique pattern_id."""
        analyzer = TemporalPatternAnalyzer(table=None, confidence_threshold=0.0)

        base = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        history = []
        for day_offset in range(5):
            history.append({
                "device_id": "living_room_ac",
                "timestamp": (base + timedelta(days=day_offset)).isoformat(),
            })
            history.append({
                "device_id": "smart_geyser",
                "timestamp": (base + timedelta(days=day_offset, hours=2)).isoformat(),
            })

        result = analyzer.detect_patterns(history)

        pattern_ids = [p.pattern_id for p in result]
        assert len(pattern_ids) == len(set(pattern_ids))
