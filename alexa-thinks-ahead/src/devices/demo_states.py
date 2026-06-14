"""
Shared simulated device states for the demo environment.

Single source of truth importable by both `demo.py` (SimulatedAdapter)
and `src/handlers/api_handler.py` without circular imports.

Each key is a device_id matching an entry in DEVICE_CONFIGS (registry.py).
Each value is a dict of simulated property values for that device.
"""

DEMO_STATES: dict[str, dict] = {
    "living_room_ac": {
        "power": True,
        "temperature": 24,
        "mode": "cool",
        "fan_speed": "auto",
    },
    "smart_lights": {
        "power": True,
        "brightness": 80,
        "color": "#FFF5E1",
        "scene": "evening",
    },
    "security_camera": {
        "armed": True,
        "motion_detected": False,
        "recording": True,
    },
    "smart_lock": {
        "locked": True,
        "auto_lock": True,
        "battery_level": 85,
    },
    "kitchen_hub": {
        "active_appliance": "none",
        "status": "idle",
    },
    "water_purifier": {
        "power": True,
        "filter_life_pct": 72,
        "water_quality_tds": 45,
    },
    "smart_geyser": {
        "power": True,
        "temperature": 55,
        "target_temperature": 55,
    },
    "inverter_ups": {
        "battery_level": 80,
        "load_watts": 450,
        "mode": "normal",
        "grid_status": "online",
    },
    "smart_tv": {
        "power": False,
        "volume": 30,
    },
    "echo_devices": {
        "power": True,
        "volume": 50,
        "active": True,
        "last_announcement": "",
    },
}
