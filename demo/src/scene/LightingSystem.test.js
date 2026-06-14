import { describe, it, expect, beforeEach } from 'vitest';
import * as THREE from 'three';
import { LightingSystem } from './LightingSystem.js';
import { TIMING } from '../utils/constants.js';

describe('LightingSystem', () => {
  let scene;
  let lighting;

  beforeEach(() => {
    scene = new THREE.Scene();
    lighting = new LightingSystem(scene);
  });

  describe('constructor', () => {
    it('creates an AmbientLight with intensity 0.4', () => {
      expect(lighting.ambient).toBeInstanceOf(THREE.AmbientLight);
      expect(lighting.ambient.intensity).toBe(0.4);
    });

    it('creates a DirectionalLight with intensity 0.8', () => {
      expect(lighting.sun).toBeInstanceOf(THREE.DirectionalLight);
      expect(lighting.sun.intensity).toBe(0.8);
    });

    it('positions the sun at (5, 10, 5)', () => {
      expect(lighting.sun.position.x).toBe(5);
      expect(lighting.sun.position.y).toBe(10);
      expect(lighting.sun.position.z).toBe(5);
    });

    it('enables castShadow on the sun', () => {
      expect(lighting.sun.castShadow).toBe(true);
    });

    it('adds both lights to the scene', () => {
      expect(scene.children).toContain(lighting.ambient);
      expect(scene.children).toContain(lighting.sun);
    });
  });

  describe('calculateLighting', () => {
    it('returns daytime values for midday (720 minutes / 12:00)', () => {
      const result = lighting.calculateLighting(720);
      expect(result.intensity.ambient).toBe(0.6);
      expect(result.intensity.sun).toBe(1.0);
      expect(result.color.ambient).toBe(0xfff8f0);
      expect(result.color.sun).toBe(0xfff4e0);
    });

    it('returns daytime values just after sunrise transition (SUNRISE + TRANSITION)', () => {
      const result = lighting.calculateLighting(TIMING.SUNRISE + TIMING.TRANSITION);
      expect(result.intensity.ambient).toBe(0.6);
      expect(result.intensity.sun).toBe(1.0);
    });

    it('returns daytime values just before sunset transition (SUNSET - TRANSITION)', () => {
      const result = lighting.calculateLighting(TIMING.SUNSET - TIMING.TRANSITION);
      expect(result.intensity.ambient).toBe(0.6);
      expect(result.intensity.sun).toBe(1.0);
    });

    it('returns nighttime values for midnight (0 minutes)', () => {
      const result = lighting.calculateLighting(0);
      expect(result.intensity.ambient).toBe(0.15);
      expect(result.intensity.sun).toBe(0.05);
      expect(result.color.ambient).toBe(0x4466aa);
      expect(result.color.sun).toBe(0x334488);
    });

    it('returns nighttime values for late night (1400 minutes / 23:20)', () => {
      const result = lighting.calculateLighting(1400);
      expect(result.intensity.ambient).toBe(0.15);
      expect(result.intensity.sun).toBe(0.05);
    });

    it('returns nighttime values just before sunrise transition starts', () => {
      const result = lighting.calculateLighting(TIMING.SUNRISE - TIMING.TRANSITION - 1);
      expect(result.intensity.ambient).toBe(0.15);
      expect(result.intensity.sun).toBe(0.05);
    });

    it('returns nighttime values just after sunset transition ends', () => {
      const result = lighting.calculateLighting(TIMING.SUNSET + TIMING.TRANSITION + 1);
      expect(result.intensity.ambient).toBe(0.15);
      expect(result.intensity.sun).toBe(0.05);
    });

    it('returns interpolated values during sunrise transition', () => {
      // Midpoint of sunrise transition (SUNRISE = 360)
      const result = lighting.calculateLighting(360);
      expect(result.intensity.ambient).toBeCloseTo(0.375, 2);
      expect(result.intensity.sun).toBeCloseTo(0.525, 2);
    });

    it('returns interpolated values during sunset transition', () => {
      // Midpoint of sunset transition (SUNSET = 1080)
      const result = lighting.calculateLighting(1080);
      expect(result.intensity.ambient).toBeCloseTo(0.375, 2);
      expect(result.intensity.sun).toBeCloseTo(0.525, 2);
    });

    it('returns near-day values at end of sunrise transition', () => {
      const result = lighting.calculateLighting(TIMING.SUNRISE + TIMING.TRANSITION - 1);
      // t should be close to 1 (day)
      expect(result.intensity.ambient).toBeGreaterThan(0.5);
      expect(result.intensity.sun).toBeGreaterThan(0.9);
    });

    it('returns near-night values at start of sunset transition', () => {
      const result = lighting.calculateLighting(TIMING.SUNSET - TIMING.TRANSITION + 1);
      // t should be close to 1 (day)
      expect(result.intensity.ambient).toBeGreaterThan(0.5);
      expect(result.intensity.sun).toBeGreaterThan(0.9);
    });
  });

  describe('interpolateLighting', () => {
    it('returns night values when t=0', () => {
      const result = lighting.interpolateLighting(0);
      expect(result.intensity.ambient).toBe(0.15);
      expect(result.intensity.sun).toBe(0.05);
      expect(result.color.ambient).toBe(0x4466aa);
      expect(result.color.sun).toBe(0xfff4e0);
    });

    it('returns day values when t=1', () => {
      const result = lighting.interpolateLighting(1);
      expect(result.intensity.ambient).toBe(0.6);
      expect(result.intensity.sun).toBe(1.0);
      expect(result.color.ambient).toBe(0xfff8f0);
      expect(result.color.sun).toBe(0xfff4e0);
    });

    it('returns midpoint values when t=0.5', () => {
      const result = lighting.interpolateLighting(0.5);
      expect(result.intensity.ambient).toBeCloseTo(0.375);
      expect(result.intensity.sun).toBeCloseTo(0.525);
    });
  });

  describe('updateForTime', () => {
    it('updates ambient light intensity and color for daytime', () => {
      lighting.updateForTime(720);
      expect(lighting.ambient.intensity).toBe(0.6);
      expect(lighting.ambient.color.getHex()).toBe(0xfff8f0);
    });

    it('updates sun light intensity and color for daytime', () => {
      lighting.updateForTime(720);
      expect(lighting.sun.intensity).toBe(1.0);
      expect(lighting.sun.color.getHex()).toBe(0xfff4e0);
    });

    it('updates ambient light intensity and color for nighttime', () => {
      lighting.updateForTime(0);
      expect(lighting.ambient.intensity).toBe(0.15);
      expect(lighting.ambient.color.getHex()).toBe(0x4466aa);
    });

    it('updates sun light intensity and color for nighttime', () => {
      lighting.updateForTime(0);
      expect(lighting.sun.intensity).toBe(0.05);
      expect(lighting.sun.color.getHex()).toBe(0x334488);
    });

    it('smoothly transitions during sunrise', () => {
      lighting.updateForTime(TIMING.SUNRISE);
      // At midpoint of transition, expect interpolated values
      expect(lighting.ambient.intensity).toBeCloseTo(0.375, 2);
      expect(lighting.sun.intensity).toBeCloseTo(0.525, 2);
    });
  });
});
