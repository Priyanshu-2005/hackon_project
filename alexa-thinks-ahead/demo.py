#!/usr/bin/env python3
"""
Alexa Thinks Ahead - Local Demo Runner
=======================================

Runs the full SENSE → THINK → ACT → EXPLAIN pipeline locally
with simulated devices and a mocked Bedrock response.

No AWS credentials needed. Shows the system working end-to-end.

Usage:
    python3 demo.py                  # Run full power cut demo
    python3 demo.py --scenario all   # Run all demo scenarios
    python3 demo.py --api            # Start local REST API server
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock
import io

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.context.engine import ContextEngine
from src.devices.base import DeviceAdapter
from src.devices.registry import DEVICE_CONFIGS
from src.intelligence.engine import ProactiveEngine
from src.intelligence.event_handler import ContextualEventHandler
from src.autonomy.engine import AutonomyEngine
from src.learning.engine import LearningEngine
from src.reasoning.client import BedrockReasoningClient
from src.reasoning.explainer import ExplanationGenerator
from src.devices.demo_states import DEMO_STATES
from src.models.device import DeviceCategory, DeviceState, DeviceCommand, CommandResult


# ============================================================
# Simulated Device Adapters (realistic demo state)
# ============================================================

class SimulatedAdapter(DeviceAdapter):
    """Simulated device adapter for local demo."""

    DEMO_STATES = DEMO_STATES

    def __init__(self, device_id, device_type, config):
        super().__init__(device_id, device_type, config)
        self._props = dict(self.DEMO_STATES.get(device_id, {}))
        self._last_updated = datetime.now(timezone.utc)

    def get_state(self):
        return DeviceState(
            device_id=self.device_id,
            device_type=self.device_type,
            category=DeviceCategory(self.config["category"]),
            status="online",
            properties=dict(self._props),
            last_updated=self._last_updated,
            battery_level=self._props.get("battery_level"),
        )

    def execute_command(self, command):
        return CommandResult(
            command_id=command.command_id,
            success=True,
            device_id=self.device_id,
            new_state=self.get_state(),
            execution_time_ms=50,
        )

    def subscribe_events(self, callback):
        return f"sub_{self.device_id}"

    def get_capabilities(self):
        return self.config.get("capabilities", [])


def create_simulated_adapters():
    """Create simulated adapters for all 10 devices."""
    adapters = {}
    for cfg in DEVICE_CONFIGS:
        adapters[cfg["device_id"]] = SimulatedAdapter(
            device_id=cfg["device_id"],
            device_type=cfg["device_type"],
            config=cfg,
        )
    return adapters


# ============================================================
# Mocked Bedrock Responses (realistic AI reasoning)
# ============================================================

def mock_power_cut_response():
    """Realistic Bedrock response for power cut scenario."""
    data = {
        "actions": [
            {
                "strategy": "energy_optimization",
                "target_devices": ["inverter_ups"],
                "confidence": 0.95,
                "reasoning": "Power cut detected. Arjun's online tuition is active. Prioritizing Wi-Fi and study room from inverter.",
            },
            {
                "strategy": "energy_optimization",
                "target_devices": ["living_room_ac", "smart_geyser"],
                "confidence": 0.93,
                "reasoning": "Shedding AC and geyser to extend inverter backup from 90min to 150min.",
            },
            {
                "strategy": "comfort_lighting",
                "target_devices": ["smart_lights"],
                "confidence": 0.88,
                "reasoning": "Switching study room to battery-powered warm mode at 70% for Arjun's comfort.",
            },
            {
                "strategy": "storm_preparation",
                "target_devices": ["echo_devices"],
                "confidence": 0.92,
                "reasoning": "Announcing power cut status to family. Reassuring Wi-Fi is prioritized.",
            },
        ],
        "reasoning_chain": (
            "SENSE: Power grid failure detected via inverter switchover signal. "
            "Context: Arjun's online tuition is active (16:00-17:30 weekdays). "
            "Dadaji resting in living room. Priya preparing dinner in kitchen. "
            "Inverter battery at 80%, current load 450W.\n\n"
            "THINK: Priority is internet continuity for Arjun's tuition class. "
            "Shed non-essential loads: AC (comfort, can wait), geyser (not needed now). "
            "Allocate inverter capacity to: Wi-Fi router, study room outlets, study lamp. "
            "Estimated backup at reduced load: 2.5 hours — sufficient for tuition to end at 17:30.\n\n"
            "ACT: (1) Shed AC and geyser, (2) Allocate inverter to priority circuits, "
            "(3) Adjust study room lighting to battery mode 70%, "
            "(4) Announce to household via Echo.\n\n"
            "EXPLAIN: Notify each family member with role-appropriate message."
        ),
        "confidence": 0.93,
        "explanation": (
            "Power cut detected. Inverter is keeping Wi-Fi and study room running "
            "for Arjun's tuition. AC and geyser paused to conserve battery. "
            "Estimated backup: 2.5 hours."
        ),
    }
    body = json.dumps({"content": [{"text": json.dumps(data)}]}).encode()
    return {"body": io.BytesIO(body)}


def mock_power_restore_response():
    """Realistic Bedrock response for power restoration."""
    data = {
        "actions": [
            {
                "strategy": "energy_optimization",
                "target_devices": ["living_room_ac", "smart_geyser", "inverter_ups"],
                "confidence": 0.95,
                "reasoning": "Grid power restored. Re-enabling AC and geyser. Inverter to recharge mode.",
            },
            {
                "strategy": "comfort_lighting",
                "target_devices": ["echo_devices"],
                "confidence": 0.90,
                "reasoning": "Announcing power restoration to family.",
            },
        ],
        "reasoning_chain": (
            "Grid power restored. Gracefully transitioning back to normal operation. "
            "Re-enabling AC for Dadaji's comfort. Geyser back on for evening use. "
            "Inverter switching to recharge mode."
        ),
        "confidence": 0.92,
        "explanation": "Power is back. Resuming normal operation and recharging the inverter.",
    }
    body = json.dumps({"content": [{"text": json.dumps(data)}]}).encode()
    return {"body": io.BytesIO(body)}


def mock_precooling_response():
    """Realistic Bedrock response for pre-cooling scenario."""
    data = {
        "actions": [
            {
                "strategy": "pre_cooling",
                "target_devices": ["living_room_ac"],
                "confidence": 0.87,
                "reasoning": "Dadaji's rest time begins in 30 minutes. Pre-cooling living room to 23°C.",
            },
        ],
        "reasoning_chain": (
            "SENSE: Time is 12:30. Dadaji's daily rest routine starts at 13:00. "
            "Living room temperature is 28°C. AC currently at 24°C in cool mode.\n\n"
            "THINK: Pre-cool to 23°C so room is comfortable when Dadaji lies down. "
            "Confidence high (87%) based on consistent daily pattern over 2 weeks.\n\n"
            "ACT: Set AC to 23°C.\n\n"
            "EXPLAIN: Proactive adjustment for elder comfort."
        ),
        "confidence": 0.87,
        "explanation": "Pre-cooling the living room for Dadaji's afternoon rest.",
    }
    body = json.dumps({"content": [{"text": json.dumps(data)}]}).encode()
    return {"body": io.BytesIO(body)}


# ============================================================
# Demo Runner
# ============================================================

def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_section(text):
    """Print a section divider."""
    print(f"\n{'─'*50}")
    print(f"  {text}")
    print(f"{'─'*50}")


def print_device_states(adapters):
    """Print current state of all devices."""
    print_section("📡 CURRENT DEVICE STATES (10 devices)")
    for device_id, adapter in adapters.items():
        state = adapter.get_state()
        status_icon = "🟢" if state.status == "online" else "🔴"
        print(f"  {status_icon} {device_id:<20} | {state.category.value:<12} | {json.dumps(state.properties)}")


def print_action_plan(result):
    """Print the action plan from pipeline execution."""
    print_section("🧠 AI REASONING (Claude Sonnet)")
    print(f"  {result['explanation']}")
    print()

    print_section("⚡ ACTIONS EXECUTED")
    for i, action in enumerate(result["actions_executed"], 1):
        confidence_bar = "█" * int(action["confidence"] * 10) + "░" * (10 - int(action["confidence"] * 10))
        print(f"  {i}. [{action['action_type']}] {action['strategy']}")
        print(f"     Devices: {', '.join(action['target_devices'])}")
        print(f"     Confidence: [{confidence_bar}] {action['confidence']:.0%}")
        print(f"     Reasoning: {action.get('reasoning', 'N/A')[:80]}...")
        print()


def print_explanations(event, actions, reasoning_chain):
    """Print family-tailored explanations."""
    explainer = ExplanationGenerator()
    explanations = explainer.generate_explanation(
        event=event,
        actions=actions,
        reasoning_chain=reasoning_chain,
        target_members=["Rajesh", "Priya", "Arjun", "Dadaji"],
    )

    print_section("💬 FAMILY ANNOUNCEMENTS (role-tailored)")
    for exp in explanations:
        role_icon = {"parent": "👨‍💼", "child": "👦", "elder": "👴"}.get(
            next((m.role for m in explainer._family.members if m.name == exp.target_member), "parent"),
            "👤"
        )
        print(f"  {role_icon} {exp.target_member} (→ {exp.target_device}):")
        print(f"     \"{exp.message[:120]}\"")
        print()


def run_power_cut_demo():
    """Run the power cut at 5:40pm demo scenario."""
    print_header("🔌 DEMO: Power Cut at 5:40 PM")
    print("  Scenario: Municipal power grid failure during Arjun's online tuition")
    print("  Family: Arjun in study room, Dadaji resting, Priya in kitchen")
    print()

    # Setup
    adapters = create_simulated_adapters()
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_power_cut_response()

    context_engine = ContextEngine(adapters=adapters, table=None)
    reasoning_client = BedrockReasoningClient(client=mock_client)
    proactive_engine = ProactiveEngine(context_engine=context_engine, reasoning_client=reasoning_client)
    handler = ContextualEventHandler(
        context_engine=context_engine,
        proactive_engine=proactive_engine,
        device_adapters=adapters,
    )

    # Show initial state
    print_device_states(adapters)

    # Trigger power cut
    print_section("⚠️  EVENT: Power Cut Detected")
    print("  Source: inverter_ups (grid switchover signal)")
    print("  Time: 17:40 IST")
    print("  Battery: 80%")
    time.sleep(1)

    event = {
        "event_type": "power_cut",
        "source": "inverter_ups",
        "details": {"grid_status": "offline", "battery_level": 80},
    }

    # Execute pipeline
    print_section("🔄 COGNITIVE PIPELINE: SENSE → THINK → ACT → EXPLAIN")
    result = handler.handle_event(event)

    print(f"  ✓ Event classified as: {'🚨 CRITICAL' if result['is_critical'] else 'Normal'}")
    print(f"  ✓ Context snapshot built: 10 devices, activities detected")
    print(f"  ✓ Bedrock reasoning invoked (Claude Sonnet)")
    print(f"  ✓ {len(result['actions_executed'])} actions planned and executed")

    # Show results
    print_action_plan(result)

    # Show explanations
    actions_for_explain = result["actions_executed"]
    print_explanations(event, actions_for_explain, result["explanation"])

    # Power restore
    print_header("⚡ DEMO: Power Restored (50 minutes later)")
    mock_client.invoke_model.return_value = mock_power_restore_response()

    restore_event = {
        "event_type": "power_restored",
        "source": "inverter_ups",
        "details": {"grid_status": "online"},
    }

    restore_result = handler.handle_event(restore_event)
    print_action_plan(restore_result)
    print("  ✅ System gracefully recovered. All devices back to normal.")


def run_precooling_demo():
    """Run the pre-cooling for Dadaji demo."""
    print_header("❄️  DEMO: Pre-Cooling for Dadaji's Rest")
    print("  Scenario: System anticipates Dadaji's 1pm rest and pre-cools the room")
    print()

    adapters = create_simulated_adapters()
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = mock_precooling_response()

    context_engine = ContextEngine(adapters=adapters, table=None)
    reasoning_client = BedrockReasoningClient(client=mock_client)
    proactive_engine = ProactiveEngine(context_engine=context_engine, reasoning_client=reasoning_client)

    print_section("🔄 PROACTIVE EVALUATION (no event - anticipatory)")
    plan = proactive_engine.evaluate_context()

    print(f"  ✓ Context evaluated: 10 devices, patterns detected")
    print(f"  ✓ Prediction: pre_cooling for Dadaji's rest")
    print(f"  ✓ Confidence: {plan.predictions[0].confidence:.0%}")
    print(f"  ✓ Action type: {plan.predictions[0].action_type.value}")
    print(f"\n  Reasoning: {plan.reasoning_chain[:200]}...")


def run_autonomy_demo():
    """Demo the autonomy tier system."""
    print_header("🔒 DEMO: Autonomy Tier System")
    print("  Shows trust building over time through user interactions")
    print()

    engine = AutonomyEngine()

    print_section("Initial State: All members at Tier 1 (Inform)")
    config = engine.get_tier_config()
    print(f"  Rajesh/climate: Tier {config['rajesh_climate']}")
    print(f"  Priya/lighting: Tier {config['priya_lighting']}")

    print_section("Simulating 5 accepted actions for Rajesh/climate...")
    for i in range(5):
        engine.record_acceptance("rajesh", "climate")
        score = engine.trust_manager.get_score("rajesh", "climate")
        tier = engine.tier_manager.determine_tier(score)
        print(f"  Acceptance {i+1}: score={score:.0f}, tier={tier}")

    print_section("Simulating an override...")
    engine.record_override("rajesh", "climate")
    score = engine.trust_manager.get_score("rajesh", "climate")
    tier = engine.tier_manager.determine_tier(score)
    print(f"  Override! score={score:.0f} (-15), tier={tier}")

    print_section("Building up to Tier 3...")
    for i in range(8):
        engine.record_acceptance("rajesh", "climate")
    score = engine.trust_manager.get_score("rajesh", "climate")
    tier = engine.tier_manager.determine_tier(score)
    print(f"  After 8 more acceptances: score={score:.0f}, tier={tier}")
    print(f"  → System can now auto-execute reversible actions for Rajesh's climate devices!")


def run_learning_demo():
    """Demo the continuous learning system."""
    print_header("📊 DEMO: Continuous Learning")
    print("  Shows Bayesian preference learning from feedback")
    print()

    from src.models.learning import FeedbackEvent
    learning = LearningEngine()

    print_section("Processing temperature preference feedback for Rajesh...")
    observations = [24.0, 23.5, 24.5, 24.0, 23.0, 24.0, 24.5, 24.0]
    for i, temp_pref in enumerate(observations):
        # Normalize to [-1, 1] range: 24°C = 0.0, each degree = 0.2
        signal = (temp_pref - 24.0) / 5.0
        feedback = FeedbackEvent(
            event_id=f"fb_{i}",
            member="rajesh",
            feedback_type="temperature_pref",
            context={"device": "living_room_ac"},
            signal_value=signal,
            timestamp=datetime.now(timezone.utc),
        )
        learning.process_feedback(feedback)

    pref = learning.get_preference("rajesh#temperature_pref")
    print(f"  After {len(observations)} observations:")
    print(f"    Mean preference signal: {pref.mean:.4f}")
    print(f"    Variance (uncertainty): {pref.variance:.4f} (started at 10.0)")
    print(f"    Personalization index: {learning.get_personalization_index('rajesh'):.1%}")

    predictions = learning.predict_preference({})
    print(f"\n  Predicted preference (blended with season): {predictions.get('rajesh#temperature_pref', 0):.4f}")
    print(f"  → System is {learning.get_personalization_index('rajesh'):.0%} personalized for Rajesh")



# ============================================================
# CORS and API Routing Helpers
# ============================================================

ALLOWED_ORIGIN = "*"
CORS_HEADERS = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}
API_PREFIX = "/api/v1"


def _strip_prefix(path: str) -> str:
    """Remove the /api/v1 prefix if present so routing is version-agnostic."""
    if path.startswith(API_PREFIX):
        stripped = path[len(API_PREFIX):]
        return stripped if stripped.startswith("/") else "/" + stripped
    return path


def run_api_demo():
    """Start a local Flask-like API server for interactive demo."""
    print_header("🌐 LOCAL API SERVER")
    print("  Starting local REST API for interactive demo...")
    print()

    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from src.handlers.api_handler import lambda_handler
    except ImportError as e:
        print(f"  Error: {e}")
        return

    class DemoHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            """Handle CORS preflight requests: 204, empty body, CORS headers."""
            self.send_response(204)
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            self.end_headers()
            # no body

        def _dispatch(self, http_method, body=""):
            """Strip prefix, parse path params, call lambda_handler, add CORS headers."""
            path = _strip_prefix(self.path)
            event = {"httpMethod": http_method, "path": path, "pathParameters": {}, "body": body}

            # Parse path segments relative to the stripped path
            parts = [p for p in path.split("/") if p]

            # GET /devices/{id}/state
            if http_method == "GET" and len(parts) >= 3 and parts[0] == "devices" and parts[-1] == "state":
                event["pathParameters"] = {"id": parts[1]}
            # POST /devices/{id}/command
            elif http_method == "POST" and len(parts) >= 3 and parts[0] == "devices" and parts[-1] == "command":
                event["pathParameters"] = {"id": parts[1]}
            # PUT /autonomy/tiers/{device}
            elif http_method == "PUT" and len(parts) >= 3 and parts[0] == "autonomy" and parts[1] == "tiers":
                event["pathParameters"] = {"device": parts[-1]}

            result = lambda_handler(event, None)

            self.send_response(result["statusCode"])
            # Include CORS allow-origin on every non-OPTIONS response
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            # Include any additional headers from the lambda response
            for k, v in result.get("headers", {}).items():
                if k not in CORS_HEADERS:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(result["body"].encode())

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length else ""
            self._dispatch("POST", body)

        def do_PUT(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode() if content_length else ""
            self._dispatch("PUT", body)

        def log_message(self, format, *args):
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    port = 8080
    server = HTTPServer(("0.0.0.0", port), DemoHandler)
    print(f"  ✅ Server running at http://localhost:{port}")
    print()
    print("  Available endpoints:")
    print(f"    GET  http://localhost:{port}/api/v1/devices")
    print(f"    GET  http://localhost:{port}/api/v1/devices/living_room_ac/state")
    print(f"    POST http://localhost:{port}/api/v1/devices/living_room_ac/command")
    print(f"    GET  http://localhost:{port}/api/v1/context/snapshot")
    print(f"    GET  http://localhost:{port}/api/v1/context/patterns")
    print(f"    GET  http://localhost:{port}/api/v1/autonomy/tiers")
    print(f"    PUT  http://localhost:{port}/api/v1/autonomy/tiers/climate")
    print(f"    POST http://localhost:{port}/api/v1/scenario/power-cut")
    print()
    print("  (Paths without /api/v1 prefix also work for backward compatibility)")
    print()
    print("  Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Alexa Thinks Ahead - Local Demo")
    parser.add_argument(
        "--scenario",
        choices=["power_cut", "precooling", "autonomy", "learning", "all"],
        default="power_cut",
        help="Demo scenario to run (default: power_cut)",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start local REST API server on port 8080",
    )
    args = parser.parse_args()

    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + "  🏠 ALEXA THINKS AHEAD - Proactive Smart Home System".center(68) + "║")
    print("║" + "  HackOn with Amazon Season 6.0".center(68) + "║")
    print("╚" + "═"*68 + "╝")

    if args.api:
        run_api_demo()
    elif args.scenario == "all":
        run_power_cut_demo()
        print("\n\n")
        run_precooling_demo()
        print("\n\n")
        run_autonomy_demo()
        print("\n\n")
        run_learning_demo()
    elif args.scenario == "power_cut":
        run_power_cut_demo()
    elif args.scenario == "precooling":
        run_precooling_demo()
    elif args.scenario == "autonomy":
        run_autonomy_demo()
    elif args.scenario == "learning":
        run_learning_demo()

    print("\n" + "─"*70)
    print("  Demo complete. No AWS credentials were needed for this local demo.")
    print("  To deploy to AWS: sam build && sam deploy --guided")
    print("─"*70 + "\n")


if __name__ == "__main__":
    main()
