# GeoScene 0.1.0 工程交付验收

> 本文件保留c24badc之前首版收尾的历史验收。2026-10-11工作台增量、新测试和浏览器证据见WORKBENCH-VERIFICATION.md；不要把下面的干净目录验证扩大解释为新工作台跨环境验证。

日期：2026-10-11（上海）；本轮开始于10月10日。基线提交2914d64，本轮修改未提交、未推送、未创建Release。无新增模型调用。

## 通过

| 检查 | 实际证据 |
| --- | --- |
| 报告路径可迁移 | 默认由backend/inspection.py所在项目定位outputs/inspection-reports，不再使用parents[5]或旧任务目录 |
| 可配置路径 | GEOSCENE_REPORT_DIR支持绝对路径、相对项目路径；空值回退；不同cwd/迁移根目录自动化通过 |
| 旧文件保留 | 未触碰旧任务报告；测试确认已有文件保留且重复导出使用不同文件名 |
| 不可写目录 | 自动化返回503及配置提示，不假装导出成功 |
| 原工程回归 | Python70 passed、3 subtests（3.98秒）；Node6 passed；构建通过（428ms） |
| 独立目录安装 | 仅复制受版本控制的当前源文件，未复制.env、node_modules、.venv；重新创建venv，pip install和npm ci成功 |
| 独立目录回归 | Python70 passed、3 subtests（12.11秒）；Node6 passed；构建386ms通过 |
| 默认A/B | 新目录浏览器54建筑/54网格/12目标，A5/12、B0/12；24条结果 |
| 参数失效/重算 | A-y改为4后结果0行、导出禁用；重算inspect-01距离0.50→2.50米 |
| 非法目标 | missing-target提示不存在，0行结果且导出禁用 |
| 报告一致性 | 新目录真实POST导出成功；GET返回报告；A高度4、B高度2、A5/B0、24行与同次截图核对一致 |
| 密钥与费用 | 独立副本无.env，后端health的api_key_configured=false；只操作普通比较/导出，无Agent调用 |
| 文档与Git | README、首版说明统一GeoScene 0.1.0；git diff --check无格式错误；未推送 |

## 复现条件和局限

Windows x64同一台电脑，Python3.14.7、Node24.13.1、Chrome153内嵌浏览器。使用新的依赖目录，但包管理器可以命中本机下载缓存，不是新操作系统或虚拟机。
新环境主要包：FastAPI0.143.0、uvicorn0.54.0、openai3.28.0、pyproj3.8.0、shapely2.2.0、pytest9.1.1。Node依赖由现有lockfile安装。
临时根目录：`C:\Users\licr\AppData\Local\Temp\geoscene-release-b2c60304b3fd49b5b4b2a3c98c4dfa1b`。
独立端口8001/5174；VITE_API_BASE_URL与GEOSCENE_ALLOWED_ORIGINS配套设置。原8000/5173服务未结束或重启，不影响原工程。
测试结束后核对命令行归属，仅停止临时副本的后台PID10028和Vite PID15328；原后台PID46072和前端PID17876仍存在。临时测试网址已停止服务，离线HTML报告仍可打开。
新副本源代码是当前工作区的受控文件，不是仅复制旧提交，因此覆盖本轮未提交修复。验证结束保留临时目录及报告作为证据，不删除用户文件；临时目录可能被系统清理，报告另存到项目outputs。

## 报告证据

项目内：`outputs/release-verification-20261011/inspection-86e0479057654d5792034ed1cb2db1eb.html`及同名JSON（Git忽略）。
原生成位置为临时根目录的outputs/inspection-reports。运行ID：1701dbaa-bc38-4535-be10-b49b3e178623。
数据版本nyc-block-v1-94305d13003f；UTC2026-10-10T17:15:56.123Z，即上海10月11日01:15:56。
执行方式“直接工具执行，无模型调用”；A位置(-90,4,-140)、B位置(0,2,160)，FOV120度，maxDistance500米。截图已目视确认有真实场景网格与视线，不为空白图。

## 未通过／未解决

- 首次后台连接失败的根因仍未确定。本轮普通比较未复现该错误，不宣称彻底修复。
- 本轮首次打开临时浏览器页出现导航等待超时；重新读取同一页后加载完成（页面加载4004.7ms），随后分析成功。它不是已证实的原后台连接故障。
- 生产构建共享包约600KB，仍有大包告警；构建成功但未进行体积优化。
- 未验证其他电脑、操作系统、Python/Node版本；Python依赖不是全量锁定，未来版本组合可能不同。
- 自定义输出目录磁盘写入不是事务；极端写入中断可能留下单个文件，不能宣称崩溃恢复已经验证。

## 待人工验收

1. 原8000服务仍是本轮开始前启动的进程：用户结束自己对应后端终端并按README重新启动，才能加载新路径逻辑。不要同时启动两个8000服务。
2. 按FIRST-RELEASE的三分钟流程，在原项目导出一份新报告并确认outputs/inspection-reports位置。
3. 独立解释FIRST-RELEASE列出的5个问题，工程通过不代替知识掌握。
4. 审阅本轮Git差异后决定提交/推送；远端目前仍为旧基线，不冒称已更新。

## 修改文件

- backend/inspection.py：项目相对默认路径、环境变量覆盖、不可写错误提示。
- backend/tests/test_inspection.py：新增6个路径/覆盖/保留/错误测试用例，原64增至70。
- backend/main.py：API名称/版本统一，精确来源列表可配置。
- src/inspection.js、src/main.js：API地址可通过VITE_API_BASE_URL配置，默认值不变。
- .gitignore：明确忽略项目outputs，保留受控示例。
- package.json、package-lock.json：统一geoscene/0.1.0，不升级Node依赖。
- README.md、docs/FIRST-RELEASE.md：统一启动、目录、边界、已有远程状态、演示和5个问题。
- docs/RELEASE-VERIFICATION.md：本记录。

本轮到此停止：不加入SLAM、RAG、多Agent、导航、复杂面积或视觉扩展，不制作其他对话负责的产品材料。
