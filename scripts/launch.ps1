# 一键启动开发环境（支持多项目追踪）(PowerShell 版)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Push-Location $ProjectDir

Write-Host "=== 启动开发环境 ==="

# 启动后端（后台）
Write-Host "启动后端服务..."
$backend = Start-Process -PassThru -NoNewWindow uvicorn -ArgumentList "backend.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"

# 启动前端（后台）
Write-Host "启动前端服务..."
$frontend = Start-Process -PassThru -NoNewWindow -WorkingDirectory "$ProjectDir/frontend" pnpm -ArgumentList "dev"

# 等待后端就绪后启动追踪器
Start-Sleep -Seconds 3

# 支持多个路径参数，每个路径启动独立追踪器
$trackerProcesses = @()
if ($args.Count -eq 0) {
    Write-Host "启动追踪器（监控: .）..."
    $trackerProcesses += Start-Process -PassThru -NoNewWindow work-journal -ArgumentList "start", "--path", "."
} else {
    foreach ($trackPath in $args) {
        Write-Host "启动追踪器（监控: $trackPath）..."
        $trackerProcesses += Start-Process -PassThru -NoNewWindow work-journal -ArgumentList "start", "--path", $trackPath
    }
}

Write-Host ""
Write-Host "后端:   http://127.0.0.1:8000"
Write-Host "前端:   http://127.0.0.1:5173"
if ($args.Count -eq 0) {
    Write-Host "追踪器: 监控 ."
} else {
    foreach ($trackPath in $args) {
        Write-Host "追踪器: 监控 $trackPath"
    }
}
Write-Host "按 Ctrl+C 停止所有服务"

# Ctrl+C 时停止所有进程
try {
    $backend | Wait-Process
} finally {
    Write-Host "停止服务..."
    work-journal stop 2>$null
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
    Pop-Location
}
