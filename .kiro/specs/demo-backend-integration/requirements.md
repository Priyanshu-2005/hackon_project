# Requirements Document

## Introduction

This feature connects the existing 3D demo frontend (`demo/`, Vite + Vanilla JS + Three.js) to the existing Python backend (`alexa-thinks-ahead/`) to produce a working local prototype for a live presentation by end of day. The integration uses a meet-in-the-middle strategy: the backend gains versioned `/api/v1` routing, a cross-origin preflight handler, and real device data sourced from the simulated adapter states, while the frontend `ApiProvider` performs light reshaping where convenient. A live power-cut scenario is driven by the real backend pipeline through a new scenario endpoint. The frontend keeps a manual mock/real mode toggle that defaults to mock for deterministic presentation.

Scope is limited to the core data views already rendered in the demo panels (devices, autonomy tiers, patterns, context snapshot) plus the live power-cut scenario. Endpoints outside this set are out of scope for this feature.

## Glossary

- **Demo_Frontend**: The Vite + Vanilla JS + Three.js application in `demo/` that renders the 3D home and data panels.
- **Backend_API**: The local REST server started via `python3 demo.py --api`, served by `DemoHandler` on port 8080 and routed by `src/handlers/api_handler.py`.
- **Api_Provider**: The `ApiProvider` class in `demo/src/data/ApiProvider.js` that issues HTTP requests to the Backend_API.
- **Mock_Provider**: The `MockProvider` class in `demo/src/data/MockProvider.js` that returns built-in offline data.
- **Data_Layer**: The `DataLayer` class in `demo/src/data/DataLayer.js` that selects between Mock_Provider and Api_Provider based on the active mode.
- **Mode**: The data source selection, one of "mock" or "real".
- **Simulated_Device_State**: The per-device property values defined in `SimulatedAdapter.DEMO_STATES` in `alexa-thinks-ahead/demo.py`.
- **Device_Config**: A device descriptor from `DEVICE_CONFIGS` in `alexa-thinks-ahead/src/devices/registry.py`, providing `device_id`, `name`, `category`, `location`, and `brand`.
- **Scenario_Endpoint**: The backend endpoint `POST /api/v1/scenario/power-cut`.
- **Event_Handler**: The `ContextualEventHandler` in `alexa-thinks-ahead/src/intelligence/event_handler.py` that runs the SENSE-THINK-ACT-EXPLAIN pipeline.
- **Action_Plan**: The result returned by Event_Handler, containing executed actions, an explanation, and a reasoning chain.

## Requirements

### Requirement 1: Versioned API Routing

**User Story:** As a frontend developer, I want the Backend_API to route the `/api/v1` paths the frontend calls, so that requests resolve instead of returning 404.

#### Acceptance Criteria

1. WHEN the Backend_API receives a GET request for path `/api/v1/devices`, THE Backend_API SHALL route the request to the device list handler.
2. WHEN the Backend_API receives a GET request for a path matching `/api/v1/devices/{id}/state`, THE Backend_API SHALL route the request to the device state handler with the parsed device identifier.
3. WHEN the Backend_API receives a POST request for a path matching `/api/v1/devices/{id}/command`, THE Backend_API SHALL route the request to the command handler with the parsed device identifier.
4. WHEN the Backend_API receives a GET request for path `/api/v1/context/snapshot`, THE Backend_API SHALL route the request to the snapshot handler.
5. WHEN the Backend_API receives a GET request for path `/api/v1/context/patterns`, THE Backend_API SHALL route the request to the patterns handler.
6. WHEN the Backend_API receives a GET request for path `/api/v1/autonomy/tiers`, THE Backend_API SHALL route the request to the tiers handler.
7. WHEN the Backend_API receives a PUT request for a path matching `/api/v1/autonomy/tiers/{device}`, THE Backend_API SHALL route the request to the tier update handler with the parsed device category.
8. IF the Backend_API receives a request for a path that matches no defined route, THEN THE Backend_API SHALL return HTTP status 404 with a JSON body containing an `error` field.

### Requirement 2: Cross-Origin Preflight Support

**User Story:** As a frontend developer, I want cross-origin POST and PUT requests from the Vite dev server to succeed, so that the demo running on port 5173 can call the Backend_API on port 8080.

#### Acceptance Criteria

1. WHEN the Backend_API receives an OPTIONS request for any path, THE Backend_API SHALL return HTTP status 204 with an empty body.
2. WHEN the Backend_API returns a response to an OPTIONS request, THE Backend_API SHALL include the header `Access-Control-Allow-Origin` with value `*`.
3. WHEN the Backend_API returns a response to an OPTIONS request, THE Backend_API SHALL include the header `Access-Control-Allow-Methods` listing GET, POST, PUT, and OPTIONS.
4. WHEN the Backend_API returns a response to an OPTIONS request, THE Backend_API SHALL include the header `Access-Control-Allow-Headers` containing `Content-Type`.
5. WHEN the Backend_API returns any non-OPTIONS response, THE Backend_API SHALL include the header `Access-Control-Allow-Origin` with value `*`.

### Requirement 3: Device List Data

**User Story:** As a presenter, I want the device list endpoint to return rich device data, so that the device panel renders all 10 devices with their real states.

#### Acceptance Criteria

1. WHEN the device list handler processes a request, THE Backend_API SHALL return HTTP status 200 with a JSON body containing a `devices` array and a `count` field.
2. WHEN the device list handler builds the `devices` array, THE Backend_API SHALL include one entry for each Device_Config in `DEVICE_CONFIGS`.
3. WHEN the device list handler builds a device entry, THE Backend_API SHALL include the fields `id`, `name`, `category`, `room`, `brand`, and `state`.
4. WHEN the device list handler populates a device entry `state`, THE Backend_API SHALL use the Simulated_Device_State for the matching device identifier.
5. WHEN the device list handler sets the `count` field, THE Backend_API SHALL set the value equal to the number of entries in the `devices` array.

### Requirement 4: Single Device State Data

**User Story:** As a presenter, I want the device state endpoint to return a single device with its real state, so that device detail views show accurate values.

#### Acceptance Criteria

1. WHEN the device state handler receives a request for a device identifier present in `DEVICE_CONFIGS`, THE Backend_API SHALL return HTTP status 200 with a JSON body containing `id`, `name`, `category`, `room`, `brand`, and `state`.
2. WHEN the device state handler populates the `state` field, THE Backend_API SHALL use the Simulated_Device_State for the requested device identifier.
3. IF the device state handler receives a request for a device identifier absent from `DEVICE_CONFIGS`, THEN THE Backend_API SHALL return HTTP status 404 with a JSON body containing an `error` field.

### Requirement 5: Context Snapshot Data

**User Story:** As a presenter, I want the context snapshot endpoint to return populated state, so that the context panel reflects the live home state.

#### Acceptance Criteria

1. WHEN the snapshot handler processes a request, THE Backend_API SHALL return HTTP status 200 with a JSON body containing `timestamp`, `deviceStates`, `activeActivities`, and `environmentals`.
2. WHEN the snapshot handler builds `deviceStates`, THE Backend_API SHALL include one entry per Device_Config, each containing an `id` field and a `state` field sourced from the Simulated_Device_State.
3. WHEN the snapshot handler sets `timestamp`, THE Backend_API SHALL set the value to an ISO 8601 formatted string.
4. WHEN the snapshot handler sets `environmentals`, THE Backend_API SHALL include the fields `temperature`, `humidity`, and `powerGrid`.

### Requirement 6: Temporal Patterns Data

**User Story:** As a presenter, I want the patterns endpoint to return a populated list, so that the patterns panel displays detected routines.

#### Acceptance Criteria

1. WHEN the patterns handler processes a request, THE Backend_API SHALL return HTTP status 200 with a JSON body containing a `patterns` array.
2. WHEN the patterns handler builds the `patterns` array, THE Backend_API SHALL include at least one pattern entry.
3. WHEN the patterns handler builds a pattern entry, THE Backend_API SHALL include the fields `id`, `confidence`, `schedule`, and `actions`.

### Requirement 7: Autonomy Tiers Data

**User Story:** As a presenter, I want the tiers endpoint to return a tier array, so that the autonomy panel renders per-category tiers and trust scores.

#### Acceptance Criteria

1. WHEN the tiers handler processes a request, THE Backend_API SHALL return HTTP status 200 with a JSON body containing a `tiers` array.
2. WHEN the tiers handler builds the `tiers` array, THE Backend_API SHALL include one entry for each device category present in `DEVICE_CONFIGS`.
3. WHEN the tiers handler builds a tier entry, THE Backend_API SHALL include the fields `category`, `currentTier`, and `trustScore`.
4. WHEN the tier update handler receives a PUT request with a body containing a tier value for a device category, THE Backend_API SHALL return HTTP status 200 with a JSON body containing `success` set to true and the updated `device` category.
5. IF the tier update handler receives a request body that omits the tier value, THEN THE Backend_API SHALL return HTTP status 400 with a JSON body containing an `error` field.

### Requirement 8: Live Power-Cut Scenario

**User Story:** As a presenter, I want a backend endpoint that runs the real power-cut pipeline, so that the 3D demo animates from a genuine Action_Plan during the live presentation.

#### Acceptance Criteria

1. WHEN the Scenario_Endpoint receives a POST request, THE Backend_API SHALL invoke the Event_Handler with a power-cut event.
2. WHEN the Event_Handler produces an Action_Plan, THE Backend_API SHALL return HTTP status 200 with a JSON body containing the executed actions, the explanation, and the reasoning chain.
3. WHEN the Scenario_Endpoint builds the actions in the response, THE Backend_API SHALL include for each action the target devices, the strategy, and the confidence value.
4. IF the Event_Handler raises an error during processing, THEN THE Backend_API SHALL return HTTP status 500 with a JSON body containing an `error` field.

### Requirement 9: Frontend Mode Selection

**User Story:** As a presenter, I want a manual toggle between mock and real data sources, so that I can run a deterministic demo and switch to the live backend on demand.

#### Acceptance Criteria

1. WHEN the Demo_Frontend initializes the Data_Layer, THE Data_Layer SHALL set the Mode to "mock".
2. WHILE the Mode is "mock", THE Data_Layer SHALL route all data requests to the Mock_Provider.
3. WHILE the Mode is "real", THE Data_Layer SHALL route all data requests to the Api_Provider.
4. WHEN the presenter activates the Mode toggle control, THE Demo_Frontend SHALL switch the active Mode between "mock" and "real".

### Requirement 10: Frontend Response Reshaping

**User Story:** As a frontend developer, I want the Api_Provider to reshape backend responses where convenient, so that the rest of the Demo_Frontend consumes the same data shapes the Mock_Provider produces.

#### Acceptance Criteria

1. WHEN the Api_Provider receives a Backend_API response whose shape differs from the Mock_Provider equivalent, THE Api_Provider SHALL transform the response to match the Mock_Provider shape before returning it.
2. WHILE the Mode is "real", THE Demo_Frontend SHALL render the device, snapshot, patterns, and tiers panels using the same field names used in "mock" mode.

### Requirement 11: Live Scenario Animation

**User Story:** As a presenter, I want the Demo_Frontend to trigger the Scenario_Endpoint and animate from its response, so that the audience sees the real pipeline drive the 3D scene.

#### Acceptance Criteria

1. WHEN the presenter activates the power-cut scenario control, THE Demo_Frontend SHALL send a POST request to the Scenario_Endpoint.
2. WHEN the Demo_Frontend receives the Action_Plan response, THE Demo_Frontend SHALL animate the affected devices in the 3D scene according to the actions in the response.
3. WHEN the Demo_Frontend receives the Action_Plan response, THE Demo_Frontend SHALL display the explanation text from the response.
4. IF the Scenario_Endpoint request fails, THEN THE Demo_Frontend SHALL display an error indication to the presenter.
