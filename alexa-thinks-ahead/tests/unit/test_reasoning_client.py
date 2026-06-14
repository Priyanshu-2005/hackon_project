"""Unit tests for the BedrockReasoningClient.

Tests prompt building, response parsing, error handling, exponential
backoff, and fallback to cached/empty responses.
"""

import io
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError

from src.models.context import ContextSnapshot, FamilyActivity, TemporalPattern
from src.models.device import DeviceCategory, DeviceState
from src.models.intelligence import ReasoningRequest, ReasoningResponse
from src.reasoning.client import BedrockReasoningClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot() -> ContextSnapshot:
    """Create a minimal ContextSnapshot for testing."""
    now = datetime.now(timezone.utc)
    return ContextSnapshot(
        snapshot_id="snap-001",
        timestamp=now,
        device_states={
            "living_room_ac": DeviceState(
                device_id="living_room_ac",
                device_type="climate",
                category=DeviceCategory.CLIMATE,
                status="online",
                properties={"temperature": 26, "mode": "cool"},
                last_updated=now,
            ),
        },
        active_activities=[
            FamilyActivity(
                member_name="Arjun",
                activity="online_tuition",
                location="study_room",
                start_time=now,
            )
        ],
        detected_patterns=[
            TemporalPattern(
                pattern_id="pat-1",
                pattern_type="daily",
                confidence=0.9,
                devices_involved=["living_room_ac"],
                schedule={"time": "17:00"},
                last_observed=now,
            )
        ],
        resource_levels={"inverter_battery": 0.8},
        environmental={"temperature_outside": 38, "season": "summer"},
        confidence=0.85,
    )


def _make_request() -> ReasoningRequest:
    """Create a minimal ReasoningRequest."""
    return ReasoningRequest(
        context=_make_snapshot(),
        event={"type": "power_cut", "severity": "critical"},
        preferences={"temperature": 24},
        autonomy_config={"climate": 3, "security": 2},
        query_type="action_plan",
    )


def _mock_bedrock_response(data: dict) -> dict:
    """Simulate a Bedrock API response with JSON content."""
    body_content = json.dumps(
        {"content": [{"text": json.dumps(data)}]}
    ).encode()
    body_stream = io.BytesIO(body_content)
    return {"body": body_stream}


def _mock_bedrock_response_raw(raw_text: str) -> dict:
    """Simulate a Bedrock API response with arbitrary text."""
    body_content = json.dumps(
        {"content": [{"text": raw_text}]}
    ).encode()
    body_stream = io.BytesIO(body_content)
    return {"body": body_stream}


# ---------------------------------------------------------------------------
# Tests: build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """Tests for BedrockReasoningClient.build_prompt."""

    def test_build_prompt_produces_nonempty_string(self):
        """build_prompt should return a non-empty string."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_build_prompt_contains_device_states(self):
        """Prompt should include device state information."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert "living_room_ac" in prompt
        assert "online" in prompt

    def test_build_prompt_contains_activities(self):
        """Prompt should include active family activities."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert "Arjun" in prompt
        assert "online_tuition" in prompt

    def test_build_prompt_contains_patterns(self):
        """Prompt should include detected temporal patterns."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert "daily" in prompt
        assert "0.90" in prompt

    def test_build_prompt_contains_event(self):
        """Prompt should include the triggering event."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert "power_cut" in prompt

    def test_build_prompt_contains_preferences(self):
        """Prompt should include family preferences."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert "temperature" in prompt

    def test_build_prompt_contains_autonomy_config(self):
        """Prompt should include autonomy tier limits."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        request = _make_request()
        prompt = reasoning_client.build_prompt(request)

        assert "climate" in prompt


# ---------------------------------------------------------------------------
# Tests: _parse_response
# ---------------------------------------------------------------------------


class TestParseResponse:
    """Tests for BedrockReasoningClient._parse_response."""

    def test_parse_valid_json_response(self):
        """Valid JSON response should parse into ReasoningResponse."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        raw_response = {
            "content": [
                {
                    "text": json.dumps(
                        {
                            "actions": [
                                {"device": "ac", "command": "set_temp", "params": {"temp": 24}}
                            ],
                            "reasoning_chain": "It's hot outside, pre-cool the house.",
                            "confidence": 0.92,
                            "explanation": "Pre-cooling the house before family arrives.",
                        }
                    )
                }
            ]
        }

        result = reasoning_client._parse_response(raw_response)

        assert result is not None
        assert isinstance(result, ReasoningResponse)
        assert len(result.actions) == 1
        assert result.confidence == 0.92
        assert "pre-cool" in result.reasoning_chain.lower()

    def test_parse_natural_language_response(self):
        """Non-JSON text should be wrapped as a natural language response."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        raw_response = {
            "content": [
                {"text": "I recommend turning on the AC because it's hot."}
            ]
        }

        result = reasoning_client._parse_response(raw_response)

        assert result is not None
        assert result.actions == []
        assert result.confidence == 0.7
        assert "AC" in result.explanation

    def test_parse_empty_content_returns_none(self):
        """Empty content list should return None (malformed)."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        raw_response = {"content": []}

        result = reasoning_client._parse_response(raw_response)

        assert result is None

    def test_parse_missing_content_key_returns_none(self):
        """Missing 'content' key should return None (malformed)."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        raw_response = {"unexpected_key": "value"}

        result = reasoning_client._parse_response(raw_response)

        assert result is None

    def test_parse_empty_text_returns_none(self):
        """Empty text in content should return None."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        raw_response = {"content": [{"text": ""}]}

        result = reasoning_client._parse_response(raw_response)

        assert result is None


# ---------------------------------------------------------------------------
# Tests: _empty_response
# ---------------------------------------------------------------------------


class TestEmptyResponse:
    """Tests for BedrockReasoningClient._empty_response."""

    def test_empty_response_returns_valid_reasoning_response(self):
        """_empty_response should return a ReasoningResponse with no actions."""
        mock_client = MagicMock()
        reasoning_client = BedrockReasoningClient(client=mock_client)

        result = reasoning_client._empty_response()

        assert isinstance(result, ReasoningResponse)
        assert result.actions == []
        assert result.confidence == 0.0
        assert result.reasoning_chain == "No reasoning available"
        assert len(result.explanation) > 0


# ---------------------------------------------------------------------------
# Tests: invoke_reasoning (successful)
# ---------------------------------------------------------------------------


class TestInvokeReasoningSuccess:
    """Tests for successful invoke_reasoning calls."""

    def test_invoke_reasoning_returns_parsed_response(self):
        """Successful Bedrock call should return parsed ReasoningResponse."""
        mock_client = MagicMock()

        response_data = {
            "actions": [{"device": "geyser", "command": "preheat"}],
            "reasoning_chain": "Morning routine detected, pre-heating geyser.",
            "confidence": 0.88,
            "explanation": "Pre-heating geyser for morning shower.",
        }
        mock_client.invoke_model.return_value = _mock_bedrock_response(
            response_data
        )

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        result = reasoning_client.invoke_reasoning(request)

        assert isinstance(result, ReasoningResponse)
        assert len(result.actions) == 1
        assert result.confidence == 0.88
        mock_client.invoke_model.assert_called_once()

    def test_invoke_reasoning_caches_successful_response(self):
        """A successful response should be cached for later fallback."""
        mock_client = MagicMock()

        response_data = {
            "actions": [{"device": "lights", "command": "dim"}],
            "reasoning_chain": "Sunset approaching.",
            "confidence": 0.75,
            "explanation": "Dimming lights for sunset.",
        }
        mock_client.invoke_model.return_value = _mock_bedrock_response(
            response_data
        )

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        reasoning_client.invoke_reasoning(request)

        assert reasoning_client._cached_response is not None
        assert reasoning_client._cached_response.confidence == 0.75


# ---------------------------------------------------------------------------
# Tests: invoke_reasoning (timeout / fallback)
# ---------------------------------------------------------------------------


class TestInvokeReasoningTimeout:
    """Tests for invoke_reasoning with timeouts and fallback behavior."""

    @patch("src.reasoning.client.time.sleep", return_value=None)
    def test_invoke_reasoning_falls_back_on_timeout(self, mock_sleep):
        """On persistent timeout, should return empty response."""
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock.ap-south-1.amazonaws.com"
        )

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        result = reasoning_client.invoke_reasoning(request)

        assert isinstance(result, ReasoningResponse)
        assert result.actions == []
        assert result.confidence == 0.0
        # Should have retried 3 times (bedrock_max_retries = 3)
        assert mock_client.invoke_model.call_count == 3

    @patch("src.reasoning.client.time.sleep", return_value=None)
    def test_invoke_reasoning_uses_cached_on_timeout(self, mock_sleep):
        """If cached response exists, fall back to it on timeout."""
        mock_client = MagicMock()

        # First call succeeds
        response_data = {
            "actions": [{"device": "ac", "command": "on"}],
            "reasoning_chain": "Hot day detected.",
            "confidence": 0.9,
            "explanation": "Turning on AC.",
        }
        mock_client.invoke_model.return_value = _mock_bedrock_response(
            response_data
        )

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        # First call — cache the response
        first_result = reasoning_client.invoke_reasoning(request)
        assert first_result.confidence == 0.9

        # Second call — simulate timeout
        mock_client.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock.ap-south-1.amazonaws.com"
        )

        second_result = reasoning_client.invoke_reasoning(request)

        # Should fall back to cached response
        assert second_result.confidence == 0.9
        assert second_result.actions == [{"device": "ac", "command": "on"}]

    @patch("src.reasoning.client.time.sleep", return_value=None)
    def test_exponential_backoff_timing(self, mock_sleep):
        """Should use exponential backoff waits: 1s, 2s, 4s."""
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock.ap-south-1.amazonaws.com"
        )

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        reasoning_client.invoke_reasoning(request)

        # Check backoff delays: 1*2^0=1, 1*2^1=2, 1*2^2=4
        # But only first 2 retries call sleep (last attempt exits loop)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0, 4.0]

    @patch("src.reasoning.client.time.sleep", return_value=None)
    def test_invoke_reasoning_handles_client_error(self, mock_sleep):
        """ClientError should trigger retries similar to timeout."""
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ClientError(
            error_response={"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            operation_name="InvokeModel",
        )

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        result = reasoning_client.invoke_reasoning(request)

        assert result.actions == []
        assert mock_client.invoke_model.call_count == 3


# ---------------------------------------------------------------------------
# Tests: invoke_reasoning (malformed response)
# ---------------------------------------------------------------------------


class TestInvokeReasoningMalformed:
    """Tests for malformed response handling."""

    def test_malformed_response_returns_empty_plan(self):
        """Malformed (empty content) response should return empty plan."""
        mock_client = MagicMock()

        # Response with empty content list
        body_content = json.dumps({"content": []}).encode()
        body_stream = io.BytesIO(body_content)
        mock_client.invoke_model.return_value = {"body": body_stream}

        reasoning_client = BedrockReasoningClient(client=mock_client)
        request = _make_request()

        result = reasoning_client.invoke_reasoning(request)

        assert isinstance(result, ReasoningResponse)
        assert result.actions == []
        assert result.confidence == 0.0
