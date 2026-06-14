import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { StateStore } from './StateStore.js';

/**
 * Property-Based Tests for StateStore tier calculation.
 *
 * **Validates: Requirements 9.3**
 *
 * Property 11: Trust score maps to correct tier — for any score in 0-100,
 * calculateTier returns the correct tier (1-5) according to the mapping:
 *   0–20  → Tier 1
 *   21–45 → Tier 2
 *   46–70 → Tier 3
 *   71–90 → Tier 4
 *   91–100 → Tier 5
 */
describe('StateStore Property Tests - Tier Calculation', () => {
  let store;

  beforeEach(() => {
    store = new StateStore();
  });

  // Helper: expected tier for a given score
  function expectedTier(score) {
    if (score <= 20) return 1;
    if (score <= 45) return 2;
    if (score <= 70) return 3;
    if (score <= 90) return 4;
    return 5;
  }

  describe('Property 11: Trust score maps to correct tier', () => {
    it('for any integer score in [0, 100], calculateTier returns the correct tier', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 100 }),
          (score) => {
            const tier = store.calculateTier(score);
            expect(tier).toBe(expectedTier(score));
          }
        ),
        { numRuns: 200 }
      );
    });

    it('for any floating-point score in [0, 100], calculateTier returns the correct tier', () => {
      fc.assert(
        fc.property(
          fc.double({ min: 0, max: 100, noNaN: true, noDefaultInfinity: true }),
          (score) => {
            const tier = store.calculateTier(score);
            expect(tier).toBe(expectedTier(score));
          }
        ),
        { numRuns: 200 }
      );
    });
  });

  describe('Boundary values', () => {
    it('correctly handles all boundary values', () => {
      const boundaries = [
        { score: 0, tier: 1 },
        { score: 20, tier: 1 },
        { score: 21, tier: 2 },
        { score: 45, tier: 2 },
        { score: 46, tier: 3 },
        { score: 70, tier: 3 },
        { score: 71, tier: 4 },
        { score: 90, tier: 4 },
        { score: 91, tier: 5 },
        { score: 100, tier: 5 },
      ];

      for (const { score, tier } of boundaries) {
        expect(store.calculateTier(score)).toBe(tier);
      }
    });

    it('scores in the middle of each range return the correct tier', () => {
      // Mid-range values
      expect(store.calculateTier(10)).toBe(1);   // middle of 0-20
      expect(store.calculateTier(33)).toBe(2);   // middle of 21-45
      expect(store.calculateTier(58)).toBe(3);   // middle of 46-70
      expect(store.calculateTier(80)).toBe(4);   // middle of 71-90
      expect(store.calculateTier(95)).toBe(5);   // middle of 91-100
    });
  });

  describe('Monotonic property: higher scores never result in lower tiers', () => {
    it('for any two scores a < b in [0, 100], tier(a) <= tier(b)', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 100 }),
          fc.integer({ min: 0, max: 100 }),
          (a, b) => {
            const low = Math.min(a, b);
            const high = Math.max(a, b);
            const tierLow = store.calculateTier(low);
            const tierHigh = store.calculateTier(high);
            expect(tierLow).toBeLessThanOrEqual(tierHigh);
          }
        ),
        { numRuns: 200 }
      );
    });

    it('sequential increments from 0 to 100 never decrease the tier', () => {
      let prevTier = 0;
      for (let score = 0; score <= 100; score++) {
        const tier = store.calculateTier(score);
        expect(tier).toBeGreaterThanOrEqual(prevTier);
        prevTier = tier;
      }
    });
  });

  describe('updateTrustScore integration with calculateTier', () => {
    it('updateTrustScore correctly sets the tier based on accumulated score', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 100 }),
          (score) => {
            const freshStore = new StateStore();
            freshStore.updateTrustScore('test-category', score);
            const result = freshStore.trustScores.get('test-category');
            expect(result.score).toBe(score);
            expect(result.tier).toBe(expectedTier(score));
          }
        ),
        { numRuns: 200 }
      );
    });

    it('multiple deltas accumulate and produce correct tier', () => {
      fc.assert(
        fc.property(
          fc.array(fc.integer({ min: -50, max: 50 }), { minLength: 1, maxLength: 10 }),
          (deltas) => {
            const freshStore = new StateStore();
            let expectedScore = 0;
            for (const delta of deltas) {
              freshStore.updateTrustScore('accum', delta);
              expectedScore = Math.max(0, Math.min(100, expectedScore + delta));
            }
            const result = freshStore.trustScores.get('accum');
            expect(result.score).toBe(expectedScore);
            expect(result.tier).toBe(expectedTier(expectedScore));
          }
        ),
        { numRuns: 200 }
      );
    });
  });

  describe('Clamping: scores above 100 clamp to 100, below 0 clamp to 0', () => {
    it('scores above 100 are clamped to 100 (tier 5)', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 101, max: 1000 }),
          (delta) => {
            const freshStore = new StateStore();
            freshStore.updateTrustScore('over', delta);
            const result = freshStore.trustScores.get('over');
            expect(result.score).toBe(100);
            expect(result.tier).toBe(5);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('scores below 0 are clamped to 0 (tier 1)', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: -1000, max: -1 }),
          (delta) => {
            const freshStore = new StateStore();
            freshStore.updateTrustScore('under', delta);
            const result = freshStore.trustScores.get('under');
            expect(result.score).toBe(0);
            expect(result.tier).toBe(1);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('adding a large positive after existing score still clamps to 100', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 50, max: 100 }),
          fc.integer({ min: 60, max: 500 }),
          (initial, extra) => {
            const freshStore = new StateStore();
            freshStore.updateTrustScore('clamp-hi', initial);
            freshStore.updateTrustScore('clamp-hi', extra);
            const result = freshStore.trustScores.get('clamp-hi');
            expect(result.score).toBe(100);
            expect(result.tier).toBe(5);
          }
        ),
        { numRuns: 100 }
      );
    });

    it('subtracting a large negative after existing score still clamps to 0', () => {
      fc.assert(
        fc.property(
          fc.integer({ min: 0, max: 50 }),
          fc.integer({ min: -500, max: -51 }),
          (initial, negative) => {
            const freshStore = new StateStore();
            freshStore.updateTrustScore('clamp-lo', initial);
            freshStore.updateTrustScore('clamp-lo', negative);
            const result = freshStore.trustScores.get('clamp-lo');
            expect(result.score).toBe(0);
            expect(result.tier).toBe(1);
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
