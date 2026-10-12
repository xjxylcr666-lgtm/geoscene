import * as THREE from 'three'
import { checkVisibility } from './visibility.js'

export function buildingMeshes(dataset) {
  return dataset.buildings.flatMap(building => building.polygons.map(rings => {
    const points = ring => ring.map(([x,z]) => new THREE.Vector2(x, -z))
    const shape = new THREE.Shape(points(rings[0]))
    shape.holes = rings.slice(1).map(ring => new THREE.Path(points(ring)))
    const geometry = new THREE.ExtrudeGeometry(shape, {depth: building.height, bevelEnabled:false, steps:1})
    geometry.rotateX(-Math.PI / 2)
    const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color:building.source==='manual'?0xc28b4b:0x90a5ad, side:THREE.DoubleSide}))
    mesh.position.y = building.base
    mesh.name = building.name
    mesh.userData.id = building.id
    mesh.updateMatrixWorld(true)
    return mesh
  }))
}

const finite = v => typeof v === 'number' && Number.isFinite(v)
function vector(value, label) {
  if (!value || !['x','y','z'].every(axis => finite(value[axis]))) throw new Error(`${label}: 坐标必须是有限数值`)
}
export function validateScheme(scheme) {
  vector(scheme.position, '观察点')
  vector(scheme.direction, '朝向')
  if (Math.hypot(...Object.values(scheme.direction)) < 1e-8) throw new Error('观察方向不能为零')
  if (!finite(scheme.fov) || scheme.fov <= 0 || scheme.fov > 180) throw new Error('视野角须在(0,180]')
  if (!finite(scheme.maxDistance) || scheme.maxDistance <= 0 || scheme.maxDistance > 2000) throw new Error('距离须在(0,2000]米')
}
export function analyzeBatch(dataset, obstacles, scheme, targetIds) {
  validateScheme(scheme)
  if (!Array.isArray(targetIds) || !targetIds.length || targetIds.length > 100 || new Set(targetIds).size !== targetIds.length) throw new Error('目标列表须为1..100个唯一ID')
  const selected = targetIds.map(id => {
    const target = dataset.targets.find(t => t.id === id)
    if (!target) throw new Error(`不存在目标 ${id}`)
    vector(target.position, '目标')
    return target
  })
  const observation = {position:new THREE.Vector3(scheme.position.x,scheme.position.y,scheme.position.z)}
  obstacles.forEach(o => o.updateMatrixWorld(true))
  const start = performance.now()
  const results = selected.map(target => ({target_id:target.id, position:target.position,
    ...checkVisibility(observation,scheme,{position:new THREE.Vector3(target.position.x,target.position.y,target.position.z)},obstacles)}))
  return {scheme:structuredClone(scheme), results, visible_count:results.filter(r=>r.visible).length,
    total:results.length, analysis_ms:performance.now()-start}
}
export function executeInspectionTool(name,args,dataset,obstacles,schemes) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) throw new Error('工具参数必须是对象')
  const ids = args.target_ids
  let selected
  if (name === 'analyze_batch') {
    selected = schemes.filter(s=>s.id===args.scheme_id)
    if(selected.length!==1) throw new Error('无效方案ID')
  } else if (name === 'compare_observers') {
    if(schemes.length!==2) throw new Error('比较需要两组方案')
    selected = schemes
  } else throw new Error('不支持的巡检工具')
  const plans = selected.map(s=>analyzeBatch(dataset,obstacles,s,ids))
  return {source:'geoscene_inspection_tool', tool_name:name, data_version:dataset.version,
    parameters:structuredClone(args), conversion:dataset.conversion, building_count:dataset.buildings.length,
    quality:dataset.quality, limitations:dataset.limitations, plans,
    comparison:plans.length===2 ? {visible_delta_B_minus_A:plans[1].visible_count-plans[0].visible_count,
      changed_target_ids:ids.filter((id,i)=>plans[0].results[i].visible!==plans[1].results[i].visible)} : null}
}

export class ResultState {
  revision=0
  result=null
  invalidate() { this.revision++; this.result=null }
  commit(revision,result) { if(revision!==this.revision) return false; this.result=structuredClone(result); return true }
}
