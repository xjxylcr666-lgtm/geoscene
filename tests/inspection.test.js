import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import * as THREE from 'three'
import {checkVisibility} from '../src/visibility.js'
import {buildingMeshes,executeInspectionTool,ResultState,validateScheme} from '../src/inspection-core.js'
const data=JSON.parse(readFileSync(new URL('../public/data/buildings/nyc-local.json',import.meta.url)))
const obstacles=buildingMeshes(data)
const args={target_ids:data.targets.map(t=>t.id)}
const object=p=>({position:new THREE.Vector3(p.x,p.y,p.z)})

test('original known-answer fixtures share the exact geometry function',()=>{
 const config=JSON.parse(readFileSync(new URL('../src/scene-config.json',import.meta.url)))
 const observer=config.find(c=>c.type==='observer')
 const walls=config.filter(c=>c.type==='wall').map(c=>{const m=new THREE.Mesh(new THREE.BoxGeometry(c.size.width,c.size.height,c.size.depth),new THREE.MeshBasicMaterial());m.position.copy(object(c.position).position);m.name=c.name;m.updateMatrixWorld();return m})
 const rows=config.filter(c=>c.type==='target').map(t=>checkVisibility(object(observer.position),observer,object(t.position),walls))
 assert.deepEqual(rows.map(r=>r.visible),[false,true,false])
 assert.equal(rows[1].distance,7);assert.equal(rows[2].distance,11)
 assert.match(rows[0].reason,/视野/);assert.match(rows[2].reason,/测试墙/)
})
test('real footprint extrusions have metre scale and participate in obstruction',()=>{
 const wall=obstacles[0];wall.geometry.computeBoundingBox();const box=wall.geometry.boundingBox
 assert.ok(box.max.x-box.min.x>1);assert.ok(box.max.x-box.min.x<500)
 assert.ok(Math.abs(box.max.y-box.min.y-10)<.001)
 const triangle=wall.geometry.attributes.position
 let hit
 for(let i=0;i<triangle.count;i+=3){
   const a=new THREE.Vector3().fromBufferAttribute(triangle,i),b=new THREE.Vector3().fromBufferAttribute(triangle,i+1),c=new THREE.Vector3().fromBufferAttribute(triangle,i+2)
   const normal=b.clone().sub(a).cross(c.clone().sub(a)).normalize()
   if(Math.abs(normal.y)>.1)continue
   const center=a.clone().add(b).add(c).multiplyScalar(1/3).add(wall.position)
   const start=center.clone().addScaledVector(normal,2),end=center.clone().addScaledVector(normal,-2)
   const cfg={direction:end.clone().sub(start),fov:90,maxDistance:10}
   hit=checkVisibility({position:start},cfg,{position:end},[wall]);break
 }
 assert.ok(hit);assert.equal(hit.visible,false);assert.equal(hit.blocker_id,wall.userData.id)
})
test('polygon holes are not filled',()=>{
 const ring=[[-5,-5],[5,-5],[5,5],[-5,5],[-5,-5]]
 const hole=[[-1,-1],[-1,1],[1,1],[1,-1],[-1,-1]]
 const meshes=buildingMeshes({buildings:[{id:'hole',name:'hole',height:10,base:0,polygons:[[ring,hole]]}]})
 const ray=new THREE.Raycaster(new THREE.Vector3(0,15,0),new THREE.Vector3(0,-1,0),0,30)
 assert.equal(ray.intersectObjects(meshes).length,0)
 ray.set(new THREE.Vector3(3,15,0),new THREE.Vector3(0,-1,0));assert.ok(ray.intersectObjects(meshes).length>0)
})
test('comparison equals two separate batch runs; stable deterministic fields',()=>{
 const result=executeInspectionTool('compare_observers',args,data,obstacles,data.schemes)
 for(const plan of result.plans){const batch=executeInspectionTool('analyze_batch',{...args,scheme_id:plan.scheme.id},data,obstacles,data.schemes);assert.deepEqual(plan.results,batch.plans[0].results)}
 assert.equal(result.comparison.visible_delta_B_minus_A,result.plans[1].visible_count-result.plans[0].visible_count)
 assert.ok(result.plans.some(p=>p.results.some(r=>r.blocker_id?.startsWith('nyc-'))))
 assert.equal(result.data_version,data.version);assert.deepEqual(result.limitations,data.limitations)
})
test('invalid targets, duplicate IDs, NaN, zero direction and range rejected',()=>{
 for(const ids of [[],['missing'],[args.target_ids[0],args.target_ids[0]]])assert.throws(()=>executeInspectionTool('compare_observers',{target_ids:ids},data,obstacles,data.schemes))
 assert.throws(()=>executeInspectionTool('analyze_batch',{...args,scheme_id:'C'},data,obstacles,data.schemes))
 for(const change of [{fov:0},{maxDistance:NaN},{direction:{x:0,y:0,z:0}},{position:{x:'1',y:1,z:0}}])assert.throws(()=>validateScheme({...data.schemes[0],...change}))
})
test('old results cannot be committed after inputs change; snapshot is copied',()=>{
 const state=new ResultState();const r=state.revision;const input={value:1};assert.equal(state.commit(r,input),true)
 input.value=2;assert.equal(state.result.value,1);state.invalidate();assert.equal(state.result,null);assert.equal(state.commit(r,input),false)
})
