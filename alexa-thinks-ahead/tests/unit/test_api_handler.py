"""Unit tests for REST API handler."""

import json
import pytest

from src.handlers.api_handler import lambda_handler


def _make_event(method="GET", path="/", path_params=None, body=None):
    """Helper to construct API Gateway event."""
    event = {
        "httpMethod": method,
        "path": path,
        "pathParameters": path_params,
        "body": json.dumps(body) if body else "",
    }
    return event


class TestGetDevices:
    """Tests for GET /devices endpoint."""

    def test_returns_200(self):
        event = _make_event("GET", "/devices")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_returns_all_10_devices(self):
        event = _make_event("GET", "/devices")
        result = lambda_handler(event, None)
        body = json.loads(result["body"])
        assert len(body["devices"]) == 10

    def test_response_has_cors_header(self):
        event = _make_event("GET", "/devices")
        result = lambda_handler(event, None)
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"


class TestGetDeviceState:
    """Tests for GET /devices/{id}/state endpoint."""

    def test_valid_device_returns_200(self):
        event = _make_event(
            "GET",
            "/devices/living_room_ac/state",
            path_params={"id": "living_room_ac"},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["device_id"] == "living_room_ac"
        assert body["status"] == "online"

    def test_invalid_device_returns_404(self):
        event = _make_event(
            "GET",
            "/devices/nonexistent/state",
            path_params={"id": "nonexistent"},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_extracts_id_from_path_when_no_path_params(self):
        event = _make_event("GET", "/devices/smart_tv/state")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["device_id"] == "smart_tv"


class TestSendCommand:
    """Tests for POST /devices/{id}/command endpoint."""

    def test_valid_command_returns_200(self):
        event = _make_event(
            "POST",
            "/devices/living_room_ac/command",
            path_params={"id": "living_room_ac"},
            body={"command": "set_temperature", "parameters": {"target_temp": 24}},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["command"] == "set_temperature"
        assert body["status"] == "executed"

    def test_missing_command_returns_400(self):
        event = _make_event(
            "POST",
            "/devices/living_room_ac/command",
            path_params={"id": "living_room_ac"},
            body={"parameters": {"target_temp": 24}},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_unknown_device_returns_404(self):
        event = _make_event(
            "POST",
            "/devices/nonexistent/command",
            path_params={"id": "nonexistent"},
            body={"command": "power_on"},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_empty_body_returns_400(self):
        event = _make_event(
            "POST",
            "/devices/living_room_ac/command",
            path_params={"id": "living_room_ac"},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 400


class TestGetContextSnapshot:
    """Tests for GET /context/snapshot endpoint."""

    def test_returns_200(self):
        event = _make_event("GET", "/context/snapshot")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["snapshot_id"] == "current"
        assert body["device_count"] == 10


class TestGetContextPatterns:
    """Tests for GET /context/patterns endpoint."""

    def test_returns_200(self):
        event = _make_event("GET", "/context/patterns")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "patterns" in body


class TestGetAutonomyTiers:
    """Tests for GET /autonomy/tiers endpoint."""

    def test_returns_200(self):
        event = _make_event("GET", "/autonomy/tiers")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "tiers" in body


class TestUpdateAutonomyTier:
    """Tests for PUT /autonomy/tiers/{device} endpoint."""

    def test_valid_update_returns_200(self):
        event = _make_event(
            "PUT",
            "/autonomy/tiers/climate",
            path_params={"device": "climate"},
            body={"tier": 3},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["device"] == "climate"
        assert body["new_tier"] == 3

    def test_missing_tier_returns_400(self):
        event = _make_event(
            "PUT",
            "/autonomy/tiers/climate",
            path_params={"device": "climate"},
            body={"level": 3},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_extracts_device_from_path(self):
        event = _make_event(
            "PUT",
            "/autonomy/tiers/security",
            body={"tier": 2},
        )
        result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["device"] == "security"


class TestNotFound:
    """Tests for unmatched routes."""

    def test_unknown_path_returns_404(self):
        event = _make_event("GET", "/unknown")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 404

    def test_wrong_method_returns_404(self):
        event = _make_event("DELETE", "/devices")
        result = lambda_handler(event, None)
        assert result["statusCode"] == 404


class TestErrorHandling:
    """Tests for error handling."""

    def test_malformed_json_body_returns_500(self):
        event = {
            "httpMethod": "POST",
            "path": "/devices/living_room_ac/command",
            "pathParameters": {"id": "living_room_ac"},
            "body": "not json",
        }
        result = lambda_handler(event, None)
        assert result["statusCode"] == 500

    def test_response_has_json_content_type(self):
        event = _make_event("GET", "/devices")
        result = lambda_handler(event, None)
        assert result["headers"]["Content-Type"] == "application/json"
