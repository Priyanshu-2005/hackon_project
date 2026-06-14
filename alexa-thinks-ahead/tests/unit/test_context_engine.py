"""Unit tests for the ContextEngine orchestrator.

Tests:
- build_snapshot returns a complete ContextSnapshot with all expected fields
- Caching: second call within TTL returns the same snapshot
- force_refresh bypasses cache
- Resource level calculation from device states
- Environmental context generation
- Confidence calculation
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.context.engine import ContextEngine
from src.models.context import ContextSnapshot, FamilyActivity, TemporalPattern
from src.models.device import DeviceCategory, DeviceState
from src.models.family import SHARMA_FAMILY


def _make_device_state(
    device_id: str,
    device_type: str = "sensor",
    category: DeviceCategory = DeviceCategory.CLIMATE,
    properties: dict = None,
    battery_level: float = None,
) -> DeviceState:
    """Create a sample DeviceState for testing."""
    return DeviceState(
        device_id=device_id,
        device_type=device_type,
        category=category,
        status="online",
        properties=properties or {"temperature": 25.0},
        last_updated=datetime.now(timezone.utc),
        battery_level=battery_level,
    )


def _make_mock_adapter(device_id: str, state: DeviceState = None) -> MagicMock:
    """Create a mock DeviceAdapter that returns a DeviceState."""
    adapter = MagicMock()
    adapter.device_id = device_id
    adapter.get_state.return_value = state or _make_device_state(device_id)
    return adapter


@pytest.fixture
def dynamo_table():
    """Create a moto-mocked DynamoDB table for device states."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
        table = dynamodb.create_table(
            TableName="alexa-thinks-ahead-device-states",
            KeySchema=[
                {"AttributeName": "device_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "device_id", "AttributeType": "S"},
                {"AttributeName": "timestamp", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(
            TableName="alexa-thinks-ahead-device-states"
        )
        yield table


@pytest.fixture
def sample_adapters():
    """Create a set of mock adapters simulating 10 devices."""
    devices = {
        "living_room_ac": _make_device_state(
            "living_room_ac", "ac", DeviceCategory.CLIMATE,
            {"temperature": 24, "mode": "cool"},
        ),
        "smart_lights": _make_device_state(
            "smart_lights", "lights", DeviceCategory.LIGHTING,
            {"brightness": 80, "color": "warm"},
        ),
        "security_camera": _make_device_state(
            "security_camera", "camera", DeviceCategory.SECURITY,
            {"recording": True},
        ),
        "smart_lock": _make_device_state(
            "smart_lock", "lock", DeviceCategory.SECURITY,
            {"locked": True},
            battery_level=85.0,
        ),
        "kitchen_hub": _make_device_state(
            "kitchen_hub", "hub", DeviceCategory.KITCHEN,
            {"active_appliance": "none"},
        ),
        "water_purifier": _make_device_state(
            "water_purifier", "purifier", DeviceCategory.UTILITY,
            {"filter_life_pct": 72},
        ),
        "smart_geyser": _make_device_state(
            "smart_geyser", "geyser", DeviceCategory.UTILITY,
            {"water_temp": 45, "heating": False},
        ),
        "inverter_ups": _make_device_state(
            "inverter_ups", "ups", DeviceCategory.POWER,
            {"battery_level": 95, "load_watts": 200},
        ),
        "smart_tv": _make_device_state(
            "smart_tv", "tv", DeviceCategory.ENTERTAINMENT,
            {"power": "off"},
        ),
        "echo_devices": _make_device_state(
            "echo_devices", "echo", DeviceCategory.ASSISTANT,
            {"listening": True},
        ),
    }
    adapters = {}
    for device_id, state in devices.items():
        adapters[device_id] = _make_mock_adapter(device_id, state)
    return adapters


class TestBuildSnapshot:
    """Tests for ContextEngine.build_snapshot()."""

    def test_returns_complete_context_snapshot(self, dynamo_table, sample_adapters):
        """build_snapshot() returns a ContextSnapshot with all expected fields."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot = engine.build_snapshot()

        assert isinstance(snapshot, ContextSnapshot)
        assert snapshot.snapshot_id is not None
        assert snapshot.timestamp is not None
        assert isinstance(snapshot.device_states, dict)
        assert isinstance(snapshot.active_activities, list)
        assert isinstance(snapshot.detected_patterns, list)
        assert isinstance(snapshot.resource_levels, dict)
        assert isinstance(snapshot.environmental, dict)
        assert isinstance(snapshot.confidence, float)

    def test_snapshot_contains_all_device_states(self, dynamo_table, sample_adapters):
        """Snapshot includes state for all 10 devices."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot = engine.build_snapshot()

        assert len(snapshot.device_states) == 10
        assert "living_room_ac" in snapshot.device_states
        assert "smart_lock" in snapshot.device_states
        assert "inverter_ups" in snapshot.device_states
        assert "water_purifier" in snapshot.device_states

    def test_snapshot_contains_resource_levels(self, dynamo_table, sample_adapters):
        """Snapshot includes resource levels extracted from device states."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot = engine.build_snapshot()

        # inverter_ups has battery_level=95 in properties
        assert "inverter_battery" in snapshot.resource_levels
        assert snapshot.resource_levels["inverter_battery"] == 0.95

        # water_purifier has filter_life_pct=72
        assert "water_filter" in snapshot.resource_levels
        assert snapshot.resource_levels["water_filter"] == 0.72

        # smart_lock has battery_level=85.0
        assert "lock_battery" in snapshot.resource_levels
        assert snapshot.resource_levels["lock_battery"] == 0.85

    def test_snapshot_contains_environmental_context(self, dynamo_table, sample_adapters):
        """Snapshot includes environmental context with expected keys."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot = engine.build_snapshot()

        assert "season" in snapshot.environmental
        assert "time_of_day" in snapshot.environmental
        assert "hour" in snapshot.environmental
        assert "is_weekend" in snapshot.environmental
        assert snapshot.environmental["season"] in [
            "summer", "monsoon", "autumn", "winter"
        ]
        assert snapshot.environmental["time_of_day"] in [
            "morning", "afternoon", "evening", "night"
        ]

    def test_snapshot_confidence_is_valid(self, dynamo_table, sample_adapters):
        """Snapshot confidence is between 0.0 and 1.0."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot = engine.build_snapshot()

        assert 0.0 <= snapshot.confidence <= 1.0


class TestContextCache:
    """Tests for context caching behavior."""

    def test_second_call_within_ttl_returns_same_snapshot(
        self, dynamo_table, sample_adapters
    ):
        """Second call to build_snapshot() within TTL returns cached snapshot."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot1 = engine.build_snapshot()
        snapshot2 = engine.build_snapshot()

        # Same object returned from cache
        assert snapshot1 is snapshot2
        assert snapshot1.snapshot_id == snapshot2.snapshot_id

    def test_force_refresh_bypasses_cache(self, dynamo_table, sample_adapters):
        """force_refresh=True builds a fresh snapshot even if cache is valid."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot1 = engine.build_snapshot()
        snapshot2 = engine.build_snapshot(force_refresh=True)

        # Different snapshot IDs (new UUID generated)
        assert snapshot1.snapshot_id != snapshot2.snapshot_id

    def test_cache_expires_after_ttl(self, dynamo_table, sample_adapters):
        """After TTL expires, a new snapshot is built."""
        engine = ContextEngine(
            adapters=sample_adapters,
            table=dynamo_table,
            family_profile=SHARMA_FAMILY,
        )

        snapshot1 = engine.build_snapshot()

        # Simulate cache expiry by backdating the cache timestamp
        engine._cache_timestamp = datetime.now(timezone.utc) - timedelta(seconds=60)

        snapshot2 = engine.build_snapshot()

        # Different snapshot - cache was expired
        assert snapshot1.snapshot_id != snapshot2.snapshot_id


class TestResourceLevels:
    """Tests for resource level calculation."""

    def test_empty_device_states_returns_empty_resources(self, dynamo_table):
        """No devices returns empty resource dict."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        resources = engine._calculate_resource_levels({})
        assert resources == {}

    def test_inverter_battery_normalized(self, dynamo_table):
        """Inverter battery is normalized to 0-1 range."""
        device_states = {
            "inverter_ups": _make_device_state(
                "inverter_ups", "ups", DeviceCategory.POWER,
                {"battery_level": 50},
            )
        }
        engine = ContextEngine(adapters={}, table=dynamo_table)
        resources = engine._calculate_resource_levels(device_states)
        assert resources["inverter_battery"] == 0.5


class TestEnvironmentalContext:
    """Tests for environmental context generation."""

    def test_time_of_day_morning(self, dynamo_table):
        """Hours 5-11 return 'morning'."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        assert engine._get_time_of_day(5) == "morning"
        assert engine._get_time_of_day(11) == "morning"

    def test_time_of_day_afternoon(self, dynamo_table):
        """Hours 12-16 return 'afternoon'."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        assert engine._get_time_of_day(12) == "afternoon"
        assert engine._get_time_of_day(16) == "afternoon"

    def test_time_of_day_evening(self, dynamo_table):
        """Hours 17-20 return 'evening'."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        assert engine._get_time_of_day(17) == "evening"
        assert engine._get_time_of_day(20) == "evening"

    def test_time_of_day_night(self, dynamo_table):
        """Hours 21-4 return 'night'."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        assert engine._get_time_of_day(0) == "night"
        assert engine._get_time_of_day(4) == "night"
        assert engine._get_time_of_day(21) == "night"
        assert engine._get_time_of_day(23) == "night"


class TestConfidenceCalculation:
    """Tests for confidence calculation."""

    def test_empty_fused_returns_zero(self, dynamo_table):
        """No fused data returns 0.0 confidence."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        assert engine._calculate_confidence({}, []) == 0.0

    def test_fresh_data_high_confidence(self, dynamo_table):
        """Fresh data (weight ~1.0) gives high confidence."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        fused = {
            "device_1": {"weight": 1.0},
            "device_2": {"weight": 0.9},
        }
        confidence = engine._calculate_confidence(fused, [])
        assert confidence >= 0.9

    def test_patterns_add_bonus(self, dynamo_table):
        """Detected patterns add up to 0.2 bonus to confidence."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        fused = {"device_1": {"weight": 0.7}}
        patterns = [MagicMock() for _ in range(4)]  # 4 patterns = 0.2 bonus
        confidence = engine._calculate_confidence(fused, patterns)
        assert confidence == 0.9  # 0.7 + 0.2

    def test_confidence_capped_at_one(self, dynamo_table):
        """Confidence never exceeds 1.0."""
        engine = ContextEngine(adapters={}, table=dynamo_table)
        fused = {"device_1": {"weight": 0.95}}
        patterns = [MagicMock() for _ in range(10)]  # Would be 0.5 bonus
        confidence = engine._calculate_confidence(fused, patterns)
        assert confidence == 1.0
