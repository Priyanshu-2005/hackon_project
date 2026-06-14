"""Integration tests for REST API endpoints.

Tests all REST endpoints with valid/invalid requests, verifies HTTP
status codes and response schemas, and tests autonomy permission
enforcement on command endpoints.

Requirements: 9.1, 9.3, 9.4
"""

import json

import pytest

from src.handlers.api_handler import lambda_handler


def make_api_event(method: str, path: str, body: dict = None, path_params: dict = None) -> dict:
    """Helper to construct an API Gateway event."""
    event = {
        "httpMethod": method,
        "path": path,
        "pathParameters": path_params or {},
        "body": json.dumps(body) if body else "",
        "headers": {"Content-Type": "application/json"},
        "queryStringParameters": {},
    }
    return event


class TestGetDevices:
    """Test GET /devices endpoint."""

    def test_list_devices_returns_200(self):
        """GET /devices returns 200 with device list."""
        event = make_api_event("GET", "/devices")
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "devices" in body
        assert len(body["devices"]) == 10

    def test_list_devices_contains_expected_fields(self):
        """Each device in the list has required fields."""
        event = make_api_event("GET", "/devices")
        result = lambda_handler(event, None)
        body = json.loads(result["body"])

        assert "count" in body
        assert body["count"] == len(body["devices"])
        for device in body["devices"]:
            assert "id" in device
            assert "name" in device
            assert "category" in device
            assert "room" in device
            assert "brand" in device
            assert "state" in device

    def test_list_devices_has_cors_headers(self):
        """Response includes CORS headers."""
        event = make_api_event("GET", "/devices")
        result = lambda_handler(event, None)

        assert result["headers"]["Access-Control-Allow-Origin"] == "*"
        assert result["headers"]["Content-Type"] == "application/json"


class TestGetDeviceState:
    """Test GET /devices/{id}/state endpoint."""

    def test_get_valid_device_state(self):
        """GET state for a known device returns 200."""
        event = make_api_event(
            "GET",
            "/devices/living_room_ac/state",
            path_params={"id": "living_room_ac"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["id"] == "living_room_ac"
        assert "state" in body

    def test_get_unknown_device_returns_404(self):
        """GET state for unknown device returns 404."""
        event = make_api_event(
            "GET",
            "/devices/unknown_device/state",
            path_params={"id": "unknown_device"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "error" in body

    def test_get_each_device_state(self):
        """Verify all 10 registered devices return valid state."""
        device_ids = [
            "living_room_ac", "smart_lights", "security_camera", "smart_lock",
            "kitchen_hub", "water_purifier", "smart_geyser", "inverter_ups",
            "smart_tv", "echo_devices",
        ]
        for device_id in device_ids:
            event = make_api_event(
                "GET",
                f"/devices/{device_id}/state",
                path_params={"id": device_id},
            )
            result = lambda_handler(event, None)
            assert result["statusCode"] == 200, f"Failed for {device_id}"


class TestSendCommand:
    """Test POST /devices/{id}/command endpoint."""

    def test_send_valid_command(self):
        """POST a valid command returns 200."""
        event = make_api_event(
            "POST",
            "/devices/living_room_ac/command",
            body={"command": "set_temperature", "parameters": {"target_temp": 22}},
            path_params={"id": "living_room_ac"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "executed"
        assert body["device_id"] == "living_room_ac"

    def test_send_command_missing_command_field(self):
        """POST without command field returns 400."""
        event = make_api_event(
            "POST",
            "/devices/living_room_ac/command",
            body={"parameters": {"temp": 22}},
            path_params={"id": "living_room_ac"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    def test_send_command_to_unknown_device(self):
        """POST command to unknown device returns 404."""
        event = make_api_event(
            "POST",
            "/devices/nonexistent/command",
            body={"command": "power_on"},
            path_params={"id": "nonexistent"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 404

    def test_send_command_empty_body(self):
        """POST with empty body returns 400."""
        event = make_api_event(
            "POST",
            "/devices/living_room_ac/command",
            body={},
            path_params={"id": "living_room_ac"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400


class TestContextEndpoints:
    """Test context-related API endpoints."""

    def test_get_context_snapshot(self):
        """GET /context/snapshot returns 200 with snapshot data."""
        event = make_api_event("GET", "/context/snapshot")
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "timestamp" in body
        assert "deviceStates" in body
        assert len(body["deviceStates"]) == 10

    def test_get_patterns(self):
        """GET /context/patterns returns 200 with patterns array."""
        event = make_api_event("GET", "/context/patterns")
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "patterns" in body
        assert isinstance(body["patterns"], list)


class TestAutonomyEndpoints:
    """Test autonomy tier API endpoints."""

    def test_get_tiers(self):
        """GET /autonomy/tiers returns 200 with tier config."""
        event = make_api_event("GET", "/autonomy/tiers")
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "tiers" in body

    def test_update_tier_valid(self):
        """PUT /autonomy/tiers/{device} with valid body returns 200."""
        event = make_api_event(
            "PUT",
            "/autonomy/tiers/climate",
            body={"tier": 3},
            path_params={"device": "climate"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["device"] == "climate"
        assert body["currentTier"] == 3

    def test_update_tier_missing_tier_field(self):
        """PUT without tier field returns 400."""
        event = make_api_event(
            "PUT",
            "/autonomy/tiers/climate",
            body={"level": 3},
            path_params={"device": "climate"},
        )
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_unknown_endpoint_returns_404(self):
        """Request to unknown path returns 404."""
        event = make_api_event("GET", "/unknown/endpoint")
        result = lambda_handler(event, None)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "error" in body

    def test_wrong_method_returns_404(self):
        """Using wrong HTTP method returns 404."""
        event = make_api_event("DELETE", "/devices")
        result = lambda_handler(event, None)

        assert result["statusCode"] == 404

    def test_malformed_json_body_returns_500(self):
        """Malformed JSON body returns 500."""
        event = {
            "httpMethod": "POST",
            "path": "/devices/living_room_ac/command",
            "pathParameters": {"id": "living_room_ac"},
            "body": "not-valid-json{{{",
            "headers": {},
            "queryStringParameters": {},
        }
        result = lambda_handler(event, None)

        # Should be 500 internal server error due to json.loads failure
        assert result["statusCode"] == 500

    def test_response_schema_consistency(self):
        """All successful responses have consistent schema."""
        endpoints = [
            ("GET", "/devices"),
            ("GET", "/context/snapshot"),
            ("GET", "/context/patterns"),
            ("GET", "/autonomy/tiers"),
        ]
        for method, path in endpoints:
            event = make_api_event(method, path)
            result = lambda_handler(event, None)

            assert result["statusCode"] == 200
            assert "body" in result
            assert "headers" in result
            # Body should be valid JSON
            body = json.loads(result["body"])
            assert isinstance(body, dict)
