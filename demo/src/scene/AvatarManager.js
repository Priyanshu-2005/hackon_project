import * as THREE from 'three';
import { COLORS } from '../utils/constants.js';
import { getOccupantPosition } from './RoomDefinitions.js';
import { FAMILY_SCHEDULE } from '../data/FamilySchedule.js';

// Re-export for backward compatibility
export { FAMILY_SCHEDULE };

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
   * Get the mesh for a specific family member avatar.
   * @param {string} memberId - Family member name
   * @returns {THREE.Mesh|undefined}
   */
  getAvatar(memberId) {
    const avatar = this.avatars.get(memberId);
    return avatar ? avatar.mesh : undefined;
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
