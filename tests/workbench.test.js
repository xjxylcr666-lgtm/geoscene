import test from 'node:test'
import assert from 'node:assert/strict'
import { buildingMeshes, analyzeBatch, ResultState } from '../src/inspection-core.js'

test('manual meshes use distinct colour and the same obstruction core',()=>{
 const building={id:'manual-test',name:'人工墙',source:'manual',base:0,height:10,polygons:[[[[-2,-2],[2,-2],[2,2],[-2,2],[-2,-2]]]]}
 const data={buildings:[building],targets:[{id:'t',position:{x:10,y:2,z:0}}]}
 const scheme={id:'A',position:{x:-10,y:2,z:0},direction:{x:1,y:0,z:0},fov:120,maxDistance:50}
 const meshes=buildingMeshes(data)
 assert.equal(meshes[0].material.color.getHex(),0xc28b4b)
 assert.equal(analyzeBatch(data,meshes,scheme,['t']).results[0].blocker_id,'manual-test')
 const official=buildingMeshes({buildings:[{...building,source:'official'}]})
 assert.equal(official[0].material.color.getHex(),0x90a5ad)
 building.height=.5
 assert.equal(analyzeBatch(data,buildingMeshes(data),scheme,['t']).results[0].visible,true)
})

test('editing a building invalidates the report snapshot and rejects delayed result',()=>{
 const state=new ResultState(), old=state.revision
 state.commit(old,{manual_buildings:[{height:10}]})
 state.invalidate()
 assert.equal(state.result,null)
 assert.equal(state.commit(old,{manual_buildings:[{height:10}]}),false)
 assert.equal(state.commit(state.revision,{manual_buildings:[{height:.5}]}),true)
})
