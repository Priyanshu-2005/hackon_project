# Design Document

## Overview

This design connects the existing Three.js demo frontend (`demo/`) to the existing Python backend (`alexa-thinks-ahead/`) to produce a working local prototype for a live presentation. It is deliberately pragmatic and minimal: it reuses code that already exists on both sides and avoids redesigning either system.

The strategy is "meet in the middle":

- **Backend** gains three small capabilities — `/api/v1` prefix routing, a CORS preflight handler, and real response bodies sourced from the already-defined simulated device states and device registry.
- **Frontend** keeps its existing mock/real toggle (defaulting to mock for a deterministic demo) and adds light response normalization in `ApiProvider` plus a wire from the power-cut control to a new scenario endpoint.
- A **live power-cut scenario** is driven by the real backend pipeline (`ContextualEventHandler`) using the same deterministic mocked reasoning already present in `demo.py`.

The frontend `MockProvider`, `schemas.js`, and `DataLayer` already define the target data shapes. The backend's job is to match those shapes; the frontend's job is to reshape only where convenient. No database, no AWS credentials, and no new framework are introduced.

### Goals

- Every `/api/v1/*` path the frontend calls resolves to a real handler.
- Cross-origin requests from the Vite dev server (`:5173`) to the backend (`:8080`) succeed.
- The device, snapshot, patterns, and tiers panels render identically whether in mock or real mode.
- The power-cut button can drive the 3D scene from a genuine backend `Action_Plan`.

### Non-Goals

- No authentication, persistence, or AWS deployment changes.
- No endpoints beyond the set listed in the contract table.
- No redesign of the cognitive pipeline, device registry, or 3D scene modules.

## Architecture

### Component / Data-Flow Overview

```
┌─────────────────────────── demo/ (Vite + Three.js, :5173) ───────────────────────────┐
│                                                                                       │
│   main.js ── DataLayer ──┬── (mode: 'mock') ── MockProvider  ── built-in data         │
│      │                   └── (mode: 'real') ── ApiProvider ──┐ normalize → mock shape │
│      │                                                       │                        │
│   power-cut-btn ── PowerCutScenario ── FloorPlan2D (Effects / SpeechBubble /          │
│      │                EventLog / timeline animation) + ReasoningPanel (explanation)   │
└──────┼───────────────────────────────────────────────────────┼───────────────────────┘
       │ HTTP (fetch, CORS)                                      │ HTTP (fetch, CORS)
       ▼                                                         ▼
┌─────────────────────────── alexa-thinks-ahead/ (:8080) ───────────────────────────────┐
│                                                                                        │
│   demo.py DemoHandler (http.server)                                                    │
│     • do_OPTIONS → 204 + CORS headers           (NEW)                                  │
│     • do_GET / do_POST / do_PUT → build event → lambda_handler                         │
│                                                                                        │
│   src/handlers/api_handler.py  lambda_handler  (prefix-aware routing, rich bodies)     │
│     • GET  /devices            → DEVICE_CONFIGS × SimulatedAdapter.DEMO_STATES          │
│     • GET  /devices/{id}/state → single device + state                                 │
│     • POST /devices/{id}/command                                                       │
│     • GET  /context/snapshot   → deviceStates + environmentals                         │
│     • GET  /context/patterns   → temporal patterns                                     │
│     • GET  /autonomy/tiers      / PUT /autonomy/tiers/{device}                          │
│     • POST /scenario/power-cut → ContextualEventHandler.handle_event   (NEW)           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

Data sources are the ones that already exist:

- `SimulatedAdapter.DEMO_STATES` in `alexa-thinks-ahead/demo.py` — per-device property values.
- `DEVICE_CONFIGS` in `alexa-thinks-ahead/src/devices/registry.py` — device descriptors (`device_id`, `name`, `category`, `location`, `brand`).
- `mock_power_cut_response()` in `demo.py` — deterministic reasoning output for the power-cut pipeline.

### Where the change lands (two thin layers)

1. **`demo.py DemoHandler`** — add `do_OPTIONS`, and make the `do_GET/do_POST/do_PUT` dispatch tolerant of the `/api/v1` prefix (strip it before building the Lambda-style event). This is the smallest change and keeps `api_handler.py` agnostic of the prefix. The path-parameter extraction in `DemoHandler` is adjusted to index relative to the stripped path so `/devices/{id}/state` still parses `id` correctly.

2. **`src/handlers/api_handler.py`** — flesh out the handler bodies so they return the shapes the frontend expects (see Response Schema Mappings), source state from `DEMO_STATES`, and add the `POST /scenario/power-cut` route.

Routing approach: `DemoHandler` strips a leading `/api/v1` (if present) so a single set of route checks in `api_handler.py` serves both the versioned and unversioned forms. This satisfies versioned routing without duplicating the route table.

## Endpoint Contract

All paths are also accepted without the `/api/v1` prefix (the prefix is stripped before routing), preserving the existing unversioned behavior.

| Method | Path (frontend calls) | Handler | Success | Error |
|--------|----------------------|---------|---------|-------|
| OPTIONS | `/api/v1/*` (any) | `DemoHandler.do_OPTIONS` | 204, empty body, CORS headers | — |
| GET | `/api/v1/devices` | `handle_get_devices` | 200 `{devices:[…], count}` | — |
| GET | `/api/v1/devices/{id}/state` | `handle_get_device_state` | 200 device entry | 404 `{error}` if unknown id |
| POST | `/api/v1/devices/{id}/command` | `handle_send_command` | 200 `{success, deviceId, command, timestamp}` | 400 missing `command`; 404 unknown id |
| GET | `/api/v1/context/snapshot` | `handle_get_snapshot` | 200 snapshot | — |
| GET | `/api/v1/context/patterns` | `handle_get_patterns` | 200 `{patterns:[…]}` | — |
| GET | `/api/v1/autonomy/tiers` | `handle_get_tiers` | 200 `{tiers:[…]}` | — |
| PUT | `/api/v1/autonomy/tiers/{device}` | `handle_update_tier` | 200 `{success:true, device, …}` | 400 `{error}` if `tier` omitted |
| POST | `/api/v1/scenario/power-cut` | `handle_power_cut_scenario` | 200 `{actions:[…], explanation, reasoning_chain}` | 500 `{error}` on pipeline failure |
| any | unmatched path | — | — | 404 `{error}` |

Every response (success or error, OPTIONS or not) carries `Access-Control-Allow-Origin: *`.

## Components and Interfaces

### Backend: `DemoHandler` (demo.py)

```python
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

class DemoHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()
        # no body

    def _dispatch(self, http_method, body=""):
        path = _strip_prefix(self.path)
        event = {"httpMethod": http_method, "path": path, "pathParameters": {}, "body": body}
        parts = [p for p in path.split("/") if p]   # index relative to stripped path
        if http_method in ("GET",) and len(parts) >= 3 and parts[0] == "devices" and parts[-1] == "state":
            event["pathParameters"] = {"id": parts[1]}
        elif http_method == "POST" and len(parts) >= 3 and parts[0] == "devices" and parts[-1] == "command":
            event["pathParameters"] = {"id": parts[1]}
        elif http_method == "PUT" and len(parts) >= 3 and parts[0] == "autonomy" and parts[1] == "tiers":
            event["pathParameters"] = {"device": parts[-1]}
        result = lambda_handler(event, None)
        self.send_response(result["statusCode"])
        for k, v in result["headers"].items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(result["body"].encode())
```

`do_GET`, `do_POST`, and `do_PUT` read any body and delegate to `_dispatch`. The CORS headers in `response()` (see below) already set `Access-Control-Allow-Origin` on every Lambda-style response, so non-OPTIONS responses are covered without extra work in the handler.

### Backend: `api_handler.py` routing and bodies

`lambda_handler` keeps its existing structure. Two changes:

1. Add the scenario route before the `404` fallthrough:

```python
elif path == "/scenario/power-cut" and http_method == "POST":
    return handle_power_cut_scenario()
```

2. Replace the placeholder handler bodies with ones that produce the frontend shapes. State is sourced from `SimulatedAdapter.DEMO_STATES`. To avoid a circular import (`demo.py` imports `api_handler`), the demo states are defined as a module-level constant the handler can read — the simplest approach is to move `DEMO_STATES` into a small shared location (e.g. `src/devices/demo_states.py`) and have both `demo.py` and `api_handler.py` import it. This keeps a single source of truth.

```python
from src.devices.registry import DEVICE_CONFIGS
from src.devices.demo_states import DEMO_STATES   # shared simulated states

def _device_entry(cfg):
    return {
        "id": cfg["device_id"],
        "name": cfg["name"],
        "category": cfg["category"],
        "room": cfg["location"],
        "brand": cfg["brand"],
        "state": dict(DEMO_STATES.get(cfg["device_id"], {})),
    }

def handle_get_devices():
    devices = [_device_entry(c) for c in DEVICE_CONFIGS]
    return response(200, {"devices": devices, "count": len(devices)})

def handle_get_device_state(device_id):
    cfg = next((c for c in DEVICE_CONFIGS if c["device_id"] == device_id), None)
    if not cfg:
        return response(404, {"error": f"Device {device_id} not found"})
    return response(200, _device_entry(cfg))

def handle_get_snapshot():
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

def handle_get_patterns():
    return response(200, {"patterns": [
        {"id": "morning_routine",  "confidence": 0.92, "schedule": "07:00",
         "actions": ["geyser_preheat", "lights_warm"]},
        {"id": "evening_cooling",  "confidence": 0.88, "schedule": "17:30",
         "actions": ["ac_precool"]},
        {"id": "security_away",    "confidence": 0.95, "schedule": "09:00",
         "actions": ["lock_arm", "camera_alert"]},
    ]})

def handle_get_tiers():
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

def handle_update_tier(device, body):
    if "tier" not in body:
        return response(400, {"error": "tier field is required"})
    return response(200, {"success": True, "device": device, "currentTier": body["tier"]})
```

### Backend: power-cut scenario handler

Reuses the exact wiring `run_power_cut_demo()` already uses (simulated adapters + `mock_power_cut_response` for deterministic local reasoning), so no AWS calls are made.

```python
def handle_power_cut_scenario():
    try:
        from unittest.mock import MagicMock
        from src.context.engine import ContextEngine
        from src.intelligence.engine import ProactiveEngine
        from src.intelligence.event_handler import ContextualEventHandler
        from src.reasoning.client import BedrockReasoningClient
        # demo.py owns create_simulated_adapters() and mock_power_cut_response()
        from demo import create_simulated_adapters, mock_power_cut_response

        adapters = create_simulated_adapters()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = mock_power_cut_response()

        context_engine = ContextEngine(adapters=adapters, table=None)
        reasoning_client = BedrockReasoningClient(client=mock_client)
        proactive = ProactiveEngine(context_engine=context_engine, reasoning_client=reasoning_client)
        handler = ContextualEventHandler(context_engine, proactive, device_adapters=adapters)

        event = {"event_type": "power_cut", "source": "inverter_ups",
                 "details": {"grid_status": "offline", "battery_level": 80}}
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
```

Note: `result["explanation"]` currently holds the reasoning chain in `event_handler.py`. For the response, `explanation` should be the short family-facing string and `reasoning_chain` the full chain. The handler maps `plan.reasoning_chain` to `reasoning_chain` and uses the plan's explanation field for `explanation`; if the plan exposes only the chain, the short explanation is read from the parsed reasoning output (the `mock_power_cut_response` data includes both an `explanation` and a `reasoning_chain`).

### Frontend: `DataLayer` (unchanged behavior, confirmed)

`DataLayer` already defaults to `'mock'`, exposes `setMode`, and routes through a `provider` getter that returns `ApiProvider` only when `mode === 'real'`. No change required; this design relies on the existing behavior.

### Frontend: `ApiProvider` normalization

`ApiProvider` already targets the correct `/api/v1/*` paths. Add light normalization so backend payloads match the `MockProvider`/`schemas.js` shapes the rest of the app consumes. Because the backend is being shaped to match the frontend, normalization is intentionally thin — mostly pass-through with a few safe coercions (e.g. ensuring `getDeviceState` returns the device entry object directly, defaulting absent arrays to `[]`).

```js
async getDevices() {
  const data = await this.request('GET', '/api/v1/devices');
  return { devices: data.devices ?? [], count: data.count ?? (data.devices?.length ?? 0) };
}

async getContextSnapshot() {
  const d = await this.request('GET', '/api/v1/context/snapshot');
  return {
    timestamp: d.timestamp,
    deviceStates: d.deviceStates ?? [],
    activeActivities: d.activeActivities ?? [],
    environmentals: d.environmentals ?? { temperature: 0, humidity: 0, powerGrid: 'unknown' },
  };
}
// getPatterns / getAutonomyTiers: pass-through; backend already emits the target shape.
```

A new scenario method drives the live demo:

```js
async runPowerCutScenario() {
  return this.request('POST', '/api/v1/scenario/power-cut', {});
}
```

### Frontend: live scenario wiring (main.js / PowerCutScenario)

The power-cut button already calls `powerCutScenario.trigger(...)`. To drive the scene from real data, the click handler (when in real mode) first POSTs to the scenario endpoint, then feeds the returned `actions` into the existing staged execution:

- Map each action's `target_devices` to the existing `FloorPlan2D` effect calls (`inverterGlow`, `dimRooms`, `highlightDevice`, `restoreRooms`) — the same calls the current `_executeAct` override uses.
- Push each action to the `EventLog` via `stateStore.addEventLogEntry(...)` with strategy/reasoning, matching the existing entry shape.
- Show the response `explanation` in the `ReasoningPanel` and surface family-facing lines through `floorPlan.showSpeechBubble(...)`, as the current `_executeExplain` override already does.
- On request failure, display an error indication (e.g. an `EventLog` error entry or a transient banner) and fall back to the existing scripted scenario so the demo never stalls.

In mock mode the existing scripted `PowerCutScenario` runs unchanged, preserving a deterministic fallback for the presentation.

## Data Models

These mirror `demo/src/data/schemas.js` exactly — the backend produces them, the frontend consumes them.

### Response Schema Mappings

**Device entry** (used by `/devices` and `/devices/{id}/state`)

| Frontend field | Source | Notes |
|----------------|--------|-------|
| `id` | `DEVICE_CONFIGS[i].device_id` | |
| `name` | `DEVICE_CONFIGS[i].name` | |
| `category` | `DEVICE_CONFIGS[i].category` | |
| `room` | `DEVICE_CONFIGS[i].location` | registry uses `location`; frontend uses `room` |
| `brand` | `DEVICE_CONFIGS[i].brand` | |
| `state` | `DEMO_STATES[device_id]` | raw simulated properties |

```jsonc
// GET /api/v1/devices
{ "devices": [ { "id": "living_room_ac", "name": "Living Room AC",
  "category": "climate", "room": "living_room", "brand": "Daikin",
  "state": { "power": true, "temperature": 24, "mode": "cool", "fan_speed": "auto" } } ],
  "count": 10 }
```

**Context snapshot** (`/context/snapshot`)

```jsonc
{ "timestamp": "2024-06-13T17:40:00+00:00",
  "deviceStates": [ { "id": "living_room_ac", "state": { "power": true, "temperature": 24 } } ],
  "activeActivities": [ { "member": "Arjun", "activity": "online_tuition", "room": "study_room" } ],
  "environmentals": { "temperature": 34, "humidity": 65, "powerGrid": "stable" } }
```

**Patterns** (`/context/patterns`) — array of `{id, confidence, schedule, actions}`.

**Tiers** (`/autonomy/tiers`) — array of `{category, currentTier, trustScore}`, one per distinct category in `DEVICE_CONFIGS`.

**Power-cut scenario** (`/scenario/power-cut`)

```jsonc
{ "actions": [ { "target_devices": ["inverter_ups"], "strategy": "energy_optimization",
                 "confidence": 0.95, "reasoning": "Power cut detected…" } ],
  "explanation": "Power cut detected. Inverter is keeping Wi-Fi and study room running…",
  "reasoning_chain": "SENSE: … THINK: … ACT: … EXPLAIN: …" }
```

### State shape mismatch note

`MockProvider` device states use slightly different field encodings than `DEMO_STATES` (e.g. `power: 'on'` string vs `power: true` boolean, `colorTemp` vs `color`). For the demo this is acceptable: the panels render whatever fields are present, and the deterministic mock mode is the presentation default. Real mode shows the genuine backend state values. If a specific panel requires identical encodings, normalization can be added in `ApiProvider` per field, but it is out of scope unless a panel visibly breaks.

## Error Handling

| Condition | Status | Body |
|-----------|--------|------|
| Unknown route | 404 | `{"error": "Not found"}` |
| Unknown device id (state) | 404 | `{"error": "Device {id} not found"}` |
| Command missing `command` | 400 | `{"error": "command field is required"}` |
| Tier update missing `tier` | 400 | `{"error": "tier field is required"}` |
| Scenario pipeline raises | 500 | `{"error": "scenario pipeline failed"}` |
| Any uncaught handler error | 500 | `{"error": "Internal server error"}` |

All error responses retain the CORS `Access-Control-Allow-Origin: *` header via `response()`. On the frontend, a failed scenario POST shows an error indication and the demo falls back to the scripted scenario.

## Security Considerations

This is a **local-only prototype** for a live demo. The backend binds to `0.0.0.0:8080` via Python's `http.server` and has **no authentication** — the production design's Bearer-token model is not implemented here.

- `Access-Control-Allow-Origin: *` is acceptable **only** because the server is local, short-lived, and serves no sensitive data (all device state is simulated).
- This configuration must not be deployed to any shared or public network. For anything beyond the local demo, restore the API Gateway + JWT authorizer described in the production plan and replace `*` with the specific frontend origin.
- No secrets are read or transmitted; the power-cut pipeline uses a mocked reasoning client, so no AWS credentials are involved.

## Intersection with the 3D Demo Spec

This feature completes the integration slice left open in the `alexa-thinks-ahead-3d-demo` spec:

- **Task 10.3 (integration tests for full workflow)** — the live power-cut path (Requirement 11) exercises "power cut scenario triggers all visual effects in sequence" against a real backend response, extending what 10.3 covers for the scripted scenario.
- **Task 11 (final checkpoint)** — wiring the real backend is a prerequisite for the end-to-end validation that task 11 gates on. The mock/real toggle (Requirement 9) ensures the 3D demo's existing mock-based tests continue to pass unchanged, since mock remains the default.

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Versioned and unversioned paths route identically

*For any* defined route, a request to its `/api/v1`-prefixed path SHALL produce the same handler dispatch (and non-404 status) as the equivalent unprefixed path, with any `{id}` or `{device}` segment extracted correctly.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

### Property 2: Unknown paths return 404 with an error field

*For any* request whose path matches no defined route, the Backend_API SHALL return HTTP status 404 with a JSON body containing an `error` field.

**Validates: Requirements 1.8**

### Property 3: Every non-OPTIONS response carries the CORS allow-origin header

*For any* endpoint and method combination (including success, 400, 404, and 500 responses), the Backend_API response headers SHALL include `Access-Control-Allow-Origin` with value `*`.

**Validates: Requirements 2.5**

### Property 4: Device list covers every config with required fields and sourced state

*For any* invocation of the device list handler, the response SHALL contain exactly one entry per `Device_Config`; each entry SHALL include `id`, `name`, `category`, `room`, `brand`, and `state`; each `state` SHALL equal the `Simulated_Device_State` for that device id; and `count` SHALL equal the number of entries.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 5: Single device state resolves present ids and rejects absent ids

*For any* device id present in `DEVICE_CONFIGS`, the device state handler SHALL return HTTP 200 with `id`, `name`, `category`, `room`, `brand`, and `state` sourced from the `Simulated_Device_State`; and *for any* id absent from `DEVICE_CONFIGS`, it SHALL return HTTP 404 with a JSON body containing an `error` field.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 6: Snapshot covers every config and has well-formed structure

*For any* invocation of the snapshot handler, the response SHALL include `timestamp` (an ISO 8601 string), `deviceStates`, `activeActivities`, and `environmentals`; `deviceStates` SHALL contain one `{id, state}` per `Device_Config` with `state` sourced from the `Simulated_Device_State`; and `environmentals` SHALL include `temperature`, `humidity`, and `powerGrid`.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Property 7: Patterns are non-empty and fully formed

*For any* invocation of the patterns handler, the response `patterns` array SHALL contain at least one entry, and every entry SHALL include the fields `id`, `confidence`, `schedule`, and `actions`.

**Validates: Requirements 6.1, 6.2, 6.3**

### Property 8: Tiers cover every category with required fields

*For any* invocation of the tiers handler, the response `tiers` array SHALL contain one entry per distinct device category present in `DEVICE_CONFIGS`, and every entry SHALL include `category`, `currentTier`, and `trustScore`.

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 9: Tier update validates the request body

*For any* PUT request body containing a tier value for a device category, the tier update handler SHALL return HTTP 200 with `success` true and the updated `device` category; and *for any* request body omitting the tier value, it SHALL return HTTP 400 with a JSON body containing an `error` field.

**Validates: Requirements 7.4, 7.5**

### Property 10: Scenario response includes required fields for every action

*For any* `Action_Plan` produced by the Event_Handler, the scenario response SHALL include `explanation` and `reasoning_chain`, and every action object SHALL include `target_devices`, `strategy`, and `confidence`.

**Validates: Requirements 8.2, 8.3**

### Property 11: Data layer routes requests by mode

*For any* sequence of mode settings, the Data_Layer SHALL route requests to the Api_Provider when the Mode is `real` and to the Mock_Provider otherwise, with the initial Mode being `mock`.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

### Property 12: Reshaped responses conform to the mock shape

*For any* Backend_API response payload, the Api_Provider-normalized result SHALL conform to the corresponding `MockProvider` schema (the same field names produced in mock mode).

**Validates: Requirements 10.1, 10.2**

### Property 13: Every targeted device in the plan is animated

*For any* `Action_Plan` response received by the Demo_Frontend, every device listed in any action's `target_devices` SHALL trigger a corresponding scene animation invocation.

**Validates: Requirements 11.2**

## Testing Strategy

**Dual approach.** Property tests (≥100 iterations each, tagged `Feature: demo-backend-integration, Property {n}: {text}`) cover the universal rules above. Example and integration tests cover fixed behaviors and wiring.

- **Backend property tests** (pytest + Hypothesis): generate device ids (in/out of registry), arbitrary unmatched paths, and tier-update bodies (with/without `tier`) to drive Properties 1–10. Source-of-truth assertions compare against `DEVICE_CONFIGS` and `DEMO_STATES` directly.
- **Backend example tests**: OPTIONS preflight returns 204 with the three CORS headers (Req 2.1–2.4); scenario endpoint invokes the handler with a `power_cut` event (Req 8.1); injected handler failure returns 500 (Req 8.4).
- **Backend integration test**: one POST to `/scenario/power-cut` with the mocked reasoning client asserts a 200 with `actions`/`explanation`/`reasoning_chain` end-to-end.
- **Frontend property tests** (existing Vitest + fast-check setup in `demo/src/data/`): Property 11 reuses the existing data-layer mode-routing test; Property 12 generates backend payloads and asserts schema conformance; Property 13 generates action plans and asserts each target device triggers an animation call (with the scene layer mocked).
- **Frontend example tests**: power-cut control issues a POST (Req 11.1); explanation text renders (Req 11.3); failed request shows an error indication and falls back to the scripted scenario (Req 11.4).

Unit tests stay focused on edge cases and wiring; property tests carry the bulk of input coverage. Tests for behavior that does not vary with input (OPTIONS headers, scenario wiring) remain single-execution examples rather than property tests.
