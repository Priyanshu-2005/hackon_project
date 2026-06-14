# Requirements Document

## Introduction

The "Alexa Thinks Ahead" 3D Interactive Demo is a single-page web application that visualizes the proactive smart home system in action. The application presents an isometric low-poly 3D house with the Sharma family, 10 smart devices, and a two-phase wizard flow (Learning Phase and Deployment Phase). Users configure household events during the Learning Phase, then observe a 24-hour simulated timeline where Alexa proactively manages the home. The demo includes a power cut scenario, speech bubbles from Echo devices, trust score gauges, and day/night lighting transitions. Built with Vite, Vanilla JS, and Three.js, it operates with built-in mock data and an optional toggle to connect to a real backend API at localhost:8080.

## Glossary

- **Demo_App**: The single-page web application built with Vite, Vanilla JS, and Three.js that renders the 3D interactive demo
- **3D_Scene**: The Three.js-rendered isometric low-poly house with rooms, devices, and family avatars
- **Learning_Phase**: The first wizard step where users configure household events and routines before deployment
- **Deployment_Phase**: The second wizard step where the 24-hour timeline simulation runs with proactive Alexa actions
- **Timeline_Scrubber**: The bottom-panel time control that spans 00:00 to 23:59 and allows scrubbing through the simulated day
- **Event_Log**: The right sidebar panel in Deployment Phase that displays chronological proactive actions and system events
- **Data_Layer**: The module responsible for providing device states, context, and patterns from either mock data or a real API
- **Mock_Data**: Built-in JSON data that mirrors the backend API structure for offline operation
- **Real_API**: The backend server running at localhost:8080 providing REST endpoints for device and context data
- **Trust_Score_Gauge**: A visual indicator showing the autonomy trust level per device category
- **Speech_Bubble**: A floating UI element attached to Echo devices displaying Alexa announcements tailored per family member
- **Power_Cut_Scenario**: A demonstration event where a simulated power grid failure triggers proactive inverter management and selective device prioritization
- **Speed_Control**: Playback rate controls (1x, 10x, 60x, 120x) that accelerate or decelerate the timeline simulation
- **Presentation_Button**: A manual trigger button that initiates the power cut scenario during live demos
- **Family_Avatar**: A 3D representation of a Sharma family member positioned within the house rooms
- **Room**: A distinct area within the 3D house model (Balcony, Master Bedroom, Kitchen, Bath, Living Room, Study Room, Kids Room)

## Requirements

### Requirement 1: Project Scaffolding

**User Story:** As a developer, I want the demo application scaffolded with Vite, Vanilla JS, and Three.js in a dedicated folder, so that I can develop and build the application independently from the backend.

#### Acceptance Criteria

1. THE Demo_App SHALL be scaffolded using Vite with Vanilla JS (no framework) in the folder `/media/priyanshu/Data/hackon/hackon_project/alexa-thinks-ahead-3d-demo/`.
2. THE Demo_App SHALL include Three.js installed via npm as a production dependency.
3. THE Demo_App SHALL use Inter or Outfit as the primary font family loaded via Google Fonts or local assets.
4. THE Demo_App SHALL apply a dark mode color scheme with Alexa blue (#00CAFF) as the primary accent color.
5. THE Demo_App SHALL apply glassmorphism styling (frosted glass effects with backdrop-blur, semi-transparent backgrounds) to all UI panels.

### Requirement 2: Data Layer with Mock and Real API Toggle

**User Story:** As a presenter, I want to toggle between built-in mock data and a real backend API, so that the demo works offline and can connect to a live server when available.

#### Acceptance Criteria

1. THE Data_Layer SHALL provide built-in Mock_Data that mirrors the structure of the backend REST API responses for all endpoints (GET /api/v1/devices, GET /api/v1/devices/{id}/state, POST /api/v1/devices/{id}/command, GET /api/v1/context/snapshot, GET /api/v1/context/patterns, GET /api/v1/autonomy/tiers, PUT /api/v1/autonomy/tiers/{device}).
2. THE Data_Layer SHALL include a visible toggle control in the UI that switches between Mock_Data mode and Real_API mode.
3. WHEN the user switches to Real_API mode, THE Data_Layer SHALL send HTTP requests to `http://localhost:8080` for all data operations.
4. WHEN the user switches to Mock_Data mode, THE Data_Layer SHALL return pre-defined mock responses without making network requests.
5. THE Demo_App SHALL default to Mock_Data mode on initial load.

### Requirement 3: Wizard Flow Navigation

**User Story:** As a user, I want a clear two-step wizard flow with a Deploy button transition, so that I can configure events first and then observe the simulation.

#### Acceptance Criteria

1. THE Demo_App SHALL present the Learning_Phase as the initial view on application load.
2. THE Demo_App SHALL display a "Deploy" button that transitions from Learning_Phase to Deployment_Phase.
3. WHEN the user clicks the "Deploy" button, THE Demo_App SHALL transition to Deployment_Phase and begin the 24-hour timeline simulation.
4. THE Demo_App SHALL not allow backward navigation from Deployment_Phase to Learning_Phase without a page reload or explicit reset action.

### Requirement 4: Learning Phase Layout

**User Story:** As a user, I want a split-panel Learning Phase with event configuration on the left and the 3D house on the right, so that I can add events while seeing the house context.

#### Acceptance Criteria

1. THE Learning_Phase SHALL display a left panel occupying 30% of the viewport width containing the event configuration form.
2. THE Learning_Phase SHALL display the 3D_Scene in a right panel occupying 70% of the viewport width.
3. THE left panel SHALL include a form for adding household events with fields for event type, time, location (room), and associated devices.
4. THE left panel SHALL pre-populate default events representing typical Sharma family routines (morning alarms, tuition schedules, work departures, dinner times).
5. WHEN the user submits a new event via the form, THE Demo_App SHALL add the event to the event list displayed below the form.
6. THE left panel SHALL allow users to remove previously added events from the list.

### Requirement 5: 3D House Model

**User Story:** As a viewer, I want to see an isometric low-poly 3D house with a cutaway roof and visible rooms, so that the smart home layout is clearly communicated.

#### Acceptance Criteria

1. THE 3D_Scene SHALL render an isometric low-poly style house model with a warm color palette.
2. THE 3D_Scene SHALL use a cutaway roof design so that all rooms are visible from the default camera angle.
3. THE 3D_Scene SHALL contain seven distinct rooms: Balcony, Master Bedroom, Kitchen, Bath, Living Room, Study Room, and Kids Room.
4. THE 3D_Scene SHALL display device indicators within their assigned rooms according to the specified room-device mapping.
5. THE 3D_Scene SHALL support camera orbit via mouse drag interaction.
6. THE 3D_Scene SHALL support camera zoom via mouse scroll interaction.

### Requirement 6: Family Avatars

**User Story:** As a viewer, I want to see family member avatars positioned in rooms that update based on the timeline, so that I understand where each person is at any given time.

#### Acceptance Criteria

1. THE 3D_Scene SHALL render six Family_Avatars representing Rajesh, Priya, Arjun, Ananya, Dadaji, and Dadiji.
2. WHILE the Deployment_Phase timeline is active, THE 3D_Scene SHALL position each Family_Avatar in the room corresponding to their scheduled location at the current simulation time.
3. THE Family_Avatars SHALL be visually distinguishable from one another through color coding or label indicators.

### Requirement 7: Deployment Phase Layout

**User Story:** As a viewer, I want a full-screen 3D house with timeline controls, event log, and speed controls during Deployment Phase, so that I can observe and control the simulation.

#### Acceptance Criteria

1. THE Deployment_Phase SHALL display the 3D_Scene in full-screen mode as the primary view.
2. THE Deployment_Phase SHALL display the Timeline_Scrubber at the bottom of the viewport spanning the range 00:00 to 23:59.
3. THE Deployment_Phase SHALL display the Event_Log as a right sidebar panel showing chronological proactive actions and system announcements.
4. THE Deployment_Phase SHALL display Speed_Control buttons offering playback rates of 1x, 10x, 60x, and 120x.
5. WHEN the user selects a Speed_Control rate, THE Demo_App SHALL advance the simulation clock at the selected multiplier relative to real time.
6. WHEN the user drags the Timeline_Scrubber, THE Demo_App SHALL jump the simulation to the corresponding time position.

### Requirement 8: Proactive Actions Display

**User Story:** As a viewer, I want to see Alexa's proactive actions (pre-cooling, geyser pre-heat, security arm, energy optimization, comfort lighting) visualized on the 3D house with event log entries, so that the intelligence of the system is clearly demonstrated.

#### Acceptance Criteria

1. WHEN a proactive action triggers at its scheduled time, THE Event_Log SHALL display an entry with the action name, target device, reasoning summary, and timestamp.
2. WHEN a proactive action triggers, THE 3D_Scene SHALL visually indicate the affected device (glow, color change, or animation) in the corresponding room.
3. THE Demo_App SHALL support the following proactive action types: pre-cooling (AC), geyser pre-heat, security arm (lock and camera), energy optimization (inverter load shifting), and comfort lighting (light warm transition).

### Requirement 9: Trust Score Gauges

**User Story:** As a viewer, I want to see trust score gauges for device categories, so that the autonomy tier system is visually communicated.

#### Acceptance Criteria

1. THE Deployment_Phase SHALL display Trust_Score_Gauges for each device category in the UI.
2. WHILE the simulation is running, THE Trust_Score_Gauges SHALL update their values as proactive actions execute and trust increases.
3. THE Trust_Score_Gauges SHALL visually indicate the current autonomy tier (1-5) corresponding to the trust score range.

### Requirement 10: Day/Night Lighting Cycle

**User Story:** As a viewer, I want the 3D scene lighting to change based on the simulation clock, so that the time of day is visually apparent.

#### Acceptance Criteria

1. WHILE the simulation clock indicates daytime (06:00 to 18:00), THE 3D_Scene SHALL render bright ambient lighting with warm tones.
2. WHILE the simulation clock indicates nighttime (18:00 to 06:00), THE 3D_Scene SHALL render dim ambient lighting with cool blue tones.
3. THE 3D_Scene SHALL smoothly transition lighting between day and night states over a simulated period of 30 minutes around sunrise and sunset times.

### Requirement 11: Speech Bubbles from Echo Devices

**User Story:** As a viewer, I want to see speech bubbles appearing from Echo devices with Alexa announcements tailored per family member, so that the communication aspect of the system is demonstrated.

#### Acceptance Criteria

1. WHEN a proactive action generates an Alexa announcement, THE 3D_Scene SHALL display a Speech_Bubble originating from the Echo device nearest to the target family member.
2. THE Speech_Bubble SHALL contain text tailored to the specific family member's role (parent, child, elder).
3. THE Speech_Bubble SHALL remain visible for 5 seconds before fading out.
4. THE Speech_Bubble SHALL use glassmorphism styling consistent with the overall UI theme.

### Requirement 12: Power Cut Scenario

**User Story:** As a presenter, I want a manually triggered power cut scenario with dramatic visual effects and intelligent device prioritization, so that I can demonstrate Alexa's contextual reasoning during live demos.

#### Acceptance Criteria

1. THE Deployment_Phase SHALL display a Presentation_Button that manually triggers the Power_Cut_Scenario at the current simulation time.
2. WHEN the Power_Cut_Scenario triggers, THE 3D_Scene SHALL display a screen flicker effect simulating sudden power loss.
3. WHEN the Power_Cut_Scenario triggers, THE 3D_Scene SHALL display an inverter glow effect on the Inverter/UPS device in the designated room.
4. WHEN the Power_Cut_Scenario triggers, THE Demo_App SHALL display a reasoning panel explaining Alexa's prioritization decisions (which devices to keep powered, rationale based on active activities).
5. WHEN the Power_Cut_Scenario triggers, THE 3D_Scene SHALL show selective room lighting where only prioritized rooms remain lit (Study Room for Arjun's tuition, Living Room for Dadaji).
6. WHEN the Power_Cut_Scenario triggers, THE Event_Log SHALL display chronological entries showing SENSE, THINK, ACT, and EXPLAIN stages of the response.
7. WHEN the Power_Cut_Scenario triggers, THE 3D_Scene SHALL display Speech_Bubbles from Echo devices announcing the power cut status and actions taken to each relevant family member.

### Requirement 13: Device Room Mapping

**User Story:** As a developer, I want devices assigned to specific rooms according to the defined layout, so that the 3D visualization accurately represents the smart home.

#### Acceptance Criteria

1. THE 3D_Scene SHALL place the Living Room AC, Smart TV, and Echo device indicators in the Living Room.
2. THE 3D_Scene SHALL place the Smart Lights indicators across all rooms (distributed).
3. THE 3D_Scene SHALL place the Security Camera and Smart Lock indicators at the house entrance area (Balcony or main door).
4. THE 3D_Scene SHALL place the Kitchen Appliance Hub indicator in the Kitchen.
5. THE 3D_Scene SHALL place the Water Purifier indicator in the Kitchen.
6. THE 3D_Scene SHALL place the Smart Geyser indicator in the Bath.
7. THE 3D_Scene SHALL place the Inverter/UPS indicator in an appropriate utility area visible in the 3D model.
8. THE 3D_Scene SHALL place an Echo device indicator in the Study Room and Kids Room in addition to the Living Room.

### Requirement 14: Simulation Speed and Playback Controls

**User Story:** As a presenter, I want precise control over the simulation speed and timeline position, so that I can navigate to interesting moments quickly during a demo.

#### Acceptance Criteria

1. WHEN the user selects 1x Speed_Control, THE Demo_App SHALL advance the simulation at real-time speed (1 simulated second per 1 real second).
2. WHEN the user selects 10x Speed_Control, THE Demo_App SHALL advance the simulation at 10 simulated seconds per 1 real second.
3. WHEN the user selects 60x Speed_Control, THE Demo_App SHALL advance the simulation at 60 simulated seconds per 1 real second (1 simulated minute per real second).
4. WHEN the user selects 120x Speed_Control, THE Demo_App SHALL advance the simulation at 120 simulated seconds per 1 real second.
5. WHILE the simulation is running, THE Timeline_Scrubber SHALL visually indicate the current simulation time position.
6. THE Demo_App SHALL allow pausing and resuming the simulation via a play/pause control.

### Requirement 15: Responsive and Performant Rendering

**User Story:** As a user, I want the application to render smoothly on a standard laptop, so that the demo runs well during presentations without dedicated GPU hardware.

#### Acceptance Criteria

1. THE 3D_Scene SHALL maintain a minimum frame rate of 30 frames per second on a device with integrated graphics.
2. THE Demo_App SHALL use low-poly geometry (under 50,000 total triangles for the house model) to maintain rendering performance.
3. THE Demo_App SHALL load and become interactive within 5 seconds on a standard broadband connection.
