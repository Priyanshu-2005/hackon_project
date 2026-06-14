"""REST API Lambda handler for API Gateway requests.

Exposes endpoints for device management, context inspection,
and autonomy tier configuration.
"""

import json
from typing import Any, Dict

from src.devices.registry import DEVICE_CONFIGS
from src.utils.logging import get_logger

logger = get_logger(__name__)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for REST API Gateway requests."""
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "")
    path_params = event.get("pathParameters") or {}
    body = event.get("body", "")

    try:
        if path == "/devices" and http_method == "GET":
            return response(200, {"devices": DEVICE_CONFIGS})

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

        return response(404, {"error": "Not found"})
    except Exception as e:
        logger.error(f"API error: {e}")
        return response(500, {"error": "Internal server error"})


def handle_get_device_state(device_id: str) -> Dict:
    """Get state for a single device."""
    device = next((d for d in DEVICE_CONFIGS if d["device_id"] == device_id), None)
    if not device:
        return response(404, {"error": f"Device {device_id} not found"})
    return response(200, {"device_id": device_id, "status": "online", "properties": {}})


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
    return response(200, {"snapshot_id": "current", "device_count": 10, "status": "active"})


def handle_get_patterns() -> Dict:
    """Get detected patterns."""
    return response(200, {"patterns": []})


def handle_get_tiers() -> Dict:
    """Get current autonomy tier config."""
    return response(200, {"tiers": {}, "message": "All members at tier 1"})


def handle_update_tier(device: str, body: Dict) -> Dict:
    """Update autonomy tier for a device category."""
    if "tier" not in body:
        return response(400, {"error": "tier field is required"})
    return response(200, {"device": device, "new_tier": body["tier"]})


def response(status_code: int, body: Dict) -> Dict:
    """Build an API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }
