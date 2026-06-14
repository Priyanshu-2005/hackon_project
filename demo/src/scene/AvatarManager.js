import * as THREE from 'three';
import { COLORS } from '../utils/constants.js';
import { getOccupantPosition } from './RoomDefinitions.js';

/**
 * Family schedule mapping room names to RoomDefinitions IDs.
 * Times are in minutes from midnight (0 = 00:00, 1440 = 24:00).
 */
export const FAMILY_SCHEDULE = {
  rajesh: [
    { start: 0, end: 390, room: 'master_bedroom', activity: 'sleeping' },
    { start: 390, end: 480, room: 'bath', activity: 'morning routine' },
    { start: 480, end: 540, room: 'kitchen', activity: 'breakfast' },
    { start: 540, end: 1110, room: null, activity: 'at work' },
    { start: 1110, end: 1380, room: 'living_room', activity: 'relaxing' },
    { start: 1380, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
  priya: [
    { start: 0, end: 360, room: 'master_bedroom', activity: 'sleeping' },
    { start: 360, end: 420, room: 'kitchen', activity: 'cooking' },
    { start: 420, end: 720, room: 'kitchen', activity: 'household' },
    { start: 720, end: 1350, room: 'living_room', activity: 'family time' },
    { start: 1350, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
  arjun: [
    { start: 0, end: 420, room: 'kids_room', activity: 'sleeping' },
    { start: 420, end: 480, room: 'kitchen', activity: 'breakfast' },
    { start: 480, end: 900, room: null, activity: 'at school' },
    { start: 900, end: 960, room: 'kitchen', activity: 'snack' },
    { start: 960, end: 1140, room: 'study_room', activity: 'tuition/study' },
    { start: 1140, end: 1320, room: 'kids_room', activity: 'relaxing' },
    { start: 1320, end: 1440, room: 'kids_room', activity: 'sleeping' },
  ],
  ananya: [
    { start: 0, end: 450, room: 'kids_room', activity: 'sleeping' },
    { start: 450, end: 480, room: 'kitchen', activity: 'breakfast' },
    { start: 480, end: 900, room: null, activity: 'at school' },
    { start: 900, end: 1020, room: 'living_room', activity: 'TV time' },
    { start: 1020, end: 1260, room: 'kids_room', activity: 'relaxing' },
    { start: 1260, end: 1440, room: 'kids_room', activity: 'sleeping' },
  ],
  dadaji: [
    { start: 0, end: 360, room: 'master_bedroom', activity: 'sleeping' },
    { start: 360, end: 420, room: 'balcony', activity: 'morning walk' },
    { start: 420, end: 780, room: 'living_room', activity: 'reading/TV' },
    { start: 780, end: 900, room: 'living_room', activity: 'afternoon rest' },
    { start: 900, end: 1290, room: 'living_room', activity: 'relaxing' },
    { start: 1290, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
  dadiji: [
    { start: 0, end: 330, room: 'master_bedroom', activity: 'sleeping' },
    { start: 330, end: 360, room: 'balcony', activity: 'prayer' },
    { start: 360, end: 480, room: 'kitchen', activity: 'tea/prayers' },
    { start: 480, end: 720, room: 'living_room', activity: 'watching TV' },
    { start: 720, end: 900, room: 'master_bedroom', activity: 'rest' },
    { start: 900, end: 1260, room: 'living_room', activity: 'family time' },
    { start: 1260, end: 1440, room: 'master_bedroom', activity: 'sleeping' },
  ],
};

const FAMILY_MEMBERS = ['rajesh', 'priya', 'arjun', 'ananya', 'dadaji', 'dadiji'];

/**
 * Manages family member avatars in the 3D scene.
 * Each avatar is a capsule-shaped mesh that moves between rooms
 * based on the family schedule.
 */
export class AvatarManager {
  /**
   * @param {THREE.Scene} scene - The Three.js scene to add avatars to.
   */
  constructor(scene) {
    this.scene = scene;
    /** @type {Map<string, { mesh: THREE.Mesh, currentRoom: string|null }>} */
    this.avatars = new Map();

    const geometry = new THREE.CapsuleGeometry(0.15, 0.4, 4, 8);

    FAMILY_MEMBERS.forEach((member, index) => {
      const material = new THREE.MeshLambertMaterial({
        color: COLORS.AVATAR_COLORS[index],
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.visible = false;
      mesh.name = `avatar_${member}`;

      this.scene.add(mesh);
      this.avatars.set(member, { mesh, currentRoom: null });
    });
  }

  /**
   * Update avatar positions based on the current time of day.
   * Lerps each avatar toward its target room position.
   * @param {number} timeMinutes - Current time in minutes from midnight (0–1440).
   */
  updatePositions(timeMinutes) {
    for (const [member, avatar] of this.avatars) {
      const schedule = FAMILY_SCHEDULE[member];
      if (!schedule) continue;

      // Find the current schedule slot
      const slot = schedule.find(
        (s) => timeMinutes >= s.start && timeMinutes < s.end
      );

      if (!slot || slot.room === null) {
        // Person is away from home
        avatar.mesh.visible = false;
        avatar.currentRoom = null;
        continue;
      }

      // Person is in a room
      avatar.mesh.visible = true;
      avatar.currentRoom = slot.room;

      const target = getOccupantPosition(slot.room, member);
      // Keep avatar at standing height
      target.y = 0.4;

      // Lerp toward target position
      avatar.mesh.position.lerp(target, 0.08);
    }
  }
}
