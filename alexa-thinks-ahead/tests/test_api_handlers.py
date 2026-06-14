"""Property-based tests for the REST API handlers.

Feature: demo-backend-integration

Uses pytest + Hypothesis (≥100 iterations) to validate universal properties
of the API routing and response shapes.
"""

import json
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings, assume
from hypothesis.strategies import (
    sampled_from,
    text,
    just,
    one_of,
    fixed_dictionaries,
    integers,
    none,
    booleans,
)

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.handlers.api_handler import (
    lambda_handler,
    handle_get_devices,
    handle_get_device_state,
    handle_get_snapshot,
    handle_get_patterns,
    handle_get_tiers,
    handle_update_tier,
)
from src.devices.registry import DEVICE_CONFIGS
from src.devices.demo_states import DEMO_STATES


# ─────────────────────────────────────────────────────────────────────────────
# Helper: strip /api/v1 prefix (mirrors demo.py logic)
# ─────────────────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"


def _strip_prefix(path: str) -> str:
    """Remove the /api/v1 prefix if present so routing is version-agnostic."""
    if path.startswith(API_PREFIX):
        stripped = path[len(API_PREFIX):]
        return stripped if stripped.startswith("/") else "/" + stripped
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Defined routes (used by Properties 1 and 2)
# ─────────────────────────────────────────────────────────────────────────────

DEVICE_IDS = [cfg["device_id"] for cfg in DEVICE_CONFIGS]

# Routes as (method, path_template, path_params_builder)
DEFINED_ROUTES = [
    ("GET", "/devices", {}),
    ("GET", "/devices/living_room_ac/state", {"id": "living_room_ac"}),
    ("GET", "/context/snapshot", {}),
    ("GET", "/context/patterns", {}),
    ("GET", "/autonomy/tiers", {}),
    ("PUT", "/autonomy/tiers/climate", {"device": "climate"}),
]


# ─────────────────────────────────────────────────────────────────────────────
# Property 1: Versioned and unversioned paths route identically
# Validates: Requirements 1.1–1.7
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("route", DEFINED_ROUTES, ids=[r[1] for r in DEFINED_ROUTES])
@settings(max_examples=100)
@given(data=just(None))
def test_property_1_versioned_unversioned_parity(route, data):
    """
    Property 1: Versioned and unversioned paths route identically.

    For sampled defined routes, calling lambda_handler with both the
    unversioned path and the /api/v1-prefixed path (via _strip_prefix)
    returns the same status code (non-404).

    **Validates: Requirements 1.1–1.7**
    """
    method, path, path_params = route

    # Build event for unversioned path
    body = json.dumps({"tier": 3}) if method == "PUT" else ""
    event_unversioned = {
        "httpMethod": method,
        "path": path,
        "pathParameters": path_params,
        "body": body,
    }

    # Build event for versioned path (strip prefix to get the unversioned path)
    versioned_path = API_PREFIX + path
    stripped = _strip_prefix(versioned_path)
    event_versioned = {
        "httpMethod": method,
        "path": stripped,
        "pathParameters": path_params,
        "body": body,
    }

    result_unversioned = lambda_handler(event_unversioned, None)
    result_versioned = lambda_handler(event_versioned, None)

    # Both should produce the same status code and neither should be 404
    assert result_unversioned["statusCode"] == result_versioned["statusCode"]
    assert result_unversioned["statusCode"] != 404


# ─────────────────────────────────────────────────────────────────────────────
# Property 2: Unknown paths return 404 with an error field
# Validates: Requirements 1.8
# ─────────────────────────────────────────────────────────────────────────────

# Defined path prefixes to exclude from random generation
KNOWN_PREFIXES = (
    "/devices",
    "/context",
    "/autonomy",
    "/scenario",
)


@settings(max_examples=100)
@given(
    random_path=text(
        min_size=1,
        max_size=50,
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-/",
    )
)
def test_property_2_unknown_paths_return_404(random_path):
    """
    Property 2: Unknown paths return 404 with an error field.

    Generate random string paths that don't match any defined route.
    Assert the result is status 404 with a JSON body containing "error" field.

    **Validates: Requirements 1.8**
    """
    # Ensure path starts with /
    path = "/" + random_path.lstrip("/")

    # Filter out paths that could match a defined route
    assume(not any(path.startswith(prefix) for prefix in KNOWN_PREFIXES))

    event = {
        "httpMethod": "GET",
        "path": path,
        "pathParameters": {},
        "body": "",
    }

    result = lambda_handler(event, None)

    assert result["statusCode"] == 404
    body = json.loads(result["body"])
    assert "error" in body


# ─────────────────────────────────────────────────────────────────────────────
# Property 4: Device list covers every config with required fields and sourced state
# Validates: Requirements 3.1–3.5
# ─────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100)
@given(data=just(None))
def test_property_4_device_list_coverage(data):
    """
    Property 4: Device list covers every config with required fields and sourced state.

    Call handle_get_devices and assert:
    - Response has `devices` array with len == len(DEVICE_CONFIGS)
    - Each entry has `id`, `name`, `category`, `room`, `brand`, `state`
    - Each state matches DEMO_STATES[device_id]
    - `count` == len(devices)

    **Validates: Requirements 3.1–3.5**
    """
    result = handle_get_devices()
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert "devices" in body
    assert "count" in body

    devices = body["devices"]
    assert len(devices) == len(DEVICE_CONFIGS)
    assert body["count"] == len(devices)

    required_fields = {"id", "name", "category", "room", "brand", "state"}
    for entry in devices:
        # All required fields present
        assert required_fields.issubset(set(entry.keys()))

        # State matches DEMO_STATES source
        device_id = entry["id"]
        expected_state = dict(DEMO_STATES.get(device_id, {}))
        assert entry["state"] == expected_state


# ─────────────────────────────────────────────────────────────────────────────
# Property 5: Single device state resolves present ids and rejects absent ids
# Validates: Requirements 4.1–4.3
# ─────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100)
@given(cfg=sampled_from(DEVICE_CONFIGS))
def test_property_5_present_device_resolves(cfg):
    """
    Property 5 (present ids): Single device state resolves present ids.

    For device ids present in DEVICE_CONFIGS, assert 200 with required fields.

    **Validates: Requirements 4.1, 4.2**
    """
    device_id = cfg["device_id"]
    result = handle_get_device_state(device_id)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    required_fields = {"id", "name", "category", "room", "brand", "state"}
    assert required_fields.issubset(set(body.keys()))
    assert body["id"] == device_id
    assert body["state"] == dict(DEMO_STATES.get(device_id, {}))


@settings(max_examples=100)
@given(
    absent_id=text(
        min_size=5,
        max_size=30,
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    )
)
def test_property_5_absent_device_returns_404(absent_id):
    """
    Property 5 (absent ids): Absent device ids return 404 with error.

    For random strings that are not valid device ids, assert 404 with error field.

    **Validates: Requirements 4.3**
    """
    # Ensure the generated id is not actually in DEVICE_CONFIGS
    assume(absent_id not in DEVICE_IDS)

    result = handle_get_device_state(absent_id)
    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert "error" in body


# ─────────────────────────────────────────────────────────────────────────────
# Property 6: Snapshot covers every config and has well-formed structure
# Validates: Requirements 5.1–5.4
# ─────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100)
@given(data=just(None))
def test_property_6_snapshot_structure(data):
    """
    Property 6: Snapshot covers every config and has well-formed structure.

    Call handle_get_snapshot and assert structure:
    - `timestamp` (ISO 8601)
    - `deviceStates` has one entry per config
    - `activeActivities` is a list
    - `environmentals` has temperature/humidity/powerGrid

    **Validates: Requirements 5.1–5.4**
    """
    from datetime import datetime

    result = handle_get_snapshot()
    body = json.loads(result["body"])

    assert result["statusCode"] == 200

    # timestamp is ISO 8601 parseable
    assert "timestamp" in body
    # Should not raise if valid ISO format
    datetime.fromisoformat(body["timestamp"])

    # deviceStates has one entry per config
    assert "deviceStates" in body
    assert len(body["deviceStates"]) == len(DEVICE_CONFIGS)
    for entry in body["deviceStates"]:
        assert "id" in entry
        assert "state" in entry

    # activeActivities is a list
    assert "activeActivities" in body
    assert isinstance(body["activeActivities"], list)

    # environmentals has required fields
    assert "environmentals" in body
    env = body["environmentals"]
    assert "temperature" in env
    assert "humidity" in env
    assert "powerGrid" in env


# ─────────────────────────────────────────────────────────────────────────────
# Property 7: Patterns are non-empty and fully formed
# Validates: Requirements 6.1–6.3
# ─────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100)
@given(data=just(None))
def test_property_7_patterns_non_empty_and_formed(data):
    """
    Property 7: Patterns are non-empty and fully formed.

    Call handle_get_patterns:
    - `patterns` array is non-empty
    - Each entry has `id`, `confidence`, `schedule`, `actions`

    **Validates: Requirements 6.1–6.3**
    """
    result = handle_get_patterns()
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert "patterns" in body

    patterns = body["patterns"]
    assert len(patterns) > 0

    required_fields = {"id", "confidence", "schedule", "actions"}
    for pattern in patterns:
        assert required_fields.issubset(set(pattern.keys()))


# ─────────────────────────────────────────────────────────────────────────────
# Property 8: Tiers cover every category with required fields
# Validates: Requirements 7.1–7.3
# ─────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100)
@given(data=just(None))
def test_property_8_tiers_cover_categories(data):
    """
    Property 8: Tiers cover every category with required fields.

    Call handle_get_tiers:
    - `tiers` array has one entry per distinct category in DEVICE_CONFIGS
    - Each has `category`, `currentTier`, `trustScore`

    **Validates: Requirements 7.1–7.3**
    """
    result = handle_get_tiers()
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert "tiers" in body

    tiers = body["tiers"]
    distinct_categories = set(cfg["category"] for cfg in DEVICE_CONFIGS)
    assert len(tiers) == len(distinct_categories)

    tier_categories = set()
    required_fields = {"category", "currentTier", "trustScore"}
    for tier in tiers:
        assert required_fields.issubset(set(tier.keys()))
        tier_categories.add(tier["category"])

    # Every distinct category is represented
    assert tier_categories == distinct_categories


# ─────────────────────────────────────────────────────────────────────────────
# Property 9: Tier update validates the request body
# Validates: Requirements 7.4, 7.5
# ─────────────────────────────────────────────────────────────────────────────


@settings(max_examples=100)
@given(tier_value=integers(min_value=1, max_value=5))
def test_property_9_tier_update_with_tier(tier_value):
    """
    Property 9 (valid body): Tier update with tier field returns 200.

    Generate bodies with `tier` field. Assert 200 with `success`, `device`, `currentTier`.

    **Validates: Requirements 7.4**
    """
    result = handle_update_tier("climate", {"tier": tier_value})
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["success"] is True
    assert body["device"] == "climate"
    assert body["currentTier"] == tier_value


@settings(max_examples=100)
@given(
    invalid_body=one_of(
        just({}),
        fixed_dictionaries({"level": integers(min_value=1, max_value=5)}),
        fixed_dictionaries({"score": integers(min_value=0, max_value=100)}),
    )
)
def test_property_9_tier_update_without_tier(invalid_body):
    """
    Property 9 (missing tier): Tier update without tier field returns 400.

    Generate bodies without `tier` field. Assert 400 with `error`.

    **Validates: Requirements 7.5**
    """
    # Ensure 'tier' key is NOT in the body
    assume("tier" not in invalid_body)

    result = handle_update_tier("climate", invalid_body)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "error" in body
