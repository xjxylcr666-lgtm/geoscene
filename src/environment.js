import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

// Scenic context only: these objects never enter the analysis obstacle collection.
export function createEnvironment(scene, camera, renderer) {
  scene.background = new THREE.Color('#b7c7cc')
  scene.fog = new THREE.FogExp2('#b7c7cc', 0.013)
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.12
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  camera.position.set(19, 17, 23)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(1, 0, 0)
  controls.enableDamping = true
  controls.minDistance = 9
  controls.maxDistance = 65
  controls.maxPolarAngle = Math.PI * 0.46
  controls.update()
  const root = new THREE.Group()
  root.name = 'Illustrative alpine research campus'
  scene.add(root)
  const mat = (color, roughness = 0.85) => new THREE.MeshStandardMaterial({ color, roughness })
  const stone = mat('#a1aba8'), road = mat('#394749'), grass = mat('#657969')
  const metal = mat('#344b52', 0.4), glass = mat('#6e9da8', 0.25)
  function block(x, y, z, w, h, d, material) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material)
    mesh.position.set(x, y, z)
    mesh.castShadow = mesh.receiveShadow = true
    root.add(mesh)
    return mesh
  }
  const land = new THREE.Mesh(new THREE.PlaneGeometry(220, 220), grass)
  land.rotation.x = -Math.PI / 2
  land.position.y = -0.18
  land.receiveShadow = true
  root.add(land)
  block(0, -0.13, 0, 18, 0.22, 13, stone)
  block(0, -0.03, 8, 85, 0.08, 3.2, road)
  block(-11, -0.03, -1, 3.2, 0.08, 42, road)
  for (let x = -40; x < 42; x += 3) block(x, 0.02, 8, 1.35, 0.02, 0.09, mat('#d1cbb2'))
  const water = new THREE.Mesh(new THREE.PlaneGeometry(200, 38), new THREE.MeshPhysicalMaterial({ color: '#638f98', roughness: 0.22, metalness: 0.3 }))
  water.rotation.x = -Math.PI / 2
  water.position.set(0, -0.1, -43)
  root.add(water)
  // Deterministic rolling mountain ridges, kept outside the analysis plaza.
  const terrain = new THREE.PlaneGeometry(220, 90, 150, 70)
  terrain.rotateX(-Math.PI / 2)
  const positions = terrain.attributes.position
  const colors = []
  for (let i = 0; i < positions.count; i++) {
    const x = positions.getX(i), z = positions.getZ(i)
    const ridge = Math.sin(x * 0.065 + z * 0.042) * 0.5 + Math.cos(x * 0.12 - z * 0.08) * 0.25
    const height = Math.max(0, (1 - Math.abs(z) / 48) * (14 + ridge * 15) + Math.sin(x * 0.29) * Math.cos(z * 0.2) * 1.5)
    positions.setY(i, height)
    const color = new THREE.Color(height > 20 ? '#c7ccc4' : height > 12 ? '#697a74' : '#455e51')
    colors.push(color.r, color.g, color.b)
  }
  terrain.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
  terrain.computeVertexNormals()
  const mountains = new THREE.Mesh(terrain, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1 }))
  mountains.position.set(0, -1, -105)
  root.add(mountains)
  // Research buildings, glazing, rooftop equipment and planted edges.
  for (const [x, z, w, d, h] of [[-19,-10,9,7,4], [16,-13,11,6,5], [29,-7,7,9,3]]) {
    block(x, h / 2, z, w, h, d, stone)
    block(x, h + 0.12, z, w + 0.4, 0.24, d + 0.4, metal)
    for (let floor = 1; floor < h; floor += 1.3) {
      block(x, floor, z + d / 2 + 0.02, w - 0.6, 0.65, 0.07, glass)
      for (let q = -w / 2 + 1; q < w / 2; q += 1.5) block(x + q, floor, z + d / 2 + 0.07, 0.08, 0.7, 0.1, metal)
    }
    block(x - 1, h + 0.4, z, 2, 0.6, 1.3, metal)
  }
  const bark = mat('#514b3c'), foliage = mat('#304f42')
  for (let i = 0; i < 90; i++) {
    const x = Math.sin(i * 12.9898) * 48
    const z = Math.cos(i * 7.231) * 24 - 6
    if ((Math.abs(x) < 10 && Math.abs(z) < 8) || Math.abs(z - 8) < 3 || Math.abs(x + 11) < 3 || z < -25) continue
    if ((x < -13 && x > -25 && z < -5 && z > -15) || (x > 9 && x < 35 && z < -2 && z > -18)) continue
    const h = 2 + (i % 5) * 0.38
    block(x, h / 3, z, 0.18, h * 0.65, 0.18, bark)
    for (let level = 0; level < 3; level++) {
      const crown = new THREE.Mesh(new THREE.ConeGeometry(0.85 - level * 0.17, h * 0.65, 7), foliage)
      crown.position.set(x, h * 0.55 + level * 0.55, z)
      crown.castShadow = true
      root.add(crown)
    }
  }
  const grid = new THREE.GridHelper(16, 16, '#638f91', '#8caaa6')
  grid.position.y = 0.012
  grid.material.transparent = true
  grid.material.opacity = 0.3
  root.add(grid)
  const reset = () => { camera.position.set(19, 17, 23); controls.target.set(1, 0, 0); controls.update() }
  return { update: () => controls.update(), reset }
}
