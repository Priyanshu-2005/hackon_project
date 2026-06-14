import { describe, it, expect } from 'vitest';
import { MockProvider } from './MockProvider.js';

describe('MockProvider', () => {
  const provider = new MockProvider();

  describe('getDevices', () => {
    it('returns all 10 devices with correct count', async () => {
      const result = await provider.getDevices();
      expect(result.devices).toHaveLength(10);
      expect(result.count).toBe(10);
    });

    it('each device has required fields', async () => {
      const { devices } = await provider.getDevices();
      for (const device of devices) {
        expect(device).toHaveProperty('id');
        expect(device).toHaveProperty('name');
        expect(device).toHaveProperty('category');
        expect(device).toHaveProperty('room');
        expect(device).toHaveProperty('brand');
        expect(device).toHaveProperty('state');
      }
    });

    it('contains the expected device IDs', async () => {
      const { devices } = await provider.getDevices();
      const ids = devices.map((d) => d.id);
      expect(ids).toContain('living_room_ac');
      expect(ids).toContain('smart_lights');
      expect(ids).toContain('security_camera');
      expect(ids).toContain('smart_lock');
      expect(ids).toContain('kitchen_hub');
      expect(ids).toContain('water_purifier');
      expect(ids).toContain('smart_geyser');
      expect(ids).toContain('inverter_ups');
      expect(ids).toContain('smart_tv');
      expect(ids).toContain('echo_devices');
    });
  });

  describe('getDeviceState', () => {
    it('returns device object for valid ID', async () => {
      const device = await provider.getDeviceState('living_room_ac');
      expect(device).not.toBeNull();
      expect(device.id).toBe('living_room_ac');
      expect(device.state.temperature).toBe(24);
      expect(device.state.mode).toBe('cool');
    });

    it('returns null for unknown device ID', async () => {
      const device = await provider.getDeviceState('nonexistent');
      expect(device).toBeNull();
    });

    it('returns a copy, not a reference', async () => {
      const device1 = await provider.getDeviceState('smart_lights');
      const device2 = await provider.getDeviceState('smart_lights');
      expect(device1).not.toBe(device2);
      expect(device1).toEqual(device2);
    });
  });

  describe('sendCommand', () => {
    it('returns success with deviceId, command, and timestamp', async () => {
      const command = { action: 'set_temperature', value: 22 };
      const result = await provider.sendCommand('living_room_ac', command);
      expect(result.success).toBe(true);
      expect(result.deviceId).toBe('living_room_ac');
      expect(result.command).toEqual(command);
      expect(result.timestamp).toBeDefined();
    });

    it('timestamp is a valid ISO string', async () => {
      const result = await provider.sendCommand('smart_tv', { action: 'power_on' });
      const date = new Date(result.timestamp);
      expect(date.toISOString()).toBe(result.timestamp);
    });
  });

  describe('getContextSnapshot', () => {
    it('returns snapshot with all required fields', async () => {
      const snapshot = await provider.getContextSnapshot();
      expect(snapshot).toHaveProperty('timestamp');
      expect(snapshot).toHaveProperty('deviceStates');
      expect(snapshot).toHaveProperty('activeActivities');
      expect(snapshot).toHaveProperty('environmentals');
    });

    it('deviceStates contains entries for all 10 devices', async () => {
      const snapshot = await provider.getContextSnapshot();
      expect(snapshot.deviceStates).toHaveLength(10);
      for (const entry of snapshot.deviceStates) {
        expect(entry).toHaveProperty('id');
        expect(entry).toHaveProperty('state');
      }
    });

    it('environmentals has expected default values', async () => {
      const snapshot = await provider.getContextSnapshot();
      expect(snapshot.environmentals.temperature).toBe(34);
      expect(snapshot.environmentals.humidity).toBe(65);
      expect(snapshot.environmentals.powerGrid).toBe('stable');
    });
  });

  describe('getPatterns', () => {
    it('returns 3 patterns', async () => {
      const result = await provider.getPatterns();
      expect(result.patterns).toHaveLength(3);
    });

    it('each pattern has required fields', async () => {
      const { patterns } = await provider.getPatterns();
      for (const pattern of patterns) {
        expect(pattern).toHaveProperty('id');
        expect(pattern).toHaveProperty('confidence');
        expect(pattern).toHaveProperty('schedule');
        expect(pattern).toHaveProperty('actions');
        expect(pattern.confidence).toBeGreaterThan(0);
        expect(pattern.confidence).toBeLessThanOrEqual(1);
        expect(Array.isArray(pattern.actions)).toBe(true);
      }
    });

    it('contains expected pattern IDs', async () => {
      const { patterns } = await provider.getPatterns();
      const ids = patterns.map((p) => p.id);
      expect(ids).toContain('morning_routine');
      expect(ids).toContain('evening_cooling');
      expect(ids).toContain('security_away');
    });
  });

  describe('getAutonomyTiers', () => {
    it('returns 8 tier entries for all device categories', async () => {
      const result = await provider.getAutonomyTiers();
      expect(result.tiers).toHaveLength(8);
    });

    it('each tier entry has category, currentTier, and trustScore', async () => {
      const { tiers } = await provider.getAutonomyTiers();
      for (const tier of tiers) {
        expect(tier).toHaveProperty('category');
        expect(tier).toHaveProperty('currentTier');
        expect(tier).toHaveProperty('trustScore');
        expect(tier.currentTier).toBeGreaterThanOrEqual(1);
        expect(tier.currentTier).toBeLessThanOrEqual(5);
        expect(tier.trustScore).toBeGreaterThanOrEqual(0);
        expect(tier.trustScore).toBeLessThanOrEqual(100);
      }
    });

    it('contains all expected categories', async () => {
      const { tiers } = await provider.getAutonomyTiers();
      const categories = tiers.map((t) => t.category);
      expect(categories).toContain('climate');
      expect(categories).toContain('lighting');
      expect(categories).toContain('security');
      expect(categories).toContain('kitchen');
      expect(categories).toContain('utility');
      expect(categories).toContain('power');
      expect(categories).toContain('entertainment');
      expect(categories).toContain('assistant');
    });
  });

  describe('updateTier', () => {
    it('returns success with device and merged config', async () => {
      const config = { currentTier: 4, trustScore: 80 };
      const result = await provider.updateTier('climate', config);
      expect(result.success).toBe(true);
      expect(result.device).toBe('climate');
      expect(result.currentTier).toBe(4);
      expect(result.trustScore).toBe(80);
    });
  });
});
