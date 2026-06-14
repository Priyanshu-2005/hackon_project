"""Unit tests for DeviceAdapter base class, DeviceAdapterFactory, and DeviceRegistry."""

from datetime import datetime, timezone
from typing import Callable, Dict, List

import pytest

from src.devices.base import DeviceAdapter
from src.devices.factory import DeviceAdapterFactory
from src.devices.registry import DEVICE_CONFIGS, DeviceRegistry
from src.models.device import (
    CommandResult,
    DeviceCategory,
    DeviceCommand,
    DeviceState,
)


# --- Concrete adapter for testing ---


class MockAdapter(DeviceAdapter):
    """A concrete implementation of DeviceAdapter for testing."""

    def get_state(self) -> DeviceState:
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory.CLIMATE,
            status="online",
            properties={"temperature": 24},
            last_updated=datetime.now(timezone.utc),
        )

    def execute_command(self, command: DeviceCommand) -> CommandResult:
        return CommandResult(
            command_id=command.command_id,
            success=True,
            device_id=self.device_id,
            execution_time_ms=50,
        )

    def subscribe_events(self, callback: Callable) -> str:
        return f"sub_{self.device_id}"

    def get_capabilities(self) -> List[str]:
        return ["power_on", "power_off", "set_temperature"]


# --- DeviceAdapter ABC tests ---


class TestDeviceAdapterABC:
    """Tests for the DeviceAdapter abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DeviceAdapter(device_id="test", device_type="ac", config={})

    def test_concrete_adapter_initializes(self):
        """A concrete adapter can be instantiated with required args."""
        adapter = MockAdapter(
            device_id="test_ac",
            device_type="ac",
            config={"brand": "TestBrand"},
        )
        assert adapter.device_id == "test_ac"
        assert adapter.device_type == "ac"
        assert adapter.config == {"brand": "TestBrand"}

    def test_get_state_returns_device_state(self):
        """get_state returns a valid DeviceState instance."""
        adapter = MockAdapter(device_id="ac1", device_type="ac", config={})
        state = adapter.get_state()
        assert isinstance(state, DeviceState)
        assert state.device_id == "ac1"
        assert state.status == "online"

    def test_execute_command_returns_command_result(self):
        """execute_command returns a CommandResult."""
        adapter = MockAdapter(device_id="ac1", device_type="ac", config={})
        cmd = DeviceCommand(
            command_id="cmd1",
            device_id="ac1",
            action="set_temperature",
            parameters={"target_temp": 22},
            source="user",
            tier_required=1,
            reversible=True,
        )
        result = adapter.execute_command(cmd)
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.command_id == "cmd1"

    def test_subscribe_events_returns_subscription_id(self):
        """subscribe_events returns a subscription ID string."""
        adapter = MockAdapter(device_id="ac1", device_type="ac", config={})
        sub_id = adapter.subscribe_events(lambda e: None)
        assert isinstance(sub_id, str)
        assert "ac1" in sub_id

    def test_get_capabilities_returns_list(self):
        """get_capabilities returns a list of capability strings."""
        adapter = MockAdapter(device_id="ac1", device_type="ac", config={})
        caps = adapter.get_capabilities()
        assert isinstance(caps, list)
        assert len(caps) > 0
        assert all(isinstance(c, str) for c in caps)


# --- DeviceRegistry tests ---


class TestDeviceRegistry:
    """Tests for the DeviceRegistry class."""

    def test_default_registry_has_10_devices(self):
        """Default registry contains all 10 Sharma household devices."""
        registry = DeviceRegistry()
        devices = registry.get_all_devices()
        assert len(devices) == 10

    def test_get_device_by_id(self):
        """Can retrieve a device by its unique ID."""
        registry = DeviceRegistry()
        ac = registry.get_device("living_room_ac")
        assert ac is not None
        assert ac["device_type"] == "ac"
        assert ac["brand"] == "Daikin"
        assert ac["category"] == "climate"

    def test_get_device_returns_none_for_unknown_id(self):
        """Returns None for a non-existent device ID."""
        registry = DeviceRegistry()
        result = registry.get_device("nonexistent_device")
        assert result is None

    def test_all_required_device_ids_present(self):
        """All 10 expected device IDs are registered."""
        registry = DeviceRegistry()
        expected_ids = [
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
        actual_ids = registry.get_device_ids()
        assert set(actual_ids) == set(expected_ids)

    def test_get_devices_by_category(self):
        """Can filter devices by category."""
        registry = DeviceRegistry()
        security_devices = registry.get_devices_by_category("security")
        assert len(security_devices) == 2
        ids = [d["device_id"] for d in security_devices]
        assert "security_camera" in ids
        assert "smart_lock" in ids

    def test_each_device_has_required_fields(self):
        """Every device config has all required fields."""
        registry = DeviceRegistry()
        required_fields = [
            "device_id",
            "device_type",
            "category",
            "brand",
            "name",
            "location",
            "capabilities",
        ]
        for device in registry.get_all_devices():
            for field in required_fields:
                assert field in device, f"Device {device['device_id']} missing field: {field}"

    def test_custom_configs(self):
        """Can initialize with custom device configs."""
        custom = [{"device_id": "custom1", "device_type": "test", "category": "test"}]
        registry = DeviceRegistry(configs=custom)
        assert len(registry.get_all_devices()) == 1
        assert registry.get_device("custom1") is not None

    def test_device_configs_constant_matches_registry(self):
        """DEVICE_CONFIGS constant matches default registry content."""
        registry = DeviceRegistry()
        assert registry.get_all_devices() == DEVICE_CONFIGS


# --- DeviceAdapterFactory tests ---


class TestDeviceAdapterFactory:
    """Tests for the DeviceAdapterFactory class."""

    def test_register_and_create(self):
        """Register an adapter class and create an instance."""
        factory = DeviceAdapterFactory()
        factory.register("ac", MockAdapter)

        registry = DeviceRegistry()
        adapter = factory.create("living_room_ac", registry)

        assert isinstance(adapter, MockAdapter)
        assert adapter.device_id == "living_room_ac"
        assert adapter.device_type == "ac"

    def test_create_raises_for_unknown_device(self):
        """Raises ValueError for a device_id not in registry."""
        factory = DeviceAdapterFactory()
        registry = DeviceRegistry()

        with pytest.raises(ValueError, match="not found in registry"):
            factory.create("nonexistent_device", registry)

    def test_create_raises_for_unregistered_type(self):
        """Raises KeyError when no adapter class is registered for the type."""
        factory = DeviceAdapterFactory()
        registry = DeviceRegistry()

        with pytest.raises(KeyError, match="No adapter registered"):
            factory.create("living_room_ac", registry)

    def test_create_all_creates_registered_adapters(self):
        """create_all creates adapters for all registered types."""
        factory = DeviceAdapterFactory()
        factory.register("ac", MockAdapter)
        factory.register("lights", MockAdapter)

        registry = DeviceRegistry()
        adapters = factory.create_all(registry)

        assert "living_room_ac" in adapters
        assert "smart_lights" in adapters
        # Unregistered types are skipped
        assert "security_camera" not in adapters

    def test_get_registered_types(self):
        """Returns list of registered type strings."""
        factory = DeviceAdapterFactory()
        factory.register("ac", MockAdapter)
        factory.register("lights", MockAdapter)

        types = factory.get_registered_types()
        assert "ac" in types
        assert "lights" in types

    def test_is_registered(self):
        """Check if a type has been registered."""
        factory = DeviceAdapterFactory()
        factory.register("ac", MockAdapter)

        assert factory.is_registered("ac") is True
        assert factory.is_registered("lights") is False

    def test_factory_passes_config_to_adapter(self):
        """Config from registry is passed to adapter constructor."""
        factory = DeviceAdapterFactory()
        factory.register("ac", MockAdapter)

        registry = DeviceRegistry()
        adapter = factory.create("living_room_ac", registry)

        assert adapter.config["brand"] == "Daikin"
        assert adapter.config["category"] == "climate"
