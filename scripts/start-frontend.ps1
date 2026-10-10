param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'node_modules\vite'))) { throw '缺少前端依赖，请在项目目录运行npm ci。' }
$npmCommand = Get-Command npm.cmd -ErrorAction Stop
if ($CheckOnly) { Write-Output '前端路径检查通过；未启动服务。'; return }
Push-Location -LiteralPath $projectRoot
try { & $npmCommand.Source run dev -- --host 127.0.0.1 --port 5173 --strictPort }
finally { Pop-Location }
