"""Context engine orchestrator - builds unified context from device telemetry and patterns.

Orchestrates all context components in sequence:
1. Sensor fusion (temporal weighting)
2. Temporal pattern detection
3. Family routine modeling
4. Conflict resolution
5. Context snapshot assembly

Requirement 2.3: ContextSnapshot containing all 10 device states, activities, patterns, resource levels.
Requirement 2.5: Detect patterns and include in snapshot.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.context.conflicts import ConflictResolver
from src.context.fusion import SensorFusion
from src.context.ingestion import SensorIngestionPipeline
from src.context.patterns import TemporalPatternAnalyzer
from src.context.routines import FamilyRoutineModeler
from src.models.context import ContextSnapshot, FamilyActivity, TemporalPattern
from src.models.device import DeviceState
from src.models.family import SHARMA_FAMILY, FamilyProfile
from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.time_utils import get_current_season, get_current_timestamp

logger = get_logger(__name__)


class ContextEngine:
    """Builds unified context from device telemetry and patterns.

    Orchestrates all context components:
    1. Sensor fusion (temporal weighting)
    2. Temporal pattern detection
    3. Family routine modeling
    4. Conflict resolution
    5. Context snapshot assembly
    """

    def __init__(
        self,
        adapters: Dict[str, Any],
        table=None,
        family_profile: Optional[FamilyProfile] = None,
    ):
        """Initialize the context engine with all sub-components.

        Args:
            adapters: Mapping of device_id to DeviceAdapter instances.
            table: DynamoDB Table resource for state storage and history queries.
            family_profile: Family profile for routine modeling. Defaults to SHARMA_FAMILY.
        """
        config = get_config()
        self._adapters = adapters
        self._table = table

        # Initialize sub-components
        self._fusion = SensorFusion()
        self._patterns = TemporalPatternAnalyzer(table=table)
        self._routines = FamilyRoutineModeler(family_profile or SHARMA_FAMILY)
        self._conflicts = ConflictResolver()
        self._ingestion = SensorIngestionPipeline(adapters=adapters, table=table)

        # Context cache
        self._cached_snapshot: Optional[ContextSnapshot] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds: int = config.sensor_poll_interval_seconds

    def build_snapshot(self, force_refresh: bool = False) -> ContextSnapshot:
        """Build a complete context snapshot.

        Uses cached snapshot if within TTL, otherwise builds fresh.

        Args:
            force_refresh: If True, bypasses cache and builds a fresh snapshot.

        Returns:
            ContextSnapshot with all device states, activities, patterns, resources.
        """
        now = get_current_timestamp()

        # Return cache if still valid
        if not force_refresh and self._is_cache_valid(now):
            logger.debug("Returning cached context snapshot")
            return self._cached_snapshot

        # 1. Collect device states via ingestion pipeline
        device_states = self._ingestion.collect_all()

        # 2. Fuse with temporal weighting
        fused = self._fusion.fuse(device_states)

        # 3. Detect patterns from history
        history = self._patterns.query_history()
        patterns = self._patterns.detect_patterns(history)

        # 4. Get active activities from family routines
        activities = self._routines.get_active_activities(now)

        # 5. Resolve conflicts between overlapping activities
        resolved_activities = self._conflicts.resolve_activity_conflicts(activities)

        # 6. Calculate resource levels from device states
        resource_levels = self._calculate_resource_levels(device_states)

        # 7. Build environmental context
        environmental = self._build_environmental_context(now)

        # 8. Calculate overall confidence
        confidence = self._calculate_confidence(fused, patterns)

        # Assemble snapshot
        snapshot = ContextSnapshot(
            snapshot_id=str(uuid4()),
            timestamp=now,
            device_states=device_states,
            active_activities=resolved_activities,
            detected_patterns=patterns,
            resource_levels=resource_levels,
            environmental=environmental,
            confidence=confidence,
        )

        # Update cache
        self._cached_snapshot = snapshot
        self._cache_timestamp = now

        logger.info(
            f"Built context snapshot {snapshot.snapshot_id}: "
            f"{len(device_states)} devices, {len(resolved_activities)} activities, "
            f"{len(patterns)} patterns, confidence={confidence:.3f}"
        )

        return snapshot

    def get_active_activities(self) -> List[FamilyActivity]:
        """Shortcut to get current active activities from the routine modeler."""
        return self._routines.get_active_activities()

    def get_resource_levels(
        self, device_states: Optional[Dict[str, DeviceState]] = None
    ) -> Dict[str, float]:
        """Get current resource levels.

        Args:
            device_states: Pre-collected device states. If None, collects fresh.

        Returns:
            Dict of resource name to level (0.0 to 1.0).
        """
        if device_states is None:
            device_states = self._ingestion.collect_all()
        return self._calculate_resource_levels(device_states)

    def _is_cache_valid(self, now: datetime) -> bool:
        """Check if the cached snapshot is still within TTL.

        Args:
            now: Current timestamp to compare against cache time.

        Returns:
            True if cache exists and is within TTL.
        """
        if self._cached_snapshot is None or self._cache_timestamp is None:
            return False
        age = (now - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl_seconds

    def _calculate_resource_levels(
        self, device_states: Dict[str, DeviceState]
    ) -> Dict[str, float]:
        """Extract resource levels from device states.

        Normalizes resource values to 0.0-1.0 range.

        Args:
            device_states: Current device states.

        Returns:
            Dict of resource name to normalized level.
        """
        resources: Dict[str, float] = {}

        # Battery from inverter/UPS
        inverter = device_states.get("inverter_ups")
        if inverter:
            battery = inverter.properties.get("battery_level", 0)
            resources["inverter_battery"] = battery / 100.0

        # Water purifier filter life
        purifier = device_states.get("water_purifier")
        if purifier:
            filter_life = purifier.properties.get("filter_life_pct", 0)
            resources["water_filter"] = filter_life / 100.0

        # Smart lock battery
        lock = device_states.get("smart_lock")
        if lock and lock.battery_level is not None:
            resources["lock_battery"] = lock.battery_level / 100.0

        return resources

    def _build_environmental_context(self, now: datetime) -> Dict[str, Any]:
        """Build environmental context from current time.

        Args:
            now: Current timestamp.

        Returns:
            Dict with season, time_of_day, hour, is_weekend.
        """
        return {
            "season": get_current_season(),
            "time_of_day": self._get_time_of_day(now.hour),
            "hour": now.hour,
            "is_weekend": now.weekday() >= 5,
        }

    def _get_time_of_day(self, hour: int) -> str:
        """Categorize hour into time-of-day period.

        Args:
            hour: Hour of the day (0-23).

        Returns:
            One of "morning", "afternoon", "evening", "night".
        """
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _calculate_confidence(
        self, fused: Dict[str, Dict[str, Any]], patterns: List[TemporalPattern]
    ) -> float:
        """Calculate overall context confidence based on data freshness and patterns.

        Confidence is derived from average temporal weight of fused devices
        plus a bonus for detected patterns (more patterns = richer context).

        Args:
            fused: Dict of fused device data with 'weight' fields.
            patterns: List of detected temporal patterns.

        Returns:
            Confidence score in [0.0, 1.0].
        """
        if not fused:
            return 0.0

        # Average weight of all fused devices
        weights = [v["weight"] for v in fused.values()]
        avg_weight = sum(weights) / len(weights)

        # Pattern confidence bonus (more patterns = more context)
        pattern_bonus = min(len(patterns) * 0.05, 0.2)

        confidence = min(avg_weight + pattern_bonus, 1.0)
        return round(confidence, 3)
