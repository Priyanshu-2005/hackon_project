"""REST API Lambda handler for API Gateway requests.

Exposes endpoints for device management, context inspection,
and autonomy tier configuration.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict

from src.devices.registry import DEVICE_CONFIGS
from src.devices.demo_states import DEMO_STATES
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _device_entry(cfg: Dict) -> Dict:
    """Build a frontend-shaped device entry from a device config."""
    return {
        "id": cfg["device_id"],
        "name": cfg["name"],
        "category": cfg["category"],
        "room": cfg["location"],
        "brand": cfg["brand"],
        "state": dict(DEMO_STATES.get(cfg["device_id"], {})),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for REST API Gateway requests."""
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    body = event.get("body", "")

    try:
        if path == "/devices" and http_method == "GET":
            return handle_get_devices()

        elif path.startswith("/devices/") and path.endswith("/state") and http_method == "GET":
            device_id = path_params.get("id", path.split("/")[2])
            return handle_get_device_state(device_id)

        elif path.startswith("/devices/") and path.endswith("/command") and http_method == "POST":
            device_id = path_params.get("id", path.split("/")[2])
            return handle_send_command(device_id, json.loads(body) if body else {})

        elif path == "/context/snapshot" and http_method == "GET":
            return handle_get_snapshot()

        elif path == "/context/patterns" and http_method == "GET":
            return handle_get_patterns()

        elif path == "/autonomy/tiers" and http_method == "GET":
            return handle_get_tiers()

        elif path.startswith("/autonomy/tiers/") and http_method == "PUT":
            device = path_params.get("device", path.split("/")[-1])
            return handle_update_tier(device, json.loads(body) if body else {})

        elif path == "/scenario/power-cut" and http_method == "POST":
            return handle_power_cut_scenario()

        return response(404, {"error": "Not found"})
    except Exception as e:
        logger.error(f"API error: {e}")
        return response(500, {"error": "Internal server error"})


def handle_get_devices() -> Dict:
    """Get all devices with their current states."""
    devices = [_device_entry(c) for c in DEVICE_CONFIGS]
    return response(200, {"devices": devices, "count": len(devices)})


def handle_get_device_state(device_id: str) -> Dict:
    """Get state for a single device."""
    cfg = next((c for c in DEVICE_CONFIGS if c["device_id"] == device_id), None)
    if not cfg:
        return response(404, {"error": f"Device {device_id} not found"})
    return response(200, _device_entry(cfg))


def handle_send_command(device_id: str, body: Dict) -> Dict:
    """Send a command to a device."""
    if not body.get("command"):
        return response(400, {"error": "command field is required"})
    device = next((d for d in DEVICE_CONFIGS if d["device_id"] == device_id), None)
    if not device:
        return response(404, {"error": f"Device {device_id} not found"})
    return response(200, {"device_id": device_id, "command": body["command"], "status": "executed"})


def handle_get_snapshot() -> Dict:
    """Get current context snapshot."""
    return response(200, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deviceStates": [
            {"id": c["device_id"], "state": dict(DEMO_STATES.get(c["device_id"], {}))}
            for c in DEVICE_CONFIGS
        ],
        "activeActivities": [
            {"member": "Arjun", "activity": "online_tuition", "room": "study_room"},
        ],
        "environmentals": {"temperature": 34, "humidity": 65, "powerGrid": "stable"},
    })


def handle_get_patterns() -> Dict:
    """Get detected patterns."""
    return response(200, {"patterns": [
        {"id": "morning_routine", "confidence": 0.92, "schedule": "07:00",
         "actions": ["geyser_preheat", "lights_warm"]},
        {"id": "evening_cooling", "confidence": 0.88, "schedule": "17:30",
         "actions": ["ac_precool"]},
        {"id": "security_away", "confidence": 0.95, "schedule": "09:00",
         "actions": ["lock_arm", "camera_alert"]},
    ]})


def handle_get_tiers() -> Dict:
    """Get current autonomy tier config."""
    seen, tiers = set(), []
    defaults = {"climate": (3, 55), "lighting": (4, 78), "security": (2, 35),
                "kitchen": (1, 12), "utility": (3, 62), "power": (3, 50),
                "entertainment": (2, 28), "assistant": (5, 95)}
    for c in DEVICE_CONFIGS:
        cat = c["category"]
        if cat in seen:
            continue
        seen.add(cat)
        tier, trust = defaults.get(cat, (1, 0))
        tiers.append({"category": cat, "currentTier": tier, "trustScore": trust})
    return response(200, {"tiers": tiers})


def handle_update_tier(device: str, body: Dict) -> Dict:
    """Update autonomy tier for a device category."""
    if "tier" not in body:
        return response(400, {"error": "tier field is required"})
    return response(200, {"success": True, "device": device, "currentTier": body["tier"]})


def handle_power_cut_scenario() -> Dict:
    """Run the power-cut scenario through the real pipeline with mocked reasoning."""
    try:
        from unittest.mock import MagicMock
        from src.context.engine import ContextEngine
        from src.intelligence.engine import ProactiveEngine
        from src.intelligence.event_handler import ContextualEventHandler
        from src.reasoning.client import BedrockReasoningClient
        from demo import create_simulated_adapters, mock_power_cut_response

        adapters = create_simulated_adapters()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = mock_power_cut_response()

        context_engine = ContextEngine(adapters=adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=mock_client)
        proactive = ProactiveEngine(context_engine=context_engine, reasoning_client=reasoning_client)
        handler = ContextualEventHandler(context_engine, proactive, device_adapters=adapters)

        event = {
            "event_type": "power_cut",
            "source": "inverter_ups",
            "details": {"grid_status": "offline", "battery_level": 80},
        }
        result = handler.handle_event(event)

        actions = [
            {
                "target_devices": a["target_devices"],
                "strategy": a["strategy"],
                "confidence": a["confidence"],
                "reasoning": a.get("reasoning", ""),
            }
            for a in result["actions_executed"]
        ]
        return response(200, {
            "actions": actions,
            "explanation": result["explanation"],
            "reasoning_chain": result["plan"].reasoning_chain,
        })
    except Exception as e:
        logger.error(f"power-cut scenario error: {e}")
        return response(500, {"error": "scenario pipeline failed"})


def response(status_code: int, body: Dict) -> Dict:
    """Build an API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }
