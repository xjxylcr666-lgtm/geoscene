param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw '缺少项目虚拟环境，请按README完成首次安装。' }
if ($CheckOnly) { Write-Output '后端路径检查通过；未启动服务。'; return }
Push-Location -LiteralPath $projectRoot
try { & $pythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 }
finally { Pop-Location }
