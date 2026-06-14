# Implementation Plan: Demo Backend Integration

## Overview

Connect the existing Three.js demo frontend (`demo/`) to the existing Python backend (`alexa-thinks-ahead/`) for a live, end-of-day presentation. The build order is sequenced for the fastest path to a working demo: extract the shared device-state source first (unblocks the backend), add the HTTP/CORS/routing layer, fill in real response bodies, wire the live power-cut scenario, then connect the frontend and add the live animation path with a scripted fallback.

Languages are already fixed by the design: **Python 3.10** (backend, stdlib `http.server` + pytest/Hypothesis) and **JavaScript** (frontend, Vite + Vitest + fast-check). No language selection needed.

Each task is scoped to roughly 15–30 minutes. Sub-tasks marked with `*` are optional polish/verification and can be skipped under time pressure.

Use Claude Opus 4.8 when getting confused or getting hallucinated or tacking js code

## Tasks

- [x] 1. Extract shared device-state source (unblocks backend, avoids circular import)
  - [x] 1.1 Create `alexa-thinks-ahead/src/devices/demo_states.py`
    - Move the `DEMO_STATES` dict (per-device simulated property values) out of `demo.py` into a new module-level `DEMO_STATES` constant in `src/devices/demo_states.py`
    - Single source of truth importable by both `demo.py` and `src/handlers/api_handler.py` without a circular import
    - _Requirements: 3.4, 4.2, 5.2_

  - [x] 1.2 Point `demo.py` `SimulatedAdapter` at the shared module
    - Replace the inline `DEMO_STATES` in `demo.py` with `from src.devices.demo_states import DEMO_STATES`
    - Verify `SimulatedAdapter` and `create_simulated_adapters()` still resolve state correctly
    - _Requirements: 3.4_

- [x] 2. Backend HTTP layer in `demo.py` `DemoHandler`
  - [x] 2.1 Add CORS preflight + `/api/v1` prefix strip + path-param dispatch
    - Add `CORS_HEADERS`, `API_PREFIX`, and `_strip_prefix(path)` helper
    - Implement `do_OPTIONS` → 204, empty body, CORS headers
    - Update `do_GET`/`do_POST`/`do_PUT` to strip the prefix and parse `{id}` / `{device}` segments relative to the stripped path before calling `lambda_handler`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 2.2 Example test: OPTIONS preflight and CORS headers
    - In `alexa-thinks-ahead/tests/test_cors.py`: assert OPTIONS returns 204 with `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Methods` (GET, POST, PUT, OPTIONS), `Access-Control-Allow-Headers` containing `Content-Type`
    - **Property 3: Every non-OPTIONS response carries the CORS allow-origin header** (single-execution example for the OPTIONS case)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Backend response bodies in `src/handlers/api_handler.py`
  - [x] 3.1 Device list + single device state handlers
    - Import `DEVICE_CONFIGS` and `DEMO_STATES`; add `_device_entry(cfg)` helper (`id`, `name`, `category`, `room`←`location`, `brand`, `state`←`DEMO_STATES`)
    - `handle_get_devices` → `{devices:[…], count}`; `handle_get_device_state` → entry or 404 `{error}` for unknown id
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3_

  - [x] 3.2 Context snapshot handler
    - `handle_get_snapshot` → `{timestamp (ISO 8601), deviceStates:[{id,state}], activeActivities, environmentals:{temperature,humidity,powerGrid}}`, one `deviceStates` entry per `DEVICE_CONFIGS`
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 3.3 Patterns, tiers, and tier-update handlers
    - `handle_get_patterns` → `{patterns:[…]}` with ≥1 entry, each `{id, confidence, schedule, actions}`
    - `handle_get_tiers` → `{tiers:[…]}`, one `{category, currentTier, trustScore}` per distinct category in `DEVICE_CONFIGS`
    - `handle_update_tier` → 200 `{success, device, currentTier}` or 400 `{error}` when `tier` is omitted
    - _Requirements: 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 3.4 Property tests: routing parity + body schema coverage
    - In `alexa-thinks-ahead/tests/test_api_handlers.py` (pytest + Hypothesis, ≥100 iterations, tagged `Feature: demo-backend-integration`):
    - **Property 1: Versioned and unversioned paths route identically** — _Validates: Requirements 1.1–1.7_
    - **Property 2: Unknown paths return 404 with an error field** — _Validates: Requirements 1.8_
    - **Property 4: Device list covers every config with required fields and sourced state** — _Validates: Requirements 3.1–3.5_
    - **Property 5: Single device state resolves present ids and rejects absent ids** — _Validates: Requirements 4.1–4.3_
    - **Property 6: Snapshot covers every config and has well-formed structure** — _Validates: Requirements 5.1–5.4_
    - **Property 7: Patterns are non-empty and fully formed** — _Validates: Requirements 6.1–6.3_
    - **Property 8: Tiers cover every category with required fields** — _Validates: Requirements 7.1–7.3_
    - **Property 9: Tier update validates the request body** — _Validates: Requirements 7.4, 7.5_

- [x] 4. Backend live power-cut scenario
  - [x] 4.1 Add `POST /scenario/power-cut` route and handler
    - Add the route before the 404 fallthrough in `lambda_handler`
    - Implement `handle_power_cut_scenario`: build simulated adapters + mocked reasoning (`create_simulated_adapters()`, `mock_power_cut_response()` from `demo.py`), run `ContextualEventHandler.handle_event` with a `power_cut` event
    - Return 200 `{actions:[{target_devices, strategy, confidence, reasoning}], explanation, reasoning_chain}`; 500 `{error}` on pipeline failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 4.2 Scenario wiring tests (example + property)
    - In `alexa-thinks-ahead/tests/test_scenario.py`: assert handler is invoked with a `power_cut` event (Req 8.1); injected handler failure returns 500 (Req 8.4); integration test asserts 200 with `actions`/`explanation`/`reasoning_chain`
    - **Property 10: Scenario response includes required fields for every action** — _Validates: Requirements 8.2, 8.3_

- [x] 5. Frontend data layer
  - [x] 5.1 Confirm `DataLayer` default mock + manual toggle
    - Verify `DataLayer` initializes Mode to `mock`, routes to `MockProvider` in mock mode and `ApiProvider` in real mode, and that `setMode` flips the active Mode
    - Adjust only if the existing behavior diverges from Requirement 9
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 5.2 `ApiProvider` normalization + `runPowerCutScenario`
    - Add thin normalization in `ApiProvider` so `getDevices`/`getContextSnapshot`/`getPatterns`/`getAutonomyTiers` return the `MockProvider`/`schemas.js` shapes (default absent arrays to `[]`, return device entry object directly)
    - Add `runPowerCutScenario()` → `POST /api/v1/scenario/power-cut`
    - _Requirements: 10.1, 10.2, 11.1_

  - [x] 5.3 Frontend property tests: mode routing + reshape
    - In `demo/src/data/` (Vitest + fast-check):
    - **Property 11: Data layer routes requests by mode** (reuse existing `DataLayer.test.js`) — _Validates: Requirements 9.1–9.4_
    - **Property 12: Reshaped responses conform to the mock shape** (new `ApiProvider.test.js`, generate backend payloads) — _Validates: Requirements 10.1, 10.2_

- [x] 6. Frontend live scenario wiring
  - [x] 6.1 Wire power-cut control to POST + animate from real action plan
    - In real mode, the power-cut control calls `apiProvider.runPowerCutScenario()`, then maps each action's `target_devices` to the existing `FloorPlan2D` effect calls (`inverterGlow`, `dimRooms`, `highlightDevice`, `restoreRooms`)
    - Push actions to `EventLog` via `stateStore.addEventLogEntry(...)`; render `explanation` in `ReasoningPanel` and surface family-facing lines via `floorPlan.showSpeechBubble(...)`
    - _Requirements: 11.1, 11.2, 11.3_

  - [x] 6.2 Error indication + scripted fallback on failure
    - On a failed scenario POST, show an error indication and fall back to the existing scripted `PowerCutScenario` so the demo never stalls
    - Mock mode continues to run the scripted scenario unchanged
    - _Requirements: 11.4_

  - [x] 6.3 Frontend scenario tests (example + property)
    - In `demo/src/scene/PowerCutScenario.test.js` (scene layer mocked): power-cut control issues a POST (Req 11.1); explanation text renders (Req 11.3); failed request shows an error indication and falls back to the scripted scenario (Req 11.4)
    - **Property 13: Every targeted device in the plan is animated** — _Validates: Requirements 11.2_

- [x] 7. Checkpoint and end-to-end validation
  - [x] 7.1 Checkpoint — run backend and frontend test suites
    - Ensure backend (`pytest`) and frontend (`npm run test`) suites pass. Ensure all tests pass, ask the user if questions arise.

  - [x] 7.2 Manual end-to-end smoke test (presenter, manual)
    - Manual steps (not a coding-agent task): start backend `python3 demo.py --api`, start frontend `npm run dev`, toggle to real mode, trigger the power cut, confirm the 3D scene animates from the real action plan and the explanation renders
    - _Requirements: 9.4, 11.1, 11.2, 11.3, 11.4_

## Notes

- Tasks marked with `*` are optional verification/polish and can be skipped under time pressure; core implementation tasks (no `*`) must be done for a working demo.
- Build order is dependency-driven: shared state (1) → HTTP/CORS layer (2) → response bodies (3) → scenario (4) → frontend data (5) → frontend wiring (6) → validation (7).
- Each task references specific requirement sub-clauses for traceability; property test tasks reference the correctness properties (1–13) from the design.
- Property tests carry input-coverage; example tests cover fixed behaviors (OPTIONS headers, scenario wiring) that do not vary with input.

### Intersection with `alexa-thinks-ahead-3d-demo` spec

- **Task 10.3 (integration tests for full workflow):** Tasks 6.1–6.3 here extend that coverage by exercising the power-cut visual-effect sequence against a *real* backend action plan, not just the scripted scenario.
- **Task 11 (final checkpoint):** Wiring the real backend (tasks 1–6) is a prerequisite for that end-to-end validation gate. The mock/real toggle (task 5.1, Requirement 9) keeps the 3D demo's existing mock-based tests passing unchanged, since mock remains the default.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "5.1"] },
    { "id": 1, "tasks": ["1.2", "5.2"] },
    { "id": 2, "tasks": ["2.1", "3.1", "6.1"] },
    { "id": 3, "tasks": ["2.2", "3.2", "6.2"] },
    { "id": 4, "tasks": ["3.3", "5.3"] },
    { "id": 5, "tasks": ["4.1"] },
    { "id": 6, "tasks": ["3.4", "4.2", "6.3"] },
    { "id": 7, "tasks": ["7.2"] }
  ]
}
```
