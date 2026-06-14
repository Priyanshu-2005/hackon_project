import * as THREE from 'three';
import { COLORS } from '../utils/constants.js';
import { getRoomPosition, ROOM_DEFINITIONS } from './RoomDefinitions.js';

/**
 * Device-to-room mapping with position offsets within each room.
 * Offsets are relative to room center to avoid overlapping devices.
 *
 * type: 'cylinder' for larger appliances (AC, TV, geyser, inverter)
 * type: 'sphere' for smaller devices (echo, camera, lock, hub, purifier)
 */
const DEVICE_PLACEMENTS = {
  living_room_ac: {
    room: 'living_room',
    offset: new THREE.Vector3(1.8, 1.8, -0.5),
    type: 'cylinder',
    label: 'AC',
  },
  smart_tv: {
    room: 'living_room',
    offset: new THREE.Vector3(-1.5, 0.8, 0.0),
    type: 'cylinder',
    label: 'TV',
  },
  echo_living: {
    room: 'living_room',
    offset: new THREE.Vector3(0.5, 0.6, 0.8),
    type: 'sphere',
    label: 'Echo',
  },
  kitchen_hub: {
    room: 'kitchen',
    offset: new THREE.Vector3(0.3, 0.7, -0.5),
    type: 'sphere',
    label: 'Hub',
  },
  water_purifier: {
    room: 'kitchen',
    offset: new THREE.Vector3(-0.6, 0.3, 0.6),
    type: 'sphere',
    label: 'Purifier',
  },
  security_camera: {
    room: 'balcony',
    offset: new THREE.Vector3(0.5, 2.0, -0.8),
    type: 'sphere',
    label: 'Camera',
  },
  smart_lock: {
    room: 'balcony',
    offset: new THREE.Vector3(-0.3, 0.9, -1.0),
    type: 'sphere',
    label: 'Lock',
  },
  smart_geyser: {
    room: 'bath',
    offset: new THREE.Vector3(0.3, 1.5, 0.2),
    type: 'cylinder',
    label: 'Geyser',
  },
  inverter_ups: {
    room: 'kitchen',
    offset: new THREE.Vector3(-0.8, 0.4, -1.5),
    type: 'cylinder',
    label: 'Inverter',
  },
  echo_study: {
    room: 'study_room',
    offset: new THREE.Vector3(0.4, 0.6, 0.3),
    type: 'sphere',
    label: 'Echo',
  },
  echo_kids: {
    room: 'kids_room',
    offset: new THREE.Vector3(-0.5, 0.6, 0.4),
    type: 'sphere',
    label: 'Echo',
  },
};

/**
 * Room IDs where smart lights are placed (one per room).
 */
const LIGHT_ROOMS = [
  'living_room',
  'master_bedroom',
  'kitchen',
  'bath',
  'study_room',
  'kids_room',
  'balcony',
];

/**
 * Creates a canvas-based text sprite for device labels.
 * @param {string} text - Label text
 * @returns {THREE.Sprite}
 */
function createLabelSprite(text) {
  const canvas = document.createElement('canvas');
  const size = 128;
  canvas.width = size;
  canvas.height = 64;
  const ctx = canvas.getContext('2d');

  // Draw label content if canvas 2D context is available (not in test env)
  if (ctx) {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    if (ctx.roundRect) {
      ctx.roundRect(4, 4, size - 8, 56, 8);
    } else {
      ctx.fillRect(4, 4, size - 8, 56);
    }
    ctx.fill();

    ctx.font = 'bold 20px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#00CAFF';
    ctx.fillText(text, size / 2, 32);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;

  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
  });

  const sprite = new THREE.Sprite(material);
  sprite.scale.set(0.6, 0.3, 1);
  return sprite;
}

/**
 * Creates the Alexa blue glow material used for device indicators.
 * @returns {THREE.MeshStandardMaterial}
 */
function createDeviceMaterial() {
  return new THREE.MeshStandardMaterial({
    color: COLORS.DEVICE_GLOW,
    emissive: COLORS.DEVICE_GLOW,
    emissiveIntensity: 0.3,
    roughness: 0.4,
    metalness: 0.6,
  });
}

/**
 * Creates the light indicator material (warm glow for lights).
 * @returns {THREE.MeshStandardMaterial}
 */
function createLightMaterial() {
  return new THREE.MeshStandardMaterial({
    color: 0xffee88,
    emissive: 0xffee88,
    emissiveIntensity: 0.4,
    roughness: 0.3,
    metalness: 0.2,
    transparent: true,
    opacity: 0.9,
  });
}

/**
 * DeviceIndicators manages the creation, placement, and access of device
 * indicator meshes within the 3D scene. Each device is represented by a
 * small glowing sphere or cylinder placed within its assigned room.
 *
 * Devices placed per room:
 * - Living Room: living_room_ac (wall unit), smart_tv (wall), echo_devices (shelf)
 * - Kitchen: kitchen_hub (counter), water_purifier (floor)
 * - Balcony/Entry: security_camera, smart_lock
 * - Bath: smart_geyser
 * - Study Room: inverter_ups (utility area), echo device
 * - Kids Room: echo device
 * - All rooms: smart_lights (one per room)
 */
export class DeviceIndicators {
  /**
   * @param {THREE.Scene} scene - The Three.js scene to add devices to
   * @param {typeof ROOM_DEFINITIONS} [roomDefinitions] - Room position/size data (optional, uses imported ROOM_DEFINITIONS)
   */
  constructor(scene, roomDefinitions) {
    this.scene = scene;
    this.roomDefinitions = roomDefinitions || ROOM_DEFINITIONS;

    /** @type {Map<string, THREE.Mesh>} deviceId → mesh */
    this.meshes = new Map();

    /** @type {Map<string, THREE.Vector3>} deviceId → world position */
    this.positions = new Map();

    /** @type {Array<{ roomId: string, lightMesh: THREE.Mesh }>} */
    this.roomLights = [];

    /** @type {THREE.Group} */
    this.group = new THREE.Group();
    this.group.name = 'DevicesGroup';
    this.scene.add(this.group);

    this._createDeviceIndicators();
    this._createSmartLights();
  }

  /**
   * Create device indicator meshes for all mapped devices.
   * @private
   */
  _createDeviceIndicators() {
    for (const [deviceId, placement] of Object.entries(DEVICE_PLACEMENTS)) {
      const roomPos = getRoomPosition(placement.room);
      const worldPos = new THREE.Vector3(
        roomPos.x + placement.offset.x,
        placement.offset.y,
        roomPos.z + placement.offset.z
      );

      let geometry;
      if (placement.type === 'cylinder') {
        geometry = new THREE.CylinderGeometry(0.12, 0.15, 0.3, 8);
      } else {
        geometry = new THREE.SphereGeometry(0.15, 8, 6);
      }

      const material = createDeviceMaterial();
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(worldPos);
      mesh.castShadow = true;
      mesh.name = deviceId;

      // Add label sprite above the device
      const label = createLabelSprite(placement.label);
      label.position.set(0, 0.35, 0);
      mesh.add(label);

      this.group.add(mesh);
      this.meshes.set(deviceId, mesh);
      this.positions.set(deviceId, worldPos.clone());
    }

    // Map canonical 'echo_devices' ID to the living room echo for the Effects system
    const echoLiving = this.meshes.get('echo_living');
    if (echoLiving) {
      this.meshes.set('echo_devices', echoLiving);
      this.positions.set('echo_devices', this.positions.get('echo_living').clone());
    }
  }

  /**
   * Create smart light indicators, one per room.
   * @private
   */
  _createSmartLights() {
    const lightGeometry = new THREE.SphereGeometry(0.1, 8, 6);

    for (const roomId of LIGHT_ROOMS) {
      const roomPos = getRoomPosition(roomId);
      // Place lights at ceiling level, slightly offset from center
      const worldPos = new THREE.Vector3(
        roomPos.x + 0.1,
        2.2, // Near ceiling
        roomPos.z - 0.1
      );

      const material = createLightMaterial();
      const mesh = new THREE.Mesh(lightGeometry.clone(), material);
      mesh.position.copy(worldPos);
      mesh.name = `smart_lights_${roomId}`;

      // Add small label
      const label = createLabelSprite('💡');
      label.position.set(0, 0.25, 0);
      label.scale.set(0.4, 0.2, 1);
      mesh.add(label);

      this.group.add(mesh);
      this.meshes.set(`smart_lights_${roomId}`, mesh);
      this.positions.set(`smart_lights_${roomId}`, worldPos.clone());
      this.roomLights.push({ roomId, lightMesh: mesh });
    }

    // Also register under the canonical 'smart_lights' ID pointing to living room light
    const livingLight = this.meshes.get('smart_lights_living_room');
    if (livingLight) {
      this.meshes.set('smart_lights', livingLight);
      this.positions.set('smart_lights', this.positions.get('smart_lights_living_room').clone());
    }
  }

  /**
   * Get the mesh for a given device ID.
   * @param {string} deviceId - Device identifier
   * @returns {THREE.Mesh|undefined}
   */
  getMesh(deviceId) {
    return this.meshes.get(deviceId);
  }

  /**
   * Get all room light indicator entries for dimming/brightening during power cut.
   * @returns {Array<{ roomId: string, lightMesh: THREE.Mesh }>}
   */
  getAllRoomLights() {
    return this.roomLights;
  }

  /**
   * Get the world position of a device indicator.
   * @param {string} deviceId - Device identifier
   * @returns {THREE.Vector3|undefined}
   */
  getDevicePosition(deviceId) {
    const pos = this.positions.get(deviceId);
    return pos ? pos.clone() : undefined;
  }

  /**
   * Dispose of all device indicator meshes and remove from scene.
   */
  dispose() {
    // Remove all meshes from the group
    while (this.group.children.length > 0) {
      const child = this.group.children[0];
      // Dispose geometry and material
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (child.material.map) child.material.map.dispose();
        child.material.dispose();
      }
      // Dispose sprite children
      child.children.forEach((sprite) => {
        if (sprite.material) {
          if (sprite.material.map) sprite.material.map.dispose();
          sprite.material.dispose();
        }
      });
      this.group.remove(child);
    }

    // Remove group from scene
    this.scene.remove(this.group);

    // Clear maps
    this.meshes.clear();
    this.positions.clear();
    this.roomLights = [];
  }
}
