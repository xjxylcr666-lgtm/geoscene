import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { buildingMeshes,executeInspectionTool,ResultState,validateScheme } from './inspection-core.js'
import './inspection.css'

const $=id=>document.getElementById(id)
const API='http://127.0.0.1:8000'
const scene=new THREE.Scene()
scene.background=new THREE.Color('#cbd8df')
const camera=new THREE.PerspectiveCamera(48,1,0.2,3000)
const renderer=new THREE.WebGLRenderer({antialias:true})
renderer.setPixelRatio(Math.min(devicePixelRatio,2))
$('viewport').appendChild(renderer.domElement)
const controls=new OrbitControls(camera,renderer.domElement)
controls.enableDamping=true
controls.maxPolarAngle=Math.PI*.49
const reset=()=>{camera.position.set(410,470,450);controls.target.set(0,0,0);controls.update()}
reset()
$('reset-view').onclick=reset
scene.add(new THREE.HemisphereLight(0xffffff,0x657078,2.5))
const sun=new THREE.DirectionalLight(0xffffff,2);sun.position.set(100,200,80);scene.add(sun)
const grid=new THREE.GridHelper(600,30,0x617b89,0xaabcc5);grid.position.y=-.1;scene.add(grid)
const indicators=new THREE.Group();scene.add(indicators)
let data,obstacles=[],loadMs=0
const state=new ResultState()
const buttons=()=>{ $('batch').disabled=!data; $('compare').disabled=!data; $('agent').disabled=!data||!$('enable-model').checked }
function clearIndicators(){for(const child of [...indicators.children]){indicators.remove(child);child.geometry?.dispose();child.material?.dispose()}}
function invalidate(){state.invalidate();$('export').disabled=true;$('results').replaceChildren();$('report-link').replaceChildren();$('status').textContent='参数已修改，旧结果和报告已失效';clearIndicators();buttons()}
const position=(obj)=>new THREE.Vector3(obj.x,obj.y,obj.z)
function readSchemes(){return data.schemes.map(s=>{const read=k=>{const value=$(`${s.id}-${k}`).value.trim();return value===''?NaN:Number(value)};const result={...s,position:{x:read('x'),y:read('y'),z:read('z')},direction:{x:read('dx'),y:read('dy'),z:read('dz')},fov:read('fov'),maxDistance:read('maxDistance')};validateScheme(result);return result})}
const readIds=()=>$('target-ids').value.split(',').map(s=>s.trim()).filter(Boolean)
function draw(result){
  clearIndicators()
  for(const target of data.targets){const row=result?.plans[0].results.find(r=>r.target_id===target.id);const mesh=new THREE.Mesh(new THREE.SphereGeometry(2.1,12,8),new THREE.MeshBasicMaterial({color:row?(row.visible?0x2caf73:0xcf4545):0xcba52d}));mesh.position.copy(position(target.position));indicators.add(mesh)}
  for(const [index,plan] of (result?.plans??[]).entries()){
    const color=plan.scheme.id==='A'?0x00bed0:0xeb9026
    const origin=position(plan.scheme.position)
    const arrow=new THREE.ArrowHelper(position(plan.scheme.direction).normalize(),origin,25,color,6,4);indicators.add(arrow)
    for(const row of plan.results){const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([origin,position(row.position)]),new THREE.LineBasicMaterial({color,transparent:true,opacity:row.visible?.85:.22}));indicators.add(line)}
  }
}
async function post(path,body){
  let response
  try { response=await fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}) }
  catch { throw new Error('无法连接本地后台，请确认8000端口服务已启动') }
  const json=await response.json();if(!response.ok)throw new Error(`HTTP ${response.status}: ${JSON.stringify(json.detail)}`);return json
}
function show(result){
  const table=document.createElement('table')
  const header=table.insertRow();for(const title of ['方案','目标','可见','米','原因']){const cell=document.createElement('th');cell.textContent=title;header.appendChild(cell)}
  for(const p of result.plans)for(const r of p.results){const row=table.insertRow();for(const value of [p.scheme.id,r.target_id,r.visible?'是':'否',r.distance.toFixed(2),r.reason])row.insertCell().textContent=value}
  $('results').replaceChildren(table)
  $('status').textContent=result.plans.map(p=>`${p.scheme.id}：${p.visible_count}/${p.total}点可见，${p.analysis_ms.toFixed(2)} ms`).join('；')
}
async function run(name,args,mode='直接工具执行，无模型调用'){
  invalidate();const revision=state.revision
  $('batch').disabled=$('compare').disabled=$('agent').disabled=true
  $('status').textContent='正在校验输入并执行几何分析…'
  try{
    const schemes=readSchemes()
    // Validate every selected input before invoking the shared geometry.
    const selected=args.target_ids.map(id=>{const t=data.targets.find(t=>t.id===id);if(!t)throw new Error(`不存在目标 ${id}`);return t})
    const validations=await Promise.all(selected.map(t=>post('/validate-target',t)))
    if(revision!==state.revision)return null
    if(validations.some(v=>!v.valid))throw new Error('Python目标校验未通过')
    const result=executeInspectionTool(name,args,data,obstacles,schemes)
    draw(result);renderer.render(scene,camera)
    const snapshot={run_id:crypto.randomUUID(),created_at:new Date().toISOString(),execution_mode:mode,result,
      screenshot:renderer.domElement.toDataURL('image/png'),conditions:{load_ms:loadMs,user_agent:navigator.userAgent,
        hardware_concurrency:navigator.hardwareConcurrency,viewport:[renderer.domElement.width,renderer.domElement.height],
        camera:{position:camera.position.toArray(),target:controls.target.toArray()},scope:'加载包含本地HTTP/解析/网格创建；分析计时仅共享几何计算'}}
    if(!state.commit(revision,snapshot))return null
    show(result);$('export').disabled=false
    return snapshot
  }catch(e){if(revision===state.revision){$('status').textContent=`分析失败：${e.message}`;clearIndicators()}return null}
  finally{if(revision===state.revision)buttons()}
}
$('batch').onclick=()=>run('analyze_batch',{scheme_id:'A',target_ids:readIds()})
$('compare').onclick=()=>run('compare_observers',{target_ids:readIds()})
$('target-ids').oninput=invalidate
$('instruction').oninput=invalidate
$('enable-model').onchange=buttons
$('export').onclick=async()=>{
  if(!state.result)return
  const snapshot=structuredClone(state.result),revision=state.revision
  $('export').disabled=true
  try{const report=await post('/inspection/reports',snapshot);if(revision!==state.revision)return
    const link=document.createElement('a');link.href=API+report.url;link.target='_blank';link.textContent='打开已保存的同次分析报告';$('report-link').replaceChildren(link)
  }catch(e){if(revision===state.revision)$('status').textContent=`报告保存失败：${e.message}`}
  finally{if(revision===state.revision)$('export').disabled=false}
}
$('agent').onclick=async()=>{
  if(!$('enable-model').checked)return
  invalidate();const revision=state.revision;$('agent').disabled=true
  const usage={prompt_tokens:0,completion_tokens:0,total_tokens:0}
  let stage='规划',responses=0
  const account=u=>{responses++;for(const key of Object.keys(usage))usage[key]+=u?.[key]??0}
  const usageText=()=>`已返回${responses}次模型响应；输入${usage.prompt_tokens} / 输出${usage.completion_tokens} / 合计${usage.total_tokens} tokens（未返回请求用量未知）`
  $('agent-status').textContent='正在请求模型规划…'
  try{
    const instruction=$('instruction').value
    const plan=await post('/inspection/agent/plan',{instruction})
    account(plan.usage)
    $('agent-status').textContent=`规划返回：${plan.tool_name??'追问'}；${usageText()}`
    if(revision!==state.revision)return
    if(plan.kind!=='tool_call'){$('agent-status').textContent=plan.message+'；'+usageText();return}
    stage='本地校验与几何执行'
    const snapshot=await run(plan.tool_name,plan.arguments,'真实模型规划 + 浏览器工具执行')
    if(!snapshot){$('agent-status').textContent=`${stage}未完成；${usageText()}`;return}
    const completedRevision=state.revision
    stage='模型结果确认'
    const completion=await post('/inspection/agent/complete',{instruction,tool_call_id:plan.tool_call_id,tool_result:snapshot.result})
    account(completion.usage)
    if(completedRevision!==state.revision)return
    snapshot.agent={tool_name:plan.tool_name,arguments:plan.arguments,usage,model_responses:responses,message:completion.message}
    state.commit(completedRevision,snapshot)
    $('agent-status').textContent=`工具 ${plan.tool_name}；${completion.message}；${usageText()}`
  }catch(e){$('agent-status').textContent=`Agent在${stage}失败：${e.message}；${usageText()}`}finally{buttons()}
}

async function load(){try{
  const started=performance.now();const response=await fetch('/data/buildings/nyc-local.json');if(!response.ok)throw new Error(`HTTP ${response.status}`)
  data=await response.json();obstacles=buildingMeshes(data);obstacles.forEach(o=>scene.add(o))
  for(const s of data.schemes){const fieldset=document.createElement('fieldset');const legend=document.createElement('legend');legend.textContent=`模拟方案 ${s.id}（米）`;fieldset.appendChild(legend)
    const values={x:s.position.x,y:s.position.y,z:s.position.z,dx:s.direction.x,dy:s.direction.y,dz:s.direction.z,fov:s.fov,maxDistance:s.maxDistance}
    for(const [key,value] of Object.entries(values)){const label=document.createElement('label');label.textContent=key;const input=document.createElement('input');input.type='number';input.step='any';input.id=`${s.id}-${key}`;input.value=value;input.oninput=invalidate;label.appendChild(input);fieldset.appendChild(label)}$('schemes').appendChild(fieldset)}
  $('target-ids').value=data.targets.map(t=>t.id).join(',')
  for(const text of data.limitations){const li=document.createElement('li');li.textContent=text;$('limitations').appendChild(li)}
  loadMs=performance.now()-started
  $('data-status').textContent=`${data.buildings.length} 条真实建筑 / ${obstacles.length} 个障碍网格 / ${data.targets.length} 个模拟目标；加载 ${loadMs.toFixed(1)} ms；1单位=1米；${data.version}`
  $('status').textContent='就绪。青色方案A，橙色方案B。';draw(null);buttons()
}catch(e){data=null;$('status').textContent=`加载失败：${e.message}`}}
const resize=()=>{const box=$('viewport');renderer.setSize(box.clientWidth,box.clientHeight);camera.aspect=box.clientWidth/box.clientHeight;camera.updateProjectionMatrix()}
window.addEventListener('resize',resize);resize()
renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera)})
load()
