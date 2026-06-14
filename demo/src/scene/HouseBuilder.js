import * as THREE from 'three';
import { COLORS, MATERIALS } from '../utils/constants.js';
import { ROOM_DEFINITIONS } from './RoomDefinitions.js';

/**
 * HouseBuilder - Creates the 3D house geometry with low-poly aesthetics.
 *
 * Builds:
 * - Floor (single BoxGeometry spanning full house footprint)
 * - Exterior walls (perimeter, 0.15 thick, 2.5 height)
 * - Interior walls (dividing walls between rooms, same thickness)
 * - Basic furniture per room (box/cylinder primitives)
 * - NO roof (cutaway design so rooms are visible from above)
 *
 * Target: ~8,000 triangles for house structure (well under 50,000 budget).
 * Uses MATERIALS from constants.js for consistent styling.
 */
export class HouseBuilder {
  /**
   * @param {THREE.Scene} scene - The Three.js scene
   */
  constructor(scene) {
    this.scene = scene;
    this.wallThickness = 0.15;
    this.wallHeight = 2.5;
  }

  /**
   * Build the entire house and add geometry to the scene.
   * @returns {THREE.Group} Group containing all house geometry
   */
  build() {
    const houseGroup = new THREE.Group();
    houseGroup.name = 'HouseGroup';

    // Build each component
    const floor = this._buildFloor();
    const exteriorWalls = this._buildExteriorWalls();
    const interiorWalls = this._buildInteriorWalls();
    const furniture = this._buildFurniture();

    houseGroup.add(floor);
    houseGroup.add(exteriorWalls);
    houseGroup.add(interiorWalls);
    houseGroup.add(furniture);

    // Add to scene
    this.scene.add(houseGroup);

    return houseGroup;
  }

  /**
   * Build the floor as a single large box spanning the full house footprint.
   * House is ~12 units wide (X) x 10 units deep (Z), centered around origin.
   */
  _buildFloor() {
    const floorWidth = 12;
    const floorDepth = 10;
    const floorHeight = 0.15;

    const geometry = new THREE.BoxGeometry(floorWidth, floorHeight, floorDepth);
    const material = MATERIALS.floor();

    const floor = new THREE.Mesh(geometry, material);
    floor.position.set(0, -floorHeight / 2, 0);
    floor.receiveShadow = true;
    floor.castShadow = true;
    floor.name = 'Floor';

    return floor;
  }

  /**
   * Build exterior walls along the perimeter of the house.
   * House bounding box: X from -6 to +6, Z from -5.5 to +5
   * (based on room positions + sizes)
   */
  _buildExteriorWalls() {
    const group = new THREE.Group();
    group.name = 'ExteriorWalls';

    const material = MATERIALS.wall();
    const t = this.wallThickness;
    const h = this.wallHeight;

    // Calculate house bounding box from room definitions
    // Left edge: balcony/kitchen/study at x=-4, width 3.5 → left edge at -4 - 3.5/2 = -5.75
    // Right edge: master/living/kids at x=2, width 5 → right edge at 2 + 5/2 = 4.5
    // Top edge (negative Z): balcony at z=-4, depth 2.5 → top at -4 - 2.5/2 = -5.25
    // Bottom edge (positive Z): kids at z=3.5, depth 2.5 → bottom at 3.5 + 2.5/2 = 4.75
    const minX = -5.75;
    const maxX = 4.5;
    const minZ = -5.25;
    const maxZ = 4.75;
    const width = maxX - minX;
    const depth = maxZ - minZ;

    // Front wall (negative Z side)
    this._addWall(group, material, width + t, h, t,
      (minX + maxX) / 2, h / 2, minZ);
    // Back wall (positive Z side)
    this._addWall(group, material, width + t, h, t,
      (minX + maxX) / 2, h / 2, maxZ);
    // Left wall (negative X side)
    this._addWall(group, material, t, h, depth,
      minX, h / 2, (minZ + maxZ) / 2);
    // Right wall (positive X side)
    this._addWall(group, material, t, h, depth,
      maxX, h / 2, (minZ + maxZ) / 2);

    return group;
  }

  /**
   * Build interior walls dividing rooms.
   */
  _buildInteriorWalls() {
    const group = new THREE.Group();
    group.name = 'InteriorWalls';

    const material = MATERIALS.wall();
    const t = this.wallThickness;
    const h = this.wallHeight;

    // Vertical divider: separates left column (balcony, kitchen, study)
    // from right column (master, bath, living, kids)
    // Left column right edge: -4 + 3.5/2 = -2.25
    // Right column left edge: various, but the divider sits between them
    const dividerX = -2.25;
    this._addWall(group, material, t, h, 10, dividerX, h / 2, 0);

    // Horizontal dividers in left column:
    // Between Balcony (z=-4, depth 2.5) and Kitchen (z=-1, depth 3)
    // Balcony bottom edge: -4 + 2.5/2 = -2.75
    const balconyKitchenZ = -2.75;
    this._addWall(group, material, 3.5, h, t,
      -4, h / 2, balconyKitchenZ);

    // Between Kitchen (z=-1, depth 3) and Study (z=2.5, depth 3)
    // Kitchen bottom edge: -1 + 3/2 = 0.5
    const kitchenStudyZ = 0.5;
    this._addWall(group, material, 3.5, h, t,
      -4, h / 2, kitchenStudyZ);

    // Horizontal dividers in right column:
    // Between Master Bedroom (z=-4, depth 2.5) and Living/Bath area
    // Master bottom edge: -4 + 2.5/2 = -2.75
    const masterLivingZ = -2.75;
    this._addWall(group, material, 5, h, t,
      2, h / 2, masterLivingZ);

    // Bath walls (small room between left divider and living room)
    // Bath at position (0, 0, -2), size (2, 2.5, 1.5)
    // Bath right edge: 0 + 2/2 = 1
    // Bath bottom edge: -2 + 1.5/2 = -1.25
    this._addWall(group, material, 2, h, t,
      0, h / 2, -1.25); // Bath bottom wall
    this._addWall(group, material, t, h, 1.5,
      1, h / 2, -2); // Bath right wall

    // Between Living Room (z=0, depth 3.5) and Kids Room (z=3.5, depth 2.5)
    // Living bottom edge: 0 + 3.5/2 = 1.75
    const livingKidsZ = 1.75;
    this._addWall(group, material, 5, h, t,
      2, h / 2, livingKidsZ);

    return group;
  }

  /**
   * Build basic furniture for each room using simple primitives.
   */
  _buildFurniture() {
    const group = new THREE.Group();
    group.name = 'FurnitureGroup';

    this._buildLivingRoomFurniture(group);
    this._buildKitchenFurniture(group);
    this._buildMasterBedroomFurniture(group);
    this._buildKidsRoomFurniture(group);
    this._buildStudyRoomFurniture(group);
    this._buildBathFurniture(group);
    this._buildBalconyFurniture(group);

    return group;
  }

  // --- Furniture builders ---

  _buildLivingRoomFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'living_room');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Sofa (long box)
    const sofaGeo = new THREE.BoxGeometry(2.2, 0.6, 0.8);
    const sofaMat = new THREE.MeshStandardMaterial({ color: 0x8b6b4a, roughness: 0.8 });
    const sofa = new THREE.Mesh(sofaGeo, sofaMat);
    sofa.position.set(baseX + 0.5, 0.3, baseZ + 1.0);
    sofa.castShadow = true;
    sofa.receiveShadow = true;
    parent.add(sofa);

    // Coffee table (low cylinder)
    const tableGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.3, 8);
    const tableMat = new THREE.MeshStandardMaterial({ color: 0x654321, roughness: 0.7 });
    const table = new THREE.Mesh(tableGeo, tableMat);
    table.position.set(baseX + 0.5, 0.15, baseZ + 0.2);
    table.castShadow = true;
    table.receiveShadow = true;
    parent.add(table);

    // TV stand (flat box)
    const tvGeo = new THREE.BoxGeometry(1.4, 0.7, 0.15);
    const tvMat = new THREE.MeshStandardMaterial({ color: 0x222222, roughness: 0.3 });
    const tv = new THREE.Mesh(tvGeo, tvMat);
    tv.position.set(baseX + 0.5, 0.4, baseZ - 1.2);
    tv.castShadow = true;
    tv.receiveShadow = true;
    parent.add(tv);
  }

  _buildKitchenFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'kitchen');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Counter (long box along one wall)
    const counterGeo = new THREE.BoxGeometry(2.2, 0.9, 0.5);
    const counterMat = new THREE.MeshStandardMaterial({ color: 0xa08060, roughness: 0.7 });
    const counter = new THREE.Mesh(counterGeo, counterMat);
    counter.position.set(baseX, 0.45, baseZ - 1.0);
    counter.castShadow = true;
    counter.receiveShadow = true;
    parent.add(counter);

    // Dining table (cylinder)
    const tableGeo = new THREE.CylinderGeometry(0.5, 0.5, 0.7, 8);
    const tableMat = new THREE.MeshStandardMaterial({ color: 0x8b7355, roughness: 0.6 });
    const table = new THREE.Mesh(tableGeo, tableMat);
    table.position.set(baseX + 0.3, 0.35, baseZ + 0.6);
    table.castShadow = true;
    table.receiveShadow = true;
    parent.add(table);
  }

  _buildMasterBedroomFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'master_bedroom');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Bed (flat wide box)
    const bedGeo = new THREE.BoxGeometry(1.8, 0.4, 2.0);
    const bedMat = new THREE.MeshStandardMaterial({ color: 0x6b8cae, roughness: 0.8 });
    const bed = new THREE.Mesh(bedGeo, bedMat);
    bed.position.set(baseX + 0.8, 0.2, baseZ);
    bed.castShadow = true;
    bed.receiveShadow = true;
    parent.add(bed);

    // Nightstand (small box)
    const standGeo = new THREE.BoxGeometry(0.4, 0.5, 0.4);
    const standMat = new THREE.MeshStandardMaterial({ color: 0x654321, roughness: 0.7 });
    const stand = new THREE.Mesh(standGeo, standMat);
    stand.position.set(baseX - 0.5, 0.25, baseZ - 0.7);
    stand.castShadow = true;
    stand.receiveShadow = true;
    parent.add(stand);
  }

  _buildKidsRoomFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'kids_room');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Kid's bed (smaller flat box)
    const bedGeo = new THREE.BoxGeometry(1.2, 0.35, 1.6);
    const bedMat = new THREE.MeshStandardMaterial({ color: 0x7cae6b, roughness: 0.8 });
    const bed = new THREE.Mesh(bedGeo, bedMat);
    bed.position.set(baseX + 1.0, 0.175, baseZ);
    bed.castShadow = true;
    bed.receiveShadow = true;
    parent.add(bed);

    // Small desk (box)
    const deskGeo = new THREE.BoxGeometry(1.0, 0.6, 0.5);
    const deskMat = new THREE.MeshStandardMaterial({ color: 0xcc9966, roughness: 0.7 });
    const desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(baseX - 0.8, 0.3, baseZ - 0.5);
    desk.castShadow = true;
    desk.receiveShadow = true;
    parent.add(desk);
  }

  _buildStudyRoomFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'study_room');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Desk (box)
    const deskGeo = new THREE.BoxGeometry(1.4, 0.7, 0.6);
    const deskMat = new THREE.MeshStandardMaterial({ color: 0x8b7355, roughness: 0.7 });
    const desk = new THREE.Mesh(deskGeo, deskMat);
    desk.position.set(baseX, 0.35, baseZ - 0.7);
    desk.castShadow = true;
    desk.receiveShadow = true;
    parent.add(desk);

    // Chair (cylinder seat)
    const chairGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.4, 8);
    const chairMat = new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.5 });
    const chair = new THREE.Mesh(chairGeo, chairMat);
    chair.position.set(baseX, 0.2, baseZ - 0.1);
    chair.castShadow = true;
    chair.receiveShadow = true;
    parent.add(chair);
  }

  _buildBathFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'bath');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Tub/shower indicator (box)
    const tubGeo = new THREE.BoxGeometry(0.7, 0.4, 1.0);
    const tubMat = new THREE.MeshStandardMaterial({ color: 0xddeeff, roughness: 0.3, metalness: 0.1 });
    const tub = new THREE.Mesh(tubGeo, tubMat);
    tub.position.set(baseX + 0.4, 0.2, baseZ);
    tub.castShadow = true;
    tub.receiveShadow = true;
    parent.add(tub);
  }

  _buildBalconyFurniture(parent) {
    const room = ROOM_DEFINITIONS.find((r) => r.id === 'balcony');
    const baseX = room.position.x;
    const baseZ = room.position.z;

    // Railing (thin tall box along outer edge)
    const railGeo = new THREE.BoxGeometry(2.8, 1.0, 0.08);
    const railMat = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.4, metalness: 0.3 });
    const rail = new THREE.Mesh(railGeo, railMat);
    rail.position.set(baseX, 0.5, baseZ - 1.0);
    rail.castShadow = true;
    rail.receiveShadow = true;
    parent.add(rail);

    // Plant pot (cylinder)
    const potGeo = new THREE.CylinderGeometry(0.2, 0.15, 0.4, 8);
    const potMat = new THREE.MeshStandardMaterial({ color: 0x8b4513, roughness: 0.9 });
    const pot = new THREE.Mesh(potGeo, potMat);
    pot.position.set(baseX + 0.8, 0.2, baseZ + 0.5);
    pot.castShadow = true;
    pot.receiveShadow = true;
    parent.add(pot);
  }

  // --- Helper methods ---

  /**
   * Add a wall box to a group.
   */
  _addWall(group, material, width, height, depth, x, y, z) {
    const geometry = new THREE.BoxGeometry(width, height, depth);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
}
