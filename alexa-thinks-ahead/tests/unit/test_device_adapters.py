"""Unit tests for all 10 concrete device adapters.

Tests each adapter for:
1. get_state() returns valid DeviceState with correct category and properties
2. execute_command() with valid params returns success
3. execute_command() with invalid params returns failure with error_message
4. When _reachable=False, get_state() returns status="offline" and commands fail
5. At least one device-specific command per adapter

Requirement 1.2: Translate commands to device-specific protocol.
Requirement 1.3: Mark device as stale when unreachable.
"""

from datetime import datetime, timezone

import pytest

from src.devices.assistant import EchoAdapter
from src.devices.climate import DaikinACAdapter
from src.devices.entertainment import FireTVAdapter
from src.devices.kitchen import SamsungKitchenAdapter
from src.devices.lighting import PhilipsHueAdapter
from src.devices.power import LuminousInverterAdapter
from src.devices.security import RingCameraAdapter, YaleLockAdapter
from src.devices.utility import HavellsGeyserAdapter, KentPurifierAdapter
from src.models.device import (
    CommandResult,
    DeviceCategory,
    DeviceCommand,
    DeviceState,
)


# --- Helper ---

def make_command(device_id: str, action: str, parameters: dict = None, **kwargs) -> DeviceCommand:
    """Create a DeviceCommand with sensible defaults."""
    return DeviceCommand(
        command_id="test_cmd_1",
        device_id=device_id,
        action=action,
        parameters=parameters or {},
        source="user",
        tier_required=1,
        reversible=True,
    )


# =============================================================================
# DaikinACAdapter Tests
# =============================================================================


class TestDaikinACAdapter:
    """Tests for DaikinACAdapter (climate)."""

    @pytest.fixture
    def adapter(self):
        return DaikinACAdapter(device_id="living_room_ac", device_type="ac", config={"brand": "Daikin"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "living_room_ac"
        assert state.device_type == "ac"
        assert state.category == DeviceCategory.CLIMATE
        assert state.status == "online"
        assert "temperature" in state.properties
        assert "mode" in state.properties
        assert isinstance(state.last_updated, datetime)

    def test_set_temperature_valid(self, adapter):
        cmd = make_command("living_room_ac", "set_temperature", {"temperature": 22})
        result = adapter.execute_command(cmd)
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.device_id == "living_room_ac"
        assert result.new_state.properties["temperature"] == 22

    def test_set_temperature_invalid(self, adapter):
        cmd = make_command("living_room_ac", "set_temperature", {"temperature": 50})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None
        assert "16" in result.error_message or "30" in result.error_message

    def test_set_mode_valid(self, adapter):
        cmd = make_command("living_room_ac", "set_mode", {"mode": "heat"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["mode"] == "heat"

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("living_room_ac", "set_temperature", {"temperature": 22})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# PhilipsHueAdapter Tests
# =============================================================================


class TestPhilipsHueAdapter:
    """Tests for PhilipsHueAdapter (lighting)."""

    @pytest.fixture
    def adapter(self):
        return PhilipsHueAdapter(device_id="smart_lights", device_type="lights", config={"brand": "Philips Hue"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "smart_lights"
        assert state.category == DeviceCategory.LIGHTING
        assert state.status == "online"
        assert "brightness" in state.properties
        assert "color" in state.properties

    def test_set_brightness_valid(self, adapter):
        cmd = make_command("smart_lights", "set_brightness", {"brightness": 50})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["brightness"] == 50

    def test_set_brightness_invalid(self, adapter):
        cmd = make_command("smart_lights", "set_brightness", {"brightness": 150})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_set_color_valid(self, adapter):
        cmd = make_command("smart_lights", "set_color", {"color": "#FF5500"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["color"] == "#FF5500"

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("smart_lights", "set_brightness", {"brightness": 50})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# RingCameraAdapter Tests
# =============================================================================


class TestRingCameraAdapter:
    """Tests for RingCameraAdapter (security)."""

    @pytest.fixture
    def adapter(self):
        return RingCameraAdapter(device_id="security_camera", device_type="camera", config={"brand": "Ring"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "security_camera"
        assert state.category == DeviceCategory.SECURITY
        assert state.status == "online"
        assert "armed" in state.properties
        assert "night_vision" in state.properties

    def test_arm_command(self, adapter):
        # Disarm first, then arm
        adapter._state["armed"] = False
        cmd = make_command("security_camera", "arm", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["armed"] is True
        assert result.new_state.properties["recording"] is True

    def test_disarm_command(self, adapter):
        cmd = make_command("security_camera", "disarm", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["armed"] is False

    def test_unknown_command_fails(self, adapter):
        cmd = make_command("security_camera", "self_destruct", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("security_camera", "arm", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# YaleLockAdapter Tests
# =============================================================================


class TestYaleLockAdapter:
    """Tests for YaleLockAdapter (security)."""

    @pytest.fixture
    def adapter(self):
        return YaleLockAdapter(device_id="smart_lock", device_type="lock", config={"brand": "Yale"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "smart_lock"
        assert state.category == DeviceCategory.SECURITY
        assert state.status == "online"
        assert "locked" in state.properties
        assert "battery_level" in state.properties
        assert state.battery_level == 85

    def test_lock_command(self, adapter):
        adapter._state["locked"] = False
        cmd = make_command("smart_lock", "lock", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["locked"] is True

    def test_unlock_command(self, adapter):
        cmd = make_command("smart_lock", "unlock", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["locked"] is False

    def test_unknown_command_fails(self, adapter):
        cmd = make_command("smart_lock", "break_in", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("smart_lock", "lock", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# SamsungKitchenAdapter Tests
# =============================================================================


class TestSamsungKitchenAdapter:
    """Tests for SamsungKitchenAdapter (kitchen)."""

    @pytest.fixture
    def adapter(self):
        return SamsungKitchenAdapter(device_id="kitchen_hub", device_type="kitchen_hub", config={"brand": "Samsung"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "kitchen_hub"
        assert state.category == DeviceCategory.KITCHEN
        assert state.status == "online"
        assert "active_appliance" in state.properties
        assert "timer_minutes" in state.properties

    def test_set_timer_valid(self, adapter):
        cmd = make_command("kitchen_hub", "set_timer", {"minutes": 15})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["timer_minutes"] == 15

    def test_set_timer_invalid(self, adapter):
        cmd = make_command("kitchen_hub", "set_timer", {"minutes": -5})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_start_appliance_valid(self, adapter):
        cmd = make_command("kitchen_hub", "start_appliance", {"appliance": "oven"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["active_appliance"] == "oven"
        assert result.new_state.properties["status"] == "running"

    def test_start_appliance_invalid(self, adapter):
        cmd = make_command("kitchen_hub", "start_appliance", {"appliance": ""})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("kitchen_hub", "set_timer", {"minutes": 10})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# KentPurifierAdapter Tests
# =============================================================================


class TestKentPurifierAdapter:
    """Tests for KentPurifierAdapter (utility)."""

    @pytest.fixture
    def adapter(self):
        return KentPurifierAdapter(device_id="water_purifier", device_type="purifier", config={"brand": "Kent"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "water_purifier"
        assert state.category == DeviceCategory.UTILITY
        assert state.status == "online"
        assert "filter_life_pct" in state.properties
        assert "water_quality_tds" in state.properties

    def test_power_on_command(self, adapter):
        adapter._state["power"] = False
        cmd = make_command("water_purifier", "power_on", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["power"] is True

    def test_get_filter_status_command(self, adapter):
        cmd = make_command("water_purifier", "get_filter_status", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state is not None

    def test_unknown_command_fails(self, adapter):
        cmd = make_command("water_purifier", "flush_system", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("water_purifier", "power_on", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# HavellsGeyserAdapter Tests
# =============================================================================


class TestHavellsGeyserAdapter:
    """Tests for HavellsGeyserAdapter (utility)."""

    @pytest.fixture
    def adapter(self):
        return HavellsGeyserAdapter(device_id="smart_geyser", device_type="geyser", config={"brand": "Havells"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "smart_geyser"
        assert state.category == DeviceCategory.UTILITY
        assert state.status == "online"
        assert "temperature" in state.properties
        assert "target_temperature" in state.properties

    def test_set_temperature_valid(self, adapter):
        cmd = make_command("smart_geyser", "set_temperature", {"temperature": 60})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["target_temperature"] == 60

    def test_set_temperature_invalid(self, adapter):
        cmd = make_command("smart_geyser", "set_temperature", {"temperature": 100})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None
        assert "30" in result.error_message or "75" in result.error_message

    def test_power_off_command(self, adapter):
        adapter._state["power"] = True
        cmd = make_command("smart_geyser", "power_off", {})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["power"] is False

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("smart_geyser", "set_temperature", {"temperature": 50})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# LuminousInverterAdapter Tests
# =============================================================================


class TestLuminousInverterAdapter:
    """Tests for LuminousInverterAdapter (power)."""

    @pytest.fixture
    def adapter(self):
        return LuminousInverterAdapter(device_id="inverter_ups", device_type="inverter", config={"brand": "Luminous"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "inverter_ups"
        assert state.category == DeviceCategory.POWER
        assert state.status == "online"
        assert "battery_level" in state.properties
        assert "load_watts" in state.properties
        assert "mode" in state.properties
        assert state.battery_level == 80

    def test_set_mode_valid(self, adapter):
        cmd = make_command("inverter_ups", "set_mode", {"mode": "eco"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["mode"] == "eco"

    def test_set_mode_invalid(self, adapter):
        cmd = make_command("inverter_ups", "set_mode", {"mode": "turbo"})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_allocate_load_valid(self, adapter):
        cmd = make_command("inverter_ups", "allocate_load", {"devices": ["wifi_router", "study_lamp"]})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["allocated_devices"] == ["wifi_router", "study_lamp"]
        assert result.new_state.properties["load_watts"] == 200

    def test_allocate_load_invalid(self, adapter):
        cmd = make_command("inverter_ups", "allocate_load", {"devices": "not_a_list"})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("inverter_ups", "set_mode", {"mode": "eco"})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# FireTVAdapter Tests
# =============================================================================


class TestFireTVAdapter:
    """Tests for FireTVAdapter (entertainment)."""

    @pytest.fixture
    def adapter(self):
        return FireTVAdapter(device_id="smart_tv", device_type="tv", config={"brand": "Fire TV"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "smart_tv"
        assert state.category == DeviceCategory.ENTERTAINMENT
        assert state.status == "online"
        assert "volume" in state.properties
        assert "input_source" in state.properties
        assert "current_app" in state.properties

    def test_set_volume_valid(self, adapter):
        cmd = make_command("smart_tv", "set_volume", {"volume": 75})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["volume"] == 75

    def test_set_volume_invalid(self, adapter):
        cmd = make_command("smart_tv", "set_volume", {"volume": 200})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_launch_app_valid(self, adapter):
        cmd = make_command("smart_tv", "launch_app", {"app": "Netflix"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["current_app"] == "Netflix"

    def test_launch_app_invalid(self, adapter):
        cmd = make_command("smart_tv", "launch_app", {"app": ""})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("smart_tv", "set_volume", {"volume": 50})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()


# =============================================================================
# EchoAdapter Tests
# =============================================================================


class TestEchoAdapter:
    """Tests for EchoAdapter (assistant)."""

    @pytest.fixture
    def adapter(self):
        return EchoAdapter(device_id="echo_devices", device_type="echo", config={"brand": "Amazon"})

    def test_get_state_returns_valid_device_state(self, adapter):
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "echo_devices"
        assert state.category == DeviceCategory.ASSISTANT
        assert state.status == "online"
        assert "volume" in state.properties
        assert "active" in state.properties

    def test_announce_valid(self, adapter):
        cmd = make_command("echo_devices", "announce", {"message": "Dinner is ready"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert result.new_state.properties["last_announcement"] == "Dinner is ready"

    def test_announce_invalid(self, adapter):
        cmd = make_command("echo_devices", "announce", {"message": ""})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_play_music_valid(self, adapter):
        cmd = make_command("echo_devices", "play_music", {"track": "Bollywood Hits"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert "Bollywood Hits" in result.new_state.properties["last_announcement"]

    def test_set_reminder_valid(self, adapter):
        cmd = make_command("echo_devices", "set_reminder", {"reminder": "Pick up groceries"})
        result = adapter.execute_command(cmd)
        assert result.success is True
        assert "Pick up groceries" in result.new_state.properties["last_announcement"]

    def test_unknown_command_fails(self, adapter):
        cmd = make_command("echo_devices", "sing_song", {})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert result.error_message is not None

    def test_unreachable_get_state_offline(self, adapter):
        adapter._reachable = False
        state = adapter.get_state()
        assert state.status == "offline"

    def test_unreachable_command_fails(self, adapter):
        adapter._reachable = False
        cmd = make_command("echo_devices", "announce", {"message": "Hello"})
        result = adapter.execute_command(cmd)
        assert result.success is False
        assert "unreachable" in result.error_message.lower()
