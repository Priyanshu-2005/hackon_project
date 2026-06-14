"""Sensor fusion with temporal weighting.

Provides temporal weight computation for sensor data fusion.
Recent readings receive higher weight, stale data gets diminished influence.
"""

from typing import Any, Dict

from src.models.device import DeviceState
from src.utils.config import get_config
from src.utils.time_utils import time_since_seconds


def compute_temporal_weight(age_seconds: float, max_staleness_seconds: int = 3600) -> float:
    """Compute temporal weight for a sensor reading based on its age.

    Weight decays linearly from 1.0 (fresh) to 0.1 (stale or beyond).
    For any non-negative age_seconds, the weight is always in [0.1, 1.0].

    Args:
        age_seconds: Age of the reading in seconds (must be non-negative).
        max_staleness_seconds: Maximum staleness window in seconds (default 3600).

    Returns:
        Weight value in [0.1, 1.0].
    """
    return max(0.1, 1.0 - (age_seconds / max_staleness_seconds))


class SensorFusion:
    """Fuses device states with temporal weighting.

    Recent readings receive weight approaching 1.0.
    Stale readings (> max_staleness_seconds) receive minimum weight of 0.1.
    """

    def __init__(self, max_staleness_seconds: int = None):
        config = get_config()
        self.max_staleness_seconds = max_staleness_seconds or config.max_staleness_seconds

    def fuse(self, device_states: Dict[str, DeviceState]) -> Dict[str, Dict[str, Any]]:
        """Fuse all device states with temporal weights.

        Args:
            device_states: Dict of device_id -> DeviceState

        Returns:
            Dict of device_id -> {
                "properties": ...,
                "weight": float (0.1 to 1.0),
                "status": str,
                "stale": bool,
                "category": str,
                "device_type": str,
                "battery_level": Optional[float],
            }
        """
        fused = {}
        for device_id, state in device_states.items():
            age = time_since_seconds(state.last_updated)
            weight = compute_temporal_weight(age, self.max_staleness_seconds)
            stale = age > self.max_staleness_seconds

            fused[device_id] = {
                "properties": state.properties,
                "weight": weight,
                "status": state.status,
                "stale": stale,
                "category": state.category.value,
                "device_type": state.device_type,
                "battery_level": state.battery_level,
            }

        return fused
