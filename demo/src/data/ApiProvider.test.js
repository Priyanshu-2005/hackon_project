/**
 * Property-Based Tests for ApiProvider response reshaping.
 *
 * Feature: demo-backend-integration, Property 12: Reshaped responses conform to the mock shape
 *
 * **Validates: Requirements 10.1, 10.2**
 *
 * For any Backend_API response payload, the Api_Provider-normalized result SHALL
 * conform to the corresponding MockProvider schema (the same field names produced
 * in mock mode):
 *   - getDevices() → {devices: Array, count: number}
 *   - getContextSnapshot() → {timestamp, deviceStates: Array, activeActivities: Array, environmentals: {temperature, humidity, powerGrid}}
 *   - getPatterns() → {patterns: Array}
 *   - getAutonomyTiers() → {tiers: Array}
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fc from 'fast-check';
import { ApiProvider } from './ApiProvider.js';

// --- Arbitraries for generating random backend payloads ---

/** Generate a random device object (as the backend might return) */
const arbDevice = fc.record({
  id: fc.string({ minLength: 1, maxLength: 30 }),
  name: fc.string({ minLength: 1, maxLength: 50 }),
  category: fc.constantFrom('climate', 'lighting', 'security', 'kitchen', 'utility', 'power', 'entertainment', 'assistant'),
  room: fc.string({ minLength: 1, maxLength: 30 }),
  brand: fc.string({ minLength: 1, maxLength: 30 }),
  state: fc.dictionary(fc.string({ minLength: 1, maxLength: 10 }), fc.oneof(fc.string(), fc.integer(), fc.boolean())),
});

/**
 * Generate a backend /devices response.
 * Simulates real JSON payloads: the `devices` field is always an array,
 * but `count` may or may not be present (ApiProvider handles both cases).
 */
const arbDevicesResponse = fc.oneof(
  // Case 1: both devices and count present
  fc.record({
    devices: fc.array(arbDevice, { minLength: 0, maxLength: 15 }),
    count: fc.nat({ max: 20 }),
  }),
  // Case 2: devices present but count missing (ApiProvider should infer from array length)
  fc.record({
    devices: fc.array(arbDevice, { minLength: 0, maxLength: 15 }),
  })
);

/**
 * Generate a backend /context/snapshot response.
 * Simulates various states: all fields present, some missing (null in JSON → undefined after parse).
 */
const arbSnapshotResponse = fc.oneof(
  // Case 1: all fields present
  fc.record({
    timestamp: fc.string({ minLength: 5, maxLength: 30 }),
    deviceStates: fc.array(
      fc.record({
        id: fc.string({ minLength: 1, maxLength: 20 }),
        state: fc.dictionary(fc.string({ minLength: 1, maxLength: 10 }), fc.oneof(fc.string(), fc.integer(), fc.boolean())),
      }),
      { minLength: 0, maxLength: 10 }
    ),
    activeActivities: fc.array(
      fc.record({
        member: fc.string({ minLength: 1, maxLength: 20 }),
        activity: fc.string({ minLength: 1, maxLength: 30 }),
        room: fc.string({ minLength: 1, maxLength: 20 }),
      }),
      { minLength: 0, maxLength: 5 }
    ),
    environmentals: fc.record({
      temperature: fc.integer({ min: -50, max: 60 }),
      humidity: fc.integer({ min: 0, max: 100 }),
      powerGrid: fc.constantFrom('stable', 'unstable', 'offline'),
    }),
  }),
  // Case 2: missing arrays (ApiProvider should default to [])
  fc.record({
    timestamp: fc.string({ minLength: 5, maxLength: 30 }),
  }),
  // Case 3: missing environmentals (ApiProvider should default)
  fc.record({
    timestamp: fc.string({ minLength: 5, maxLength: 30 }),
    deviceStates: fc.array(
      fc.record({
        id: fc.string({ minLength: 1, maxLength: 20 }),
        state: fc.dictionary(fc.string({ minLength: 1, maxLength: 10 }), fc.oneof(fc.string(), fc.integer(), fc.boolean())),
      }),
      { minLength: 0, maxLength: 5 }
    ),
    activeActivities: fc.array(
      fc.record({
        member: fc.string({ minLength: 1, maxLength: 20 }),
        activity: fc.string({ minLength: 1, maxLength: 30 }),
        room: fc.string({ minLength: 1, maxLength: 20 }),
      }),
      { minLength: 0, maxLength: 3 }
    ),
  })
);

/** Generate a backend /context/patterns response */
const arbPatternsResponse = fc.oneof(
  // Case 1: patterns present
  fc.record({
    patterns: fc.array(
      fc.record({
        id: fc.string({ minLength: 1, maxLength: 20 }),
        confidence: fc.double({ min: 0, max: 1, noNaN: true, noDefaultInfinity: true }),
        schedule: fc.string({ minLength: 3, maxLength: 10 }),
        actions: fc.array(fc.string({ minLength: 1, maxLength: 20 }), { minLength: 1, maxLength: 5 }),
      }),
      { minLength: 0, maxLength: 5 }
    ),
  }),
  // Case 2: patterns missing (ApiProvider defaults to [])
  fc.record({})
);

/** Generate a backend /autonomy/tiers response */
const arbTiersResponse = fc.oneof(
  // Case 1: tiers present
  fc.record({
    tiers: fc.array(
      fc.record({
        category: fc.constantFrom('climate', 'lighting', 'security', 'kitchen', 'utility', 'power', 'entertainment', 'assistant'),
        currentTier: fc.integer({ min: 1, max: 5 }),
        trustScore: fc.integer({ min: 0, max: 100 }),
      }),
      { minLength: 0, maxLength: 8 }
    ),
  }),
  // Case 2: tiers missing (ApiProvider defaults to [])
  fc.record({})
);

describe('Property 12: Reshaped responses conform to the mock shape', () => {
  let provider;
  let mockFetch;

  beforeEach(() => {
    provider = new ApiProvider('http://localhost:8080');
    mockFetch = vi.fn();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /**
   * Helper: make fetch resolve with a given JSON payload.
   */
  function setupFetchResponse(data) {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => data,
    });
  }

  describe('getDevices() → {devices: Array, count: number}', () => {
    it('for any backend devices payload, normalized result has devices array and numeric count', async () => {
      await fc.assert(
        fc.asyncProperty(arbDevicesResponse, async (backendPayload) => {
          setupFetchResponse(backendPayload);
          const result = await provider.getDevices();

          // Shape assertions
          expect(result).toHaveProperty('devices');
          expect(result).toHaveProperty('count');
          expect(Array.isArray(result.devices)).toBe(true);
          expect(typeof result.count).toBe('number');
          // count must be a non-negative integer
          expect(result.count).toBeGreaterThanOrEqual(0);
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('getContextSnapshot() → {timestamp, deviceStates, activeActivities, environmentals}', () => {
    it('for any backend snapshot payload, normalized result conforms to mock shape', async () => {
      await fc.assert(
        fc.asyncProperty(arbSnapshotResponse, async (backendPayload) => {
          setupFetchResponse(backendPayload);
          const result = await provider.getContextSnapshot();

          // Top-level fields always present
          expect(result).toHaveProperty('timestamp');
          expect(result).toHaveProperty('deviceStates');
          expect(result).toHaveProperty('activeActivities');
          expect(result).toHaveProperty('environmentals');

          // deviceStates and activeActivities are arrays (defaults to [])
          expect(Array.isArray(result.deviceStates)).toBe(true);
          expect(Array.isArray(result.activeActivities)).toBe(true);

          // environmentals is an object with the 3 required fields
          expect(typeof result.environmentals).toBe('object');
          expect(result.environmentals).not.toBeNull();
          expect(result.environmentals).toHaveProperty('temperature');
          expect(result.environmentals).toHaveProperty('humidity');
          expect(result.environmentals).toHaveProperty('powerGrid');
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('getPatterns() → {patterns: Array}', () => {
    it('for any backend patterns payload, normalized result has patterns array', async () => {
      await fc.assert(
        fc.asyncProperty(arbPatternsResponse, async (backendPayload) => {
          setupFetchResponse(backendPayload);
          const result = await provider.getPatterns();

          expect(result).toHaveProperty('patterns');
          expect(Array.isArray(result.patterns)).toBe(true);
        }),
        { numRuns: 100 }
      );
    });
  });

  describe('getAutonomyTiers() → {tiers: Array}', () => {
    it('for any backend tiers payload, normalized result has tiers array', async () => {
      await fc.assert(
        fc.asyncProperty(arbTiersResponse, async (backendPayload) => {
          setupFetchResponse(backendPayload);
          const result = await provider.getAutonomyTiers();

          expect(result).toHaveProperty('tiers');
          expect(Array.isArray(result.tiers)).toBe(true);
        }),
        { numRuns: 100 }
      );
    });
  });
});
