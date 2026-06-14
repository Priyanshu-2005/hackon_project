"""Unit tests for the Alexa Smart Home Skill handler."""

import pytest

from src.handlers.skill_handler import (
    lambda_handler,
    handle_discovery,
    handle_control,
    handle_query,
    handle_explain,
    handle_override,
    error_response,
    validate_alexa_signature,
)
from src.devices.registry import DEVICE_CONFIGS


class TestLambdaHandlerRouting:
    """Test lambda_handler routes requests to correct sub-handlers."""

    def test_routes_discovery_request(self):
        """Discovery namespace routes to handle_discovery."""
        event = {
            "directive": {
                "header": {
                    "namespace": "Alexa.Discovery",
                    "name": "Discover",
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                }
            }
        }
        response = lambda_handler(event, None)
        assert response["event"]["header"]["name"] == "Discover.Response"

    def test_routes_power_controller_request(self):
        """PowerController namespace routes to handle_control."""
        event = {
            "directive": {
                "header": {
                    "namespace": "Alexa.PowerController",
                    "name": "TurnOn",
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                    "correlationToken": "token-123",
                },
                "endpoint": {"endpointId": "living_room_ac"},
            }
        }
        response = lambda_handler(event, None)
        assert response["event"]["header"]["name"] == "Response"

    def test_routes_report_state_request(self):
        """Alexa ReportState routes to handle_query."""
        event = {
            "directive": {
                "header": {
                    "namespace": "Alexa",
                    "name": "ReportState",
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                    "correlationToken": "token-123",
                },
                "endpoint": {"endpointId": "smart_lights"},
            }
        }
        response = lambda_handler(event, None)
        assert response["event"]["header"]["name"] == "StateReport"

    def test_routes_explain_action_intent(self):
        """ExplainAction custom intent routes to handle_explain."""
        event = {
            "request": {
                "type": "IntentRequest",
                "intent": {"name": "ExplainAction"},
            }
        }
        response = lambda_handler(event, None)
        assert response["version"] == "1.0"
        assert "adjusted the settings" in response["response"]["outputSpeech"]["text"]

    def test_routes_override_action_intent(self):
        """OverrideAction custom intent routes to handle_override."""
        event = {
            "request": {
                "type": "IntentRequest",
                "intent": {"name": "OverrideAction"},
            }
        }
        response = lambda_handler(event, None)
        assert response["version"] == "1.0"
        assert "override" in response["response"]["outputSpeech"]["text"]

    def test_unsupported_directive_returns_error(self):
        """Unknown directives return an error response."""
        event = {
            "directive": {
                "header": {
                    "namespace": "Alexa.Unknown",
                    "name": "DoSomething",
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                }
            }
        }
        response = lambda_handler(event, None)
        assert response["event"]["header"]["name"] == "ErrorResponse"
        assert response["event"]["payload"]["type"] == "INVALID_DIRECTIVE"

    def test_empty_event_returns_error(self):
        """Empty event returns an error response."""
        response = lambda_handler({}, None)
        assert response["event"]["header"]["name"] == "ErrorResponse"


class TestHandleDiscovery:
    """Test the Discovery handler returns all 10 devices."""

    def test_returns_all_10_devices(self):
        """Discovery response contains all 10 registered devices."""
        event = {
            "directive": {
                "header": {
                    "namespace": "Alexa.Discovery",
                    "name": "Discover",
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                }
            }
        }
        response = handle_discovery(event)
        endpoints = response["event"]["payload"]["endpoints"]
        assert len(endpoints) == 10

    def test_response_header_format(self):
        """Discovery response has correct header fields."""
        event = {"directive": {"header": {}}}
        response = handle_discovery(event)
        header = response["event"]["header"]
        assert header["namespace"] == "Alexa.Discovery"
        assert header["name"] == "Discover.Response"
        assert header["payloadVersion"] == "3"

    def test_endpoint_has_required_fields(self):
        """Each endpoint has all required Alexa fields."""
        event = {"directive": {"header": {}}}
        response = handle_discovery(event)
        endpoints = response["event"]["payload"]["endpoints"]

        for endpoint in endpoints:
            assert "endpointId" in endpoint
            assert "manufacturerName" in endpoint
            assert "friendlyName" in endpoint
            assert "description" in endpoint
            assert "displayCategories" in endpoint
            assert "capabilities" in endpoint
            assert len(endpoint["capabilities"]) >= 1

    def test_device_ids_match_registry(self):
        """Endpoint IDs correspond to device IDs in the registry."""
        event = {"directive": {"header": {}}}
        response = handle_discovery(event)
        endpoints = response["event"]["payload"]["endpoints"]
        endpoint_ids = {ep["endpointId"] for ep in endpoints}
        registry_ids = {d["device_id"] for d in DEVICE_CONFIGS}
        assert endpoint_ids == registry_ids

    def test_capabilities_include_power_for_applicable_devices(self):
        """Devices with power_on capability have PowerController interface."""
        event = {"directive": {"header": {}}}
        response = handle_discovery(event)
        endpoints = response["event"]["payload"]["endpoints"]

        # Living room AC has power_on capability
        ac_endpoint = next(
            ep for ep in endpoints if ep["endpointId"] == "living_room_ac"
        )
        interfaces = [cap["interface"] for cap in ac_endpoint["capabilities"]]
        assert "Alexa.PowerController" in interfaces


class TestHandleControl:
    """Test the Control handler for power commands."""

    def _make_control_event(self, device_id: str, command: str) -> dict:
        return {
            "directive": {
                "header": {
                    "namespace": "Alexa.PowerController",
                    "name": command,
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                    "correlationToken": "token-abc",
                },
                "endpoint": {"endpointId": device_id},
            }
        }

    def test_turn_on_returns_on_state(self):
        """TurnOn command returns powerState ON."""
        event = self._make_control_event("living_room_ac", "TurnOn")
        response = handle_control(event)
        props = response["context"]["properties"]
        power_prop = next(p for p in props if p["name"] == "powerState")
        assert power_prop["value"] == "ON"

    def test_turn_off_returns_off_state(self):
        """TurnOff command returns powerState OFF."""
        event = self._make_control_event("smart_lights", "TurnOff")
        response = handle_control(event)
        props = response["context"]["properties"]
        power_prop = next(p for p in props if p["name"] == "powerState")
        assert power_prop["value"] == "OFF"

    def test_response_includes_endpoint_id(self):
        """Response includes the target endpoint ID."""
        event = self._make_control_event("smart_geyser", "TurnOn")
        response = handle_control(event)
        assert response["event"]["endpoint"]["endpointId"] == "smart_geyser"

    def test_response_includes_correlation_token(self):
        """Response includes the correlation token from the request."""
        event = self._make_control_event("smart_tv", "TurnOn")
        response = handle_control(event)
        assert response["event"]["header"]["correlationToken"] == "token-abc"

    def test_response_header_is_alexa_response(self):
        """Control response has namespace Alexa and name Response."""
        event = self._make_control_event("echo_devices", "TurnOn")
        response = handle_control(event)
        assert response["event"]["header"]["namespace"] == "Alexa"
        assert response["event"]["header"]["name"] == "Response"


class TestHandleQuery:
    """Test the Query (ReportState) handler."""

    def _make_query_event(self, device_id: str) -> dict:
        return {
            "directive": {
                "header": {
                    "namespace": "Alexa",
                    "name": "ReportState",
                    "payloadVersion": "3",
                    "messageId": "test-msg",
                    "correlationToken": "token-xyz",
                },
                "endpoint": {"endpointId": device_id},
            }
        }

    def test_returns_state_report(self):
        """Query response has StateReport name."""
        event = self._make_query_event("living_room_ac")
        response = handle_query(event)
        assert response["event"]["header"]["name"] == "StateReport"

    def test_returns_endpoint_id(self):
        """State report includes requested device endpoint."""
        event = self._make_query_event("smart_lock")
        response = handle_query(event)
        assert response["event"]["endpoint"]["endpointId"] == "smart_lock"

    def test_known_device_has_properties(self):
        """Known device with power capability has power state property."""
        event = self._make_query_event("living_room_ac")
        response = handle_query(event)
        props = response["context"]["properties"]
        assert len(props) > 0
        assert props[0]["namespace"] == "Alexa.PowerController"

    def test_unknown_device_has_empty_properties(self):
        """Unknown device returns empty properties list."""
        event = self._make_query_event("nonexistent_device")
        response = handle_query(event)
        assert response["context"]["properties"] == []

    def test_includes_correlation_token(self):
        """State report includes the correlation token."""
        event = self._make_query_event("smart_lights")
        response = handle_query(event)
        assert response["event"]["header"]["correlationToken"] == "token-xyz"


class TestHandleExplain:
    """Test the ExplainAction custom intent handler."""

    def test_returns_speech_response(self):
        """ExplainAction returns a speech response."""
        event = {"request": {"intent": {"name": "ExplainAction"}}}
        response = handle_explain(event)
        assert response["version"] == "1.0"
        assert response["response"]["outputSpeech"]["type"] == "PlainText"

    def test_response_ends_session(self):
        """ExplainAction response ends the session."""
        event = {"request": {"intent": {"name": "ExplainAction"}}}
        response = handle_explain(event)
        assert response["response"]["shouldEndSession"] is True

    def test_explanation_mentions_context(self):
        """Explanation text references context-based reasoning."""
        event = {"request": {"intent": {"name": "ExplainAction"}}}
        response = handle_explain(event)
        text = response["response"]["outputSpeech"]["text"]
        assert "context" in text.lower() or "preferences" in text.lower()


class TestHandleOverride:
    """Test the OverrideAction custom intent handler."""

    def test_returns_speech_response(self):
        """OverrideAction returns a speech response."""
        event = {"request": {"intent": {"name": "OverrideAction"}}}
        response = handle_override(event)
        assert response["version"] == "1.0"
        assert response["response"]["outputSpeech"]["type"] == "PlainText"

    def test_response_ends_session(self):
        """OverrideAction response ends the session."""
        event = {"request": {"intent": {"name": "OverrideAction"}}}
        response = handle_override(event)
        assert response["response"]["shouldEndSession"] is True

    def test_override_confirms_action(self):
        """Override text confirms the override was recorded."""
        event = {"request": {"intent": {"name": "OverrideAction"}}}
        response = handle_override(event)
        text = response["response"]["outputSpeech"]["text"]
        assert "override" in text.lower()


class TestErrorResponse:
    """Test the error response builder."""

    def test_error_response_structure(self):
        """Error response has correct structure."""
        response = error_response("INTERNAL_ERROR", "Something went wrong")
        assert response["event"]["header"]["namespace"] == "Alexa"
        assert response["event"]["header"]["name"] == "ErrorResponse"
        assert response["event"]["payload"]["type"] == "INTERNAL_ERROR"
        assert response["event"]["payload"]["message"] == "Something went wrong"

    def test_error_response_payload_version(self):
        """Error response has payloadVersion 3."""
        response = error_response("INVALID_VALUE", "Bad value")
        assert response["event"]["header"]["payloadVersion"] == "3"


class TestValidateAlexaSignature:
    """Test Alexa request signature validation."""

    def test_empty_cert_url_returns_false(self):
        """Empty signing cert URL is invalid."""
        assert validate_alexa_signature("", "sig", b"body") is False

    def test_http_cert_url_returns_false(self):
        """Non-HTTPS cert URL is invalid."""
        url = "http://s3.amazonaws.com/echo.api/cert.pem"
        assert validate_alexa_signature(url, "sig", b"body") is False

    def test_wrong_host_returns_false(self):
        """Cert URL with wrong host is invalid."""
        url = "https://evil.example.com/echo.api/cert.pem"
        assert validate_alexa_signature(url, "sig", b"body") is False

    def test_wrong_path_returns_false(self):
        """Cert URL with wrong path prefix is invalid."""
        url = "https://s3.amazonaws.com/wrong-path/cert.pem"
        assert validate_alexa_signature(url, "sig", b"body") is False

    def test_valid_cert_url_returns_true(self):
        """Valid Amazon S3 cert URL passes validation."""
        url = "https://s3.amazonaws.com/echo.api/echo-api-cert.pem"
        assert validate_alexa_signature(url, "sig", b"body") is True

    def test_none_cert_url_returns_false(self):
        """None cert URL is invalid."""
        assert validate_alexa_signature(None, "sig", b"body") is False
