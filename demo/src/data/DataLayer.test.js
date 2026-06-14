/**
 * Property tests for the DataLayer module.
 *
 * Feature: demo-backend-integration, Property 11: Data layer routes requests by mode
 *
 * **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
 *
 * Property 1: Data layer mode routing - when mode is 'mock', all calls go to
 * MockProvider; when mode is 'real', all calls go to ApiProvider.
 *
 * Property 2: Mock data schema conformance - all mock data responses match
 * the expected schema structure.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { DataLayer } from './DataLayer.js';
import { MockProvider } from './MockProvider.js';
import { ApiProvider } from './ApiProvider.js';

describe('DataLayer - Property 1: Mode Routing', () => {
  let dataLayer;

  beforeEach(() => {
    dataLayer = new DataLayer();
  });

  it('defaults to mock mode on construction', () => {
    expect(dataLayer.mode).toBe('mock');
  });

  it('provider returns MockProvider instance when mode is mock', () => {
    dataLayer.setMode('mock');
    expect(dataLayer.provider).toBeInstanceOf(MockProvider);
  });

  it('provider returns ApiProvider instance when mode is real', () => {
    dataLayer.setMode('real');
    expect(dataLayer.provider).toBeInstanceOf(ApiProvider);
  });

  it('switching from mock to real changes the active provider', () => {
    dataLayer.setMode('mock');
    const mockRef = dataLayer.provider;
    expect(mockRef).toBeInstanceOf(MockProvider);

    dataLayer.setMode('real');
    const realRef = dataLayer.provider;
    expect(realRef).toBeInstanceOf(ApiProvider);
    expect(realRef).not.toBe(mockRef);
  });

  it('switching from real back to mock restores MockProvider', () => {
    dataLayer.setMode('real');
    expect(dataLayer.provider).toBeInstanceOf(ApiProvider);

    dataLayer.setMode('mock');
    expect(dataLayer.provider).toBeInstanceOf(MockProvider);
  });

  it('multiple mode toggles always return the correct provider type', () => {
    const modes = ['mock', 'real', 'mock', 'real', 'real', 'mock'];
    for (const mode of modes) {
      dataLayer.setMode(mode);
      if (mode === 'mock') {
        expect(dataLayer.provider).toBeInstanceOf(MockProvider);
      } else {
        expect(dataLayer.provider).toBeInstanceOf(ApiProvider);
      }
    }
  });

  it('delegated methods route to MockProvider in mock mode', async () => {
    dataLayer.setMode('mock');
    const result = await dataLayer.getDevices();
    // MockProvider always returns devices array - if we get a result, routing worked
    expect(result).toHaveProperty('devices');
    expect(result).toHaveProperty('count');
    expect(result.devices.length).toBeGreaterThan(0);
  });

  it('all delegated methods exist on DataLayer and route correctly in mock mode', async () => {
    dataLayer.setMode('mock');

    // getDevices
    const devices = await dataLayer.getDevices();
    expect(devices).toBeDefined();

    // getDeviceState
    const state = await dataLayer.getDeviceState('living_room_ac');
    expect(state).toBeDefined();

    // sendCommand
    const cmdResult = await dataLayer.sendCommand('living_room_ac', { power: 'on' });
    expect(cmdResult).toBeDefined();

    // getContextSnapshot
    const snapshot = await dataLayer.getContextSnapshot();
    expect(snapshot).toBeDefined();

    // getPatterns
    const patterns = await dataLayer.getPatterns();
    expect(patterns).toBeDefined();

    // getAutonomyTiers
    const tiers = await dataLayer.getAutonomyTiers();
    expect(tiers).toBeDefined();

    // updateTier
    const tierUpdate = await dataLayer.updateTier('climate', { currentTier: 4 });
    expect(tierUpdate).toBeDefined();
  });

  it('provider identity remains stable without mode change', () => {
    dataLayer.setMode('mock');
    const ref1 = dataLayer.provider;
    const ref2 = dataLayer.provider;
    expect(ref1).toBe(ref2);

    dataLayer.setMode('real');
    const ref3 = dataLayer.provider;
    const ref4 = dataLayer.provider;
    expect(ref3).toBe(ref4);
  });
});

describe('DataLayer - Property 2: Mock Data Schema Conformance', () => {
  let dataLayer;

  beforeEach(() => {
    dataLayer = new DataLayer();
    dataLayer.setMode('mock');
  });

  describe('Device schema conformance', () => {
    it('getDevices returns an object with devices array and count', async () => {
      const result = await dataLayer.getDevices();
      expect(result).toHaveProperty('devices');
      expect(result).toHaveProperty('count');
      expect(Array.isArray(result.devices)).toBe(true);
      expect(typeof result.count).toBe('number');
      expect(result.count).toBe(result.devices.length);
    });

    it('every device has required fields: id, name, category, room, brand, state', async () => {
      const { devices } = await dataLayer.getDevices();
      for (const device of devices) {
        expect(device).toHaveProperty('id');
        expect(device).toHaveProperty('name');
        expect(device).toHaveProperty('category');
        expect(device).toHaveProperty('room');
        expect(device).toHaveProperty('brand');
        expect(device).toHaveProperty('state');

        expect(typeof device.id).toBe('string');
        expect(typeof device.name).toBe('string');
        expect(typeof device.category).toBe('string');
        expect(typeof device.room).toBe('string');
        expect(typeof device.brand).toBe('string');
        expect(typeof device.state).toBe('object');
        expect(device.state).not.toBeNull();
      }
    });

    it('device IDs are unique', async () => {
      const { devices } = await dataLayer.getDevices();
      const ids = devices.map((d) => d.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });

    it('device categories are from the expected set', async () => {
      const validCategories = [
        'climate',
        'lighting',
        'security',
        'kitchen',
        'utility',
        'power',
        'entertainment',
        'assistant',
      ];
      const { devices } = await dataLayer.getDevices();
      for (const device of devices) {
        expect(validCategories).toContain(device.category);
      }
    });
  });

  describe('Pattern schema conformance', () => {
    it('getPatterns returns an object with patterns array', async () => {
      const result = await dataLayer.getPatterns();
      expect(result).toHaveProperty('patterns');
      expect(Array.isArray(result.patterns)).toBe(true);
    });

    it('every pattern has required fields: id, confidence, schedule, actions', async () => {
      const { patterns } = await dataLayer.getPatterns();
      expect(patterns.length).toBeGreaterThan(0);
      for (const pattern of patterns) {
        expect(pattern).toHaveProperty('id');
        expect(pattern).toHaveProperty('confidence');
        expect(pattern).toHaveProperty('schedule');
        expect(pattern).toHaveProperty('actions');

        expect(typeof pattern.id).toBe('string');
        expect(typeof pattern.confidence).toBe('number');
        expect(typeof pattern.schedule).toBe('string');
        expect(Array.isArray(pattern.actions)).toBe(true);
      }
    });

    it('pattern confidence values are between 0 and 1', async () => {
      const { patterns } = await dataLayer.getPatterns();
      for (const pattern of patterns) {
        expect(pattern.confidence).toBeGreaterThanOrEqual(0);
        expect(pattern.confidence).toBeLessThanOrEqual(1);
      }
    });

    it('pattern actions are non-empty string arrays', async () => {
      const { patterns } = await dataLayer.getPatterns();
      for (const pattern of patterns) {
        expect(pattern.actions.length).toBeGreaterThan(0);
        for (const action of pattern.actions) {
          expect(typeof action).toBe('string');
          expect(action.length).toBeGreaterThan(0);
        }
      }
    });
  });

  describe('Autonomy tier schema conformance', () => {
    it('getAutonomyTiers returns an object with tiers array', async () => {
      const result = await dataLayer.getAutonomyTiers();
      expect(result).toHaveProperty('tiers');
      expect(Array.isArray(result.tiers)).toBe(true);
    });

    it('every tier has required fields: category, currentTier, trustScore', async () => {
      const { tiers } = await dataLayer.getAutonomyTiers();
      expect(tiers.length).toBeGreaterThan(0);
      for (const tier of tiers) {
        expect(tier).toHaveProperty('category');
        expect(tier).toHaveProperty('currentTier');
        expect(tier).toHaveProperty('trustScore');

        expect(typeof tier.category).toBe('string');
        expect(typeof tier.currentTier).toBe('number');
        expect(typeof tier.trustScore).toBe('number');
      }
    });

    it('tier currentTier values are between 1 and 5', async () => {
      const { tiers } = await dataLayer.getAutonomyTiers();
      for (const tier of tiers) {
        expect(tier.currentTier).toBeGreaterThanOrEqual(1);
        expect(tier.currentTier).toBeLessThanOrEqual(5);
      }
    });

    it('tier trustScore values are between 0 and 100', async () => {
      const { tiers } = await dataLayer.getAutonomyTiers();
      for (const tier of tiers) {
        expect(tier.trustScore).toBeGreaterThanOrEqual(0);
        expect(tier.trustScore).toBeLessThanOrEqual(100);
      }
    });

    it('tier categories are from the expected device category set', async () => {
      const validCategories = [
        'climate',
        'lighting',
        'security',
        'kitchen',
        'utility',
        'power',
        'entertainment',
        'assistant',
      ];
      const { tiers } = await dataLayer.getAutonomyTiers();
      for (const tier of tiers) {
        expect(validCategories).toContain(tier.category);
      }
    });
  });

  describe('Context snapshot schema conformance', () => {
    it('getContextSnapshot returns required top-level fields', async () => {
      const snapshot = await dataLayer.getContextSnapshot();
      expect(snapshot).toHaveProperty('timestamp');
      expect(snapshot).toHaveProperty('deviceStates');
      expect(snapshot).toHaveProperty('activeActivities');
      expect(snapshot).toHaveProperty('environmentals');

      expect(typeof snapshot.timestamp).toBe('string');
      expect(Array.isArray(snapshot.deviceStates)).toBe(true);
      expect(Array.isArray(snapshot.activeActivities)).toBe(true);
      expect(typeof snapshot.environmentals).toBe('object');
    });

    it('environmentals has temperature, humidity, and powerGrid fields', async () => {
      const { environmentals } = await dataLayer.getContextSnapshot();
      expect(environmentals).toHaveProperty('temperature');
      expect(environmentals).toHaveProperty('humidity');
      expect(environmentals).toHaveProperty('powerGrid');

      expect(typeof environmentals.temperature).toBe('number');
      expect(typeof environmentals.humidity).toBe('number');
      expect(typeof environmentals.powerGrid).toBe('string');
    });
  });

  describe('Command response schema conformance', () => {
    it('sendCommand returns success, deviceId, command, and timestamp', async () => {
      const result = await dataLayer.sendCommand('living_room_ac', {
        power: 'on',
      });
      expect(result).toHaveProperty('success');
      expect(result).toHaveProperty('deviceId');
      expect(result).toHaveProperty('command');
      expect(result).toHaveProperty('timestamp');

      expect(typeof result.success).toBe('boolean');
      expect(result.success).toBe(true);
      expect(result.deviceId).toBe('living_room_ac');
      expect(typeof result.timestamp).toBe('string');
    });
  });
});

/**
 * Feature: demo-backend-integration, Property 11: Data layer routes requests by mode
 *
 * **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
 *
 * For any sequence of mode settings, the Data_Layer SHALL route requests to the
 * Api_Provider when the Mode is 'real' and to the Mock_Provider otherwise,
 * with the initial Mode being 'mock'.
 */
describe('Property 11: Data layer routes requests by mode (property-based)', () => {
  it('for any sequence of mode switches, the provider always matches the current mode', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom('mock', 'real'), { minLength: 1, maxLength: 20 }),
        (modeSequence) => {
          const dataLayer = new DataLayer();

          // Initial mode must be 'mock' (Requirement 9.1)
          expect(dataLayer.mode).toBe('mock');
          expect(dataLayer.provider).toBeInstanceOf(MockProvider);

          for (const mode of modeSequence) {
            dataLayer.setMode(mode);

            if (mode === 'real') {
              // Requirement 9.3: real mode routes to ApiProvider
              expect(dataLayer.provider).toBeInstanceOf(ApiProvider);
            } else {
              // Requirement 9.2: mock mode routes to MockProvider
              expect(dataLayer.provider).toBeInstanceOf(MockProvider);
            }
          }
        }
      ),
      { numRuns: 100 }
    );
  });

  it('for any mode value, repeated access to provider returns the same instance', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('mock', 'real'),
        (mode) => {
          const dataLayer = new DataLayer();
          dataLayer.setMode(mode);
          const ref1 = dataLayer.provider;
          const ref2 = dataLayer.provider;
          expect(ref1).toBe(ref2);
        }
      ),
      { numRuns: 100 }
    );
  });
});
