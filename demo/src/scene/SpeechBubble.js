import * as THREE from 'three';
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

/**
 * SpeechBubbleManager — Manages CSS2DObject-based speech bubbles
 * that overlay the 3D scene at specified world positions.
 *
 * Uses the CSS2DRenderer already set up by SceneManager to render
 * DOM elements positioned in 3D space.
 */
export class SpeechBubbleManager {
  /**
   * @param {THREE.Scene} scene - The Three.js scene to add bubbles to
   */
  constructor(scene) {
    this.scene = scene;
    this.activeBubbles = [];
  }

  /**
   * Show a speech bubble at a given 3D position.
   * @param {THREE.Vector3} position - World position for the bubble
   * @param {string} text - HTML text content to display
   * @param {number} [duration=5000] - Time in ms before fade-out starts
   */
  show(position, text, duration = 5000) {
    // Create the DOM element
    const el = document.createElement('div');
    el.className = 'speech-bubble';
    el.innerHTML = text;

    // Wrap in CSS2DObject
    const label = new CSS2DObject(el);
    label.position.copy(position);

    // Add to scene
    this.scene.add(label);

    // Track the bubble
    const bubble = { label, el, timers: [] };
    this.activeBubbles.push(bubble);

    // Schedule fade-out after duration
    const fadeTimer = setTimeout(() => {
      el.classList.add('fade-out');

      // Remove after the CSS transition completes (500ms)
      const removeTimer = setTimeout(() => {
        this._removeBubble(bubble);
      }, 500);

      bubble.timers.push(removeTimer);
    }, duration);

    bubble.timers.push(fadeTimer);

    return bubble;
  }

  /**
   * Remove a specific bubble from the scene and clean up.
   * @param {object} bubble - The bubble record to remove
   */
  _removeBubble(bubble) {
    // Clear any pending timers
    bubble.timers.forEach((t) => clearTimeout(t));
    bubble.timers = [];

    // Remove from scene
    this.scene.remove(bubble.label);

    // Clean up DOM element
    if (bubble.el.parentNode) {
      bubble.el.parentNode.removeChild(bubble.el);
    }

    // Remove from active array
    const idx = this.activeBubbles.indexOf(bubble);
    if (idx !== -1) {
      this.activeBubbles.splice(idx, 1);
    }
  }

  /**
   * Remove all active bubbles from the scene.
   */
  clear() {
    // Copy the array since _removeBubble mutates it
    const bubbles = [...this.activeBubbles];
    bubbles.forEach((bubble) => this._removeBubble(bubble));
  }

  /**
   * Get the current array of active bubbles.
   * @returns {Array} The active bubbles
   */
  getActiveBubbles() {
    return this.activeBubbles;
  }
}
