import { describe, expect, beforeEach } from 'vitest';
import { test as fcTest } from '@fast-check/vitest';
import fc from 'fast-check';
import * as THREE from 'three';
import { LightingSystem } from './LightingSystem.js';
import { TIMING } from '../utils/constants.js';

/**
 * Property-Based Tests for LightingSystem day/night cycle.
 *
 * **Validates: Requirements 10.1, 10.2, 10.3**
 *
 * Property 12: Lighting matches time of day — daytime has higher intensity than nighttime.
 *   - Daytime range [390, 1050]: ambient >= 0.5, warm tones
 *   - Nighttime range [0, 329] ∪ [1111, 1439]: ambient <= 0.2, cool blue tones
 *
 * Property 13: Lighting transition interpolation — transition values are strictly
 *   between day and night values, and sunrise transitions are monotonically increasing,
 *   sunset transitions monotonically decreasing.
 */
describe('LightingSystem Property Tests', () => {
  let lighting;

  beforeEach(() => {
    const scene = new THREE.Scene();
    lighting = new LightingSystem(scene);
  });

  const { SUNRISE, SUNSET, TRANSITION } = TIMING;
  // Daytime: [SUNRISE + TRANSITION, SUNSET - TRANSITION] = [390, 1050]
  const DAY_START = SUNRISE + TRANSITION;   // 390
  const DAY_END = SUNSET - TRANSITION;      // 1050
  // Nighttime: [0, SUNRISE - TRANSITION - 1] ∪ [SUNSET + TRANSITION + 1, 1439] = [0, 329] ∪ [1111, 1439]
  const NIGHT_END_MORNING = SUNRISE - TRANSITION - 1;   // 329
  const NIGHT_START_EVENING = SUNSET + TRANSITION + 1;  // 1111

  // Night intensity values
  const NIGHT_AMBIENT = 0.15;
  const NIGHT_SUN = 0.05;
  // Day intensity values
  const DAY_AMBIENT = 0.6;
  const DAY_SUN = 1.0;

  describe('Property 12: Lighting matches time of day', () => {
    fcTest.prop(
      [fc.integer({ min: DAY_START, max: DAY_END })]
    )(
      'for any daytime value [390, 1050], ambient intensity >= 0.5 with warm tones',
      (timeMinutes) => {
        const result = lighting.calculateLighting(timeMinutes);
        expect(result.intensity.ambient).toBeGreaterThanOrEqual(0.5);
        expect(result.intensity.sun).toBe(DAY_SUN);
        // Warm tone: ambient color should be 0xfff8f0
        expect(result.color.ambient).toBe(0xfff8f0);
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: NIGHT_END_MORNING })]
    )(
      'for any early nighttime value [0, 329], ambient <= 0.2 with cool blue tones',
      (timeMinutes) => {
        const result = lighting.calculateLighting(timeMinutes);
        expect(result.intensity.ambient).toBeLessThanOrEqual(0.2);
        expect(result.intensity.sun).toBe(NIGHT_SUN);
        // Cool blue tone: ambient color should be 0x4466aa
        expect(result.color.ambient).toBe(0x4466aa);
      }
    );

    fcTest.prop(
      [fc.integer({ min: NIGHT_START_EVENING, max: 1439 })]
    )(
      'for any late nighttime value [1111, 1439], ambient <= 0.2 with cool blue tones',
      (timeMinutes) => {
        const result = lighting.calculateLighting(timeMinutes);
        expect(result.intensity.ambient).toBeLessThanOrEqual(0.2);
        expect(result.intensity.sun).toBe(NIGHT_SUN);
        // Cool blue tone: ambient color should be 0x4466aa
        expect(result.color.ambient).toBe(0x4466aa);
      }
    );

    fcTest.prop(
      [
        fc.integer({ min: DAY_START, max: DAY_END }),
        fc.oneof(
          fc.integer({ min: 0, max: NIGHT_END_MORNING }),
          fc.integer({ min: NIGHT_START_EVENING, max: 1439 })
        ),
      ]
    )(
      'daytime ambient intensity is always greater than nighttime ambient intensity',
      (dayTime, nightTime) => {
        const dayResult = lighting.calculateLighting(dayTime);
        const nightResult = lighting.calculateLighting(nightTime);
        expect(dayResult.intensity.ambient).toBeGreaterThan(nightResult.intensity.ambient);
        expect(dayResult.intensity.sun).toBeGreaterThan(nightResult.intensity.sun);
      }
    );
  });

  describe('Property 13: Lighting transition interpolation', () => {
    // Sunrise transition interior: (330, 389] — excluding 330 where t=0 gives exact night values
    // At 330: t = 0 (exact night boundary), at 389: t approaches 1 but still < day threshold
    const SUNRISE_TRANS_START_EXCL = SUNRISE - TRANSITION + 1;  // 331
    const SUNRISE_TRANS_END = SUNRISE + TRANSITION - 1;          // 389

    // Sunset transition interior: [1051, 1109] — excluding 1110 where t=0 gives exact night values
    // At 1051: t approaches 1 but still < day threshold, at 1110: t = 0 (exact night boundary)
    const SUNSET_TRANS_START = SUNSET - TRANSITION + 1;  // 1051
    const SUNSET_TRANS_END_EXCL = SUNSET + TRANSITION - 1;  // 1109

    // Full transition ranges for monotonicity (including boundaries is valid)
    const SUNRISE_TRANS_FULL_START = SUNRISE - TRANSITION;  // 330
    const SUNRISE_TRANS_FULL_END = SUNRISE + TRANSITION - 1;  // 389
    const SUNSET_TRANS_FULL_START = SUNSET - TRANSITION + 1;  // 1051
    const SUNSET_TRANS_FULL_END = SUNSET + TRANSITION;  // 1110

    fcTest.prop(
      [fc.integer({ min: SUNRISE_TRANS_START_EXCL, max: SUNRISE_TRANS_END })]
    )(
      'during sunrise transition (331, 389], intensities are strictly between night and day values',
      (timeMinutes) => {
        const result = lighting.calculateLighting(timeMinutes);
        // Ambient: strictly between 0.15 and 0.6
        expect(result.intensity.ambient).toBeGreaterThan(NIGHT_AMBIENT);
        expect(result.intensity.ambient).toBeLessThan(DAY_AMBIENT);
        // Sun: strictly between 0.05 and 1.0
        expect(result.intensity.sun).toBeGreaterThan(NIGHT_SUN);
        expect(result.intensity.sun).toBeLessThan(DAY_SUN);
      }
    );

    fcTest.prop(
      [fc.integer({ min: SUNSET_TRANS_START, max: SUNSET_TRANS_END_EXCL })]
    )(
      'during sunset transition [1051, 1109], intensities are strictly between night and day values',
      (timeMinutes) => {
        const result = lighting.calculateLighting(timeMinutes);
        // Ambient: strictly between 0.15 and 0.6
        expect(result.intensity.ambient).toBeGreaterThan(NIGHT_AMBIENT);
        expect(result.intensity.ambient).toBeLessThan(DAY_AMBIENT);
        // Sun: strictly between 0.05 and 1.0
        expect(result.intensity.sun).toBeGreaterThan(NIGHT_SUN);
        expect(result.intensity.sun).toBeLessThan(DAY_SUN);
      }
    );

    fcTest.prop(
      [
        fc.integer({ min: SUNRISE_TRANS_FULL_START, max: SUNRISE_TRANS_FULL_END }),
        fc.integer({ min: SUNRISE_TRANS_FULL_START, max: SUNRISE_TRANS_FULL_END }),
      ]
    )(
      'sunrise transition is monotonically increasing: for any t1 < t2 in [330, 389], intensity(t1) <= intensity(t2)',
      (a, b) => {
        const t1 = Math.min(a, b);
        const t2 = Math.max(a, b);
        const result1 = lighting.calculateLighting(t1);
        const result2 = lighting.calculateLighting(t2);
        expect(result2.intensity.ambient).toBeGreaterThanOrEqual(result1.intensity.ambient);
        expect(result2.intensity.sun).toBeGreaterThanOrEqual(result1.intensity.sun);
      }
    );

    fcTest.prop(
      [
        fc.integer({ min: SUNSET_TRANS_FULL_START, max: SUNSET_TRANS_FULL_END }),
        fc.integer({ min: SUNSET_TRANS_FULL_START, max: SUNSET_TRANS_FULL_END }),
      ]
    )(
      'sunset transition is monotonically decreasing: for any t1 < t2 in [1051, 1110], intensity(t1) >= intensity(t2)',
      (a, b) => {
        const t1 = Math.min(a, b);
        const t2 = Math.max(a, b);
        const result1 = lighting.calculateLighting(t1);
        const result2 = lighting.calculateLighting(t2);
        expect(result1.intensity.ambient).toBeGreaterThanOrEqual(result2.intensity.ambient);
        expect(result1.intensity.sun).toBeGreaterThanOrEqual(result2.intensity.sun);
      }
    );
  });
});
