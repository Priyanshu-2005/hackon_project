"""Device adapter factory for instantiating adapters by device type.

Maps device_type strings to their corresponding adapter classes and
creates instances with the appropriate configuration.
"""

from typing import Dict, Optional, Type

from src.devices.base import DeviceAdapter
from src.devices.registry import DeviceRegistry


class DeviceAdapterFactory:
    """Factory that maps device_type strings to adapter classes and instantiates them.

    Usage:
        factory = DeviceAdapterFactory()
        factory.register("ac", DaikinACAdapter)
        adapter = factory.create("living_room_ac", registry)
    """

    def __init__(self):
        """Initialize with an empty adapter class registry."""
        self._adapter_classes: Dict[str, Type[DeviceAdapter]] = {}

    def register(self, device_type: str, adapter_class: Type[DeviceAdapter]) -> None:
        """Register an adapter class for a given device type.

        Args:
            device_type: The device type string (e.g. "ac", "lights").
            adapter_class: The DeviceAdapter subclass to use for this type.
        """
        self._adapter_classes[device_type] = adapter_class

    def create(
        self, device_id: str, registry: DeviceRegistry
    ) -> Optional[DeviceAdapter]:
        """Create an adapter instance for a device from the registry.

        Looks up the device configuration from the registry, finds the
        registered adapter class for that device type, and instantiates it.

        Args:
            device_id: The unique device identifier.
            registry: DeviceRegistry containing device configurations.

        Returns:
            A DeviceAdapter instance, or None if device or adapter not found.

        Raises:
            ValueError: If device_id not found in registry.
            KeyError: If no adapter class registered for the device type.
        """
        config = registry.get_device(device_id)
        if config is None:
            raise ValueError(f"Device '{device_id}' not found in registry.")

        device_type = config["device_type"]
        adapter_class = self._adapter_classes.get(device_type)
        if adapter_class is None:
            raise KeyError(
                f"No adapter registered for device type '{device_type}'."
            )

        return adapter_class(
            device_id=config["device_id"],
            device_type=config["device_type"],
            config=config,
        )

    def create_all(self, registry: DeviceRegistry) -> Dict[str, DeviceAdapter]:
        """Create adapter instances for all devices in the registry.

        Only creates adapters for device types that have been registered.
        Skips devices with no registered adapter class.

        Args:
            registry: DeviceRegistry containing device configurations.

        Returns:
            Dict mapping device_id to DeviceAdapter instances.
        """
        adapters = {}
        for config in registry.get_all_devices():
            device_type = config["device_type"]
            adapter_class = self._adapter_classes.get(device_type)
            if adapter_class is not None:
                adapters[config["device_id"]] = adapter_class(
                    device_id=config["device_id"],
                    device_type=config["device_type"],
                    config=config,
                )
        return adapters

    def get_registered_types(self) -> list:
        """Return list of device types that have registered adapters.

        Returns:
            List of device type strings.
        """
        return list(self._adapter_classes.keys())

    def is_registered(self, device_type: str) -> bool:
        """Check if a device type has a registered adapter class.

        Args:
            device_type: The device type string to check.

        Returns:
            True if an adapter class is registered for the type.
        """
        return device_type in self._adapter_classes
