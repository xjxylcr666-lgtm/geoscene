import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { buildingMeshes,ResultState,validateScheme } from './inspection-core.js'
import './inspection.css'

const $=id=>document.getElementById(id)
const API=(import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/,'')
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
let data,obstacles=[],loadMs=0,manual=[],busy=false,editing=false,placing=false,selected='',closed=false
const history=[]
const preview=new THREE.Group();scene.add(preview)
const state=new ResultState()
const buttons=()=>{for(const id of ['batch','batch-b','compare'])$(id).disabled=!data||busy||editing; $('agent').disabled=!data||busy||editing||!$('enable-model').checked; $('export').disabled=!state.result||busy||editing }
function clearIndicators(){for(const child of [...indicators.children]){indicators.remove(child);child.geometry?.dispose();child.material?.dispose()}}
function invalidate(){state.invalidate();$('export').disabled=true;$('results').replaceChildren();$('report-link').replaceChildren();$('status').textContent='参数已修改，旧结果和报告已失效';clearIndicators();$('policy').textContent='';buttons()}
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
  catch { throw new Error(`无法连接本地后台 ${API}，请确认服务已启动及跨域配置正确`) }
  const json=await response.json();if(!response.ok)throw new Error(`HTTP ${response.status}: ${JSON.stringify(json.detail)}`);return json
}
function show(result){
  $('policy').textContent=result.rules.conclusion+'；'+result.rules.basis
  switchTab('analysis')
  const table=document.createElement('table')
  const header=table.insertRow();for(const title of ['方案','目标','可见','米','原因']){const cell=document.createElement('th');cell.textContent=title;header.appendChild(cell)}
  for(const p of result.plans)for(const r of p.results){const row=table.insertRow();for(const value of [p.scheme.id,r.target_id,r.visible?'是':'否',r.distance.toFixed(2),r.reason])row.insertCell().textContent=value}
  $('results').replaceChildren(table)
  $('status').textContent=result.plans.map(p=>`${p.scheme.id}：${p.visible_count}/${p.total}点可见，${p.analysis_ms.toFixed(2)} ms`).join('；')
}
async function run(name,args,mode='直接工具执行，无模型调用'){
  invalidate();const revision=state.revision
  busy=true;buttons()
  $('batch').disabled=$('compare').disabled=$('agent').disabled=true
  $('status').textContent='正在校验输入并执行几何分析…'
  try{
    const schemes=readSchemes()
    const result=await post('/inspection/workbench/evaluate',{...project(),tool_name:name,arguments:args,schemes,critical_target_ids:readCritical()})
    if(revision!==state.revision)return null
    draw(result);renderer.render(scene,camera)
    const snapshot={run_id:result.server_run_id,created_at:result.generated_at,execution_mode:mode,result,
      screenshot:renderer.domElement.toDataURL('image/png'),conditions:{load_ms:loadMs,user_agent:navigator.userAgent,
        hardware_concurrency:navigator.hardwareConcurrency,viewport:[renderer.domElement.width,renderer.domElement.height],
        camera:{position:camera.position.toArray(),target:controls.target.toArray()},scope:'加载包含本地HTTP/解析/网格创建；分析计时仅共享几何计算'}}
    if(!state.commit(revision,snapshot))return null
    show(result);$('export').disabled=false
    return snapshot
  }catch(e){if(revision===state.revision){$('status').textContent=`分析失败：${e.message}`;clearIndicators()}return null}
  finally{busy=false;buttons()}
}
$('batch').onclick=()=>run('analyze_batch',{scheme_id:'A',target_ids:readIds()})
$('compare').onclick=()=>run('compare_observers',{target_ids:readIds()})
$('batch-b').onclick=()=>run('analyze_batch',{scheme_id:'B',target_ids:readIds()})
$('critical-ids').oninput=invalidate
$('target-ids').oninput=invalidate
$('instruction').oninput=invalidate
$('enable-model').onchange=buttons
async function exportReport(){
  if(!state.result)return
  const snapshot=structuredClone(state.result),revision=state.revision
  $('export').disabled=true
  try{const report=await post('/inspection/workbench/report',snapshot);if(revision!==state.revision)return
    $('report-link').replaceChildren();for(const [url,label] of [[report.url,'打开 HTML 预检报告'],[report.json_url,'下载同次 JSON 快照']]){const link=document.createElement('a');link.href=API+url;link.target='_blank';link.rel='noopener';link.textContent=label;$('report-link').appendChild(link)};switchTab('reports')
  }catch(e){if(revision===state.revision)$('status').textContent=`报告保存失败：${e.message}`}
  finally{if(revision===state.revision)$('export').disabled=false}
}
$('export').onclick=exportReport
$('agent').onclick=async()=>{
  if(!$('enable-model').checked||busy||editing)return
  if($('instruction').value.includes('关键')&&!readCritical().length){$('agent-status').textContent='请先指定必须验收的关键目标ID，不由模型猜测。';return}
  invalidate();const revision=state.revision;busy=true;buttons()
  const usage={prompt_tokens:0,completion_tokens:0,total_tokens:0}
  let stage='规划',responses=0
  const account=u=>{responses++;for(const key of Object.keys(usage))usage[key]+=u?.[key]??0}
  const usageText=()=>`已返回${responses}次模型响应；输入${usage.prompt_tokens} / 输出${usage.completion_tokens} / 合计${usage.total_tokens} tokens（未返回请求用量未知）`
  $('agent-status').textContent='正在请求模型规划…'
  try{
    const instruction=$('instruction').value
    const plan=await post('/inspection/workbench/agent-plan',{...project(),instruction,critical_target_ids:readCritical()})
    account(plan.usage)
    $('agent-status').textContent=`规划返回：${plan.tool_name??'追问'}；${usageText()}`
    if(revision!==state.revision)return
    if(plan.kind!=='tool_call'){$('agent-status').textContent=plan.message+'；'+usageText();return}
    stage='本地校验与几何执行'
    const snapshot=await run(plan.tool_name,plan.arguments,'模型规划 + 后台共享JS几何执行')
    if(!snapshot){$('agent-status').textContent=`${stage}未完成；${usageText()}`;return}
    const completedRevision=state.revision
    busy=true;buttons()
    stage='模型结果确认'
    const completion=await post('/inspection/agent/complete',{instruction,tool_call_id:plan.tool_call_id,tool_result:snapshot.result})
    account(completion.usage)
    if(completedRevision!==state.revision)return
    snapshot.agent={tool_name:plan.tool_name,arguments:plan.arguments,usage,model_responses:responses,message:completion.message}
    state.commit(completedRevision,snapshot)
    if(plan.generate_report)await exportReport()
    $('agent-status').textContent=`工具 ${plan.tool_name}；${completion.message}；${usageText()}`
  }catch(e){$('agent-status').textContent=`Agent在${stage}失败：${e.message}；${usageText()}`}finally{busy=false;buttons()}
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
  $('data-status').textContent=`${data.version} · 官方 ${data.buildings.length} / 人工 0 栋 · ${data.targets.length} 模拟目标；加载 ${loadMs.toFixed(1)} ms；1单位=1米`
  $('status').textContent='就绪。青色方案A，橙色方案B。';draw(null);buttons()
}catch(e){data=null;$('status').textContent=`加载失败：${e.message}`}}
const resize=()=>{const box=$('viewport');renderer.setSize(box.clientWidth,box.clientHeight);camera.aspect=box.clientWidth/box.clientHeight;camera.updateProjectionMatrix()}
window.addEventListener('resize',resize);new ResizeObserver(resize).observe($('viewport'));resize()
renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera)})
load()
function switchTab(name){document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==name);document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===name)))}
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>switchTab(b.dataset.tab))
switchTab('project')
const readCritical=()=>$('critical-ids').value.split(',').map(s=>s.trim()).filter(Boolean)
const project=()=>({schema:'geoscene-manual-project-v1',data_version:data.version,coordinate_system:'local_xz_metres',manual_buildings:manual})
const numeric=id=>$(id).value.trim()===''?NaN:Number($(id).value)
function points(){return $('points').value.trim().split('\n').filter(Boolean).map(line=>line.split(',').map(v=>v.trim()===''?NaN:Number(v)))}
function draft(){
  return {id:selected||'manual-'+crypto.randomUUID(),name:$('building-name').value,source:'manual',height_source:'user_input',method:$('method').value,height:numeric('height'),x:numeric('x'),z:numeric('z'),length:numeric('length'),width:numeric('width'),rotation:numeric('rotation'),points:points()}
}
function ringFor(d){if(d.method==='polygon')return d.points;const a=d.rotation*Math.PI/180;return [[-d.length/2,-d.width/2],[d.length/2,-d.width/2],[d.length/2,d.width/2],[-d.length/2,d.width/2]].map(([u,v])=>[d.x+u*Math.cos(a)-v*Math.sin(a),d.z+u*Math.sin(a)+v*Math.cos(a)])}
function disposeGroup(group){for(const child of [...group.children]){group.remove(child);child.traverse(o=>{o.geometry?.dispose();o.material?.dispose()})}}
function previewDraft(){
  editing=true;invalidate();disposeGroup(preview)
  const d=draft(),ring=ringFor(d)
  $('points-label').hidden=d.method!=='polygon'
  for(const id of ['x','z','length','width','rotation'])$(id).disabled=d.method==='polygon'
  $('confirm-building').disabled=d.method==='polygon'&&!closed
  if(!ring.length||ring.length>100||ring.some(p=>p.length!==2||p.some(v=>!Number.isFinite(v)||Math.abs(v)>6000))){$('editor-status').textContent='请输入有效X,Z数值，最多100点，坐标范围以后台校验为准';return}
  const path=ring.map(([x,z])=>new THREE.Vector3(x,.3,z))
  if(d.method==='rectangle'||closed)path.push(path[0])
  preview.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(path),new THREE.LineBasicMaterial({color:0x006dff})))
  if(ring.length>=3&&Number.isFinite(d.height)&&d.height>0){
    try{for(const mesh of buildingMeshes({buildings:[{...d,base:0,polygons:[[ring]]}]})){mesh.material.transparent=true;mesh.material.opacity=.35;mesh.material.depthWrite=false;preview.add(mesh)}}catch{/* Backend validates before commit. */}
  }
  $('editor-status').textContent=(d.method==='polygon'?ring.length+'个点；'+(closed?'已闭合':'未闭合'):'矩形预览')+'。未保存，不参与分析；请确认或取消。'
}
function endEdit(){editing=false;placing=false;closed=false;disposeGroup(preview);$('place').textContent='开启地面选点';$('editor-status').textContent='编辑已结束。只有已确认建筑参与分析。';invalidate();buttons()}
function updateBuildings(){
  obstacles.forEach(o=>{scene.remove(o);o.geometry.dispose();o.material.dispose()})
  obstacles=buildingMeshes({...data,buildings:[...data.buildings,...manual]});obstacles.forEach(o=>scene.add(o))
  $('building-list').replaceChildren(new Option('新建建筑',''),...manual.map(b=>new Option(b.name+' ['+b.id.slice(-6)+']',b.id)))
  $('building-list').value=selected
  $('data-status').textContent=data.version+' · 官方 '+data.buildings.length+' / 人工 '+manual.length+' 栋 · '+data.targets.length+' 模拟目标 · 本地米制'
}
function remember(){history.push(structuredClone(manual));if(history.length>20)history.shift()}
function selectBuilding(id){
  endEdit();selected=id
  const b=manual.find(b=>b.id===id)
  if(!b)return
  for(const [key,value] of Object.entries(b)){if(['height','x','z','length','width','rotation','method'].includes(key))$(key).value=value}
  $('building-name').value=b.name;$('points').value=(b.points??[]).map(p=>p.join(',')).join('\n');closed=b.method==='polygon'
  $('points-label').hidden=b.method!=='polygon';$('building-list').value=id;switchTab('editor')
  for(const key of ['x','z','length','width','rotation'])$(key).disabled=b.method==='polygon'
  $('editor-status').textContent='已选中 '+b.name+'；来源 manual，高度 user_input。修改后须确认保存。'
}
for(const id of ['building-name','height','x','z','length','width','rotation','method','points'])$(id).addEventListener('input',()=>{if(id==='points'||id==='method')closed=false;previewDraft()})
$('place').onclick=()=>{placing=!placing;$('place').textContent=placing?'正在选点（点击停止）':'开启地面选点';if(placing)previewDraft()}
$('close-polygon').onclick=()=>{if(points().length<3){$('editor-status').textContent='至少3个点才能闭合';return}closed=true;previewDraft()}
$('remove-point').onclick=()=>{const p=points();p.pop();$('points').value=p.map(p=>p.join(',')).join('\n');closed=false;previewDraft()}
$('cancel-building').onclick=endEdit
$('new-building').onclick=()=>{endEdit();selected='';$('building-list').value='';$('building-name').value='人工建筑';$('points').value='';previewDraft()}
$('building-list').onchange=()=>selectBuilding($('building-list').value)
$('confirm-building').onclick=async()=>{
  if($('method').value==='polygon'&&!closed){$('editor-status').textContent='请先闭合多边形';return}
  const revision=state.revision,d=draft()
  $('confirm-building').disabled=true
  try{const proposed=manual.filter(b=>b.id!==d.id).concat(d);const valid=await post('/inspection/workbench/project',{...project(),manual_buildings:proposed})
    if(revision!==state.revision)return
    remember();manual=valid.manual_buildings;selected=d.id;endEdit();invalidate();updateBuildings();$('editor-status').textContent='已保存 '+d.name+'，现已进入遮挡障碍物集合。'
  }catch(e){$('editor-status').textContent='保存失败：'+e.message}finally{$('confirm-building').disabled=$('method').value==='polygon'&&!closed&&editing}
}
$('delete-building').onclick=()=>{if(!manual.some(b=>b.id===selected)){$('editor-status').textContent='请先选择人工建筑；官方数据只读';return}remember();manual=manual.filter(b=>b.id!==selected);selected='';endEdit();invalidate();updateBuildings();$('editor-status').textContent='已删除选中建筑，可撤销。'}
$('undo').onclick=()=>{if(!history.length){$('editor-status').textContent='没有可撤销操作';return}manual=history.pop();selected='';endEdit();invalidate();updateBuildings()}
$('save-project').onclick=async()=>{if(editing){$('status').textContent='请先确认或取消未保存的建筑编辑';return}
  const revision=state.revision
  try{const saved=await post('/inspection/workbench/project/export',project());if(revision!==state.revision)return
    const a=document.createElement('a');a.href=API+saved.url;a.textContent='下载已保存的人工建筑项目 JSON';$('project-link').replaceChildren(a);$('status').textContent='项目已保存到本地后台报告目录，可下载后导入恢复。'
  }catch(e){$('status').textContent='项目保存失败：'+e.message}
}
$('load-project').onchange=async e=>{
  const file=e.target.files[0];if(!file)return
  const revision=state.revision
  try{if(file.size>1000000)throw new Error('项目文件不能超过1MB');const parsed=JSON.parse(await file.text());const valid=await post('/inspection/workbench/project',parsed);if(revision!==state.revision)throw new Error('读取期间参数变化，请重新导入');remember();manual=valid.manual_buildings;selected='';endEdit();invalidate();updateBuildings();$('status').textContent='已恢复 '+manual.length+' 栋人工建筑，官方数据未修改'}
  catch(error){$('status').textContent='导入失败：'+error.message}finally{e.target.value=''}
}
const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2(),ground=new THREE.Plane(new THREE.Vector3(0,1,0),0)
let down
function groundPoint(event){const rect=renderer.domElement.getBoundingClientRect();mouse.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(mouse,camera);return raycaster.ray.intersectPlane(ground,new THREE.Vector3())}
renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY])
renderer.domElement.addEventListener('pointermove',e=>{const p=groundPoint(e);if(p)$('pointer-status').textContent='本地坐标 X '+p.x.toFixed(2)+' / Z '+p.z.toFixed(2)+' 米 · 选中 '+(manual.find(b=>b.id===selected)?.name??'无')})
renderer.domElement.addEventListener('pointerup',e=>{
  if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>4)return
  const p=groundPoint(e);if(!p)return
  if(placing){if($('method').value==='rectangle'){$('x').value=p.x.toFixed(2);$('z').value=p.z.toFixed(2)}else{$('points').value+=($('points').value?'\n':'')+p.x.toFixed(2)+','+p.z.toFixed(2);closed=false}previewDraft()}
  else{const hit=raycaster.intersectObjects(obstacles).find(h=>manual.some(b=>b.id===h.object.userData.id));if(hit)selectBuilding(hit.object.userData.id)}
})
window.addEventListener('keydown',e=>{if(e.key==='Escape')endEdit()})
