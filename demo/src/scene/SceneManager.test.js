/**
 * @vitest-environment happy-dom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as THREE from 'three';

// Mock CSS2DRenderer since it requires DOM
vi.mock('three/addons/renderers/CSS2DRenderer.js', () => {
  class CSS2DRenderer {
    constructor() {
      this.domElement = document.createElement('div');
    }
    setSize() {}
    render() {}
  }
  return { CSS2DRenderer };
});

// Mock OrbitControls since it requires a canvas with getContext
vi.mock('three/addons/controls/OrbitControls.js', () => {
  class OrbitControls {
    constructor(camera, domElement) {
      this.camera = camera;
      this.domElement = domElement;
      this.enableDamping = false;
      this.dampingFactor = 0;
      this.maxPolarAngle = Infinity;
      this.minDistance = 0;
      this.maxDistance = Infinity;
    }
    update() {}
    dispose() {}
  }
  return { OrbitControls };
});

// Mock WebGLRenderer since it requires WebGL context
vi.mock('three', async () => {
  const actual = await vi.importActual('three');
  class MockWebGLRenderer {
    constructor(params) {
      this.params = params;
      this.domElement = document.createElement('canvas');
      this.shadowMap = { enabled: false, type: null };
    }
    setPixelRatio() {}
    setSize() {}
    render() {}
    dispose() {}
  }
  return {
    ...actual,
    WebGLRenderer: MockWebGLRenderer,
  };
});

import { SceneManager } from './SceneManager.js';

describe('SceneManager', () => {
  let manager;

  beforeEach(() => {
    manager = new SceneManager();
  });

  afterEach(() => {
    manager.dispose();
  });

  describe('constructor', () => {
    it('creates a THREE.Scene', () => {
      expect(manager.scene).toBeInstanceOf(THREE.Scene);
    });

    it('sets scene background color to 0x0d1117', () => {
      expect(manager.scene.background).toBeInstanceOf(THREE.Color);
      const expected = new THREE.Color(0x0d1117);
      expect(manager.scene.background.r).toBeCloseTo(expected.r);
      expect(manager.scene.background.g).toBeCloseTo(expected.g);
      expect(manager.scene.background.b).toBeCloseTo(expected.b);
    });

    it('creates a PerspectiveCamera with FOV 45', () => {
      expect(manager.camera).toBeInstanceOf(THREE.PerspectiveCamera);
      expect(manager.camera.fov).toBe(45);
    });

    it('positions camera at (12, 10, 12)', () => {
      expect(manager.camera.position.x).toBe(12);
      expect(manager.camera.position.y).toBe(10);
      expect(manager.camera.position.z).toBe(12);
    });

    it('sets near clipping plane to 0.1 and far to 1000', () => {
      expect(manager.camera.near).toBe(0.1);
      expect(manager.camera.far).toBe(1000);
    });

    it('creates WebGLRenderer with antialias and alpha', () => {
      expect(manager.renderer.params.antialias).toBe(true);
      expect(manager.renderer.params.alpha).toBe(true);
    });

    it('enables shadow map with PCFSoftShadowMap', () => {
      expect(manager.renderer.shadowMap.enabled).toBe(true);
      expect(manager.renderer.shadowMap.type).toBe(THREE.PCFSoftShadowMap);
    });

    it('configures OrbitControls with damping', () => {
      expect(manager.controls.enableDamping).toBe(true);
      expect(manager.controls.dampingFactor).toBe(0.05);
    });

    it('configures OrbitControls polar angle constraint', () => {
      expect(manager.controls.maxPolarAngle).toBeCloseTo(Math.PI / 2.2);
    });

    it('configures OrbitControls distance constraints', () => {
      expect(manager.controls.minDistance).toBe(5);
      expect(manager.controls.maxDistance).toBe(30);
    });

    it('creates CSS2DRenderer with absolute positioning', () => {
      expect(manager.labelRenderer.domElement.style.position).toBe('absolute');
      // happy-dom normalizes '0' to '0px'
      expect(manager.labelRenderer.domElement.style.top).toMatch(/^0(px)?$/);
      expect(manager.labelRenderer.domElement.style.left).toMatch(/^0(px)?$/);
      expect(manager.labelRenderer.domElement.style.pointerEvents).toBe('none');
    });
  });

  describe('accessor methods', () => {
    it('getScene() returns the scene', () => {
      expect(manager.getScene()).toBe(manager.scene);
      expect(manager.getScene()).toBeInstanceOf(THREE.Scene);
    });

    it('getCamera() returns the camera', () => {
      expect(manager.getCamera()).toBe(manager.camera);
      expect(manager.getCamera()).toBeInstanceOf(THREE.PerspectiveCamera);
    });

    it('getCss2dRenderer() returns the label renderer', () => {
      expect(manager.getCss2dRenderer()).toBe(manager.labelRenderer);
    });
  });

  describe('init(container)', () => {
    it('appends renderer domElement to container', () => {
      const container = document.createElement('div');
      Object.defineProperty(container, 'clientWidth', { value: 800 });
      Object.defineProperty(container, 'clientHeight', { value: 600 });

      // Mock requestAnimationFrame to prevent infinite loop
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      manager.init(container);

      expect(container.contains(manager.renderer.domElement)).toBe(true);
      expect(container.contains(manager.labelRenderer.domElement)).toBe(true);

      vi.restoreAllMocks();
    });

    it('sets renderer size to container dimensions', () => {
      const container = document.createElement('div');
      Object.defineProperty(container, 'clientWidth', { value: 1024 });
      Object.defineProperty(container, 'clientHeight', { value: 768 });

      const setSizeSpy = vi.spyOn(manager.renderer, 'setSize');
      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      manager.init(container);

      expect(setSizeSpy).toHaveBeenCalledWith(1024, 768);

      vi.restoreAllMocks();
    });

    it('updates camera aspect ratio based on container', () => {
      const container = document.createElement('div');
      Object.defineProperty(container, 'clientWidth', { value: 1920 });
      Object.defineProperty(container, 'clientHeight', { value: 1080 });

      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);

      manager.init(container);

      expect(manager.camera.aspect).toBeCloseTo(1920 / 1080);

      vi.restoreAllMocks();
    });
  });

  describe('_onResize()', () => {
    it('does nothing if container is not set', () => {
      expect(() => manager._onResize()).not.toThrow();
    });

    it('updates dimensions when container is set', () => {
      const container = document.createElement('div');
      Object.defineProperty(container, 'clientWidth', { value: 800, configurable: true });
      Object.defineProperty(container, 'clientHeight', { value: 600, configurable: true });

      vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 1);
      manager.init(container);

      // Simulate resize
      Object.defineProperty(container, 'clientWidth', { value: 1200, configurable: true });
      Object.defineProperty(container, 'clientHeight', { value: 900, configurable: true });

      const setSizeSpy = vi.spyOn(manager.renderer, 'setSize');
      manager._onResize();

      expect(setSizeSpy).toHaveBeenCalledWith(1200, 900);
      expect(manager.camera.aspect).toBeCloseTo(1200 / 900);

      vi.restoreAllMocks();
    });
  });

  describe('dispose()', () => {
    it('disposes renderer and controls', () => {
      const rendererDisposeSpy = vi.spyOn(manager.renderer, 'dispose');
      const controlsDisposeSpy = vi.spyOn(manager.controls, 'dispose');

      manager.dispose();

      expect(rendererDisposeSpy).toHaveBeenCalled();
      expect(controlsDisposeSpy).toHaveBeenCalled();
    });
  });
});
