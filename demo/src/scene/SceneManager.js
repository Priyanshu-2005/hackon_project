import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';

/**
 * SceneManager — Sets up and manages the Three.js scene, camera, renderers,
 * controls, and the animation loop for the 3D demo.
 */
export class SceneManager {
  constructor() {
    // 1. Three.js Scene with dark background
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0d1117);

    // 2. PerspectiveCamera — FOV 45, isometric-like angle
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    this.camera.position.set(12, 10, 12);
    this.camera.lookAt(0, 0, 0);

    // 3. WebGLRenderer — antialias, alpha, shadows
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // 4. OrbitControls — damping, constrained polar angle and zoom
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.maxPolarAngle = Math.PI / 2.2;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 30;

    // 5. CSS2DRenderer — for speech bubble overlays
    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.domElement.style.position = 'absolute';
    this.labelRenderer.domElement.style.top = '0';
    this.labelRenderer.domElement.style.left = '0';
    this.labelRenderer.domElement.style.pointerEvents = 'none';

    // Bind resize handler
    this._onResize = this._onResize.bind(this);
    window.addEventListener('resize', this._onResize);
  }

  /**
   * init(container) — Appends renderers to the container and starts the animation loop.
   * @param {HTMLElement} container - The DOM element to mount renderers into (e.g. #3d-container)
   */
  init(container) {
    this.container = container;

    // Set initial sizes based on container
    const width = container.clientWidth;
    const height = container.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height);
    this.labelRenderer.setSize(width, height);

    // Append renderer canvases to container
    container.appendChild(this.renderer.domElement);
    container.appendChild(this.labelRenderer.domElement);

    // Start the animation loop
    this.animate();
  }

  /**
   * animate() — requestAnimationFrame loop that updates controls and renders the scene.
   */
  animate() {
    requestAnimationFrame(() => this.animate());
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
  }

  /**
   * Resize handler — updates camera aspect, renderer size, and CSS2D renderer size.
   */
  _onResize() {
    if (!this.container) return;

    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height);
    this.labelRenderer.setSize(width, height);
  }

  /**
   * getScene() — returns the Three.js scene.
   * @returns {THREE.Scene}
   */
  getScene() {
    return this.scene;
  }

  /**
   * getCamera() — returns the PerspectiveCamera.
   * @returns {THREE.PerspectiveCamera}
   */
  getCamera() {
    return this.camera;
  }

  /**
   * getCss2dRenderer() — returns the CSS2DRenderer (label renderer).
   * @returns {CSS2DRenderer}
   */
  getCss2dRenderer() {
    return this.labelRenderer;
  }

  /**
   * Cleanup — removes event listeners and disposes of renderer resources.
   */
  dispose() {
    window.removeEventListener('resize', this._onResize);
    this.renderer.dispose();
    this.controls.dispose();
  }
}
