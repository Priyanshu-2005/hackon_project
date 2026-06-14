"""Sensor ingestion pipeline for collecting device telemetry.

Requirement 2.1: Collect telemetry from all 10 devices at 30-second intervals
and store in DynamoDB.
Requirement 2.4: Mark device as stale when not reported within threshold.
Requirement 12.2: Continue operating with remaining devices when one fails.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

import boto3

from src.devices.base import DeviceAdapter
from src.models.device import DeviceState
from src.utils.config import get_config
from src.utils.dynamo_utils import calculate_ttl, serialize_for_dynamo
from src.utils.logging import get_logger
from src.utils.time_utils import format_iso, get_current_timestamp

logger = get_logger(__name__)


class SensorIngestionPipeline:
    """Collects device state from all adapters and stores in DynamoDB.

    Handles device failures gracefully by marking them stale and
    continuing with remaining devices (Requirement 12.2).
    """

    def __init__(
        self,
        adapters: Dict[str, DeviceAdapter],
        table,
    ):
        """Initialize the ingestion pipeline.

        Args:
            adapters: Mapping of device_id to DeviceAdapter instances.
            table: A boto3 DynamoDB Table resource for storing states.
        """
        self.adapters = adapters
        self.table = table
        self._config = get_config()
        self._stale_devices: Dict[str, datetime] = {}

    def collect_all(self) -> Dict[str, DeviceState]:
        """Collect state from all registered devices.

        Iterates all adapters, calling get_state() on each.
        On failure, marks the device as stale and continues with others.

        Returns:
            Dict mapping device_id to DeviceState for all successfully
            collected devices.
        """
        collected: Dict[str, DeviceState] = {}

        for device_id, adapter in self.adapters.items():
            try:
                state = adapter.get_state()
                collected[device_id] = state
                self._store_state(device_id, state)

                # Clear stale marker on successful collection
                if device_id in self._stale_devices:
                    del self._stale_devices[device_id]
                    logger.info(
                        f"Device {device_id} recovered from stale state"
                    )

            except Exception as e:
                self._mark_stale(device_id, e)

        logger.info(
            f"Collected state from {len(collected)}/{len(self.adapters)} devices"
        )
        return collected

    def collect_single(self, device_id: str) -> Optional[DeviceState]:
        """Collect state from a single device on demand.

        Args:
            device_id: The ID of the device to collect from.

        Returns:
            DeviceState if successful, None if device not found or failed.
        """
        adapter = self.adapters.get(device_id)
        if adapter is None:
            logger.warning(f"Device {device_id} not found in adapter registry")
            return None

        try:
            state = adapter.get_state()
            self._store_state(device_id, state)

            # Clear stale marker on successful collection
            if device_id in self._stale_devices:
                del self._stale_devices[device_id]

            return state
        except Exception as e:
            self._mark_stale(device_id, e)
            return None

    def get_stale_devices(self) -> Dict[str, datetime]:
        """Return dict of device_id -> timestamp when marked stale."""
        return dict(self._stale_devices)

    def _store_state(self, device_id: str, state: DeviceState) -> None:
        """Store a device state record in DynamoDB.

        Uses device_id as partition key and timestamp as sort key.
        """
        timestamp = format_iso(state.last_updated)
        ttl = calculate_ttl(self._config.device_state_ttl_days)

        item = {
            "device_id": device_id,
            "timestamp": timestamp,
            "device_type": state.device_type,
            "category": state.category.value,
            "status": state.status,
            "properties": state.properties,
            "ttl": ttl,
        }

        if state.battery_level is not None:
            item["battery_level"] = state.battery_level

        serialized = serialize_for_dynamo(item)
        self.table.put_item(Item=serialized)

    def _mark_stale(self, device_id: str, error: Exception) -> None:
        """Mark a device as stale due to collection failure.

        Requirement 2.4: Mark device as stale when not reported within threshold.
        """
        now = get_current_timestamp()
        self._stale_devices[device_id] = now
        logger.warning(
            f"Device {device_id} marked stale: {type(error).__name__}: {error}"
        )
