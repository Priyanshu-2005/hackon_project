import * as THREE from 'three';

/**
 * Room definitions for the Sharma family smart home.
 * Layout (top-down view):
 *
 * ┌─────────────────────────────────────┐
 * │  Balcony  │     Master Bedroom      │
 * │           │                         │
 * ├───────────┤    ┌──────┐             │
 * │           │    │Bath  │             │
 * │  Kitchen  │    └──────┘─────────────┤
 * │           │                         │
 * │           │     Living Room         │
 * ├───────────┤       (main)            │
 * │  Study    │                         │
 * │  Room     ├─────────────────────────┤
 * │           │     Kids Room           │
 * │           │                         │
 * └───────────┴─────────────────────────┘
 *
 * Coordinate system:
 * - House is ~12 units wide x 10 units deep, centered around origin
 * - Y=0 is ground level, Y is up
 * - Left column (Balcony, Kitchen, Study): X ~ -4
 * - Right column (Master, Bath, Living, Kids): X ~ +2
 */

export const ROOM_DEFINITIONS = [
  {
    id: 'balcony',
    name: 'Balcony',
    position: new THREE.Vector3(-4, 0, -4),
    size: { width: 3.5, height: 2.5, depth: 2.5 },
  },
  {
    id: 'master_bedroom',
    name: 'Master Bedroom',
    position: new THREE.Vector3(2, 0, -4),
    size: { width: 5, height: 2.5, depth: 2.5 },
  },
  {
    id: 'kitchen',
    name: 'Kitchen',
    position: new THREE.Vector3(-4, 0, -1),
    size: { width: 3.5, height: 2.5, depth: 3 },
  },
  {
    id: 'bath',
    name: 'Bath',
    position: new THREE.Vector3(0, 0, -2),
    size: { width: 2, height: 2.5, depth: 1.5 },
  },
  {
    id: 'living_room',
    name: 'Living Room',
    position: new THREE.Vector3(2, 0, 0),
    size: { width: 5, height: 2.5, depth: 3.5 },
  },
  {
    id: 'study_room',
    name: 'Study Room',
    position: new THREE.Vector3(-4, 0, 2.5),
    size: { width: 3.5, height: 2.5, depth: 3 },
  },
  {
    id: 'kids_room',
    name: 'Kids Room',
    position: new THREE.Vector3(2, 0, 3.5),
    size: { width: 5, height: 2.5, depth: 2.5 },
  },
];

/**
 * Get the center position of a room by its ID.
 * @param {string} roomId - Room ID matching constants.js ROOMS
 * @returns {THREE.Vector3} Center position of the room
 */
export function getRoomPosition(roomId) {
  const room = ROOM_DEFINITIONS.find((r) => r.id === roomId);
  if (!room) {
    console.warn(`Room not found: ${roomId}`);
    return new THREE.Vector3(0, 0, 0);
  }
  return room.position.clone();
}

/**
 * Get a position offset within a room for a specific occupant to avoid overlap.
 * @param {string} roomId - Room ID
 * @param {string} memberId - Family member identifier (or index)
 * @returns {THREE.Vector3} Position within the room
 */
export function getOccupantPosition(roomId, memberId) {
  const room = ROOM_DEFINITIONS.find((r) => r.id === roomId);
  if (!room) {
    return new THREE.Vector3(0, 0, 0);
  }

  // Create a deterministic offset based on memberId hash
  let hash = 0;
  const id = String(memberId);
  for (let i = 0; i < id.length; i++) {
    hash = (hash * 31 + id.charCodeAt(i)) | 0;
  }

  // Spread occupants within 60% of the room size to keep them away from walls
  const spreadX = room.size.width * 0.3;
  const spreadZ = room.size.depth * 0.3;

  const angle = ((hash & 0xffff) / 0xffff) * Math.PI * 2;
  const radius = 0.5 + ((hash >>> 16) & 0xff) / 255 * 0.5;

  const offsetX = Math.cos(angle) * radius * spreadX;
  const offsetZ = Math.sin(angle) * radius * spreadZ;

  return new THREE.Vector3(
    room.position.x + offsetX,
    0,
    room.position.z + offsetZ
  );
}

/**
 * Get a room definition object by its ID.
 * @param {string} roomId - Room ID matching constants.js ROOMS
 * @returns {object|null} Room definition or null
 */
export function getRoomById(roomId) {
  return ROOM_DEFINITIONS.find((r) => r.id === roomId) || null;
}
