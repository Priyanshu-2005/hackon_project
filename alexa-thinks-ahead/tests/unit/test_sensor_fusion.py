"""Unit tests for the SensorFusion class.

Tests temporal weighting, staleness marking, and fused output structure.
"""

from datetime import datetime, timedelta, timezone

from src.context.fusion import SensorFusion
from src.models.device import DeviceCategory, DeviceState


def _make_device_state(device_id: str, age_seconds: float, **kwargs) -> DeviceState:
    """Helper to create a DeviceState with a specific age."""
    last_updated = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return DeviceState(
        device_id=device_id,
        device_type=kwargs.get("device_type", "climate"),
        category=kwargs.get("category", DeviceCategory.CLIMATE),
        status=kwargs.get("status", "online"),
        properties=kwargs.get("properties", {"temperature": 24}),
        last_updated=last_updated,
        battery_level=kwargs.get("battery_level", None),
    )


class TestSensorFusionFreshStates:
    """Test that fresh device states receive weight close to 1.0."""

    def test_fresh_state_weight_near_one(self):
        """A device updated just now should get weight ~1.0."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {"ac_1": _make_device_state("ac_1", age_seconds=0)}

        result = fusion.fuse(states)

        assert result["ac_1"]["weight"] >= 0.99

    def test_slightly_old_state_high_weight(self):
        """A device updated 5 minutes ago should still have high weight."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {"light_1": _make_device_state("light_1", age_seconds=300)}

        result = fusion.fuse(states)

        # 300/3600 = 0.083, so weight = 1.0 - 0.083 = ~0.917
        assert result["light_1"]["weight"] > 0.9


class TestSensorFusionStaleStates:
    """Test that stale device states (> 1 hour old) get minimum weight."""

    def test_two_hour_old_state_gets_minimum_weight(self):
        """A device not updated for 2 hours should get weight = 0.1."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {"cam_1": _make_device_state("cam_1", age_seconds=7200)}

        result = fusion.fuse(states)

        assert result["cam_1"]["weight"] == 0.1

    def test_exactly_one_hour_state_at_boundary(self):
        """A device exactly at staleness boundary gets weight = 0.1 (min floor)."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {"lock_1": _make_device_state("lock_1", age_seconds=3600)}

        result = fusion.fuse(states)

        # 3600/3600 = 1.0, weight = max(0.1, 1.0 - 1.0) = max(0.1, 0.0) = 0.1
        assert result["lock_1"]["weight"] == 0.1


class TestSensorFusionOutputContainsAllDevices:
    """Test that fused output contains all input devices."""

    def test_all_devices_present_in_output(self):
        """Every device in input should appear in fused output."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {
            "ac_1": _make_device_state("ac_1", age_seconds=10),
            "light_1": _make_device_state("light_1", age_seconds=600),
            "camera_1": _make_device_state("camera_1", age_seconds=1800),
            "lock_1": _make_device_state("lock_1", age_seconds=5000),
            "geyser_1": _make_device_state("geyser_1", age_seconds=100),
        }

        result = fusion.fuse(states)

        assert set(result.keys()) == set(states.keys())

    def test_empty_input_produces_empty_output(self):
        """An empty device dict should produce an empty fused output."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        result = fusion.fuse({})
        assert result == {}


class TestSensorFusionStaleFlag:
    """Test that the stale flag is correctly set for old timestamps."""

    def test_stale_flag_true_for_old_device(self):
        """A device older than max_staleness_seconds should be flagged stale."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {"old_device": _make_device_state("old_device", age_seconds=7200)}

        result = fusion.fuse(states)

        assert result["old_device"]["stale"] is True

    def test_stale_flag_false_for_fresh_device(self):
        """A recently updated device should not be flagged stale."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {"fresh_device": _make_device_state("fresh_device", age_seconds=60)}

        result = fusion.fuse(states)

        assert result["fresh_device"]["stale"] is False

    def test_stale_flag_false_just_below_threshold(self):
        """A device just below the staleness threshold should not be flagged stale."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        # Use 3500 seconds (well within threshold)
        states = {"edge_device": _make_device_state("edge_device", age_seconds=3500)}

        result = fusion.fuse(states)

        assert result["edge_device"]["stale"] is False


class TestSensorFusionOutputFields:
    """Test that fused output includes expected fields per device."""

    def test_output_contains_all_expected_fields(self):
        """Each fused entry should have properties, weight, status, stale, category, device_type, battery_level."""
        fusion = SensorFusion(max_staleness_seconds=3600)
        states = {
            "inverter_1": _make_device_state(
                "inverter_1",
                age_seconds=120,
                device_type="inverter",
                category=DeviceCategory.POWER,
                status="online",
                properties={"battery_level": 80, "mode": "standby"},
                battery_level=80.0,
            )
        }

        result = fusion.fuse(states)
        entry = result["inverter_1"]

        assert "properties" in entry
        assert "weight" in entry
        assert "status" in entry
        assert "stale" in entry
        assert "category" in entry
        assert "device_type" in entry
        assert "battery_level" in entry
        assert entry["category"] == "power"
        assert entry["device_type"] == "inverter"
        assert entry["battery_level"] == 80.0
        assert entry["status"] == "online"
