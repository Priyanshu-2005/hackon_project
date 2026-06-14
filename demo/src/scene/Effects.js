import * as THREE from 'three';

/**
 * Effects manages visual effects for the 3D demo, including device highlighting,
 * power cut flicker overlays, inverter glow, and selective room dimming.
 *
 * Used during proactive action execution and the power cut scenario to provide
 * visual feedback in the 3D scene.
 */
export class Effects {
  /**
   * @param {THREE.Scene} scene - The Three.js scene
   * @param {import('./DeviceIndicators.js').DeviceIndicators} deviceIndicators - Device mesh accessor
   */
  constructor(scene, deviceIndicators) {
    this.scene = scene;
    this.deviceIndicators = deviceIndicators;

    /** @type {Map<string, { cleanup: Function }>} */
    this.activeAnimations = new Map();
  }

  /**
   * Pulse glow animation on a device mesh for a given duration.
   * Uses a sinusoidal pulse on the emissive intensity.
   *
   * @param {string} deviceId - Device identifier
   * @param {number} [duration=2000] - Duration in milliseconds
   */
  highlightDevice(deviceId, duration = 2000) {
    const mesh = this.deviceIndicators.getMesh(deviceId);
    if (!mesh || !mesh.material) return;

    const originalEmissiveIntensity = mesh.material.emissiveIntensity;
    const startTime = performance.now();
    let animationId = null;

    const animate = () => {
      const elapsed = performance.now() - startTime;
      if (elapsed >= duration) {
        // Restore original intensity
        mesh.material.emissiveIntensity = originalEmissiveIntensity;
        this.activeAnimations.delete(`highlight_${deviceId}`);
        return;
      }

      // Sinusoidal pulse: sin(t * PI * 4) completes 2 full cycles in the duration
      const t = elapsed / duration;
      const pulse = Math.sin(t * Math.PI * 4) * 0.5 + 0.5;
      mesh.material.emissiveIntensity = originalEmissiveIntensity + pulse;

      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);

    // Store cleanup function
    this.activeAnimations.set(`highlight_${deviceId}`, {
      cleanup: () => {
        if (animationId !== null) {
          cancelAnimationFrame(animationId);
        }
        mesh.material.emissiveIntensity = originalEmissiveIntensity;
      },
    });
  }

  /**
   * Screen flicker effect simulating a power cut.
   * Alternates the flicker overlay opacity over several cycles.
   *
   * @param {number} [duration=800] - Total flicker duration in milliseconds
   */
  powerCutFlicker(duration = 800) {
    const overlay = document.getElementById('flicker-overlay');
    if (!overlay) return;

    overlay.style.display = 'block';
    overlay.style.opacity = '0';

    const flickerCycles = 4;
    const cycleTime = duration / flickerCycles;
    const startTime = performance.now();
    let animationId = null;

    const animate = () => {
      const elapsed = performance.now() - startTime;
      if (elapsed >= duration) {
        overlay.style.display = 'none';
        overlay.style.opacity = '0';
        this.activeAnimations.delete('powerCutFlicker');
        return;
      }

      // Determine which half of the cycle we're in
      const cycleProgress = (elapsed % cycleTime) / cycleTime;
      // First half: opacity ramps up, second half: ramps down
      if (cycleProgress < 0.5) {
        overlay.style.opacity = '0.8';
      } else {
        overlay.style.opacity = '0';
      }

      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);

    this.activeAnimations.set('powerCutFlicker', {
      cleanup: () => {
        if (animationId !== null) {
          cancelAnimationFrame(animationId);
        }
        overlay.style.display = 'none';
        overlay.style.opacity = '0';
      },
    });
  }

  /**
   * Adds a green glow effect to the inverter device, indicating it has activated.
   * Clones the material with green emissive and adds a green PointLight.
   *
   * @param {string} deviceId - The inverter device ID (e.g., 'inverter_ups')
   */
  inverterGlow(deviceId) {
    const mesh = this.deviceIndicators.getMesh(deviceId);
    if (!mesh) return;

    // Store original material for cleanup
    const originalMaterial = mesh.material;

    // Clone material and apply green emissive glow
    const glowMaterial = originalMaterial.clone();
    glowMaterial.emissive = new THREE.Color(0x00ff88);
    glowMaterial.emissiveIntensity = 0.6;
    mesh.material = glowMaterial;

    // Add a PointLight at the inverter position for ambient green glow
    const light = new THREE.PointLight(0x00ff88, 1, 3);
    light.position.copy(mesh.position);
    this.scene.add(light);

    // Store references for cleanup
    this.activeAnimations.set(`inverterGlow_${deviceId}`, {
      cleanup: () => {
        mesh.material = originalMaterial;
        glowMaterial.dispose();
        this.scene.remove(light);
        light.dispose();
      },
    });
  }

  /**
   * Dims all rooms except specified ones. Used during power cut to show
   * selective power (inverter keeping only certain rooms lit).
   *
   * @param {string[]} roomsToKeepLit - Array of room IDs that should remain lit
   */
  dimRooms(roomsToKeepLit) {
    const roomLights = this.deviceIndicators.getAllRoomLights();
    const dimmedLights = [];

    for (const { roomId, lightMesh } of roomLights) {
      if (roomsToKeepLit.includes(roomId)) continue;

      // Store original values for restoration
      const originalEmissiveIntensity = lightMesh.material.emissiveIntensity;
      const originalOpacity = lightMesh.material.opacity;

      // Dim the light
      lightMesh.material.emissiveIntensity = 0.02;
      lightMesh.material.opacity = 0.3;

      dimmedLights.push({
        lightMesh,
        originalEmissiveIntensity,
        originalOpacity,
      });
    }

    this.activeAnimations.set('dimRooms', {
      cleanup: () => {
        for (const { lightMesh, originalEmissiveIntensity, originalOpacity } of dimmedLights) {
          lightMesh.material.emissiveIntensity = originalEmissiveIntensity;
          lightMesh.material.opacity = originalOpacity;
        }
      },
    });
  }

  /**
   * Restores all active effects to their original states.
   * Cleans up animations, materials, lights, and overlays.
   */
  restoreAll() {
    for (const [key, animation] of this.activeAnimations) {
      animation.cleanup();
    }
    this.activeAnimations.clear();
  }
}
