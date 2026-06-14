/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as THREE from 'three';
import { DeviceIndicators } from './DeviceIndicators.js';
import { getRoomPosition, ROOM_DEFINITIONS } from './RoomDefinitions.js';

describe('DeviceIndicators', () => {
  let scene;
  let indicators;

  beforeEach(() => {
    scene = new THREE.Scene();
    indicators = new DeviceIndicators(scene, ROOM_DEFINITIONS);
  });

  describe('constructor', () => {
    it('should add a DevicesGroup to the scene', () => {
      const group = scene.getObjectByName('DevicesGroup');
      expect(group).toBeDefined();
      expect(group).toBeInstanceOf(THREE.Group);
    });

    it('should create mesh indicators for named devices', () => {
      // 11 named devices in DEVICE_PLACEMENTS + echo_devices alias
      expect(indicators.meshes.size).toBeGreaterThanOrEqual(11);
    });
  });

  describe('getMesh', () => {
    it('should return a mesh for living_room_ac', () => {
      const mesh = indicators.getMesh('living_room_ac');
      expect(mesh).toBeInstanceOf(THREE.Mesh);
      expect(mesh.name).toBe('living_room_ac');
    });

    it('should return undefined for an invalid device ID', () => {
      const mesh = indicators.getMesh('nonexistent_device');
      expect(mesh).toBeUndefined();
    });

    it('should return meshes for all echo device placements', () => {
      expect(indicators.getMesh('echo_living')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('echo_study')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('echo_kids')).toBeInstanceOf(THREE.Mesh);
    });

    it('should map echo_devices to echo_living for canonical access', () => {
      const echoDevices = indicators.getMesh('echo_devices');
      const echoLiving = indicators.getMesh('echo_living');
      expect(echoDevices).toBe(echoLiving);
    });

    it('should return meshes for core devices', () => {
      expect(indicators.getMesh('smart_tv')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('security_camera')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('smart_lock')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('kitchen_hub')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('water_purifier')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('smart_geyser')).toBeInstanceOf(THREE.Mesh);
      expect(indicators.getMesh('inverter_ups')).toBeInstanceOf(THREE.Mesh);
    });
  });

  describe('getAllRoomLights', () => {
    it('should return an array of room light entries', () => {
      const lights = indicators.getAllRoomLights();
      expect(Array.isArray(lights)).toBe(true);
      expect(lights.length).toBe(7); // 7 rooms with smart lights
    });

    it('should include roomId and lightMesh in each entry', () => {
      const lights = indicators.getAllRoomLights();
      for (const entry of lights) {
        expect(entry).toHaveProperty('roomId');
        expect(entry).toHaveProperty('lightMesh');
        expect(entry.lightMesh).toBeInstanceOf(THREE.Mesh);
      }
    });

    it('should have lights for all standard rooms', () => {
      const lights = indicators.getAllRoomLights();
      const roomIds = lights.map((l) => l.roomId);
      expect(roomIds).toContain('living_room');
      expect(roomIds).toContain('master_bedroom');
      expect(roomIds).toContain('kitchen');
      expect(roomIds).toContain('bath');
      expect(roomIds).toContain('study_room');
      expect(roomIds).toContain('kids_room');
      expect(roomIds).toContain('balcony');
    });
  });

  describe('room placement - Requirement 13', () => {
    it('13.1: should place AC, TV, and Echo in the Living Room', () => {
      const roomPos = getRoomPosition('living_room');
      const ac = indicators.getMesh('living_room_ac');
      const tv = indicators.getMesh('smart_tv');
      const echo = indicators.getMesh('echo_living');

      for (const mesh of [ac, tv, echo]) {
        expect(Math.abs(mesh.position.x - roomPos.x)).toBeLessThan(3);
        expect(Math.abs(mesh.position.z - roomPos.z)).toBeLessThan(3);
      }
    });

    it('13.2: should place smart lights across all rooms', () => {
      const lights = indicators.getAllRoomLights();
      const roomIds = lights.map((l) => l.roomId);
      expect(roomIds.length).toBe(7);
    });

    it('13.3: should place security_camera and smart_lock in the balcony', () => {
      const roomPos = getRoomPosition('balcony');
      const cam = indicators.getMesh('security_camera');
      const lock = indicators.getMesh('smart_lock');

      expect(Math.abs(cam.position.x - roomPos.x)).toBeLessThan(3);
      expect(Math.abs(cam.position.z - roomPos.z)).toBeLessThan(3);
      expect(Math.abs(lock.position.x - roomPos.x)).toBeLessThan(3);
      expect(Math.abs(lock.position.z - roomPos.z)).toBeLessThan(3);
    });

    it('13.4: should place kitchen_hub in the Kitchen', () => {
      const roomPos = getRoomPosition('kitchen');
      const mesh = indicators.getMesh('kitchen_hub');
      expect(Math.abs(mesh.position.x - roomPos.x)).toBeLessThan(3);
      expect(Math.abs(mesh.position.z - roomPos.z)).toBeLessThan(3);
    });

    it('13.5: should place water_purifier in the Kitchen', () => {
      const roomPos = getRoomPosition('kitchen');
      const mesh = indicators.getMesh('water_purifier');
      expect(Math.abs(mesh.position.x - roomPos.x)).toBeLessThan(3);
      expect(Math.abs(mesh.position.z - roomPos.z)).toBeLessThan(3);
    });

    it('13.6: should place smart_geyser in the Bath', () => {
      const roomPos = getRoomPosition('bath');
      const mesh = indicators.getMesh('smart_geyser');
      expect(Math.abs(mesh.position.x - roomPos.x)).toBeLessThan(3);
      expect(Math.abs(mesh.position.z - roomPos.z)).toBeLessThan(3);
    });

    it('13.7: should place inverter_ups in an appropriate utility area', () => {
      const mesh = indicators.getMesh('inverter_ups');
      // Inverter is placed near kitchen (utility area)
      const kitchenPos = getRoomPosition('kitchen');
      expect(Math.abs(mesh.position.x - kitchenPos.x)).toBeLessThan(4);
      expect(Math.abs(mesh.position.z - kitchenPos.z)).toBeLessThan(4);
    });

    it('13.8: should place Echo devices in study_room and kids_room', () => {
      const studyPos = getRoomPosition('study_room');
      const kidsPos = getRoomPosition('kids_room');
      const echoStudy = indicators.getMesh('echo_study');
      const echoKids = indicators.getMesh('echo_kids');

      expect(Math.abs(echoStudy.position.x - studyPos.x)).toBeLessThan(3);
      expect(Math.abs(echoStudy.position.z - studyPos.z)).toBeLessThan(3);
      expect(Math.abs(echoKids.position.x - kidsPos.x)).toBeLessThan(3);
      expect(Math.abs(echoKids.position.z - kidsPos.z)).toBeLessThan(3);
    });
  });

  describe('device geometry', () => {
    it('should use CylinderGeometry for AC (larger device)', () => {
      const mesh = indicators.getMesh('living_room_ac');
      expect(mesh.geometry).toBeInstanceOf(THREE.CylinderGeometry);
    });

    it('should use CylinderGeometry for geyser', () => {
      const mesh = indicators.getMesh('smart_geyser');
      expect(mesh.geometry).toBeInstanceOf(THREE.CylinderGeometry);
    });

    it('should use CylinderGeometry for inverter (larger device)', () => {
      const mesh = indicators.getMesh('inverter_ups');
      expect(mesh.geometry).toBeInstanceOf(THREE.CylinderGeometry);
    });

    it('should use SphereGeometry for smaller devices', () => {
      const echo = indicators.getMesh('echo_living');
      expect(echo.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });
  });

  describe('label sprites', () => {
    it('should add a sprite child to each device mesh', () => {
      const mesh = indicators.getMesh('living_room_ac');
      const sprites = mesh.children.filter((c) => c.isSprite);
      expect(sprites.length).toBe(1);
    });

    it('should position labels above the device mesh', () => {
      const mesh = indicators.getMesh('kitchen_hub');
      const sprite = mesh.children.find((c) => c.isSprite);
      expect(sprite).toBeDefined();
      expect(sprite.position.y).toBeGreaterThan(0);
    });
  });

  describe('materials', () => {
    it('should use emissive material for device glow', () => {
      const mesh = indicators.getMesh('echo_living');
      expect(mesh.material.emissive).toBeDefined();
      expect(mesh.material.emissiveIntensity).toBeGreaterThan(0);
    });
  });

  describe('getDevicePosition', () => {
    it('should return a Vector3 for a known device', () => {
      const pos = indicators.getDevicePosition('living_room_ac');
      expect(pos).toBeInstanceOf(THREE.Vector3);
    });

    it('should return undefined for unknown device', () => {
      const pos = indicators.getDevicePosition('nonexistent');
      expect(pos).toBeUndefined();
    });

    it('should return a clone (not the original reference)', () => {
      const pos1 = indicators.getDevicePosition('echo_living');
      const pos2 = indicators.getDevicePosition('echo_living');
      expect(pos1).not.toBe(pos2);
      expect(pos1.x).toBe(pos2.x);
    });
  });
});
