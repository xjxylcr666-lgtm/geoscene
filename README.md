# GeoScene 第1—7天与首次 Agent 场景分析

## 首版入口（2026-10-08更新）

先阅读 `docs/FIRST-RELEASE.md`：项目定位、3分钟演示顺序、验证结果和限制。
两个启动脚本会自行定位项目，不依赖PowerShell当前目录：

```powershell
& "C:\Users\licr\Documents\Codex\2026-09-24\geoscene-2-3-6-python-json-2\work\threejs-day23\scripts\start-backend.ps1"
```

另开终端：

```powershell
& "C:\Users\licr\Documents\Codex\2026-09-24\geoscene-2-3-6-python-json-2\work\threejs-day23\scripts\start-frontend.ps1"
```

若系统策略禁止脚本，不修改安全策略，使用下方手动cd与启动命令即可。端口已占用时先检查是否已有服务，不重复启动、不盲目结束其他进程。

## 2026-10-06：真实建筑巡检工作包

新增入口：http://127.0.0.1:5173/inspection.html 。原首页与模拟场景保留。
54条纽约官方建筑轮廓真正进入障碍物集合；12个模拟目标支持批量分析、A/B观察方案比较和同次截图HTML报告。
所有建筑高度暂假设10米、地面0米，不是实测三维城市；仅计算目标点可见性，不计算建筑可见面积。
数据来源、坐标转换及加工限制见 `public/data/buildings/README.md`。

新环境先执行 `python -m venv .venv`，再安装下方依赖。普通分析和报告不需要模型密钥。
仅需要真实模型调用时才自行配置密钥，不能将密钥发进聊天；新巡检Agent默认关闭。2026-10-08已完成真实双方案比较、缺参追问、无效目标拒绝；其余自动化使用测试替身，不混作真实调用。
前端建议固定端口：`npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`。

新增关键文件：

- `backend/building_adapter.py`：离线投影与数据质量处理。
- `src/visibility.js`：原、新场景共用的几何计算，不维护第二套算法。
- `src/inspection-core.js`：建筑拉伸、批量分析、方案比较与结果版本。
- `src/inspection.js`：真实页面、后台校验、失效处理、同次截图。
- `backend/inspection.py`：巡检Agent协议和HTML/JSON报告保存。

验证命令（均不调用收费模型）：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm test
npm run build
npm run benchmark
```

离线重新转换：`.\.venv\Scripts\python.exe -m backend.building_adapter`。
`scripts/fetch_buildings.py` 是有界联网获取脚本，已有原始数据时拒绝覆盖，不需要为正常启动重复下载。
工具包括 `analyze_batch(target_ids, scheme_id)` 和 `compare_observers(target_ids)`；前端执行实际几何，Python不重新计算射线。
新增接口为 `/inspection/agent/plan`、`/inspection/agent/complete`、`/inspection/reports`（POST）。
报告保存在本次工作目录旁的 `2026-09-28/geoscene-130-6-7-python-http/outputs/inspection-reports`；迁移机器时需调整 `backend/inspection.py` 的 REPORTS 路径。
本地接口没有身份认证，绑定127.0.0.1；不要直接开放公网。后端字段一致性检查不等于对不可信浏览器的防篡改认证。

## 首次安装

打开 PowerShell：

```powershell
cd C:\Users\licr\Documents\Codex\2026-09-24\geoscene-2-3-6-python-json-2\work\threejs-day23
npm install
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

普通校验与几何分析无需密钥。需要Agent时，在本机 `.env` 中配置 `DEEPSEEK_API_KEY`，可选 `DEEPSEEK_MODEL=deepseek-flash` 和 `DEEPSEEK_BASE_URL=https://api.deepseek.com`。自行输入实际密钥，不通过聊天传递。
真实 `.env` 已被 `.gitignore` 排除，不能提交或发到聊天中。

## 启动

终端一（后端）：

```powershell
cd C:\Users\licr\Documents\Codex\2026-09-24\geoscene-2-3-6-python-json-2\work\threejs-day23
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

终端二（前端）：

```powershell
cd C:\Users\licr\Documents\Codex\2026-09-24\geoscene-2-3-6-python-json-2\work\threejs-day23
npm run dev
```

页面地址为 `http://127.0.0.1:5173/`，接口文档为
`http://127.0.0.1:8000/docs`。按 `Ctrl + C` 停止对应服务。

## 主要文件

- `src/scene-config.json`：场景对象、观察点、目标和墙的配置。
- `src/main.js`：创建场景、执行可见性检查、处理按钮与展示结果。
- `src/style.css`：全屏画布样式。
- `backend/validation.py`：复用的目标配置校验函数。
- `backend/scene_validation.py`：整份场景的对象类型、ID、位置、尺寸和观察参数校验。
- `backend/agent_service.py`：DeepSeek 工具选择与工具结果回传。
- `backend/geojson_adapter.py`：把 USGS GeoJSON 地震点转换为场景目标。
- `backend/main.py`：校验接口和 Agent 接口。
- `backend/tests/`：校验、Agent 协议和 HTTP 接口测试。
- `public/data/usgs-earthquakes-2025-01-01-to-07.geojson`：官方公开数据的稳定离线快照。

## 使用“检查当前观察点”

1. 在右上角输入目标 ID，例如 `target-1`。
2. 点击“检查当前观察点”。
3. 页面显示实际计算结果，并用绿色或红色视线表示可见或不可见。
4. 输入不存在的 ID 会显示明确错误。
5. 修改输入或保存场景配置后，旧结果会被清除或重置，需重新点击检查。

## 当前检查顺序

1. 最大距离。
2. 目标中心与观察方向的夹角是否超过 `fov / 2`。
3. 观察点到目标的射线是否先碰到 `obstacles` 中的墙。

目标存入 `targets`，墙存入 `obstacles`，因此目标自身不会被误判为遮挡物。

## Agent 分析流程

1. 页面把自然语言指令和当前目标 ID 列表发送到 `POST /agent/plan`。
2. DeepSeek 在两个工具中选择：`list_scene_targets()` 读取运行时目标列表，或
   `analyze_visibility(target_id)` 请求指定目标的可见性分析。
3. 列表工具直接遍历浏览器当前加载的 `targets`，不由模型编写列表。
4. 可见性工具先用目标的普通 JSON 数据调用 `POST /validate-target`。
5. 校验通过后，浏览器执行现有 `checkVisibility` JavaScript 几何函数。
6. 页面把带有可信 `source` 标记的真实结果发送到
   `POST /agent/complete`。
7. 后端使用工具结果生成受保护的最终结论，模型文字不能覆盖目标列表或几何字段。
8. 页面同时显示本轮 Agent 规划和结果确认消耗的总 token 数。
9. 组合指令可以先列出目标，再按真实名称选择 ID 并执行可见性分析；网页最多允许
   3 步工具调用，防止无限循环。

当前 Agent 能分析已加载场景中目标的可见性。它不能新增场景对象、读取真实地图、
访问数据库，也没有把 Three.js 几何算法迁移到 Python。

## USGS 公开数据演示

点击“加载 USGS 公开地震演示”后，网页读取项目内的 GeoJSON 快照，通过
`POST /geojson/earthquakes-to-targets` 转为 8 个运行时目标，再用
`POST /validate-scene` 校验整份场景。输入框会提供目标 ID 候选，选中目标时显示震级、
经纬度、深度和 USGS 事件链接。Agent 的列表和可见性工具会读取切换后的真实运行时目标，
不是固定演示回答。

快照来自 [USGS Earthquake Catalog API](https://earthquake.usgs.gov/fdsnws/event/1/1)：

```text
2025-01-01 至 2025-01-08，M>=5，按震级排序，最多8条
```

经纬度会归一化到本地 Three.js 平面，目的是演示数据适配与真实工具执行。因此页面中的
距离和遮挡属于本地演示场景，不代表地球表面距离或真实地形遮挡。点击“恢复内置演示场景”
可回到原来的三个教学目标。

当前演示目标：

- `target-1`：位于观察方向侧面，用于验证“视野外”。
- `target-2`：位于正前方、墙体之前，用于验证“目标可见”。
- `target-3`：位于正前方、墙体之后，用于验证“被测试墙遮挡”。

健康检查：`GET http://127.0.0.1:8000/health`。它只报告服务、模型名称和密钥是否
已配置，不会返回密钥内容。

整场景校验：`POST http://127.0.0.1:8000/validate-scene`。请求体是完整场景对象数组，
响应包含 `valid`、`errors` 和各对象类型的 `counts`。网页上的“校验当前完整场景”
按钮已接入此接口；USGS 演示会动态替换目标，但尚未提供任意文件上传。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm run build
```

## 当前保留场景

观察点为 `(-5, 1, 0)`，朝 `+x`，最大距离为 12，视野角为 90°。
