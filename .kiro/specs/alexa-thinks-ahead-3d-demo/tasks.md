# Implementation Plan: Alexa Thinks Ahead 3D Demo

## Overview

Build a single-page 3D interactive demo using Vite, Vanilla JS, and Three.js that visualizes the "Alexa Thinks Ahead" proactive smart home system. The implementation follows an incremental approach: project scaffolding → core modules (scene, simulation, data) → UI panels → effects and scenarios → integration and wiring.

## Tasks

- [x] 1. Project scaffolding and core infrastructure
  - [x] 1.1 Initialize Vite project with Vanilla JS and install dependencies
    - Run `npm create vite@latest` with vanilla template in `demo/`
    - Install Three.js via npm: `three`
    - Create `vite.config.js` with manual chunks for `three` and `three/addons`
    - Create directory structure: `src/scene/`, `src/simulation/`, `src/data/`, `src/ui/`, `src/utils/`, `src/styles/`
    - Create `index.html` with container divs for 3D scene, panels, overlays
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Create utility modules (constants, eventBus, helpers)
    - Create `src/utils/constants.js` with COLORS, MATERIALS factories, timing constants, and room definitions
    - Create `src/utils/eventBus.js` with pub/sub EventBus class and EVENTS enum
    - Create `src/utils/helpers.js` with time formatting and interpolation utilities
    - _Requirements: 1.4_

  - [x] 1.3 Create base CSS styles with glassmorphism and dark theme
    - Create `src/styles/main.css` with CSS custom properties (--color-accent: #00CAFF, dark background)
    - Create `src/styles/glassmorphism.css` with `.glass-panel`, `.btn-accent`, `.btn-deploy` classes
    - Create `src/styles/panels.css` with layout styles for learning/deployment phases
    - Apply Inter font via Google Fonts link in index.html
    - _Requirements: 1.3, 1.4, 1.5_

- [x] 2. Data layer implementation
  - [x] 2.1 Implement MockProvider with all device data
    - Create `src/data/MockProvider.js` with full device list (10 devices), `getDevices()`, `getDeviceState()`, `sendCommand()`, `getContextSnapshot()`, `getPatterns()`, `getAutonomyTiers()`, `updateTier()`
    - Create `src/data/schemas.js` with JSDoc type definitions for API responses
    - _Requirements: 2.1, 2.5_

  - [x] 2.2 Implement ApiProvider for real backend
    - Create `src/data/ApiProvider.js` with HTTP client targeting `http://localhost:8080`
    - Implement all provider methods using fetch API with error handling
    - _Requirements: 2.3_

  - [x] 2.3 Implement DataLayer with mode toggle
    - Create `src/data/DataLayer.js` with mode switching ('mock' | 'real')
    - Delegate all calls to active provider
    - Default to 'mock' mode on initialization
    - _Requirements: 2.2, 2.4, 2.5_

  - [x] 2.4 Write property tests for data layer mode routing
    - **Property 1: Data layer mode routing**
    - **Property 2: Mock data schema conformance**
    - **Validates: Requirements 2.1, 2.3, 2.4**

- [x] 3. Simulation engine
  - [x] 3.1 Implement SimulationEngine with clock and tick loop
    - Create `src/simulation/SimulationEngine.js` with time tracking (0–1439 minutes), speed multiplier, start/pause/resume/seekTo methods
    - Use `requestAnimationFrame` for tick loop
    - Implement listener registration (onTick/offTick) for time updates
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.6_

  - [x] 3.2 Implement StateStore for device and family state
    - Create `src/simulation/StateStore.js` with Maps for devices, familyPositions, trustScores
    - Implement event log array with chronological entries
    - Implement pub/sub listener pattern (on/emit) for state changes
    - Implement `calculateTier()` mapping scores to tiers 1–5
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 3.3 Implement EventScheduler and ProactiveActions
    - Create `src/simulation/EventScheduler.js` that evaluates scheduled actions against current time
    - Create `src/simulation/ProactiveActions.js` with all proactive action definitions (geyser pre-heat, pre-cooling, security arm, energy optimization, comfort lighting)
    - Fire events via eventBus when trigger times are reached
    - Update trust scores on each action execution
    - _Requirements: 8.1, 8.3, 9.2_

  - [x] 3.4 Write property tests for simulation engine
    - **Property 7: Speed multiplier clock advancement**
    - **Property 8: Scrubber-simulation time bidirectional sync**
    - **Property 9: Pause and resume controls clock**
    - **Validates: Requirements 7.5, 7.6, 14.1–14.6**

  - [x] 3.5 Write property tests for StateStore tier calculation
    - **Property 11: Trust score maps to correct tier**
    - **Validates: Requirements 9.3**

- [x] 4. Checkpoint - Ensure core modules work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. 3D scene setup
  - [x] 5.1 Implement SceneManager with Three.js renderer and controls
    - Create `src/scene/SceneManager.js` with PerspectiveCamera (isometric-like angle at position 12,10,12), WebGLRenderer with antialiasing and shadows, OrbitControls with damping
    - Set up CSS2DRenderer for speech bubble overlays
    - Implement resize handler and animation loop
    - _Requirements: 5.5, 5.6, 15.1_

  - [x] 5.2 Implement HouseBuilder with low-poly geometry
    - Create `src/scene/HouseBuilder.js` that builds floor, exterior/interior walls, roof (cutaway), and basic furniture using box/cylinder primitives
    - Create `src/scene/RoomDefinitions.js` with room bounding boxes, positions, names for 7 rooms
    - Merge static geometry into BufferGeometry for performance
    - _Requirements: 5.1, 5.2, 5.3, 15.2_

  - [x] 5.3 Implement DeviceIndicators with room placement
    - Create `src/scene/DeviceIndicators.js` that creates sphere/cylinder meshes for 10 devices
    - Place devices in assigned rooms per the device-room mapping
    - Add label sprites for device identification
    - Implement `getMesh(deviceId)` and `getAllRoomLights()` accessors
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

  - [x] 5.4 Implement LightingSystem with day/night cycle
    - Create `src/scene/LightingSystem.js` with AmbientLight + DirectionalLight
    - Implement `updateForTime(timeMinutes)` with sunrise/sunset transitions
    - Use 30-minute interpolation windows at 06:00 and 18:00
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 5.5 Write property tests for lighting system
    - **Property 12: Lighting matches time of day**
    - **Property 13: Lighting transition interpolation**
    - **Validates: Requirements 10.1, 10.2, 10.3**

  - [x] 5.6 Implement AvatarManager with family schedule
    - Create `src/scene/AvatarManager.js` with CapsuleGeometry avatars for 6 family members
    - Implement `updatePositions(timeMinutes, schedule)` with smooth lerp movement
    - Include FAMILY_SCHEDULE data with per-member room assignments throughout the day
    - Hide avatars when family member is "away"
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.7 Write property test for avatar positioning
    - **Property 6: Avatar position matches schedule**
    - **Validates: Requirements 6.2**

- [x] 6. Checkpoint - Ensure 3D scene renders correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. UI panels implementation
  - [x] 7.1 Implement UIManager with phase transitions
    - Create `src/ui/UIManager.js` with phase state ('learning' | 'deployment')
    - Implement `deploy()` method that transitions phase and starts simulation
    - Wire up panel initialization and show/hide logic
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 7.2 Write property test for phase navigation
    - **Property 3: No backward phase navigation**
    - **Validates: Requirements 3.4**

  - [x] 7.3 Implement LearningPanel with event form
    - Create `src/ui/LearningPanel.js` with event configuration form (type, time, room selects)
    - Pre-populate default Sharma family events
    - Implement addEvent/removeEvent with list rendering
    - Include "Deploy →" button at bottom
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 7.4 Write property tests for event list management
    - **Property 4: Event addition grows list**
    - **Property 5: Event removal shrinks list**
    - **Validates: Requirements 4.5, 4.6**

  - [x] 7.5 Implement DeploymentPanel with timeline and speed controls
    - Create `src/ui/DeploymentPanel.js` with timeline scrubber (range input 0–1439), time display, play/pause button, speed control buttons (1x, 10x, 60x, 120x)
    - Bind scrubber to simulation seekTo, bind speed buttons to setSpeed
    - Update scrubber position on simulation tick
    - _Requirements: 7.2, 7.4, 7.5, 7.6, 14.5_

  - [x] 7.6 Implement EventLog sidebar
    - Create `src/ui/EventLog.js` that listens to StateStore 'eventlog' events
    - Render chronological entries with action name, device, reasoning, timestamp
    - Auto-scroll to latest entry
    - _Requirements: 7.3, 8.1_

  - [x] 7.7 Implement TrustGauges component
    - Create `src/ui/TrustGauges.js` that displays gauge for each device category
    - Listen to StateStore trust updates and animate gauge value changes
    - Show tier number (1–5) alongside score
    - _Requirements: 9.1, 9.2, 9.3_

  - [x] 7.8 Write property test for event log entries
    - **Property 10: Event log entries contain required fields**
    - **Validates: Requirements 8.1**

- [x] 8. Effects and speech bubbles
  - [x] 8.1 Implement Effects module (glow, flicker, dim)
    - Create `src/scene/Effects.js` with `highlightDevice()` pulse animation, `powerCutFlicker()` overlay, `inverterGlow()` with PointLight, `dimRooms()` for selective power
    - _Requirements: 8.2, 12.2, 12.3, 12.5_

  - [x] 8.2 Implement SpeechBubble system with CSS2DRenderer
    - Create `src/scene/SpeechBubble.js` with CSS2DObject-based bubbles
    - Implement `show(position, text, duration)` with 5-second visibility and fade-out
    - Apply glassmorphism styling to bubble elements
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 8.3 Write property test for speech bubble lifetime
    - **Property 14: Speech bubble lifetime**
    - **Validates: Requirements 11.3**

- [x] 9. Power cut scenario
  - [x] 9.1 Implement PowerCutScenario with SENSE-THINK-ACT-EXPLAIN flow
    - Create `src/ui/ReasoningPanel.js` for the reasoning overlay display
    - Implement PowerCutScenario class in `src/simulation/PowerCutScenario.js` with staged execution (SENSE → flicker, THINK → reasoning panel, ACT → inverter glow + dim rooms, EXPLAIN → speech bubbles)
    - Add "⚡ Power Cut" presentation button to DeploymentPanel
    - Log all stages to EventLog with SENSE/THINK/ACT/EXPLAIN labels
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7_

- [ ] 10. Integration and wiring
  - [x] 10.1 Wire all modules together in main.js entry point
    - Create `src/main.js` that bootstraps: SceneManager, SimulationEngine, StateStore, DataLayer, EventScheduler, UIManager, Effects, SpeechBubbleManager, AvatarManager, LightingSystem
    - Connect simulation tick to LightingSystem.updateForTime and AvatarManager.updatePositions
    - Connect eventBus PROACTIVE_ACTION events to Effects.highlightDevice and SpeechBubble.show
    - Connect DataLayer toggle UI to mode switching
    - Wire PowerCutScenario to presentation button
    - _Requirements: 3.3, 7.1, 8.2_

  - [x] 10.2 Implement layout switching between Learning and Deployment phases
    - Learning phase: 30% left panel + 70% 3D scene
    - Deployment phase: full-screen 3D + bottom timeline + right sidebar event log + trust gauges overlay
    - Ensure CSS transitions are smooth between phases
    - _Requirements: 4.1, 4.2, 7.1, 7.2, 7.3_

  - [ ] 10.3 Write integration tests for full workflow
    - Test Learning → Deploy transition starts simulation
    - Test proactive actions fire at correct times and update event log
    - Test power cut scenario triggers all visual effects in sequence
    - _Requirements: 3.3, 8.1, 12.1_

- [ ] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The project uses Vanilla JS with ES modules — no framework
- Three.js addons (OrbitControls, CSS2DRenderer) imported from `three/addons/`
- All geometry should stay well under the 50,000 triangle budget (target ~20,000)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["2.1", "2.2", "3.1", "3.2"] },
    { "id": 3, "tasks": ["2.3", "2.4", "3.3", "3.4", "3.5"] },
    { "id": 4, "tasks": ["5.1", "5.2"] },
    { "id": 5, "tasks": ["5.3", "5.4", "5.6"] },
    { "id": 6, "tasks": ["5.5", "5.7", "7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3", "7.5", "7.6", "7.7"] },
    { "id": 8, "tasks": ["7.4", "7.8", "8.1", "8.2"] },
    { "id": 9, "tasks": ["8.3", "9.1"] },
    { "id": 10, "tasks": ["10.1", "10.2"] },
    { "id": 11, "tasks": ["10.3"] }
  ]
}
```
