"""Tests for the POST /scenario/power-cut endpoint and scenario pipeline.

Example tests:
- Req 8.1: Handler is invoked with a power_cut event
- Req 8.4: Injected handler failure returns 500 with {"error": "scenario pipeline failed"}
- Integration: 200 with actions/explanation/reasoning_chain

Property 10: Scenario response includes required fields for every action
- Validates: Requirements 8.2, 8.3
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.handlers.api_handler import lambda_handler, handle_power_cut_scenario


# ============================================================
# Example Test 1 (Req 8.1): Handler invoked with power_cut event
# ============================================================

class TestScenarioHandlerInvocation:
    """Assert handler is invoked with a power_cut event (Req 8.1)."""

    def test_scenario_endpoint_invokes_event_handler_with_power_cut(self):
        """POST /scenario/power-cut invokes ContextualEventHandler.handle_event
        with an event containing event_type: 'power_cut'.
        """
        mock_plan = MagicMock()
        mock_plan.reasoning_chain = "test chain"
        mock_handler_instance = MagicMock()
        mock_handler_instance.handle_event.return_value = {
            "event_type": "power_cut",
            "is_critical": True,
            "plan": mock_plan,
            "actions_executed": [
                {
                    "target_devices": ["inverter_ups"],
                    "strategy": "energy_optimization",
                    "confidence": 0.95,
                    "reasoning": "test reasoning",
                }
            ],
            "explanation": "test explanation",
            "timestamp": "2024-06-13T17:40:00+00:00",
        }

        with patch(
            "src.intelligence.event_handler.ContextualEventHandler",
            return_value=mock_handler_instance,
        ) as MockHandlerClass:
            event = {
                "httpMethod": "POST",
                "path": "/scenario/power-cut",
                "pathParameters": {},
                "body": "",
            }
            result = lambda_handler(event, None)

            # Verify the handler was called
            assert mock_handler_instance.handle_event.called
            # Verify the event passed to handle_event has event_type: "power_cut"
            call_args = mock_handler_instance.handle_event.call_args[0][0]
            assert call_args["event_type"] == "power_cut"

    def test_scenario_route_matches_post_method(self):
        """POST /scenario/power-cut routes to the scenario handler (not 404)."""
        # Run the actual handler (uses mocked reasoning via demo.py)
        event = {
            "httpMethod": "POST",
            "path": "/scenario/power-cut",
            "pathParameters": {},
            "body": "",
        }
        result = lambda_handler(event, None)
        # Should not be a 404
        assert result["statusCode"] != 404


# ============================================================
# Example Test 2 (Req 8.4): Injected failure returns 500
# ============================================================

class TestScenarioFailure:
    """Injected handler failure returns 500 (Req 8.4)."""

    def test_pipeline_failure_returns_500(self):
        """When create_simulated_adapters raises, scenario returns 500
        with {"error": "scenario pipeline failed"}.
        """
        with patch(
            "demo.create_simulated_adapters",
            side_effect=RuntimeError("simulated failure"),
        ):
            event = {
                "httpMethod": "POST",
                "path": "/scenario/power-cut",
                "pathParameters": {},
                "body": "",
            }
            result = lambda_handler(event, None)

            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert body["error"] == "scenario pipeline failed"

    def test_event_handler_exception_returns_500(self):
        """When ContextualEventHandler.handle_event raises, response is 500."""
        mock_handler_instance = MagicMock()
        mock_handler_instance.handle_event.side_effect = Exception("reasoning failed")

        with patch(
            "src.intelligence.event_handler.ContextualEventHandler",
            return_value=mock_handler_instance,
        ):
            event = {
                "httpMethod": "POST",
                "path": "/scenario/power-cut",
                "pathParameters": {},
                "body": "",
            }
            result = lambda_handler(event, None)

            assert result["statusCode"] == 500
            body = json.loads(result["body"])
            assert body["error"] == "scenario pipeline failed"


# ============================================================
# Integration Test (Req 8.1-8.3): Full pipeline with mocked reasoning
# ============================================================

class TestScenarioIntegration:
    """Integration test: call handle_power_cut_scenario() directly and
    assert 200 with actions/explanation/reasoning_chain (Req 8.1-8.3).
    """

    def test_power_cut_scenario_returns_200_with_required_fields(self):
        """Full integration: scenario returns 200 with correct structure."""
        result = handle_power_cut_scenario()

        assert result["statusCode"] == 200
        body = json.loads(result["body"])

        # Top-level required fields
        assert "actions" in body
        assert "explanation" in body
        assert "reasoning_chain" in body

        # actions is an array
        assert isinstance(body["actions"], list)
        assert len(body["actions"]) > 0

        # explanation and reasoning_chain are strings
        assert isinstance(body["explanation"], str)
        assert len(body["explanation"]) > 0
        assert isinstance(body["reasoning_chain"], str)
        assert len(body["reasoning_chain"]) > 0

        # Each action has target_devices, strategy, confidence
        for action in body["actions"]:
            assert "target_devices" in action
            assert "strategy" in action
            assert "confidence" in action
            assert isinstance(action["target_devices"], list)
            assert isinstance(action["strategy"], str)
            assert isinstance(action["confidence"], (int, float))

    def test_power_cut_scenario_via_lambda_handler(self):
        """Call via lambda_handler with correct event structure."""
        event = {
            "httpMethod": "POST",
            "path": "/scenario/power-cut",
            "pathParameters": {},
            "body": "",
        }
        result = lambda_handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "actions" in body
        assert "explanation" in body
        assert "reasoning_chain" in body

    def test_scenario_actions_have_valid_confidence_range(self):
        """Each action's confidence is between 0 and 1."""
        result = handle_power_cut_scenario()
        body = json.loads(result["body"])

        for action in body["actions"]:
            assert 0 <= action["confidence"] <= 1

    def test_scenario_target_devices_are_nonempty(self):
        """Each action targets at least one device."""
        result = handle_power_cut_scenario()
        body = json.loads(result["body"])

        for action in body["actions"]:
            assert len(action["target_devices"]) > 0


# ============================================================
# Property 10: Scenario response includes required fields
# for every action (Hypothesis, ≥100 iterations)
# ============================================================

class TestScenarioProperty:
    """Property 10: Scenario response includes required fields for every action.

    Feature: demo-backend-integration, Property 10: Scenario response includes required fields

    **Validates: Requirements 8.2, 8.3**

    Since the scenario uses deterministic mocked reasoning, we run it
    multiple times and assert the structural invariants always hold.
    """

    @given(run_index=st.integers(min_value=0, max_value=999))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        deadline=None,
    )
    def test_property_scenario_response_always_has_required_fields(self, run_index):
        """Property 10: Every invocation of the scenario returns actions,
        explanation, and reasoning_chain. Every action has target_devices (list),
        strategy (string), and confidence (number).

        Feature: demo-backend-integration, Property 10: Scenario response includes required fields
        """
        result = handle_power_cut_scenario()

        # Response status is 200
        assert result["statusCode"] == 200

        body = json.loads(result["body"])

        # Top-level fields present
        assert "actions" in body, "Response must include 'actions'"
        assert "explanation" in body, "Response must include 'explanation'"
        assert "reasoning_chain" in body, "Response must include 'reasoning_chain'"

        # Type checks on top-level fields
        assert isinstance(body["actions"], list), "'actions' must be an array"
        assert isinstance(body["explanation"], str), "'explanation' must be a string"
        assert isinstance(body["reasoning_chain"], str), "'reasoning_chain' must be a string"

        # Non-empty actions
        assert len(body["actions"]) > 0, "'actions' must contain at least one action"

        # Every action has required fields with correct types
        for i, action in enumerate(body["actions"]):
            assert "target_devices" in action, f"Action {i} must have 'target_devices'"
            assert "strategy" in action, f"Action {i} must have 'strategy'"
            assert "confidence" in action, f"Action {i} must have 'confidence'"

            assert isinstance(
                action["target_devices"], list
            ), f"Action {i} 'target_devices' must be a list"
            assert isinstance(
                action["strategy"], str
            ), f"Action {i} 'strategy' must be a string"
            assert isinstance(
                action["confidence"], (int, float)
            ), f"Action {i} 'confidence' must be a number"
