import * as THREE from 'three'
import './style.css'
import { checkVisibility } from './visibility.js'
import { createEnvironment } from './environment.js'
import jsonSceneObjects from './scene-config.json'

const builtInSceneConfig = JSON.parse(JSON.stringify(jsonSceneObjects))
let currentSceneConfig = JSON.parse(JSON.stringify(jsonSceneObjects))
let activeCoordinateMode = 'local_cartesian'
// 1. 场景：存放所有三维对象
const scene = new THREE.Scene()
scene.background = new THREE.Color(0xbfdcff)
// 2. 相机：决定我们从哪里观看
const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  100
)
camera.position.set(7, 6, 9)
camera.lookAt(0, 0, 0)

// 3. 渲染器：把三维场景画到网页上
const renderer = new THREE.WebGLRenderer({ antialias: true })
renderer.setSize(window.innerWidth, window.innerHeight)
renderer.setPixelRatio(window.devicePixelRatio)
renderer.shadowMap.enabled = true
document.querySelector('#app').appendChild(renderer.domElement)
const environment = createEnvironment(scene, camera, renderer)
const sceneHeading = document.createElement('div')
sceneHeading.className = 'scene-heading'
sceneHeading.innerHTML = '<span>GEOSCENE / SPATIAL INTELLIGENCE</span><h1>山湖观测站</h1><p>ALPINE RESEARCH CAMPUS · 3D WORKSPACE</p>'
document.body.appendChild(sceneHeading)
const sceneFooter = document.createElement('div')
sceneFooter.className = 'scene-footer'
sceneFooter.textContent = '拖动旋转 · 滚轮缩放 · 右键平移 ｜ 示意环境，不参与遮挡计算'
document.body.appendChild(sceneFooter)

// 检查工具界面：读取目标 ID，并执行本地可见性检查
const toolPanel = document.createElement('div')
toolPanel.className = 'tool-panel'
toolPanel.style.position = 'fixed'
toolPanel.style.top = '16px'
toolPanel.style.right = '16px'
toolPanel.style.padding = '12px'
toolPanel.style.borderRadius = '8px'
toolPanel.style.background = 'rgba(0, 0, 0, 0.72)'
toolPanel.style.color = '#ffffff'
toolPanel.style.fontFamily = 'sans-serif'
toolPanel.style.zIndex = '20'
toolPanel.style.maxHeight = 'calc(100vh - 32px)'
toolPanel.style.overflowY = 'auto'

const panelTitle = document.createElement('div')
panelTitle.textContent = 'GeoScene Agent 场景分析'
panelTitle.style.fontSize = '17px'
panelTitle.style.fontWeight = '700'
panelTitle.style.marginBottom = '4px'

const panelSubtitle = document.createElement('div')
panelSubtitle.textContent = 'Python校验 · Three.js几何 · DeepSeek工具调用'
panelSubtitle.style.fontSize = '12px'
panelSubtitle.style.color = '#b9dfff'
panelSubtitle.style.marginBottom = '10px'

const targetIdInput = document.createElement('input')
targetIdInput.value = 'target-1'
targetIdInput.placeholder = '目标 ID'
targetIdInput.setAttribute('list', 'target-id-options')

const targetIdOptions = document.createElement('datalist')
targetIdOptions.id = 'target-id-options'

const checkButton = document.createElement('button')
checkButton.textContent = '检查当前观察点'
checkButton.style.marginLeft = '8px'
const resetViewButton = document.createElement('button')
resetViewButton.textContent = '重置视角'
resetViewButton.addEventListener('click', environment.reset)

const toolMessage = document.createElement('div')
toolMessage.style.marginTop = '8px'
toolMessage.textContent = '尚未检查'

const targetDetails = document.createElement('div')
targetDetails.style.marginTop = '6px'
targetDetails.style.maxWidth = '390px'
targetDetails.style.fontSize = '12px'
targetDetails.style.color = '#d6eaff'

const agentInstructionInput = document.createElement('input')
agentInstructionInput.value = '分析 target-1 的可见性'
agentInstructionInput.placeholder = '向Agent下达场景分析指令'
agentInstructionInput.style.display = 'block'
agentInstructionInput.style.width = '100%'
agentInstructionInput.style.marginTop = '12px'

const agentButton = document.createElement('button')
agentButton.textContent = '让 Agent 分析'
agentButton.style.marginTop = '8px'

const agentMessage = document.createElement('div')
agentMessage.style.marginTop = '8px'
agentMessage.style.maxWidth = '360px'
agentMessage.textContent = 'Agent 尚未运行'

const agentUsage = document.createElement('div')
agentUsage.style.marginTop = '6px'
agentUsage.style.fontSize = '12px'
agentUsage.style.color = '#cccccc'
agentUsage.textContent = '模型用量：尚无'

const sceneValidationButton = document.createElement('button')
sceneValidationButton.textContent = '校验当前完整场景'
sceneValidationButton.style.display = 'block'
sceneValidationButton.style.marginTop = '12px'

const sceneValidationMessage = document.createElement('div')
sceneValidationMessage.style.marginTop = '8px'
sceneValidationMessage.textContent = '尚未校验完整场景'

const publicDataButton = document.createElement('button')
publicDataButton.textContent = '加载 USGS 公开地震演示'
publicDataButton.style.display = 'block'
publicDataButton.style.marginTop = '12px'

const restoreDemoButton = document.createElement('button')
restoreDemoButton.textContent = '恢复内置演示场景'
restoreDemoButton.style.marginTop = '8px'
restoreDemoButton.style.marginLeft = '8px'

const publicDataMessage = document.createElement('div')
publicDataMessage.style.marginTop = '8px'
publicDataMessage.style.maxWidth = '390px'
publicDataMessage.textContent = '数据模式：内置本地演示'

const publicDataSource = document.createElement('a')
publicDataSource.href = 'https://earthquake.usgs.gov/fdsnws/event/1/'
publicDataSource.target = '_blank'
publicDataSource.rel = 'noreferrer'
publicDataSource.textContent = '数据来源：USGS Earthquake Catalog API'
publicDataSource.style.display = 'block'
publicDataSource.style.marginTop = '6px'
publicDataSource.style.color = '#9fd8ff'

const publicDataLegend = document.createElement('div')
publicDataLegend.style.display = 'none'
publicDataLegend.style.marginTop = '6px'
publicDataLegend.style.fontSize = '12px'
publicDataLegend.textContent = '图例：🔴 M≥7　🟠 M≥6　🟡 M≥5；柱高随震级增大'

const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const validationApiUrl = apiBase + '/validate-target'
const sceneValidationApiUrl = apiBase + '/validate-scene'
const earthquakeAdapterApiUrl = apiBase + '/geojson/earthquakes-to-targets'
const agentPlanApiUrl = apiBase + '/agent/plan'
const agentCompleteApiUrl = apiBase + '/agent/complete'
let visibilityLine = null
let requestVersion = 0

function friendlyRequestError(error) {
  if (error instanceof TypeError && error.message === 'Failed to fetch') {
    return '无法连接本地后台，请确认 8000 端口服务已启动'
  }
  return error.message
}

function usageTotal(...usages) {
  return usages.reduce(
    (total, usage) => total + (usage?.total_tokens ?? 0),
    0
  )
}

toolPanel.append(
  panelTitle,
  panelSubtitle,
  resetViewButton,
  targetIdInput,
  targetIdOptions,
  checkButton,
  toolMessage,
  targetDetails,
  agentInstructionInput,
  agentButton,
  agentMessage,
  agentUsage,
  sceneValidationButton,
  sceneValidationMessage,
  publicDataButton,
  restoreDemoButton,
  publicDataMessage,
  publicDataSource,
  publicDataLegend
)
document.body.appendChild(toolPanel)
const inspectionLink = document.createElement('a')
inspectionLink.href = '/inspection.html'
inspectionLink.textContent = '进入真实建筑巡检 / 批量与方案比较 →'
inspectionLink.style.display = 'block'
inspectionLink.style.marginTop = '12px'
toolPanel.prepend(inspectionLink)

sceneValidationButton.addEventListener('click', async () => {
  sceneValidationButton.disabled = true
  sceneValidationMessage.style.color = '#9fd8ff'
  sceneValidationMessage.textContent = '正在校验完整场景配置...'

  try {
    const response = await fetch(sceneValidationApiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentSceneConfig),
    })
    if (!response.ok) {
      throw new Error(`整场景校验接口返回 HTTP ${response.status}`)
    }

    const validation = await response.json()
    if (!validation.valid) {
      sceneValidationMessage.style.color = '#ff8b8b'
      sceneValidationMessage.textContent = `场景配置无效：${validation.errors.join('；')}`
      return
    }

    const counts = validation.counts
    sceneValidationMessage.style.color = '#7cff9b'
    sceneValidationMessage.textContent = [
      '场景配置有效',
      `方块 ${counts.box ?? 0}`,
      `观察点 ${counts.observer ?? 0}`,
      `目标 ${counts.target ?? 0}`,
      `墙 ${counts.wall ?? 0}`,
    ].join('；')
  } catch (error) {
    sceneValidationMessage.style.color = '#ff8b8b'
    sceneValidationMessage.textContent = `场景校验失败：${friendlyRequestError(error)}`
  } finally {
    sceneValidationButton.disabled = false
  }
})

publicDataButton.addEventListener('click', async () => {
  publicDataButton.disabled = true
  restoreDemoButton.disabled = true
  publicDataMessage.style.color = '#9fd8ff'
  publicDataMessage.textContent = '正在读取USGS离线GeoJSON并转换场景目标...'

  try {
    const sourceResponse = await fetch(
      '/data/usgs-earthquakes-2025-01-01-to-07.geojson'
    )
    if (!sourceResponse.ok) {
      throw new Error(`公开数据文件返回 HTTP ${sourceResponse.status}`)
    }
    const geojson = await sourceResponse.json()

    const adapterResponse = await fetch(earthquakeAdapterApiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(geojson),
    })
    if (!adapterResponse.ok) {
      throw new Error(`GeoJSON转换接口返回 HTTP ${adapterResponse.status}`)
    }
    const converted = await adapterResponse.json()
    const candidateScene = [
      ...builtInSceneConfig.filter((item) => item.type !== 'target'),
      ...converted.targets,
    ]

    const validationResponse = await fetch(sceneValidationApiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(candidateScene),
    })
    if (!validationResponse.ok) {
      throw new Error(`整场景校验接口返回 HTTP ${validationResponse.status}`)
    }
    const validation = await validationResponse.json()
    if (!validation.valid) {
      throw new Error(`转换后的场景无效：${validation.errors.join('；')}`)
    }

    replaceSceneTargets(
      converted.targets,
      candidateScene,
      'normalized_geographic_demo'
    )
    publicDataMessage.style.color = '#7cff9b'
    publicDataMessage.textContent = [
      `已加载 ${converted.metadata.count} 条USGS地震记录`,
      '震级决定柱体高度和颜色',
      '经纬度已归一化为本地演示坐标',
      '场景距离不代表真实地理距离',
    ].join('；')
    publicDataLegend.style.display = 'block'
    boxes.forEach((box) => {
      box.visible = false
    })
  } catch (error) {
    publicDataMessage.style.color = '#ff8b8b'
    publicDataMessage.textContent = `公开数据加载失败：${friendlyRequestError(error)}`
  } finally {
    publicDataButton.disabled = false
    restoreDemoButton.disabled = false
  }
})

restoreDemoButton.addEventListener('click', () => {
  const restoredScene = JSON.parse(JSON.stringify(builtInSceneConfig))
  const restoredTargets = restoredScene.filter((item) => item.type === 'target')
  replaceSceneTargets(restoredTargets, restoredScene, 'local_cartesian')
  publicDataMessage.style.color = '#ffffff'
  publicDataMessage.textContent = '数据模式：内置本地演示'
  publicDataLegend.style.display = 'none'
  boxes.forEach((box) => {
    box.visible = true
  })
})

async function runVisibilityTool(targetId, currentRequestVersion) {
  const target = targets.find(
    (item) => item.userData.id === targetId
  )

  if (!target) {
    throw new Error(`未找到目标 ID "${targetId}"`)
  }

  clearVisibilityLine()
  toolMessage.style.color = '#9fd8ff'
  toolMessage.textContent = '正在请求 Python 校验...'

  const targetData = {
    name: target.name,
    position: {
      x: target.position.x,
      y: target.position.y,
      z: target.position.z,
    },
  }

  const response = await fetch(validationApiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(targetData),
  })

  if (currentRequestVersion !== requestVersion) {
    throw new Error('请求已被新的操作取代')
  }
  if (!response.ok) {
    throw new Error(`校验接口返回 HTTP ${response.status}`)
  }

  const validation = await response.json()
  if (!validation.valid) {
    throw new Error(`配置校验失败：${validation.errors.join('；')}`)
  }
  if (!observer || !observerConfig) {
    throw new Error('缺少观察点或观察点配置')
  }

  scene.updateMatrixWorld(true)
  const result = checkVisibility(
    observer,
    observerConfig,
    target,
    obstacles
  )
  showVisibilityResult(result, observer, target)

  return {
    source: 'geoscene_visibility_tool',
    target_id: targetId,
    visible: result.visible,
    reason: result.reason,
    distance: result.distance,
    angle: result.angle ?? null,
    coordinate_mode: activeCoordinateMode,
  }
}

function runTargetListTool() {
  clearVisibilityLine()
  const targetList = targets.map((target) => ({
    id: target.userData.id,
    name: target.name,
    position: {
      x: target.position.x,
      y: target.position.y,
      z: target.position.z,
    },
  }))

  toolMessage.style.color = '#7cff9b'
  toolMessage.textContent = `已从当前场景读取 ${targetList.length} 个目标`
  return {
    source: 'geoscene_target_list_tool',
    targets: targetList,
  }
}

async function executeAgentTool(plan, currentRequestVersion) {
  if (plan.tool_name === 'analyze_visibility') {
    return runVisibilityTool(
      plan.arguments.target_id,
      currentRequestVersion
    )
  }
  if (plan.tool_name === 'list_scene_targets') {
    return runTargetListTool()
  }
  throw new Error(`不支持的工具：${plan.tool_name}`)
}

checkButton.addEventListener('click', async () => {
  const currentRequestVersion = ++requestVersion
  const targetId = targetIdInput.value.trim()
  checkButton.disabled = true

  try {
    await runVisibilityTool(targetId, currentRequestVersion)
  } catch (error) {
    if (currentRequestVersion !== requestVersion) return
    clearVisibilityLine()
    toolMessage.style.color = '#ff8b8b'
    toolMessage.textContent = `检查失败：${friendlyRequestError(error)}`
  } finally {
    if (currentRequestVersion === requestVersion) {
      checkButton.disabled = false
    }
  }
})

agentButton.addEventListener('click', async () => {
  const currentRequestVersion = ++requestVersion
  const instruction = agentInstructionInput.value.trim()
  checkButton.disabled = true
  agentButton.disabled = true
  clearVisibilityLine()
  toolMessage.style.color = '#ffd166'
  toolMessage.textContent = '等待 Agent 选择工具...'
  agentMessage.style.color = '#9fd8ff'
  agentMessage.textContent = '正在请求 DeepSeek 制定工具调用...'

  try {
    const planResponse = await fetch(agentPlanApiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instruction,
        available_target_ids: targets.map((item) => item.userData.id),
      }),
    })
    if (currentRequestVersion !== requestVersion) return
    if (!planResponse.ok) {
      throw new Error(`Agent规划接口返回 HTTP ${planResponse.status}`)
    }

    const plan = await planResponse.json()
    if (plan.kind === 'message') {
      toolMessage.textContent = '未执行场景工具'
      agentMessage.style.color = '#ffd166'
      agentMessage.textContent = plan.message
      agentUsage.textContent = `模型用量：${usageTotal(plan.usage)} tokens`
      return
    }
    if (plan.kind !== 'tool_call') {
      throw new Error(plan.message || 'Agent未生成可执行的工具调用')
    }

    let currentPlan = plan
    let totalTokens = usageTotal(plan.usage)
    const executedTools = []

    for (let step = 1; step <= 3; step += 1) {
      agentMessage.textContent = `第 ${step} 步工具：${currentPlan.tool_name}(${JSON.stringify(
        currentPlan.arguments
      )})`
      executedTools.push(currentPlan.tool_name)
      const toolResult = await executeAgentTool(
        currentPlan,
        currentRequestVersion
      )

      agentMessage.textContent = '真实工具结果已生成，正在交回模型确认...'
      const completeResponse = await fetch(agentCompleteApiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          instruction,
          tool_call_id: currentPlan.tool_call_id,
          tool_name: currentPlan.tool_name,
          arguments: currentPlan.arguments,
          tool_result: toolResult,
        }),
      })
      if (currentRequestVersion !== requestVersion) return
      if (!completeResponse.ok) {
        throw new Error(`Agent结果接口返回 HTTP ${completeResponse.status}`)
      }

      const completion = await completeResponse.json()
      totalTokens += usageTotal(completion.usage)
      if (completion.kind === 'tool_call') {
        currentPlan = completion
        continue
      }

      agentMessage.style.color = '#7cff9b'
      agentMessage.textContent = completion.message
      agentUsage.textContent = `模型用量：${totalTokens} tokens；工具链：${executedTools.join(
        ' → '
      )}`
      return
    }

    throw new Error('Agent工具调用超过3步安全上限')
  } catch (error) {
    if (currentRequestVersion !== requestVersion) return
    agentMessage.style.color = '#ff8b8b'
    agentMessage.textContent = `Agent执行失败：${friendlyRequestError(error)}`
    if (!visibilityLine) {
      clearVisibilityLine()
      toolMessage.style.color = '#ff8b8b'
      toolMessage.textContent = '未获得新的场景分析结果'
    }
  } finally {
    if (currentRequestVersion === requestVersion) {
      checkButton.disabled = false
      agentButton.disabled = false
    }
  }
})

targetIdInput.addEventListener('input', () => {
  requestVersion += 1
  checkButton.disabled = false
  agentButton.disabled = false
  clearVisibilityLine()
  toolMessage.style.color = '#ffd166'
  toolMessage.textContent = '参数已修改，请重新检查'
  updateTargetDetails()
})

agentInstructionInput.addEventListener('input', () => {
  requestVersion += 1
  checkButton.disabled = false
  agentButton.disabled = false
  clearVisibilityLine()
  toolMessage.style.color = '#ffd166'
  toolMessage.textContent = 'Agent指令已修改，旧结果已失效'
  agentMessage.style.color = '#ffd166'
  agentMessage.textContent = '请重新运行Agent'
  agentUsage.textContent = '模型用量：旧记录已失效'
})

// 灯光
const ambientLight = new THREE.HemisphereLight(0xdbeaf1, 0x50614c, 2)
scene.add(ambientLight)

const sunLight = new THREE.DirectionalLight(0xffe3b0, 3)
sunLight.position.set(-12, 25, 12)
sunLight.castShadow = true
sunLight.shadow.mapSize.set(2048, 2048)
sunLight.shadow.camera.left = -35
sunLight.shadow.camera.right = 35
sunLight.shadow.camera.top = 35
sunLight.shadow.camera.bottom = -35
sunLight.shadow.camera.far = 90
sunLight.shadow.normalBias = 0.04
scene.add(sunLight)

// 地面
const groundGeometry = new THREE.PlaneGeometry(12, 8)
const groundMaterial = new THREE.MeshStandardMaterial({
  color: 0xaab8b1,
  roughness: 0.95
})
const ground = new THREE.Mesh(groundGeometry, groundMaterial)
ground.rotation.x = -Math.PI / 2
ground.receiveShadow = true
ground.position.y = -0.015
scene.add(ground)

// 创建方块的函数
function createMagnitudeLabel(magnitude, height) {
  const canvas = document.createElement('canvas')
  canvas.width = 160
  canvas.height = 48
  const context = canvas.getContext('2d')
  context.fillStyle = 'rgba(8, 18, 30, 0.82)'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.strokeStyle = '#ffffff'
  context.lineWidth = 2
  context.strokeRect(2, 2, canvas.width - 4, canvas.height - 4)
  context.fillStyle = '#ffffff'
  context.font = 'bold 27px sans-serif'
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillText(`M${magnitude.toFixed(1)}`, canvas.width / 2, canvas.height / 2)

  const texture = new THREE.CanvasTexture(canvas)
  texture.colorSpace = THREE.SRGBColorSpace
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: true,
  })
  const sprite = new THREE.Sprite(material)
  sprite.scale.set(1.05, 0.32, 1)
  sprite.position.set(0, height / 2 + 0.3, 0)
  sprite.renderOrder = 10
  return sprite
}

function createBox(config) {
  const geometry = new THREE.BoxGeometry(
    config.size.width,
    config.size.height,
    config.size.depth
  )

  const material = new THREE.MeshStandardMaterial({
    color: config.type === 'box' ? '#77969a' : config.type === 'wall' ? '#52646a' : config.color,
    roughness: 0.42,
    metalness: 0.18,
  })

  const box = new THREE.Mesh(geometry, material)

  box.position.set(
    config.position.x,
    config.position.y,
    config.position.z
  )

  box.name = config.name
  box.userData.id = config.id
  box.userData.type = config.type
  box.userData.sourceData = config.sourceData ?? null
  if (config.sourceData?.magnitude >= 6) {
    box.add(createMagnitudeLabel(config.sourceData.magnitude, config.size.height))
  }
  box.castShadow = true
  box.receiveShadow = true
  scene.add(box)

  return box

}

// 创建观察点：球体表示位置，箭头表示观察方向
function createObserver(config) {
  const observer = new THREE.Group()
  observer.position.set(
    config.position.x,
    config.position.y,
    config.position.z
  )
  observer.name = config.name
  observer.userData.id = config.id

  const marker = new THREE.Mesh(
    new THREE.SphereGeometry(0.25, 24, 16),
    new THREE.MeshStandardMaterial({ color: 0xffffff })
  )
  marker.castShadow = true
  observer.add(marker)

  const direction = new THREE.Vector3(
    config.direction.x,
    config.direction.y,
    config.direction.z
  ).normalize()
  const arrow = new THREE.ArrowHelper(
    direction,
    new THREE.Vector3(0, 0, 0),
    2,
    0xffaa00
  )
  observer.add(arrow)
  scene.add(observer)

  return observer
}

// 根据 JSON 配置创建方块
const boxes = []
const targets = []
const obstacles = []
let observer = null

for (const config of currentSceneConfig) {
  if (config.type === 'box') {
    boxes.push(createBox(config))
  } else if (config.type === 'target') {
    targets.push(createBox(config))
  } else if (config.type === 'wall') {
    obstacles.push(createBox(config))
  } else if (config.type === 'observer') {
    observer = createObserver(config)
  }
}
updateTargetOptions()
updateTargetDetails()

function disposeSceneObject(object) {
  scene.remove(object)
  object.traverse((child) => {
    child.geometry?.dispose()
    const materials = Array.isArray(child.material)
      ? child.material
      : [child.material]
    for (const material of materials) {
      material?.map?.dispose()
      material?.dispose()
    }
  })
}

function replaceSceneTargets(targetConfigs, sceneConfig, coordinateMode) {
  requestVersion += 1
  clearVisibilityLine()
  for (const target of targets) {
    disposeSceneObject(target)
  }
  targets.length = 0
  for (const config of targetConfigs) {
    targets.push(createBox(config))
  }

  currentSceneConfig = JSON.parse(JSON.stringify(sceneConfig))
  activeCoordinateMode = coordinateMode
  const firstTargetId = targets[0]?.userData.id ?? ''
  targetIdInput.value = firstTargetId
  updateTargetOptions()
  updateTargetDetails()
  agentInstructionInput.value = '当前场景有哪些目标'
  toolMessage.style.color = '#ffd166'
  toolMessage.textContent = '场景数据已切换，请重新检查'
  agentMessage.style.color = '#ffd166'
  agentMessage.textContent = '场景数据已切换，请重新运行Agent'
  agentUsage.textContent = '模型用量：尚无'
  sceneValidationMessage.style.color = '#ffd166'
  sceneValidationMessage.textContent = '新场景已通过校验'
}

function updateTargetOptions() {
  targetIdOptions.replaceChildren()
  for (const config of currentSceneConfig.filter((item) => item.type === 'target')) {
    const option = document.createElement('option')
    option.value = config.id
    option.label = config.name
    targetIdOptions.appendChild(option)
  }
}

function updateTargetDetails() {
  const targetId = targetIdInput.value.trim()
  const config = currentSceneConfig.find(
    (item) => item.type === 'target' && item.id === targetId
  )
  targetDetails.replaceChildren()
  if (!config) {
    targetDetails.textContent = targetId
      ? '当前 ID 不在场景目标列表中'
      : '请选择一个目标'
    return
  }

  const source = config.sourceData
  if (!source) {
    targetDetails.textContent = `${config.name}；本地坐标 (${config.position.x}, ${config.position.y}, ${config.position.z})`
    return
  }

  const summary = document.createElement('span')
  summary.textContent = [
    `${config.name}；M${source.magnitude.toFixed(1)}`,
    `经度 ${source.longitude.toFixed(2)}`,
    `纬度 ${source.latitude.toFixed(2)}`,
    `深度 ${source.depthKm.toFixed(1)} km`,
  ].join('；')
  targetDetails.appendChild(summary)
  if (source.url) {
    const link = document.createElement('a')
    link.href = source.url
    link.target = '_blank'
    link.rel = 'noreferrer'
    link.textContent = '查看 USGS 事件'
    link.style.display = 'block'
    link.style.marginTop = '3px'
    link.style.color = '#9fd8ff'
    targetDetails.appendChild(link)
  }
}

function clearVisibilityLine() {
  if (!visibilityLine) return

  scene.remove(visibilityLine)
  visibilityLine.geometry.dispose()
  visibilityLine.material.dispose()
  visibilityLine = null
}

function showVisibilityResult(result, observerObject, target) {
  clearVisibilityLine()

  toolMessage.style.color = result.visible ? '#7cff9b' : '#ff8b8b'
  toolMessage.textContent = `${result.visible ? '可见' : '不可见'}：${result.reason}`

  const lineGeometry = new THREE.BufferGeometry().setFromPoints([
    observerObject.position.clone(),
    target.position.clone(),
  ])
  const lineMaterial = new THREE.LineBasicMaterial({
    color: result.visible ? 0x33ff66 : 0xff3333,
  })
  visibilityLine = new THREE.Line(lineGeometry, lineMaterial)
  scene.add(visibilityLine)
}

const observerConfig = jsonSceneObjects.find(
  (config) => config.type === 'observer'
)

// 持续绘制画面
function animate() {
  environment.update()
  renderer.render(scene, camera)
}

renderer.setAnimationLoop(animate)

// 浏览器窗口改变时保持画面比例
function resizeViewport() {
  const viewport = document.querySelector('#app')
  camera.aspect = viewport.clientWidth / viewport.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(viewport.clientWidth, viewport.clientHeight)
}
window.addEventListener('resize', resizeViewport)
resizeViewport()
