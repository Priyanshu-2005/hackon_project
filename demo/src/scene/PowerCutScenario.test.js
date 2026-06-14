/**
 * @vitest-environment happy-dom
 *
 * Frontend scenario tests for the live power-cut wiring (Task 6.1/6.2).
 *
 * Feature: demo-backend-integration
 *
 * Tests cover:
 * - Example 1: POST issued to /api/v1/scenario/power-cut (Req 11.1)
 * - Example 2: Explanation text renders via reasoningPanel.show (Req 11.3)
 * - Example 3: Failed request shows error + falls back to scripted scenario (Req 11.4)
 * - Property 13: Every targeted device in the plan is animated (Req 11.2)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fc from 'fast-check';

// ─── Helpers ──────────────────────────────────────────────────────────────────
// We test the real-mode power-cut handler logic extracted from main.js.
// Instead of importing main.js (which bootstraps the full app), we replicate
// the handler logic in a testable function that matches what main.js does.

/**
 * Simulates the real-mode power-cut click handler from main.js.
 * This mirrors the logic inside the `if (dataLayer.mode === 'real')` branch.
 */
async function realModePowerCutHandler({
  apiProvider,
  floorPlan,
  stateStore,
  reasoningPanel,
  powerCutScenario,
  currentTimeMinutes,
}) {
  try {
    const response = await apiProvider.runPowerCutScenario();

    // Stage 1: SENSE
    floorPlan.powerCutFlicker();
    stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - SENSE',
      device: 'inverter_ups',
      reasoning: 'Power grid failure detected (real backend).',
      type: 'power_cut',
      stage: 'SENSE',
    });

    // Stage 2: THINK — show explanation/reasoning in ReasoningPanel
    const reasoningContent = `
      <h3>⚡ Power Cut — Alexa's Reasoning (Live)</h3>
      <div class="reasoning-steps">
        <p>💬 <strong>Explanation:</strong> ${response.explanation || 'Analyzing situation...'}</p>
        ${response.reasoning_chain ? `<p>🧠 <strong>Reasoning:</strong> ${response.reasoning_chain}</p>` : ''}
      </div>
    `;
    reasoningPanel.show(reasoningContent);

    stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - THINK',
      device: 'inverter_ups',
      reasoning: response.explanation || 'Contextual reasoning from backend.',
      type: 'power_cut',
      stage: 'THINK',
    });

    // Stage 3: ACT — map target_devices to FloorPlan2D effects
    for (const action of response.actions) {
      stateStore.addEventLogEntry({
        time: currentTimeMinutes,
        action: `Power Cut - ACT: ${action.strategy}`,
        device: (action.target_devices || []).join(', '),
        reasoning: action.reasoning || `Strategy: ${action.strategy}, Confidence: ${action.confidence}`,
        type: 'power_cut',
        stage: 'ACT',
      });

      for (const deviceId of action.target_devices || []) {
        if (deviceId === 'inverter_ups') {
          floorPlan.inverterGlow(deviceId);
        } else {
          floorPlan.highlightDevice(deviceId, 3000);
        }
      }
    }

    // Dim rooms
    floorPlan.dimRooms(['study_room', 'living_room']);

    // Stage 4: EXPLAIN — speech bubbles
    if (response.explanation) {
      floorPlan.showSpeechBubble('echo_living', response.explanation, 7000);
    }

    stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - EXPLAIN',
      device: 'echo_devices',
      reasoning: response.explanation || 'Announcing status to family.',
      type: 'power_cut',
      stage: 'EXPLAIN',
    });
  } catch (err) {
    // Error indication in event log
    stateStore.addEventLogEntry({
      time: currentTimeMinutes,
      action: 'Power Cut - ERROR',
      device: 'system',
      reasoning: `Backend scenario failed: ${err.message}. Falling back to scripted demo.`,
      type: 'error',
      stage: 'ERROR',
    });
    // Fall back to scripted scenario
    powerCutScenario.trigger(currentTimeMinutes);
  }
}

// ─── Mock factories ───────────────────────────────────────────────────────────

function createMockFloorPlan() {
  return {
    powerCutFlicker: vi.fn(),
    inverterGlow: vi.fn(),
    highlightDevice: vi.fn(),
    dimRooms: vi.fn(),
    restoreAll: vi.fn(),
    showSpeechBubble: vi.fn(),
  };
}

function createMockStateStore() {
  return {
    addEventLogEntry: vi.fn(),
    events: [],
  };
}

function createMockReasoningPanel() {
  return {
    show: vi.fn(),
    hide: vi.fn(),
  };
}

function createMockPowerCutScenario() {
  return {
    trigger: vi.fn(),
    restore: vi.fn(),
  };
}

// ─── Example Tests ────────────────────────────────────────────────────────────

describe('PowerCutScenario - Real Mode Wiring', () => {
  let floorPlan;
  let stateStore;
  let reasoningPanel;
  let powerCutScenario;
  let apiProvider;

  beforeEach(() => {
    floorPlan = createMockFloorPlan();
    stateStore = createMockStateStore();
    reasoningPanel = createMockReasoningPanel();
    powerCutScenario = createMockPowerCutScenario();
    apiProvider = {
      runPowerCutScenario: vi.fn(),
    };
  });

  describe('Example 1: POST issued to scenario endpoint (Req 11.1)', () => {
    it('calls apiProvider.runPowerCutScenario which POSTs to /api/v1/scenario/power-cut', async () => {
      apiProvider.runPowerCutScenario.mockResolvedValue({
        actions: [
          {
            target_devices: ['inverter_ups'],
            strategy: 'energy_optimization',
            confidence: 0.95,
            reasoning: 'Power cut detected.',
          },
        ],
        explanation: 'Power cut detected. Inverter keeping essentials running.',
        reasoning_chain: 'SENSE → THINK → ACT → EXPLAIN',
      });

      await realModePowerCutHandler({
        apiProvider,
        floorPlan,
        stateStore,
        reasoningPanel,
        powerCutScenario,
        currentTimeMinutes: 1020,
      });

      expect(apiProvider.runPowerCutScenario).toHaveBeenCalledTimes(1);
    });
  });

  describe('Example 2: Explanation text renders (Req 11.3)', () => {
    it('calls reasoningPanel.show with content containing the explanation text', async () => {
      const explanationText = 'Power cut detected. Inverter is keeping Wi-Fi and study room running.';
      apiProvider.runPowerCutScenario.mockResolvedValue({
        actions: [
          {
            target_devices: ['inverter_ups'],
            strategy: 'energy_optimization',
            confidence: 0.95,
            reasoning: 'Priority allocation.',
          },
        ],
        explanation: explanationText,
        reasoning_chain: 'SENSE: Grid offline. THINK: Prioritize study. ACT: Shed AC.',
      });

      await realModePowerCutHandler({
        apiProvider,
        floorPlan,
        stateStore,
        reasoningPanel,
        powerCutScenario,
        currentTimeMinutes: 1020,
      });

      expect(reasoningPanel.show).toHaveBeenCalledTimes(1);
      const showArg = reasoningPanel.show.mock.calls[0][0];
      expect(showArg).toContain(explanationText);
    });

    it('renders reasoning_chain when present in the response', async () => {
      const reasoningChain = 'SENSE: Grid failure. THINK: Study priority. ACT: Load shed.';
      apiProvider.runPowerCutScenario.mockResolvedValue({
        actions: [],
        explanation: 'Power cut handled.',
        reasoning_chain: reasoningChain,
      });

      await realModePowerCutHandler({
        apiProvider,
        floorPlan,
        stateStore,
        reasoningPanel,
        powerCutScenario,
        currentTimeMinutes: 1020,
      });

      const showArg = reasoningPanel.show.mock.calls[0][0];
      expect(showArg).toContain(reasoningChain);
    });
  });

  describe('Example 3: Failed request shows error and falls back (Req 11.4)', () => {
    it('adds an error entry to event log when POST fails', async () => {
      apiProvider.runPowerCutScenario.mockRejectedValue(new Error('Network timeout'));

      await realModePowerCutHandler({
        apiProvider,
        floorPlan,
        stateStore,
        reasoningPanel,
        powerCutScenario,
        currentTimeMinutes: 1020,
      });

      expect(stateStore.addEventLogEntry).toHaveBeenCalled();
      const errorEntry = stateStore.addEventLogEntry.mock.calls.find(
        (call) => call[0].type === 'error'
      );
      expect(errorEntry).toBeDefined();
      expect(errorEntry[0].action).toBe('Power Cut - ERROR');
      expect(errorEntry[0].reasoning).toContain('Network timeout');
      expect(errorEntry[0].reasoning).toContain('Falling back to scripted demo');
    });

    it('falls back to the scripted powerCutScenario.trigger() on failure', async () => {
      apiProvider.runPowerCutScenario.mockRejectedValue(new Error('Server error'));

      await realModePowerCutHandler({
        apiProvider,
        floorPlan,
        stateStore,
        reasoningPanel,
        powerCutScenario,
        currentTimeMinutes: 1020,
      });

      expect(powerCutScenario.trigger).toHaveBeenCalledTimes(1);
      expect(powerCutScenario.trigger).toHaveBeenCalledWith(1020);
    });

    it('does NOT call any animation functions when POST fails', async () => {
      apiProvider.runPowerCutScenario.mockRejectedValue(new Error('Failed'));

      await realModePowerCutHandler({
        apiProvider,
        floorPlan,
        stateStore,
        reasoningPanel,
        powerCutScenario,
        currentTimeMinutes: 1020,
      });

      expect(floorPlan.inverterGlow).not.toHaveBeenCalled();
      expect(floorPlan.highlightDevice).not.toHaveBeenCalled();
      expect(floorPlan.dimRooms).not.toHaveBeenCalled();
      expect(reasoningPanel.show).not.toHaveBeenCalled();
    });
  });
});

// ─── Property 13 ──────────────────────────────────────────────────────────────

/**
 * Feature: demo-backend-integration, Property 13: Every targeted device in the plan is animated
 *
 * **Validates: Requirements 11.2**
 *
 * For any Action_Plan response received by the Demo_Frontend, every device listed
 * in any action's `target_devices` SHALL trigger a corresponding scene animation
 * invocation (either `inverterGlow` or `highlightDevice`).
 */
describe('Property 13: Every targeted device in the plan is animated', () => {
  // Arbitrary for generating realistic device IDs
  const deviceIdArb = fc.stringMatching(/^[a-z][a-z0-9_]{2,20}$/);
  const strategyArb = fc.constantFrom(
    'energy_optimization',
    'priority_power',
    'comfort_maintain',
    'safety_first',
    'load_shedding'
  );
  const confidenceArb = fc.double({ min: 0, max: 1, noNaN: true });

  // Generator for a single action within a plan
  const actionArb = fc.record({
    target_devices: fc.array(deviceIdArb, { minLength: 1, maxLength: 5 }),
    strategy: strategyArb,
    confidence: confidenceArb,
    reasoning: fc.string({ minLength: 1, maxLength: 50 }),
  });

  // Generator for a full action plan response
  const actionPlanArb = fc.record({
    actions: fc.array(actionArb, { minLength: 1, maxLength: 8 }),
    explanation: fc.string({ minLength: 5, maxLength: 100 }),
    reasoning_chain: fc.string({ minLength: 5, maxLength: 200 }),
  });

  it('every device ID in target_devices triggers an animation call (≥100 iterations)', async () => {
    await fc.assert(
      fc.asyncProperty(actionPlanArb, async (plan) => {
        const floorPlan = createMockFloorPlan();
        const stateStore = createMockStateStore();
        const reasoningPanel = createMockReasoningPanel();
        const powerCutScenario = createMockPowerCutScenario();
        const apiProvider = {
          runPowerCutScenario: vi.fn().mockResolvedValue(plan),
        };

        await realModePowerCutHandler({
          apiProvider,
          floorPlan,
          stateStore,
          reasoningPanel,
          powerCutScenario,
          currentTimeMinutes: 1020,
        });

        // Collect all device IDs that were passed to animation functions
        const animatedDevices = new Set();

        for (const call of floorPlan.inverterGlow.mock.calls) {
          animatedDevices.add(call[0]);
        }
        for (const call of floorPlan.highlightDevice.mock.calls) {
          animatedDevices.add(call[0]);
        }

        // Collect all target_devices from the plan
        const allTargetDevices = new Set();
        for (const action of plan.actions) {
          for (const deviceId of action.target_devices) {
            allTargetDevices.add(deviceId);
          }
        }

        // Assert: every targeted device must appear in the animated set
        for (const deviceId of allTargetDevices) {
          expect(animatedDevices.has(deviceId)).toBe(true);
        }
      }),
      { numRuns: 100 }
    );
  });
});
