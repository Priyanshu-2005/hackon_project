"""Device registry holding all 10 device configurations for the Sharma household.

Provides DEVICE_CONFIGS constant and helper functions for querying
registered devices by ID or listing all devices.
"""

from typing import Dict, List, Optional


# All 10 device configurations for the Sharma household
DEVICE_CONFIGS: List[Dict] = [
    {
        "device_id": "living_room_ac",
        "device_type": "ac",
        "category": "climate",
        "brand": "Daikin",
        "name": "Living Room AC",
        "location": "living_room",
        "capabilities": ["set_temperature", "set_mode", "set_fan_speed", "power_on", "power_off"],
    },
    {
        "device_id": "smart_lights",
        "device_type": "lights",
        "category": "lighting",
        "brand": "Philips Hue",
        "name": "Smart Lights",
        "location": "whole_house",
        "capabilities": ["set_brightness", "set_color", "set_scene", "power_on", "power_off"],
    },
    {
        "device_id": "security_camera",
        "device_type": "camera",
        "category": "security",
        "brand": "Ring",
        "name": "Security Camera",
        "location": "entrance",
        "capabilities": ["arm", "disarm", "get_feed", "motion_detection", "night_vision"],
    },
    {
        "device_id": "smart_lock",
        "device_type": "lock",
        "category": "security",
        "brand": "Yale",
        "name": "Smart Lock",
        "location": "main_door",
        "capabilities": ["lock", "unlock", "get_status", "set_auto_lock"],
    },
    {
        "device_id": "kitchen_hub",
        "device_type": "kitchen_hub",
        "category": "kitchen",
        "brand": "Samsung",
        "name": "Kitchen Appliance Hub",
        "location": "kitchen",
        "capabilities": ["get_status", "set_timer", "start_appliance", "stop_appliance"],
    },
    {
        "device_id": "water_purifier",
        "device_type": "purifier",
        "category": "utility",
        "brand": "Kent",
        "name": "Water Purifier",
        "location": "kitchen",
        "capabilities": ["power_on", "power_off", "get_filter_status", "get_water_quality"],
    },
    {
        "device_id": "smart_geyser",
        "device_type": "geyser",
        "category": "utility",
        "brand": "Havells",
        "name": "Smart Geyser",
        "location": "bathroom",
        "capabilities": ["power_on", "power_off", "set_temperature", "get_temperature"],
    },
    {
        "device_id": "inverter_ups",
        "device_type": "inverter",
        "category": "power",
        "brand": "Luminous",
        "name": "Inverter/UPS",
        "location": "utility_room",
        "capabilities": [
            "get_battery_level",
            "get_load",
            "set_mode",
            "allocate_load",
            "get_backup_time",
        ],
    },
    {
        "device_id": "smart_tv",
        "device_type": "tv",
        "category": "entertainment",
        "brand": "Fire TV",
        "name": "Smart TV",
        "location": "living_room",
        "capabilities": ["power_on", "power_off", "set_volume", "set_input", "launch_app"],
    },
    {
        "device_id": "echo_devices",
        "device_type": "echo",
        "category": "assistant",
        "brand": "Amazon",
        "name": "Echo Devices",
        "location": "whole_house",
        "capabilities": ["announce", "notify", "play_music", "set_reminder", "get_status"],
    },
]


class DeviceRegistry:
    """Registry holding all device configurations.

    Provides methods to query devices by ID or retrieve all device configs.
    """

    def __init__(self, configs: Optional[List[Dict]] = None):
        """Initialize registry with device configs.

        Args:
            configs: List of device config dicts. Defaults to DEVICE_CONFIGS.
        """
        self._configs = configs if configs is not None else DEVICE_CONFIGS
        self._index = {cfg["device_id"]: cfg for cfg in self._configs}

    def get_all_devices(self) -> List[Dict]:
        """Return all device configurations.

        Returns:
            List of device configuration dictionaries.
        """
        return list(self._configs)

    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get a single device configuration by ID.

        Args:
            device_id: The unique device identifier.

        Returns:
            Device config dict, or None if not found.
        """
        return self._index.get(device_id)

    def get_devices_by_category(self, category: str) -> List[Dict]:
        """Get all devices in a specific category.

        Args:
            category: Category string (e.g. "climate", "security").

        Returns:
            List of device configs matching the category.
        """
        return [cfg for cfg in self._configs if cfg["category"] == category]

    def get_device_ids(self) -> List[str]:
        """Return all registered device IDs.

        Returns:
            List of device ID strings.
        """
        return list(self._index.keys())
