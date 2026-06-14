import { describe, it, expect, beforeEach } from 'vitest';
import { StateStore } from './StateStore.js';

describe('StateStore', () => {
  let store;

  beforeEach(() => {
    store = new StateStore();
  });

  describe('setDeviceState', () => {
    it('stores device state for a new device', () => {
      store.setDeviceState('ac_1', { state: 'on', room: 'livingRoom', category: 'climate', tier: 3 });
      expect(store.devices.get('ac_1')).toEqual({ state: 'on', room: 'livingRoom', category: 'climate', tier: 3 });
    });

    it('merges state into existing device entry', () => {
      store.setDeviceState('ac_1', { state: 'on', room: 'livingRoom', category: 'climate', tier: 3 });
      store.setDeviceState('ac_1', { state: 'off' });
      expect(store.devices.get('ac_1')).toEqual({ state: 'off', room: 'livingRoom', category: 'climate', tier: 3 });
    });

    it('emits device:<id> event on state change', () => {
      const received = [];
      store.on('device:ac_1', (data) => received.push(data));
      store.setDeviceState('ac_1', { state: 'on' });
      expect(received).toEqual([{ state: 'on' }]);
    });
  });

  describe('setFamilyPosition', () => {
    it('stores family member position', () => {
      store.setFamilyPosition('rajesh', 'kitchen', 'breakfast');
      expect(store.familyPositions.get('rajesh')).toEqual({ room: 'kitchen', activity: 'breakfast' });
    });

    it('emits family:<id> event on position change', () => {
      const received = [];
      store.on('family:rajesh', (data) => received.push(data));
      store.setFamilyPosition('rajesh', 'livingRoom', 'relaxing');
      expect(received).toEqual([{ room: 'livingRoom', activity: 'relaxing' }]);
    });
  });

  describe('updateTrustScore', () => {
    it('initializes score from zero and calculates tier', () => {
      store.updateTrustScore('climate', 10);
      const result = store.trustScores.get('climate');
      expect(result.score).toBe(10);
      expect(result.tier).toBe(1);
    });

    it('accumulates deltas on successive calls', () => {
      store.updateTrustScore('climate', 30);
      store.updateTrustScore('climate', 20);
      const result = store.trustScores.get('climate');
      expect(result.score).toBe(50);
      expect(result.tier).toBe(3);
    });

    it('clamps score at 100 (upper bound)', () => {
      store.updateTrustScore('security', 120);
      expect(store.trustScores.get('security').score).toBe(100);
      expect(store.trustScores.get('security').tier).toBe(5);
    });

    it('clamps score at 0 (lower bound)', () => {
      store.updateTrustScore('lighting', 10);
      store.updateTrustScore('lighting', -50);
      expect(store.trustScores.get('lighting').score).toBe(0);
      expect(store.trustScores.get('lighting').tier).toBe(1);
    });

    it('emits trust:<category> event', () => {
      const received = [];
      store.on('trust:climate', (data) => received.push(data));
      store.updateTrustScore('climate', 50);
      expect(received).toEqual([{ score: 50, tier: 3 }]);
    });
  });

  describe('calculateTier', () => {
    it('maps 0-20 to tier 1', () => {
      expect(store.calculateTier(0)).toBe(1);
      expect(store.calculateTier(10)).toBe(1);
      expect(store.calculateTier(20)).toBe(1);
    });

    it('maps 21-45 to tier 2', () => {
      expect(store.calculateTier(21)).toBe(2);
      expect(store.calculateTier(33)).toBe(2);
      expect(store.calculateTier(45)).toBe(2);
    });

    it('maps 46-70 to tier 3', () => {
      expect(store.calculateTier(46)).toBe(3);
      expect(store.calculateTier(58)).toBe(3);
      expect(store.calculateTier(70)).toBe(3);
    });

    it('maps 71-90 to tier 4', () => {
      expect(store.calculateTier(71)).toBe(4);
      expect(store.calculateTier(80)).toBe(4);
      expect(store.calculateTier(90)).toBe(4);
    });

    it('maps 91-100 to tier 5', () => {
      expect(store.calculateTier(91)).toBe(5);
      expect(store.calculateTier(95)).toBe(5);
      expect(store.calculateTier(100)).toBe(5);
    });
  });

  describe('addEventLogEntry', () => {
    it('pushes entry to events array', () => {
      const entry = { action: 'pre-cool', device: 'ac_1', reasoning: 'Hot day', timestamp: 1000 };
      store.addEventLogEntry(entry);
      expect(store.events).toHaveLength(1);
      expect(store.events[0]).toEqual(entry);
    });

    it('maintains chronological order', () => {
      store.addEventLogEntry({ timestamp: 100 });
      store.addEventLogEntry({ timestamp: 200 });
      store.addEventLogEntry({ timestamp: 300 });
      expect(store.events.map(e => e.timestamp)).toEqual([100, 200, 300]);
    });

    it('emits eventlog event with the entry', () => {
      const received = [];
      store.on('eventlog', (data) => received.push(data));
      const entry = { action: 'security-arm', timestamp: 500 };
      store.addEventLogEntry(entry);
      expect(received).toEqual([entry]);
    });
  });

  describe('pub/sub (on/emit)', () => {
    it('supports multiple listeners on the same key', () => {
      const results = [];
      store.on('test', (data) => results.push('a:' + data));
      store.on('test', (data) => results.push('b:' + data));
      store.emit('test', 'hello');
      expect(results).toEqual(['a:hello', 'b:hello']);
    });

    it('does not throw when emitting with no listeners', () => {
      expect(() => store.emit('nonexistent', {})).not.toThrow();
    });

    it('isolates listeners across different keys', () => {
      const results = [];
      store.on('key1', () => results.push('key1'));
      store.on('key2', () => results.push('key2'));
      store.emit('key1', null);
      expect(results).toEqual(['key1']);
    });
  });
});
