import * as THREE from 'three';

/**
 * Color palette for the 3D demo.
 * Dark mode with Alexa blue accent (#00CAFF).
 */
export const COLORS = {
  ACCENT: 0x00caff,
  DARK_BG: 0x0d1117,
  WALL: 0xf5e6d3,
  FLOOR: 0xe8d5b7,
  ROOF: 0xcc7744,
  DEVICE_GLOW: 0x00caff,
  AVATAR_COLORS: [0xff6b6b, 0x4ecdc4, 0x45b7d1, 0xf7dc6f, 0xbb8fce, 0x82e0aa],
};

/**
 * Material factory functions for reusable Three.js materials.
 */
export const MATERIALS = {
  wall() {
    return new THREE.MeshStandardMaterial({
      color: COLORS.WALL,
      roughness: 0.9,
      metalness: 0.0,
    });
  },

  floor() {
    return new THREE.MeshStandardMaterial({
      color: COLORS.FLOOR,
      roughness: 0.85,
      metalness: 0.0,
    });
  },

  device() {
    return new THREE.MeshStandardMaterial({
      color: COLORS.DEVICE_GLOW,
      emissive: COLORS.DEVICE_GLOW,
      emissiveIntensity: 0.3,
      roughness: 0.4,
      metalness: 0.6,
    });
  },

  glass() {
    return new THREE.MeshStandardMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0.3,
      roughness: 0.1,
      metalness: 0.0,
    });
  },
};

/**
 * Timing constants for the day/night cycle (in minutes from midnight).
 */
export const TIMING = {
  SUNRISE: 360,      // 06:00
  SUNSET: 1080,      // 18:00
  TRANSITION: 30,    // 30-minute interpolation window
};

/**
 * Room definitions with IDs and display names.
 */
export const ROOMS = [
  { id: 'living_room', name: 'Living Room' },
  { id: 'master_bedroom', name: 'Master Bedroom' },
  { id: 'kitchen', name: 'Kitchen' },
  { id: 'bath', name: 'Bath' },
  { id: 'study_room', name: 'Study Room' },
  { id: 'kids_room', name: 'Kids Room' },
  { id: 'balcony', name: 'Balcony' },
];
