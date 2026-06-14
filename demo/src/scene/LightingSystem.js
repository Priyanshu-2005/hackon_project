import * as THREE from 'three';
import { TIMING, COLORS } from '../utils/constants.js';

/**
 * LightingSystem manages day/night cycle lighting for the 3D scene.
 * Uses AmbientLight for base illumination, DirectionalLight as the sun,
 * and a PointLight for subtle Alexa blue accent.
 * Transitions smoothly over 30-minute windows at sunrise (06:00) and sunset (18:00).
 */
export class LightingSystem {
  /**
   * @param {THREE.Scene} scene - The Three.js scene to add lights to
   */
  constructor(scene) {
    this.scene = scene;

    // Ambient light — base illumination (0.4 intensity default)
    this.ambient = new THREE.AmbientLight(0xffffff, 0.4);

    // Directional light — acts as the sun (warm white, 0.8 intensity default)
    this.sun = new THREE.DirectionalLight(0xfff4e0, 0.8);
    this.sun.position.set(5, 10, 5);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.width = 1024;
    this.sun.shadow.mapSize.height = 1024;

    // Point light — subtle Alexa blue accent
    this.accent = new THREE.PointLight(COLORS.ACCENT, 0.3);
    this.accent.position.set(0, 3, 0);

    // Add lights to scene
    scene.add(this.ambient, this.sun, this.accent);
  }

  /**
   * Update lighting based on time of day.
   * @param {number} timeMinutes - Minutes since midnight (0–1439)
   */
  updateForTime(timeMinutes) {
    const { intensity, color } = this.calculateLighting(timeMinutes);
    this.ambient.intensity = intensity.ambient;
    this.ambient.color.set(color.ambient);
    this.sun.intensity = intensity.sun;
    this.sun.color.set(color.sun);
  }

  /**
   * Calculate lighting parameters based on time of day.
   * Returns intensity and color values for ambient and sun lights.
   *
   * - Daytime (SUNRISE+30 to SUNSET-30): warm, bright lighting
   * - Nighttime (before SUNRISE-30 or after SUNSET+30): cool blue, dim lighting
   * - Transition zones: smooth interpolation over 30-minute windows
   *
   * @param {number} timeMinutes - Minutes since midnight (0–1439)
   * @returns {{ intensity: { ambient: number, sun: number }, color: { ambient: number, sun: number } }}
   */
  calculateLighting(timeMinutes) {
    const { SUNRISE, SUNSET, TRANSITION } = TIMING;

    // Full daytime: warm and bright
    if (timeMinutes >= SUNRISE + TRANSITION && timeMinutes <= SUNSET - TRANSITION) {
      return {
        intensity: { ambient: 0.6, sun: 1.0 },
        color: { ambient: 0xfff8f0, sun: 0xfff4e0 },
      };
    }

    // Full nighttime: cool blue and dim
    if (timeMinutes < SUNRISE - TRANSITION || timeMinutes > SUNSET + TRANSITION) {
      return {
        intensity: { ambient: 0.15, sun: 0.05 },
        color: { ambient: 0x4466aa, sun: 0x334488 },
      };
    }

    // Transition zones: interpolate between night and day
    let t;
    if (timeMinutes >= SUNRISE - TRANSITION && timeMinutes <= SUNRISE + TRANSITION) {
      // Sunrise transition: night → day
      t = (timeMinutes - (SUNRISE - TRANSITION)) / (TRANSITION * 2);
    } else {
      // Sunset transition: day → night
      t = 1 - (timeMinutes - (SUNSET - TRANSITION)) / (TRANSITION * 2);
    }

    // Clamp t to [0, 1]
    t = Math.max(0, Math.min(1, t));
    return this.interpolateLighting(t);
  }

  /**
   * Interpolate between night and day lighting values.
   * @param {number} t - Interpolation factor (0 = night, 1 = day)
   * @returns {{ intensity: { ambient: number, sun: number }, color: { ambient: number, sun: number } }}
   */
  interpolateLighting(t) {
    const dayColor = new THREE.Color(0xfff8f0);
    const nightColor = new THREE.Color(0x4466aa);

    const ambientColor = nightColor.clone().lerp(dayColor, t);

    return {
      intensity: {
        ambient: 0.15 + 0.45 * t,
        sun: 0.05 + 0.95 * t,
      },
      color: {
        ambient: ambientColor.getHex(),
        sun: 0xfff4e0,
      },
    };
  }
}
