"""Property-based tests for context snapshot completeness.

Property 8: Context Snapshot Completeness - For any context snapshot built from
the device registry (regardless of individual device online/offline status), the
snapshot SHALL contain state entries for all devices that successfully report.

**Validates: Requirements 2.3, 12.2**

Uses hypothesis to generate random combinations of online/offline devices and verify:
1. The number of device states in the snapshot matches the number of reachable devices
2. All reachable devices appear in the snapshot
3. Unreachable devices are NOT in the snapshot (they couldn't report)
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis.strategies import booleans, lists
from moto import mock_aws

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.context.ingestion import SensorIngestionPipeline
from src.devices.base import DeviceAdapter
from src.models.device import DeviceCategory, DeviceState

DEVICE_IDS = [
    "living_room_ac",
    "smart_lights",
    "security_camera",
    "smart_lock",
    "kitchen_hub",
    "water_purifier",
    "smart_geyser",
    "inverter_ups",
    "smart_tv",
    "echo_devices",
]

DEVICE_CATEGORIES = [
    DeviceCategory.CLIMATE,
    DeviceCategory.LIGHTING,
    DeviceCategory.SECURITY,
    DeviceCategory.SECURITY,
    DeviceCategory.KITCHEN,
    DeviceCategory.UTILITY,
    DeviceCategory.UTILITY,
    DeviceCategory.POWER,
    DeviceCategory.ENTERTAINMENT,
    DeviceCategory.ASSISTANT,
]


def _make_device_state(device_id: str, category: DeviceCategory) -> DeviceState:
    """Create a valid DeviceState for a given device."""
    return DeviceState(
        device_id=device_id,
        device_type=device_id.replace("_", " "),
        category=category,
        status="online",
        properties={"active": True},
        last_updated=datetime.now(timezone.utc),
    )


def _make_mock_adapter(
    device_id: str, category: DeviceCategory, reachable: bool
) -> MagicMock:
    """Create a mock DeviceAdapter that either returns state or raises.

    Args:
        device_id: The device identifier.
        category: The device category.
        reachable: If True, get_state() returns a valid DeviceState.
                   If False, get_state() raises ConnectionError.
    """
    adapter = MagicMock(spec=DeviceAdapter)
    adapter.device_id = device_id
    if reachable:
        adapter.get_state.return_value = _make_device_state(device_id, category)
    else:
        adapter.get_state.side_effect = ConnectionError(
            f"Device {device_id} unreachable"
        )
    return adapter


class TestSnapshotCompleteness:
    """Property 8: Context Snapshot Completeness.

    For any context snapshot built from the device registry (regardless of
    individual device online/offline status), the snapshot SHALL contain state
    entries for all devices that successfully report.

    **Validates: Requirements 2.3, 12.2**
    """

    @given(
        reachability=lists(booleans(), min_size=10, max_size=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_snapshot_contains_exactly_reachable_devices(self, reachability):
        """Property 8: Snapshot contains state entries for all reporting devices.

        For any random combination of online/offline devices:
        1. The number of device states matches the number of reachable devices
        2. All reachable devices appear in the snapshot
        3. Unreachable devices are NOT in the snapshot
        """
        with mock_aws():
            # Create DynamoDB table
            dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
            table = dynamodb.create_table(
                TableName="test-device-states",
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

            # Build adapters based on random reachability booleans
            adapters = {}
            expected_reachable = set()
            expected_unreachable = set()

            for i, (device_id, reachable) in enumerate(
                zip(DEVICE_IDS, reachability)
            ):
                category = DEVICE_CATEGORIES[i]
                adapters[device_id] = _make_mock_adapter(
                    device_id, category, reachable
                )
                if reachable:
                    expected_reachable.add(device_id)
                else:
                    expected_unreachable.add(device_id)

            # Run the ingestion pipeline (which is what builds the snapshot's device_states)
            pipeline = SensorIngestionPipeline(adapters=adapters, table=table)
            collected = pipeline.collect_all()

            # Property 1: Count matches reachable count
            assert len(collected) == len(expected_reachable), (
                f"Expected {len(expected_reachable)} device states, "
                f"got {len(collected)}. "
                f"Reachability: {dict(zip(DEVICE_IDS, reachability))}"
            )

            # Property 2: All reachable devices appear in the snapshot
            for device_id in expected_reachable:
                assert device_id in collected, (
                    f"Reachable device '{device_id}' missing from snapshot. "
                    f"Collected: {list(collected.keys())}"
                )

            # Property 3: Unreachable devices are NOT in the snapshot
            for device_id in expected_unreachable:
                assert device_id not in collected, (
                    f"Unreachable device '{device_id}' should NOT be in snapshot. "
                    f"Collected: {list(collected.keys())}"
                )

    @given(
        reachability=lists(booleans(), min_size=10, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_all_devices_reachable_gives_full_snapshot(self, reachability):
        """When all devices are reachable, snapshot has exactly 10 device states.

        This is a special case verifying Requirement 2.3: snapshot contains
        device_states for all 10 devices when all are reporting.
        """
        # Force all reachable for this specific test
        all_reachable = [True] * 10

        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
            table = dynamodb.create_table(
                TableName="test-device-states-full",
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

            adapters = {}
            for i, device_id in enumerate(DEVICE_IDS):
                category = DEVICE_CATEGORIES[i]
                adapters[device_id] = _make_mock_adapter(
                    device_id, category, True
                )

            pipeline = SensorIngestionPipeline(adapters=adapters, table=table)
            collected = pipeline.collect_all()

            # All 10 devices must be present
            assert len(collected) == 10, (
                f"Expected 10 device states for all-reachable, got {len(collected)}"
            )
            for device_id in DEVICE_IDS:
                assert device_id in collected, (
                    f"Device '{device_id}' missing from full snapshot"
                )

    @given(
        reachability=lists(booleans(), min_size=10, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_stale_devices_tracked_correctly(self, reachability):
        """Unreachable devices are tracked as stale by the pipeline.

        Requirement 12.2: Continue operating with remaining devices.
        The pipeline must track which devices failed so the system knows
        which ones are unavailable.
        """
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
            table = dynamodb.create_table(
                TableName="test-device-states-stale",
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

            adapters = {}
            expected_unreachable = set()

            for i, (device_id, reachable) in enumerate(
                zip(DEVICE_IDS, reachability)
            ):
                category = DEVICE_CATEGORIES[i]
                adapters[device_id] = _make_mock_adapter(
                    device_id, category, reachable
                )
                if not reachable:
                    expected_unreachable.add(device_id)

            pipeline = SensorIngestionPipeline(adapters=adapters, table=table)
            pipeline.collect_all()

            stale_devices = pipeline.get_stale_devices()

            # All unreachable devices should be marked stale
            for device_id in expected_unreachable:
                assert device_id in stale_devices, (
                    f"Unreachable device '{device_id}' not tracked as stale"
                )

            # Reachable devices should NOT be marked stale
            for device_id in DEVICE_IDS:
                if device_id not in expected_unreachable:
                    assert device_id not in stale_devices, (
                        f"Reachable device '{device_id}' incorrectly marked stale"
                    )
