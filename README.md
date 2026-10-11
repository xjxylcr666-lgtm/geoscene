# GeoScene 0.1.0

基于真实公开建筑轮廓的**目标点可见性分析原型**。Python校验数据，浏览器JavaScript/Three.js计算几何；可选DeepSeek Agent选择工具，不替代几何计算。

54条真实纽约建筑轮廓、12个模拟目标；全部建筑高度假设10米、地面为平地，观察方案为模拟。不是实测三维城市、机器人导航或商业成熟平台。

## 安装（Windows PowerShell）

在包含package.json的项目根目录打开终端。首次安装：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm ci
```

需预先安装Python、Node.js/npm。实际测试版本和环境边界见[验收记录](docs/RELEASE-VERIFICATION.md)。npm使用package-lock.json；Python为版本范围，未来可能解析出不同版本。

## 最短启动

两个终端都进入项目根目录。终端一：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

终端二：

```powershell
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

- **巡检入口**：http://127.0.0.1:5173/inspection.html
- 旧模拟/USGS演示：http://127.0.0.1:5173/
- API文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

也可分别运行scripts/start-backend.ps1和scripts/start-frontend.ps1，脚本自动定位项目。若策略禁止脚本，使用上方手动命令，不关闭安全策略。保持两个终端运行；Ctrl+C停止对应服务。端口占用先核对进程归属，不盲目结束进程。

## 报告保存与迁移

默认保存到**当前项目根目录下outputs/inspection-reports/**，自动创建。每次生成独立HTML和同名JSON快照，不依赖启动工作目录或旧任务路径。

可在启动后端前指定环境变量：

```powershell
$env:GEOSCENE_REPORT_DIR = 'outputs/my-reports'
```

支持绝对路径；相对路径始终相对于项目根目录。重启后端生效；空值或未设置使用默认目录。目录不可写返回503及检查提示。自定义目录若放在项目其他位置，需自行添加忽略规则。

旧任务目录中的报告**未删除、未移动**。需要通过接口访问旧报告时，可明确配置其目录；系统不自动搜索或迁移。项目outputs已被Git忽略。docs/example-agent-report.html和同名JSON是刻意保留的历史示例，不随当前运行更新。

## 普通分析与Agent

普通分析、比较、报告导出无需.env和模型账户，不收费。
巡检工具：analyze_batch(target_ids, scheme_id)、compare_observers(target_ids)。
流程：目标选择→Python校验→浏览器共用几何→结果与同次截图→保存报告。

只有启用真实Agent才在本机.env配置DEEPSEEK_API_KEY，可选DEEPSEEK_MODEL、DEEPSEEK_BASE_URL。密钥不要发聊天或提交Git。Agent复选框默认关闭，启用后API单独计费。
2026-10-08有真实比较、缺参追问和非法对象处理样例；本次交付不新增付费调用。无多轮记忆，追问后重新提交完整指令。

## 独立复现端口

默认保持8000/5173。若同时运行另一个副本，后端终端：

```powershell
$env:GEOSCENE_ALLOWED_ORIGINS = 'http://127.0.0.1:5174'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

前端终端：

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8001'
npm run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

VITE变量进入前端代码，不得放密钥；构建前也要设置，修改后重启Vite或重建。默认跨域来源仅127.0.0.1:5173，localhost不自动视为相同源。不要用关闭安全机制解决跨域。

## 测试与交接

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm test
npm run build
```

均不调用收费模型。npm run benchmark仅CPU几何计时，不代表网络、模型或GPU性能。

- [首版说明、3分钟演示、5个必须掌握的问题](docs/FIRST-RELEASE.md)
- [本轮复现与验收清单](docs/RELEASE-VERIFICATION.md)
- [数据来源、坐标、许可和假设](public/data/buildings/README.md)

## 当前限制和版本

目标点单射线可见性不是整栋建筑面积比例；无DEM、范围外建筑、树木、精细立面和屋顶，不作为测绘、安全或导航认证。
原首页环境山湖与建筑是装饰；巡检页54个建筑网格实际参与遮挡。USGS归一化演示距离不代表地理距离。
本机接口无身份认证；后端一致性检查不是不可信浏览器的防篡改认证，不要直接开放公网。
首次后台连接失败根因尚未确定，后续成功不等于彻底修复，详见验收记录。
GitHub远程已存在，基线2914d64曾同步；本轮变更等待审阅，不擅自提交、推送或创建Release。

## 关键文件

backend/inspection.py：报告与巡检协议；backend/validation.py：目标校验；
backend/building_adapter.py：米制转换；src/visibility.js：共用几何；
src/inspection-core.js：批量比较；src/inspection.js：巡检页；src/main.js：旧演示。
