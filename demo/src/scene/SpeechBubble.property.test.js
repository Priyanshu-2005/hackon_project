// @vitest-environment happy-dom
/**
 * Property-based tests for SpeechBubbleManager lifetime behavior.
 *
 * **Validates: Requirements 11.3**
 *
 * Property 14: Speech bubble lifetime — bubbles remain visible for the specified
 * duration, then fade out and are removed.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { fc } from '@fast-check/vitest';
import * as THREE from 'three';

// Mock CSS2DObject since it requires a renderer context
vi.mock('three/addons/renderers/CSS2DRenderer.js', () => {
  class CSS2DObject extends THREE.Object3D {
    constructor(element) {
      super();
      this.element = element;
      this.isCSS2DObject = true;
    }
  }
  return { CSS2DObject, CSS2DRenderer: class {} };
});

import { SpeechBubbleManager } from './SpeechBubble.js';

describe('Property 14: Speech bubble lifetime', () => {
  let scene;
  let manager;

  beforeEach(() => {
    vi.useFakeTimers();
    scene = new THREE.Scene();
    manager = new SpeechBubbleManager(scene);
  });

  afterEach(() => {
    manager.clear();
    vi.useRealTimers();
  });

  it('bubble is still active before duration elapses', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1000, max: 10000 }),
        (duration) => {
          // Reset state for each run
          manager.clear();
          scene.children.length = 0;

          const pos = new THREE.Vector3(0, 1, 0);
          manager.show(pos, 'Test bubble', duration);

          // Advance time to just before the duration
          vi.advanceTimersByTime(duration - 1);

          // Bubble should still be active
          expect(manager.getActiveBubbles().length).toBe(1);
          expect(scene.children.length).toBe(1);

          // The bubble should NOT have fade-out class yet
          const bubble = manager.getActiveBubbles()[0];
          expect(bubble.el.classList.contains('fade-out')).toBe(false);

          // Clean up for next iteration
          manager.clear();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('bubble gets fade-out class at exactly duration ms', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1000, max: 10000 }),
        (duration) => {
          // Reset state for each run
          manager.clear();
          scene.children.length = 0;

          const pos = new THREE.Vector3(2, 3, 1);
          manager.show(pos, 'Fade test', duration);

          // Advance exactly to the duration
          vi.advanceTimersByTime(duration);

          // Bubble should now have the fade-out class
          const bubble = manager.getActiveBubbles()[0];
          expect(bubble.el.classList.contains('fade-out')).toBe(true);

          // But the bubble should still be in the scene (not yet removed)
          expect(scene.children.length).toBe(1);
          expect(manager.getActiveBubbles().length).toBe(1);

          // Clean up for next iteration
          manager.clear();
        }
      ),
      { numRuns: 50 }
    );
  });

  it('bubble is removed from scene at duration + 500ms', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1000, max: 10000 }),
        (duration) => {
          // Reset state for each run
          manager.clear();
          scene.children.length = 0;

          const pos = new THREE.Vector3(-1, 0, 4);
          manager.show(pos, 'Remove test', duration);

          // Advance past duration + fade-out transition (500ms)
          vi.advanceTimersByTime(duration + 500);

          // Bubble should be completely removed
          expect(manager.getActiveBubbles().length).toBe(0);
          expect(scene.children.length).toBe(0);

          // No cleanup needed — already removed
        }
      ),
      { numRuns: 50 }
    );
  });

  it('all bubbles are tracked in activeBubbles for any count 1-5', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 5 }),
        (count) => {
          // Reset state for each run
          manager.clear();
          scene.children.length = 0;

          // Show `count` bubbles
          for (let i = 0; i < count; i++) {
            const pos = new THREE.Vector3(i, i, i);
            manager.show(pos, `Bubble ${i}`, 5000);
          }

          // All should be tracked
          expect(manager.getActiveBubbles().length).toBe(count);
          expect(scene.children.length).toBe(count);

          // Clean up for next iteration
          manager.clear();
        }
      ),
      { numRuns: 30 }
    );
  });

  it('default duration is 5000ms when not specified', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }), // arbitrary input to run multiple times
        (_n) => {
          // Reset state for each run
          manager.clear();
          scene.children.length = 0;

          const pos = new THREE.Vector3(0, 0, 0);
          manager.show(pos, 'Default duration test');

          // At 4999ms, no fade-out yet
          vi.advanceTimersByTime(4999);
          const bubble = manager.getActiveBubbles()[0];
          expect(bubble.el.classList.contains('fade-out')).toBe(false);

          // At 5000ms, fade-out should start
          vi.advanceTimersByTime(1);
          expect(bubble.el.classList.contains('fade-out')).toBe(true);

          // At 5500ms total, bubble should be removed
          vi.advanceTimersByTime(500);
          expect(manager.getActiveBubbles().length).toBe(0);
          expect(scene.children.length).toBe(0);
        }
      ),
      { numRuns: 10 }
    );
  });
});
