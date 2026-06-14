/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
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

describe('SpeechBubbleManager', () => {
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

  describe('constructor', () => {
    it('stores scene reference', () => {
      expect(manager.scene).toBe(scene);
    });

    it('initializes activeBubbles as an empty array', () => {
      expect(manager.activeBubbles).toEqual([]);
    });
  });

  describe('show', () => {
    it('creates a CSS2DObject and adds it to the scene', () => {
      const pos = new THREE.Vector3(1, 2, 3);
      manager.show(pos, 'Hello');

      expect(scene.children.length).toBe(1);
      expect(scene.children[0].isCSS2DObject).toBe(true);
    });

    it('sets the correct position on the CSS2DObject', () => {
      const pos = new THREE.Vector3(5, 3, -2);
      manager.show(pos, 'Test');

      const label = scene.children[0];
      expect(label.position.x).toBe(5);
      expect(label.position.y).toBe(3);
      expect(label.position.z).toBe(-2);
    });

    it('creates a div element with class speech-bubble', () => {
      const pos = new THREE.Vector3(0, 0, 0);
      manager.show(pos, 'Bubble text');

      const bubble = manager.activeBubbles[0];
      expect(bubble.el.tagName).toBe('DIV');
      expect(bubble.el.className).toBe('speech-bubble');
    });

    it('sets innerHTML to the provided text', () => {
      const pos = new THREE.Vector3(0, 0, 0);
      manager.show(pos, '<strong>Power cut</strong> detected');

      const bubble = manager.activeBubbles[0];
      expect(bubble.el.innerHTML).toBe('<strong>Power cut</strong> detected');
    });

    it('adds bubble to activeBubbles array', () => {
      const pos = new THREE.Vector3(0, 0, 0);
      manager.show(pos, 'Test');

      expect(manager.activeBubbles.length).toBe(1);
    });

    it('supports multiple bubbles at once', () => {
      manager.show(new THREE.Vector3(0, 0, 0), 'First');
      manager.show(new THREE.Vector3(1, 1, 1), 'Second');
      manager.show(new THREE.Vector3(2, 2, 2), 'Third');

      expect(manager.activeBubbles.length).toBe(3);
      expect(scene.children.length).toBe(3);
    });

    it('starts fade-out after the specified duration', () => {
      const pos = new THREE.Vector3(0, 0, 0);
      manager.show(pos, 'Fading', 3000);

      const bubble = manager.activeBubbles[0];
      expect(bubble.el.classList.contains('fade-out')).toBe(false);

      vi.advanceTimersByTime(3000);
      expect(bubble.el.classList.contains('fade-out')).toBe(true);
    });

    it('uses default duration of 5000ms', () => {
      const pos = new THREE.Vector3(0, 0, 0);
      manager.show(pos, 'Default duration');

      const bubble = manager.activeBubbles[0];

      vi.advanceTimersByTime(4999);
      expect(bubble.el.classList.contains('fade-out')).toBe(false);

      vi.advanceTimersByTime(1);
      expect(bubble.el.classList.contains('fade-out')).toBe(true);
    });

    it('removes bubble from scene after fade-out transition (500ms)', () => {
      const pos = new THREE.Vector3(0, 0, 0);
      manager.show(pos, 'Will disappear', 5000);

      // Advance past duration
      vi.advanceTimersByTime(5000);
      expect(scene.children.length).toBe(1); // Still in scene during fade

      // Advance past fade-out transition
      vi.advanceTimersByTime(500);
      expect(scene.children.length).toBe(0);
      expect(manager.activeBubbles.length).toBe(0);
    });
  });

  describe('clear', () => {
    it('removes all active bubbles from the scene', () => {
      manager.show(new THREE.Vector3(0, 0, 0), 'One');
      manager.show(new THREE.Vector3(1, 1, 1), 'Two');
      manager.show(new THREE.Vector3(2, 2, 2), 'Three');

      expect(scene.children.length).toBe(3);

      manager.clear();

      expect(scene.children.length).toBe(0);
      expect(manager.activeBubbles.length).toBe(0);
    });

    it('clears pending timers so no delayed removal occurs', () => {
      manager.show(new THREE.Vector3(0, 0, 0), 'Timer test', 2000);

      manager.clear();

      // Advance time — no errors or unexpected behavior
      vi.advanceTimersByTime(5000);
      expect(manager.activeBubbles.length).toBe(0);
    });

    it('works when there are no active bubbles', () => {
      expect(() => manager.clear()).not.toThrow();
      expect(manager.activeBubbles.length).toBe(0);
    });
  });

  describe('getActiveBubbles', () => {
    it('returns the active bubbles array', () => {
      expect(manager.getActiveBubbles()).toBe(manager.activeBubbles);
    });

    it('reflects current state after show and clear', () => {
      manager.show(new THREE.Vector3(0, 0, 0), 'A');
      manager.show(new THREE.Vector3(1, 1, 1), 'B');

      expect(manager.getActiveBubbles().length).toBe(2);

      manager.clear();
      expect(manager.getActiveBubbles().length).toBe(0);
    });
  });
});
