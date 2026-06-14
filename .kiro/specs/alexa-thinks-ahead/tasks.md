 -+-mplementation Plan: Alexa Thinks Ahead

## Overview

This plan implements the Alexa Thinks Ahead proactive smart home system in 5 phases matching the hackathon schedule. Each task is scoped to 15-30 minutes of implementation. The system is built with Python 3.10 on AWS serverless (Lambda, DynamoDB, EventBridge, API Gateway) using SAM for IaC.

## Tasks

- [x] 1. Project Setup and Core Data Models
  - [x] 1.1 Initialize project structure and dependencies
    - Create directory structure: src/ (devices, context, intelligence, autonomy, learning, reasoning, handlers, models, utils), tests/ (unit, integration), and root config files
    - Create requirements.txt with boto3, moto, hypothesis, pytest, python-dateutil, pydantic
    - Create pytest.ini with test discovery configuration
    - Create src/__init__.py and all subpackage __init__.py files
    - _Requirements: 11.1_

  - [x] 1.2 Implement core data models (dataclasses)
    - Create src/models/device.py with DeviceState, DeviceCommand, CommandResult, DeviceCategory enum
    - Create src/models/context.py with ContextSnapshot, TemporalPattern, FamilyActivity
    - Create src/models/autonomy.py with TrustScore, TierDecision, ActionType enum
    - Create src/models/intelligence.py with Prediction, ActionPlan, ReasoningRequest, ReasoningResponse
    - Create src/models/learning.py with PreferenceDistribution, FeedbackEvent
    - Create src/models/family.py with FamilyMember, FamilyProfile (Sharma family config)
    - All models use Python dataclasses with proper type hints
    - _Requirements: 1.5, 2.3, 5.1, 5.2_

  - [x] 1.3 Write property tests for data model validation
    - **Property 1: Trust Score Bounds Invariant** - verify TrustScore.score always in [0, 100]
    - **Property 6: Sensor Fusion Weight Bounds** - verify weight calculations bounded [0.1, 1.0]
    - **Validates: Requirements 5.1, 2.2**

- [x] 2. Device Adapter Layer (Phase 1)
  - [x] 2.1 Implement base DeviceAdapter abstract class and adapter factory
    - Create src/devices/base.py with DeviceAdapter ABC (get_state, execute_command, subscribe_events, get_capabilities)
    - Create src/devices/factory.py with DeviceAdapterFactory that instantiates adapters by device type
    - Create src/devices/registry.py with DeviceRegistry holding all 10 device configurations
    - _Requirements: 1.1, 1.5_

  - [x] 2.2 Implement device adapters for all 10 devices
    - Create src/devices/climate.py (DaikinACAdapter) - controls temperature, mode, fan speed
    - Create src/devices/lighting.py (PhilipsHueAdapter) - controls brightness, color, scenes
    - Create src/devices/security.py (RingCameraAdapter, YaleLockAdapter) - arm/disarm, lock/unlock
    - Create src/devices/kitchen.py (SamsungKitchenAdapter) - appliance status, timers
    - Create src/devices/utility.py (KentPurifierAdapter, HavellsGeyserAdapter) - on/off, temperature
    - Create src/devices/power.py (LuminousInverterAdapter) - battery level, load allocation, mode
    - Create src/devices/entertainment.py (FireTVAdapter) - power, volume, input
    - Create src/devices/assistant.py (EchoAdapter) - announcements, notifications
    - Each adapter normalizes state to DeviceState dataclass
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 2.3 Write unit tests for device adapters
    - Test each adapter returns valid DeviceState
    - Test command execution returns valid CommandResult
    - Test stale device marking when unreachable
    - _Requirements: 1.2, 1.3_

- [x] 3. Configuration and Utilities
  - [x] 3.1 Implement configuration management
    - Create src/utils/config.py with system configuration (thresholds, intervals, timeouts)
    - Create src/utils/constants.py with tier thresholds, confidence thresholds, device categories
    - Create src/models/family.py Sharma family profile (6 members, roles, preferred devices, routines)
    - _Requirements: 5.2, 4.2, 4.3, 4.4_

  - [x] 3.2 Implement utility modules
    - Create src/utils/logging.py with structured logging (JSON format for CloudWatch)
    - Create src/utils/time_utils.py with timestamp helpers, season detection, temporal calculations
    - Create src/utils/dynamo_utils.py with DynamoDB serialization/deserialization helpers
    - _Requirements: 6.3_

- [x] 4. Checkpoint - Foundation Validated
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Sensor Ingestion and Context Engine (Phase 2)
  - [x] 5.1 Implement sensor ingestion pipeline
    - Create src/context/ingestion.py with SensorIngestionPipeline class
    - Collect state from all 10 devices via adapter get_state()
    - Store state records in DynamoDB with device_id (partition) + timestamp (sort) keys
    - Handle device failures gracefully (mark stale, continue with others)
    - _Requirements: 2.1, 2.4, 12.2_

  - [x] 5.2 Implement sensor fusion with temporal weighting
    - Create src/context/fusion.py with SensorFusion class
    - Apply temporal weights: weight = max(0.1, 1.0 - (age_seconds / 3600))
    - Mark stale devices (> 1 hour) with reduced weight
    - Produce fused state dict with weights per device
    - _Requirements: 2.2, 2.4_

  - [x] 5.3 Write property test for sensor fusion weights
    - **Property 6: Sensor Fusion Weight Bounds** - for any timestamp, weight is in [0.1, 1.0]
    - **Validates: Requirement 2.2**

  - [x] 5.4 Implement temporal pattern analyzer
    - Create src/context/patterns.py with TemporalPatternAnalyzer class
    - Query 24-hour history from DynamoDB
    - Detect daily patterns (recurring device usage at similar times)
    - Detect weekly patterns (weekday vs. weekend differences)
    - Assign confidence scores [0.0, 1.0] to each pattern
    - Filter patterns: only include confidence >= 0.75 in snapshot
    - _Requirements: 2.5, 3.1, 3.2_

  - [x] 5.5 Implement family routine modeler
    - Create src/context/routines.py with FamilyRoutineModeler class
    - Model per-member schedules from calendar + device usage correlation
    - Track active activities per member (Arjun's tuition, Dadaji's rest, etc.)
    - Provide get_active_activities() for current context
    - _Requirements: 3.3_

  - [x] 5.6 Implement conflict resolver
    - Create src/context/conflicts.py with ConflictResolver class
    - Priority ordering: safety > elder comfort > child needs > efficiency
    - Resolve overlapping device needs between family members
    - Return resolved action queue with priority-based winners
    - _Requirements: 3.4, 12.4_

  - [x] 5.7 Write property test for conflict resolution
    - **Property 11: Conflict Resolution Priority Ordering** - safety always wins over lower priorities
    - **Validates: Requirements 3.4, 12.4**

  - [x] 5.8 Implement context engine orchestrator
    - Create src/context/engine.py with ContextEngine class
    - Orchestrate: fusion → patterns → routines → conflicts → snapshot
    - Build complete ContextSnapshot with all 10 device states, activities, patterns, resources
    - Implement context cache for repeated queries within same cycle
    - _Requirements: 2.3, 2.5_

  - [x] 5.9 Write property test for context snapshot completeness
    - **Property 8: Context Snapshot Completeness** - snapshot always contains all 10 devices
    - **Validates: Requirements 2.3, 12.2**

- [x] 6. Checkpoint - Context Engine Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Proactive Intelligence Engine (Phase 3)
  - [x] 7.1 Implement Bedrock reasoning client
    - Create src/reasoning/client.py with BedrockReasoningClient class
    - Initialize boto3 bedrock-runtime client for ap-south-1
    - Build structured prompts from ContextSnapshot + preferences + autonomy config
    - Invoke Claude Sonnet (anthropic.claude-3-sonnet) with 3-second timeout
    - Parse response into ActionPlan with predictions and reasoning chain
    - Implement exponential backoff (1s, 2s, 4s) on failures
    - Handle malformed responses: discard and return empty plan
    - _Requirements: 4.1, 4.6, 4.7, 12.1_

  - [x] 7.2 Implement confidence-based action routing
    - Create src/intelligence/routing.py with route_action() function
    - Thresholds: >= 0.85 AUTO_EXECUTE, >= 0.60 RECOMMEND, >= 0.40 INFORM, < 0.40 discard
    - Apply routing to each prediction in an action plan
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 7.3 Write property test for action routing
    - **Property 7: Action Routing Consistency** - confidence maps deterministically to action type
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

  - [x] 7.4 Implement proactive engine with intelligence strategies
    - Create src/intelligence/engine.py with ProactiveEngine class
    - Evaluate context against intelligence strategies: pre_cooling, geyser_preheat, security_arm, energy_optimization, comfort_lighting, storm_preparation
    - Generate predictions with confidence scores from Bedrock reasoning
    - Prioritize predictions by confidence (highest first)
    - No hardcoded scenario logic — all decisions flow through Bedrock
    - _Requirements: 4.1, 13.2_

  - [x] 7.5 Implement event-driven contextual handler
    - Create src/intelligence/event_handler.py with ContextualEventHandler class
    - Handle any event through generic SENSE-THINK-ACT-EXPLAIN pipeline
    - Gather full context snapshot on event
    - Invoke reasoning with event context
    - Execute actions based on autonomy permissions
    - Generate and deliver explanations
    - _Requirements: 7.1, 7.3, 10.1, 13.1_

- [x] 8. Autonomy Tier Engine (Phase 4)
  - [x] 8.1 Implement trust score management
    - Create src/autonomy/trust.py with TrustScoreManager class
    - Initialize scores at 0 for all member-category pairs (6 members × 8 categories)
    - record_acceptance(): increase by min(5, 100 - current)
    - record_override(): decrease by 15, floor at 0
    - Store scores in DynamoDB (member_category partition key)
    - _Requirements: 5.1, 5.3, 5.4_

  - [x] 8.2 Write property tests for trust score operations
    - **Property 1: Trust Score Bounds Invariant** - score always in [0, 100] after any operation sequence
    - **Property 3: Override Always Decreases Trust** - override reduces score (or stays at 0)
    - **Property 4: Acceptance Never Decreases Trust** - acceptance increases or maintains score
    - **Validates: Requirements 5.1, 5.3, 5.4, 5.7**

  - [x] 8.3 Implement tier determination and permission checks
    - Create src/autonomy/tiers.py with TierManager class
    - Map scores to tiers: [0-20]=1, [21-45]=2, [46-70]=3, [71-90]=4, [91-100]=5
    - check_permission(member, action): permit iff member_tier >= action.tier_required
    - Return TierDecision with permitted flag, tiers, and reason
    - _Requirements: 5.2, 5.5_

  - [x] 8.4 Write property tests for tier logic
    - **Property 2: Tier Monotonicity with Score** - higher score never maps to lower tier
    - **Property 9: Tier Permission Consistency** - permitted iff member_tier >= required_tier
    - **Property 10: De-escalation Immediacy on Override** - tier never increases on override
    - **Validates: Requirements 5.2, 5.5, 5.7**

  - [x] 8.5 Implement escalation and decay logic
    - Create src/autonomy/escalation.py with EscalationManager class
    - check_escalation(): require 7-day window + 80% acceptance rate + score meets threshold
    - apply_decay(): reduce score by configurable amount per inactive day
    - Escalation is gradual; de-escalation is immediate on override
    - _Requirements: 5.6, 5.7, 5.8_

  - [x] 8.6 Implement autonomy engine orchestrator
    - Create src/autonomy/engine.py with AutonomyEngine class
    - Orchestrate: trust scoring + tier management + escalation + decay
    - Provide get_tier_config() for reasoning client
    - Track all interactions for learning engine feedback
    - _Requirements: 5.1, 5.2, 5.5, 5.6_

- [x] 9. Checkpoint - Autonomy Engine Complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Continuous Learning Engine (Phase 5)
  - [x] 10.1 Implement Bayesian preference updater
    - Create src/learning/bayesian.py with BayesianUpdater class
    - Conjugate Gaussian update: posterior_precision = prior_precision + obs_precision
    - posterior_mean = weighted average of prior and observation
    - posterior_variance always less than prior_variance
    - _Requirements: 6.2_

  - [x] 10.2 Write property test for Bayesian updates
    - **Property 5: Bayesian Update Variance Reduction** - posterior variance < prior variance for any valid prior and observation
    - **Validates: Requirement 6.2**

  - [x] 10.3 Implement feedback collector
    - Create src/learning/feedback.py with FeedbackCollector class
    - Accept feedback from multiple channels: explicit ratings (1-5), overrides (signal=-1), acceptances (signal=+1), adjustments (signal=partial)
    - Convert all signals to normalized [-1.0, 1.0] range
    - Store feedback events in DynamoDB
    - _Requirements: 6.1_

  - [x] 10.4 Implement seasonal models
    - Create src/learning/seasonal.py with SeasonalModel class
    - Determine season from month: summer(Mar-Jun), monsoon(Jul-Sep), autumn(Oct-Nov), winter(Dec-Feb)
    - Maintain separate preference distributions per season
    - Blend seasonal prediction with overall preference for final output
    - _Requirements: 6.3_

  - [x] 10.5 Implement learning engine orchestrator
    - Create src/learning/engine.py with LearningEngine class
    - Process feedback → Bayesian update → seasonal model update
    - 90-day rolling window for observation decay
    - Track personalization index per member
    - Provide predict_preference() for reasoning client
    - _Requirements: 6.2, 6.4, 6.5_

- [x] 11. Lambda Handlers and API Layer
  - [x] 11.1 Implement Alexa skill handler
    - Create src/handlers/skill_handler.py with lambda_handler function
    - Handle Discovery: return all 10 devices with capabilities
    - Handle Control: route commands through device adapter, return confirmation
    - Handle Query: return current device state
    - Handle custom intents: ExplainAction (why), OverrideAction (override)
    - Validate Alexa request signatures
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 11.2 Implement REST API handler
    - Create src/handlers/api_handler.py with lambda_handler function
    - GET /devices - list all devices with states
    - GET /devices/{id}/state - single device state
    - POST /devices/{id}/command - send command (checks autonomy)
    - GET /context/snapshot - current context snapshot
    - GET /context/patterns - detected patterns
    - GET /autonomy/tiers - current tier config
    - PUT /autonomy/tiers/{device} - update tier
    - Return proper HTTP status codes (200, 400, 401, 403, 500)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 11.3 Implement event processor handler
    - Create src/handlers/event_handler.py with lambda_handler function
    - Process EventBridge device events
    - Detect critical events (power_cut, security_breach) for immediate processing
    - Route to ContextualEventHandler for full pipeline execution
    - _Requirements: 7.1, 7.3_

  - [x] 11.4 Implement scheduled context fusion handler
    - Create src/handlers/context_handler.py with lambda_handler function
    - Triggered every 30 seconds by EventBridge schedule
    - Run full context engine cycle: ingest → fuse → detect → model → snapshot
    - Store snapshot in DynamoDB context cache
    - _Requirements: 2.1_

- [x] 12. Explanation and Communication
  - [x] 12.1 Implement explanation generator
    - Create src/reasoning/explainer.py with ExplanationGenerator class
    - Generate natural language explanations from reasoning chains
    - Include triggering event, reasoning summary, and expected benefit
    - Tailor messages per family member (role-appropriate language)
    - Route announcements to appropriate Echo devices
    - _Requirements: 10.1, 10.2, 10.3_

- [x] 13. Infrastructure (SAM Template)
  - [x] 13.1 Create SAM template with all resources
    - Create template.yaml with:
      - SkillHandlerFunction (512MB, 30s timeout)
      - ContextEngineFunction (1024MB, 60s timeout)
      - ReasoningProxyFunction (2048MB, 90s timeout)
      - EventProcessorFunction (512MB, 30s timeout)
      - APIHandlerFunction (512MB, 30s timeout)
      - DeviceStateTable (DynamoDB, on-demand, TTL)
      - ContextSnapshotTable (DynamoDB, on-demand, TTL)
      - TrustScoreTable (DynamoDB, on-demand)
      - PreferenceTable (DynamoDB, on-demand)
      - SmartHomeEventBus (EventBridge custom bus)
      - API Gateway with JWT authorizer
      - IAM policies (least privilege per function)
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 14. Checkpoint - Full Stack Integrated
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Integration Tests and Demo Scenario
  - [x] 15.1 Write integration tests for cognitive pipeline
    - Create tests/integration/test_pipeline.py
    - Test full SENSE → THINK → ACT → EXPLAIN cycle with mocked Bedrock
    - Use moto for DynamoDB and EventBridge mocking
    - Verify context snapshot produced, reasoning invoked, actions dispatched
    - _Requirements: 7.1, 2.3, 4.1_

  - [x] 15.2 Write integration tests for autonomy + learning loop
    - Create tests/integration/test_autonomy_learning.py
    - Test acceptance → trust increase → tier escalation flow
    - Test override → trust decrease → tier de-escalation flow
    - Test feedback → Bayesian update → improved prediction flow
    - _Requirements: 5.3, 5.4, 5.6, 6.2_

  - [x] 15.3 Implement demo scenario test (power cut at 5:40pm)
    - Create tests/integration/test_demo_scenario.py
    - Simulate: power cut event → context gathering → Bedrock reasoning → load shedding → announcements → power restore → recovery
    - Verify: Wi-Fi and study room prioritized, AC/geyser shed, announcements sent, graceful recovery
    - Use mocked Bedrock with realistic response for demo rehearsal
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [x] 15.4 Write integration tests for API endpoints
    - Create tests/integration/test_api.py
    - Test all REST endpoints with valid/invalid requests
    - Verify HTTP status codes and response schemas
    - Test autonomy permission enforcement on command endpoints
    - _Requirements: 9.1, 9.3, 9.4_

- [x] 16. Final Checkpoint - All Tests Pass
  - Ensure all tests pass, ask the user if questions arise.

## Task Dependency Graph

```json
{
  "waves": [
    {
      "name": "Wave 1 - Foundation Setup",
      "tasks": ["1.1", "1.2"],
      "description": "Project structure, dependencies, and core data models"
    },
    {
      "name": "Wave 2 - Device Layer",
      "tasks": ["1.3", "2.1", "2.2", "2.3", "3.1", "3.2"],
      "description": "Device adapters, configuration, and utilities"
    },
    {
      "name": "Wave 3 - Context Engine",
      "tasks": ["5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7", "5.8", "5.9"],
      "description": "Sensor fusion, patterns, routines, and conflict resolution"
    },
    {
      "name": "Wave 4 - Intelligence & Autonomy",
      "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "8.1", "8.2", "8.3", "8.4", "8.5", "8.6"],
      "description": "Proactive engine, reasoning client, trust scoring, tier management"
    },
    {
      "name": "Wave 5 - Learning & Handlers",
      "tasks": ["10.1", "10.2", "10.3", "10.4", "10.5", "11.1", "11.2", "11.3", "11.4", "12.1"],
      "description": "Continuous learning, Lambda handlers, API, and explanations"
    },
    {
      "name": "Wave 6 - Infrastructure & Integration",
      "tasks": ["13.1", "15.1", "15.2", "15.3", "15.4"],
      "description": "SAM template, integration tests, and demo scenario"
    }
  ]
}
```

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery during hackathon crunch time
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- Property tests validate universal correctness properties using hypothesis library
- All DynamoDB operations are mocked with moto in tests
- Bedrock API calls are mocked with unittest.mock in tests
- The demo scenario test (15.3) serves dual purpose: validation and demo rehearsal
- Priority for hackathon: tasks 1-9 (core logic) > tasks 10-12 (learning + API) > tasks 13-15 (infra + integration)
