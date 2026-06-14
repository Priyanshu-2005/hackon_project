/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as THREE from 'three';
import { Effects } from './Effects.js';

/**
 * Mock DeviceIndicators that provides getMesh and getAllRoomLights.
 */
function createMockDeviceIndicators() {
  const meshes = new Map();
  const roomLights = [];

  // Create a device mesh with standard material
  function createDeviceMesh(name, position = new THREE.Vector3(0, 0, 0)) {
    const geometry = new THREE.SphereGeometry(0.15, 8, 6);
    const material = new THREE.MeshStandardMaterial({
      color: 0x00caff,
      emissive: new THREE.Color(0x00caff),
      emissiveIntensity: 0.3,
      roughness: 0.4,
      metalness: 0.6,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(position);
    mesh.name = name;
    return mesh;
  }

  // Create light mesh with transparent material
  function createLightMesh(roomId) {
    const geometry = new THREE.SphereGeometry(0.1, 8, 6);
    const material = new THREE.MeshStandardMaterial({
      color: 0xffee88,
      emissive: new THREE.Color(0xffee88),
      emissiveIntensity: 0.4,
      roughness: 0.3,
      metalness: 0.2,
      transparent: true,
      opacity: 0.9,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = `smart_lights_${roomId}`;
    return mesh;
  }

  // Add device meshes
  const inverterMesh = createDeviceMesh('inverter_ups', new THREE.Vector3(1, 0.4, -1));
  meshes.set('inverter_ups', inverterMesh);

  const acMesh = createDeviceMesh('living_room_ac', new THREE.Vector3(2, 1.8, 0));
  meshes.set('living_room_ac', acMesh);

  const echoMesh = createDeviceMesh('echo_devices', new THREE.Vector3(0.5, 0.6, 0.8));
  meshes.set('echo_devices', echoMesh);

  // Add room lights
  const rooms = ['living_room', 'master_bedroom', 'kitchen', 'study_room', 'kids_room'];
  for (const roomId of rooms) {
    const lightMesh = createLightMesh(roomId);
    meshes.set(`smart_lights_${roomId}`, lightMesh);
    roomLights.push({ roomId, lightMesh });
  }

  return {
    getMesh: (deviceId) => meshes.get(deviceId),
    getAllRoomLights: () => roomLights,
    meshes,
    roomLights,
  };
}

describe('Effects', () => {
  let scene;
  let deviceIndicators;
  let effects;

  beforeEach(() => {
    scene = new THREE.Scene();
    deviceIndicators = createMockDeviceIndicators();
    effects = new Effects(scene, deviceIndicators);

    // Mock DOM elements for flicker overlay
    const overlay = document.createElement('div');
    overlay.id = 'flicker-overlay';
    overlay.style.display = 'none';
    document.body.appendChild(overlay);
  });

  afterEach(() => {
    effects.restoreAll();
    const overlay = document.getElementById('flicker-overlay');
    if (overlay) overlay.remove();
  });

  describe('constructor', () => {
    it('stores scene and deviceIndicators references', () => {
      expect(effects.scene).toBe(scene);
      expect(effects.deviceIndicators).toBe(deviceIndicators);
    });

    it('initializes activeAnimations as an empty Map', () => {
      expect(effects.activeAnimations).toBeInstanceOf(Map);
      expect(effects.activeAnimations.size).toBe(0);
    });
  });

  describe('highlightDevice', () => {
    it('does nothing if device mesh is not found', () => {
      effects.highlightDevice('nonexistent_device');
      expect(effects.activeAnimations.size).toBe(0);
    });

    it('registers an active animation for the device', () => {
      effects.highlightDevice('living_room_ac');
      expect(effects.activeAnimations.has('highlight_living_room_ac')).toBe(true);
    });

    it('restores emissive intensity after cleanup', () => {
      const mesh = deviceIndicators.getMesh('living_room_ac');
      const original = mesh.material.emissiveIntensity;

      effects.highlightDevice('living_room_ac');
      // Manually trigger cleanup
      effects.activeAnimations.get('highlight_living_room_ac').cleanup();

      expect(mesh.material.emissiveIntensity).toBe(original);
    });
  });

  describe('powerCutFlicker', () => {
    it('shows the flicker overlay', () => {
      effects.powerCutFlicker();
      const overlay = document.getElementById('flicker-overlay');
      expect(overlay.style.display).toBe('block');
    });

    it('registers an active animation', () => {
      effects.powerCutFlicker();
      expect(effects.activeAnimations.has('powerCutFlicker')).toBe(true);
    });

    it('hides overlay on cleanup', () => {
      effects.powerCutFlicker();
      effects.activeAnimations.get('powerCutFlicker').cleanup();

      const overlay = document.getElementById('flicker-overlay');
      expect(overlay.style.display).toBe('none');
      expect(overlay.style.opacity).toBe('0');
    });

    it('does nothing if overlay element is missing', () => {
      document.getElementById('flicker-overlay').remove();
      effects.powerCutFlicker();
      expect(effects.activeAnimations.has('powerCutFlicker')).toBe(false);
    });
  });

  describe('inverterGlow', () => {
    it('does nothing if device mesh is not found', () => {
      effects.inverterGlow('nonexistent');
      expect(effects.activeAnimations.size).toBe(0);
    });

    it('changes material to green emissive', () => {
      effects.inverterGlow('inverter_ups');
      const mesh = deviceIndicators.getMesh('inverter_ups');

      expect(mesh.material.emissive.getHex()).toBe(0x00ff88);
      expect(mesh.material.emissiveIntensity).toBe(0.6);
    });

    it('adds a PointLight to the scene', () => {
      const lightsBefore = scene.children.filter((c) => c.isPointLight);
      effects.inverterGlow('inverter_ups');
      const lightsAfter = scene.children.filter((c) => c.isPointLight);

      expect(lightsAfter.length).toBe(lightsBefore.length + 1);

      const addedLight = lightsAfter[lightsAfter.length - 1];
      expect(addedLight.color.getHex()).toBe(0x00ff88);
      expect(addedLight.intensity).toBe(1);
      expect(addedLight.distance).toBe(3);
    });

    it('restores original material on cleanup', () => {
      const mesh = deviceIndicators.getMesh('inverter_ups');
      const originalEmissive = mesh.material.emissive.getHex();
      const originalIntensity = mesh.material.emissiveIntensity;

      effects.inverterGlow('inverter_ups');
      effects.activeAnimations.get('inverterGlow_inverter_ups').cleanup();

      expect(mesh.material.emissive.getHex()).toBe(originalEmissive);
      expect(mesh.material.emissiveIntensity).toBe(originalIntensity);
    });

    it('removes PointLight from scene on cleanup', () => {
      effects.inverterGlow('inverter_ups');
      effects.activeAnimations.get('inverterGlow_inverter_ups').cleanup();

      const lights = scene.children.filter((c) => c.isPointLight);
      expect(lights.length).toBe(0);
    });
  });

  describe('dimRooms', () => {
    it('dims rooms that are NOT in the keep-lit list', () => {
      effects.dimRooms(['study_room']);

      const roomLights = deviceIndicators.getAllRoomLights();
      for (const { roomId, lightMesh } of roomLights) {
        if (roomId === 'study_room') {
          // Should remain at original values
          expect(lightMesh.material.emissiveIntensity).toBe(0.4);
          expect(lightMesh.material.opacity).toBe(0.9);
        } else {
          // Should be dimmed
          expect(lightMesh.material.emissiveIntensity).toBe(0.02);
          expect(lightMesh.material.opacity).toBe(0.3);
        }
      }
    });

    it('restores all lights on cleanup', () => {
      effects.dimRooms(['study_room']);
      effects.activeAnimations.get('dimRooms').cleanup();

      const roomLights = deviceIndicators.getAllRoomLights();
      for (const { lightMesh } of roomLights) {
        expect(lightMesh.material.emissiveIntensity).toBe(0.4);
        expect(lightMesh.material.opacity).toBe(0.9);
      }
    });

    it('keeps all rooms lit when all are in the keep-lit list', () => {
      const allRooms = deviceIndicators.getAllRoomLights().map((r) => r.roomId);
      effects.dimRooms(allRooms);

      const roomLights = deviceIndicators.getAllRoomLights();
      for (const { lightMesh } of roomLights) {
        expect(lightMesh.material.emissiveIntensity).toBe(0.4);
        expect(lightMesh.material.opacity).toBe(0.9);
      }
    });

    it('dims all rooms when keep-lit list is empty', () => {
      effects.dimRooms([]);

      const roomLights = deviceIndicators.getAllRoomLights();
      for (const { lightMesh } of roomLights) {
        expect(lightMesh.material.emissiveIntensity).toBe(0.02);
        expect(lightMesh.material.opacity).toBe(0.3);
      }
    });
  });

  describe('restoreAll', () => {
    it('cleans up all active animations', () => {
      effects.highlightDevice('living_room_ac');
      effects.inverterGlow('inverter_ups');
      effects.dimRooms(['study_room']);
      effects.powerCutFlicker();

      expect(effects.activeAnimations.size).toBeGreaterThan(0);

      effects.restoreAll();

      expect(effects.activeAnimations.size).toBe(0);
    });

    it('restores all device materials after multiple effects', () => {
      const inverterMesh = deviceIndicators.getMesh('inverter_ups');
      const originalInverterEmissive = inverterMesh.material.emissive.getHex();

      effects.inverterGlow('inverter_ups');
      effects.dimRooms(['study_room']);
      effects.restoreAll();

      // Inverter material restored
      expect(inverterMesh.material.emissive.getHex()).toBe(originalInverterEmissive);

      // Room lights restored
      const roomLights = deviceIndicators.getAllRoomLights();
      for (const { lightMesh } of roomLights) {
        expect(lightMesh.material.emissiveIntensity).toBe(0.4);
        expect(lightMesh.material.opacity).toBe(0.9);
      }
    });

    it('removes all added lights from the scene', () => {
      effects.inverterGlow('inverter_ups');
      effects.restoreAll();

      const lights = scene.children.filter((c) => c.isPointLight);
      expect(lights.length).toBe(0);
    });
  });
});
