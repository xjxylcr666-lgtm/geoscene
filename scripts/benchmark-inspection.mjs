import {readFileSync,writeFileSync,mkdirSync} from 'node:fs'
import os from 'node:os'
import {buildingMeshes,executeInspectionTool} from '../src/inspection-core.js'
const folder=new URL('../public/data/buildings/',import.meta.url)
const reports=[]
for(const name of ['sample-local.json','nyc-local.json']){
 const start=performance.now();const data=JSON.parse(readFileSync(new URL(name,folder)));const meshes=buildingMeshes(data);const load_ms=performance.now()-start
 const args={target_ids:data.targets.map(t=>t.id)}
 const trials=[];let result
 for(let i=0;i<20;i++){const start=performance.now();result=executeInspectionTool('compare_observers',args,data,meshes,data.schemes);trials.push(performance.now()-start)}
 const sorted=[...trials].sort((a,b)=>a-b)
 reports.push({name,buildings:data.buildings.length,meshes:meshes.length,targets:data.targets.length,load_ms,
  comparison_trials_ms:trials,median_ms:(sorted[9]+sorted[10])/2,max_ms:sorted.at(-1),result})
}
const output=new URL('../work/verification/',import.meta.url);mkdirSync(output,{recursive:true})
writeFileSync(new URL('benchmark.json',output),JSON.stringify({created_at:new Date().toISOString(),runtime:process.version,platform:os.platform(),cpu:os.cpus()[0].model,scope:'Node CPU geometry only; no browser GPU, network or model latency',reports},null,2))
console.log(JSON.stringify(reports.map(({name,buildings,targets,load_ms,median_ms,max_ms,result})=>({name,buildings,targets,load_ms,median_ms,max_ms,visible:result.plans.map(p=>p.visible_count)})),null,2))
