"""Device adapters for all 10 smart home devices."""

from src.devices.base import DeviceAdapter
from src.devices.factory import DeviceAdapterFactory
from src.devices.registry import DEVICE_CONFIGS, DeviceRegistry

from src.devices.climate import DaikinACAdapter
from src.devices.lighting import PhilipsHueAdapter
from src.devices.security import RingCameraAdapter, YaleLockAdapter
from src.devices.kitchen import SamsungKitchenAdapter
from src.devices.utility import KentPurifierAdapter, HavellsGeyserAdapter
from src.devices.power import LuminousInverterAdapter
from src.devices.entertainment import FireTVAdapter
from src.devices.assistant import EchoAdapter

__all__ = [
    "DeviceAdapter",
    "DeviceAdapterFactory",
    "DeviceRegistry",
    "DEVICE_CONFIGS",
    "DaikinACAdapter",
    "PhilipsHueAdapter",
    "RingCameraAdapter",
    "YaleLockAdapter",
    "SamsungKitchenAdapter",
    "KentPurifierAdapter",
    "HavellsGeyserAdapter",
    "LuminousInverterAdapter",
    "FireTVAdapter",
    "EchoAdapter",
]
