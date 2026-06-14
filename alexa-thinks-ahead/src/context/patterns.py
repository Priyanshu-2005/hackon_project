"""Temporal pattern analyzer for detecting recurring device usage patterns.

Detects daily and weekly patterns from device state history stored in DynamoDB.
Assigns confidence scores based on consistency of occurrences.
Only patterns meeting the confidence threshold (default 0.75) are included in snapshots.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.models.context import TemporalPattern
from src.utils.config import get_config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TemporalPatternAnalyzer:
    """Analyzes device usage history to detect recurring temporal patterns.

    Detects daily and weekly patterns from device state history.
    Assigns confidence scores based on consistency of occurrences.
    """

    def __init__(self, table=None, confidence_threshold: float = None):
        """Initialize the pattern analyzer.

        Args:
            table: DynamoDB Table resource for querying history.
            confidence_threshold: Minimum confidence to include a pattern.
                Defaults to config.pattern_confidence_threshold (0.75).
        """
        config = get_config()
        self.table = table
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else config.pattern_confidence_threshold
        )
        self.history_hours = config.context_history_hours

    def detect_patterns(self, history: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Detect all patterns from device usage history.

        Args:
            history: List of device state records with device_id, timestamp, properties.

        Returns:
            List of TemporalPattern objects that meet the confidence threshold.
        """
        daily_patterns = self._detect_daily_patterns(history)
        weekly_patterns = self._detect_weekly_patterns(history)

        all_patterns = daily_patterns + weekly_patterns

        # Filter by confidence threshold
        filtered = [p for p in all_patterns if p.confidence >= self.confidence_threshold]

        logger.info(
            f"Detected {len(all_patterns)} total patterns, "
            f"{len(filtered)} above threshold {self.confidence_threshold}"
        )

        return filtered

    def _detect_daily_patterns(self, history: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Detect daily recurring patterns.

        Groups events by device_id and hour-of-day.
        If a device is consistently used at the same hour over multiple days,
        that's a daily pattern. Confidence = days_used_at_hour / total_days.
        """
        # Group by device_id and hour
        hourly_usage: Dict[str, Dict[int, set]] = {}  # device_id -> {hour -> set of dates}
        total_days: set = set()

        for record in history:
            device_id = record.get("device_id", "")
            ts_str = record.get("timestamp", "")

            if not device_id or not ts_str:
                continue

            try:
                ts = datetime.fromisoformat(ts_str) if isinstance(ts_str, str) else ts_str
                hour = ts.hour
                day = ts.date()
                total_days.add(day)
            except (ValueError, AttributeError, TypeError):
                continue

            if device_id not in hourly_usage:
                hourly_usage[device_id] = {}
            if hour not in hourly_usage[device_id]:
                hourly_usage[device_id][hour] = set()
            hourly_usage[device_id][hour].add(day)

        patterns = []
        num_days = max(len(total_days), 1)

        for device_id, hours in hourly_usage.items():
            for hour, days_used in hours.items():
                # Confidence: how consistently this device is used at this hour
                confidence = len(days_used) / num_days
                confidence = min(confidence, 1.0)

                if confidence > 0:
                    pattern = TemporalPattern(
                        pattern_id=f"daily_{device_id}_{hour:02d}",
                        pattern_type="daily",
                        confidence=confidence,
                        devices_involved=[device_id],
                        schedule={"hour": hour, "frequency": "daily"},
                        last_observed=datetime.now(timezone.utc),
                    )
                    patterns.append(pattern)

        return patterns

    def _detect_weekly_patterns(self, history: List[Dict[str, Any]]) -> List[TemporalPattern]:
        """Detect weekly patterns (weekday vs weekend differences).

        Identifies devices that show significantly different usage
        patterns between weekdays and weekends. Higher skew from the
        expected 5/7 weekday ratio indicates a stronger weekly pattern.
        """
        weekday_usage: Dict[str, int] = {}  # device_id -> count
        weekend_usage: Dict[str, int] = {}  # device_id -> count

        for record in history:
            device_id = record.get("device_id", "")
            ts_str = record.get("timestamp", "")

            if not device_id or not ts_str:
                continue

            try:
                ts = datetime.fromisoformat(ts_str) if isinstance(ts_str, str) else ts_str
                is_weekend = ts.weekday() >= 5  # Saturday=5, Sunday=6
            except (ValueError, AttributeError, TypeError):
                continue

            if is_weekend:
                weekend_usage[device_id] = weekend_usage.get(device_id, 0) + 1
            else:
                weekday_usage[device_id] = weekday_usage.get(device_id, 0) + 1

        patterns = []
        all_device_ids = set(list(weekday_usage.keys()) + list(weekend_usage.keys()))

        for device_id in all_device_ids:
            wd_count = weekday_usage.get(device_id, 0)
            we_count = weekend_usage.get(device_id, 0)
            total = wd_count + we_count

            if total == 0:
                continue

            # Expected ratio: 5/7 weekdays ≈ 0.714
            weekday_ratio = wd_count / total
            expected_ratio = 5.0 / 7.0

            # Skew from expected distribution
            skew = abs(weekday_ratio - expected_ratio)

            # Normalize skew to confidence: max possible skew is ~0.714
            # Scale so moderate skew gives meaningful confidence
            confidence = min(skew * 3.0, 1.0)

            if confidence > 0:
                dominant = "weekdays" if weekday_ratio > expected_ratio else "weekends"
                pattern = TemporalPattern(
                    pattern_id=f"weekly_{device_id}_{dominant}",
                    pattern_type="weekly",
                    confidence=confidence,
                    devices_involved=[device_id],
                    schedule={"dominant_period": dominant, "frequency": "weekly"},
                    last_observed=datetime.now(timezone.utc),
                )
                patterns.append(pattern)

        return patterns

    def query_history(self, hours: int = None) -> List[Dict[str, Any]]:
        """Query device state history from DynamoDB.

        Args:
            hours: Number of hours of history to query (default: 24 from config).

        Returns:
            List of device state records.
        """
        if self.table is None:
            logger.warning("No DynamoDB table configured, returning empty history")
            return []

        hours = hours or self.history_hours
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        since_str = since.isoformat()

        try:
            # Scan with filter (for hackathon simplicity; production would use GSI)
            response = self.table.scan(
                FilterExpression="attribute_exists(#ts) AND #ts >= :since",
                ExpressionAttributeNames={"#ts": "timestamp"},
                ExpressionAttributeValues={":since": since_str},
            )
            items = response.get("Items", [])
            logger.info(f"Queried {len(items)} history records from last {hours} hours")
            return items
        except Exception as e:
            logger.error(f"Failed to query history: {e}")
            return []
