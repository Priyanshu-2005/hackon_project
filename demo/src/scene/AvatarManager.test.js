import { describe, it, expect, beforeEach, vi } from 'vitest';
import { test as fcTest } from '@fast-check/vitest';
import fc from 'fast-check';
import * as THREE from 'three';
import { AvatarManager, FAMILY_SCHEDULE } from './AvatarManager.js';
import { ROOM_DEFINITIONS, getOccupantPosition } from './RoomDefinitions.js';

/**
 * Property-Based Tests for AvatarManager
 *
 * Property 6: Avatar position matches schedule
 *
 * **Validates: Requirements 6.2**
 */
describe('AvatarManager - Property Tests', () => {
  let scene;
  let avatarManager;

  beforeEach(() => {
    scene = new THREE.Scene();
    avatarManager = new AvatarManager(scene);
  });

  /**
   * Helper: find which room a family member should be in at a given time.
   */
  function getScheduleSlot(memberId, timeMinutes) {
    const schedule = FAMILY_SCHEDULE[memberId];
    return schedule.find((s) => timeMinutes >= s.start && timeMinutes < s.end);
  }

  /**
   * Helper: get the room definition by ID.
   */
  function getRoomDef(roomId) {
    return ROOM_DEFINITIONS.find((r) => r.id === roomId);
  }

  /**
   * Helper: run updatePositions multiple times to let lerp converge.
   */
  function convergePositions(timeMinutes, iterations = 50) {
    for (let i = 0; i < iterations; i++) {
      avatarManager.updatePositions(timeMinutes);
    }
  }

  const FAMILY_MEMBERS = ['rajesh', 'priya', 'arjun', 'ananya', 'dadaji', 'dadiji'];

  /**
   * Property 6: Avatar position matches schedule
   *
   * For any simulation time T (0–1439) and any family member with a schedule
   * entry for that time specifying a room, after calling updatePositions(T)
   * multiple times (to let lerp converge), the avatar's position should be
   * within the bounding box of that room.
   *
   * For any time when a member has room=null, the avatar should be hidden
   * (visible = false).
   */
  describe('Property 6: Avatar position matches schedule', () => {
    fcTest.prop(
      [
        fc.integer({ min: 0, max: 1438 }),
        fc.constantFrom(...FAMILY_MEMBERS),
      ]
    )(
      'avatar is within the assigned room bounding box after convergence',
      (timeMinutes, memberId) => {
        const slot = getScheduleSlot(memberId, timeMinutes);

        // Skip if no schedule slot covers this time
        fc.pre(slot !== undefined);
        // Only test when member is in a room (not away)
        fc.pre(slot.room !== null);

        const roomDef = getRoomDef(slot.room);
        // Skip if room definition doesn't exist
        fc.pre(roomDef !== undefined);

        // Run updatePositions enough times for lerp to converge
        convergePositions(timeMinutes, 50);

        const mesh = avatarManager.getAvatar(memberId);
        expect(mesh.visible).toBe(true);

        // Room bounding box: position ± size/2 with tolerance for occupant spread
        // The getOccupantPosition uses 60% of room size (0.3 * width/depth as spread)
        // plus a radius factor up to 1.0, so max offset is 0.3 * size * 1.0
        // We use the full room size with a small tolerance
        const tolerance = 0.5; // extra tolerance for lerp convergence
        const halfWidth = roomDef.size.width / 2 + tolerance;
        const halfDepth = roomDef.size.depth / 2 + tolerance;

        const minX = roomDef.position.x - halfWidth;
        const maxX = roomDef.position.x + halfWidth;
        const minZ = roomDef.position.z - halfDepth;
        const maxZ = roomDef.position.z + halfDepth;

        expect(mesh.position.x).toBeGreaterThanOrEqual(minX);
        expect(mesh.position.x).toBeLessThanOrEqual(maxX);
        expect(mesh.position.z).toBeGreaterThanOrEqual(minZ);
        expect(mesh.position.z).toBeLessThanOrEqual(maxZ);
      }
    );

    fcTest.prop(
      [
        fc.integer({ min: 0, max: 1438 }),
        fc.constantFrom(...FAMILY_MEMBERS),
      ]
    )(
      'avatar is hidden (visible=false) when member is away (room=null)',
      (timeMinutes, memberId) => {
        const slot = getScheduleSlot(memberId, timeMinutes);

        // Only test when member is away
        fc.pre(slot !== undefined);
        fc.pre(slot.room === null);

        // Run updatePositions to apply visibility
        convergePositions(timeMinutes, 50);

        const mesh = avatarManager.getAvatar(memberId);
        expect(mesh.visible).toBe(false);
      }
    );

    fcTest.prop(
      [fc.integer({ min: 0, max: 1438 })]
    )(
      'all visible avatars are within their assigned room bounds',
      (timeMinutes) => {
        convergePositions(timeMinutes, 50);

        for (const memberId of FAMILY_MEMBERS) {
          const mesh = avatarManager.getAvatar(memberId);
          const slot = getScheduleSlot(memberId, timeMinutes);

          if (!slot || slot.room === null) {
            expect(mesh.visible).toBe(false);
          } else {
            expect(mesh.visible).toBe(true);

            const roomDef = getRoomDef(slot.room);
            if (roomDef) {
              const tolerance = 0.5;
              const halfWidth = roomDef.size.width / 2 + tolerance;
              const halfDepth = roomDef.size.depth / 2 + tolerance;

              expect(mesh.position.x).toBeGreaterThanOrEqual(roomDef.position.x - halfWidth);
              expect(mesh.position.x).toBeLessThanOrEqual(roomDef.position.x + halfWidth);
              expect(mesh.position.z).toBeGreaterThanOrEqual(roomDef.position.z - halfDepth);
              expect(mesh.position.z).toBeLessThanOrEqual(roomDef.position.z + halfDepth);
            }
          }
        }
      }
    );
  });
});
