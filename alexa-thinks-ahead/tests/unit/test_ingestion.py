"""Unit tests for the SensorIngestionPipeline.

Tests:
- collect_all() returns states for all reachable devices
- A failing device doesn't prevent other devices from being collected
- States are stored in DynamoDB correctly
- collect_single() for a specific device
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.context.ingestion import SensorIngestionPipeline
from src.devices.base import DeviceAdapter
from src.models.device import DeviceCategory, DeviceState


def _make_device_state(device_id: str, device_type: str = "sensor") -> DeviceState:
    """Create a sample DeviceState for testing."""
    return DeviceState(
        device_id=device_id,
        device_type=device_type,
        category=DeviceCategory.CLIMATE,
        status="online",
        properties={"temperature": 25.0, "humidity": 60.0},
        last_updated=datetime.now(timezone.utc),
    )


def _make_mock_adapter(device_id: str, should_fail: bool = False) -> MagicMock:
    """Create a mock DeviceAdapter that returns a DeviceState or raises."""
    adapter = MagicMock(spec=DeviceAdapter)
    adapter.device_id = device_id
    if should_fail:
        adapter.get_state.side_effect = ConnectionError(
            f"Device {device_id} unreachable"
        )
    else:
        adapter.get_state.return_value = _make_device_state(device_id)
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


class TestCollectAll:
    """Tests for SensorIngestionPipeline.collect_all()."""

    def test_returns_states_for_all_reachable_devices(self, dynamo_table):
        """collect_all() returns states for all reachable devices."""
        adapters = {
            "living_room_ac": _make_mock_adapter("living_room_ac"),
            "smart_lights": _make_mock_adapter("smart_lights"),
            "security_camera": _make_mock_adapter("security_camera"),
        }

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        result = pipeline.collect_all()

        assert len(result) == 3
        assert "living_room_ac" in result
        assert "smart_lights" in result
        assert "security_camera" in result
        for device_id, state in result.items():
            assert isinstance(state, DeviceState)
            assert state.device_id == device_id

    def test_failing_device_does_not_block_others(self, dynamo_table):
        """A failing device doesn't prevent other devices from being collected."""
        adapters = {
            "living_room_ac": _make_mock_adapter("living_room_ac"),
            "smart_lights": _make_mock_adapter("smart_lights", should_fail=True),
            "security_camera": _make_mock_adapter("security_camera"),
        }

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        result = pipeline.collect_all()

        # Two devices should succeed
        assert len(result) == 2
        assert "living_room_ac" in result
        assert "security_camera" in result
        assert "smart_lights" not in result

        # The failing device should be marked stale
        stale = pipeline.get_stale_devices()
        assert "smart_lights" in stale

    def test_stores_states_in_dynamodb(self, dynamo_table):
        """States are stored in DynamoDB with device_id + timestamp keys."""
        adapters = {
            "living_room_ac": _make_mock_adapter("living_room_ac"),
        }

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        pipeline.collect_all()

        # Query DynamoDB for stored items
        response = dynamo_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("device_id").eq(
                "living_room_ac"
            )
        )
        items = response["Items"]
        assert len(items) == 1

        item = items[0]
        assert item["device_id"] == "living_room_ac"
        assert "timestamp" in item
        assert item["status"] == "online"
        assert item["category"] == "climate"
        assert "properties" in item
        assert "ttl" in item

    def test_stale_device_recovers_on_success(self, dynamo_table):
        """A previously stale device is cleared when it reports successfully."""
        adapter = _make_mock_adapter("smart_lights", should_fail=True)
        adapters = {"smart_lights": adapter}

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)

        # First collection fails
        pipeline.collect_all()
        assert "smart_lights" in pipeline.get_stale_devices()

        # Fix the adapter
        adapter.get_state.side_effect = None
        adapter.get_state.return_value = _make_device_state("smart_lights")

        # Second collection succeeds
        result = pipeline.collect_all()
        assert "smart_lights" in result
        assert "smart_lights" not in pipeline.get_stale_devices()


class TestCollectSingle:
    """Tests for SensorIngestionPipeline.collect_single()."""

    def test_collect_single_returns_state(self, dynamo_table):
        """collect_single() returns the DeviceState for a specific device."""
        adapters = {
            "living_room_ac": _make_mock_adapter("living_room_ac"),
            "smart_lights": _make_mock_adapter("smart_lights"),
        }

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        result = pipeline.collect_single("living_room_ac")

        assert result is not None
        assert isinstance(result, DeviceState)
        assert result.device_id == "living_room_ac"

    def test_collect_single_stores_in_dynamodb(self, dynamo_table):
        """collect_single() stores the state in DynamoDB."""
        adapters = {
            "living_room_ac": _make_mock_adapter("living_room_ac"),
        }

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        pipeline.collect_single("living_room_ac")

        response = dynamo_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("device_id").eq(
                "living_room_ac"
            )
        )
        assert len(response["Items"]) == 1

    def test_collect_single_unknown_device_returns_none(self, dynamo_table):
        """collect_single() returns None for an unknown device_id."""
        adapters = {"living_room_ac": _make_mock_adapter("living_room_ac")}

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        result = pipeline.collect_single("nonexistent_device")

        assert result is None

    def test_collect_single_failing_device_returns_none(self, dynamo_table):
        """collect_single() returns None and marks device stale on failure."""
        adapters = {
            "smart_lights": _make_mock_adapter("smart_lights", should_fail=True),
        }

        pipeline = SensorIngestionPipeline(adapters=adapters, table=dynamo_table)
        result = pipeline.collect_single("smart_lights")

        assert result is None
        assert "smart_lights" in pipeline.get_stale_devices()
