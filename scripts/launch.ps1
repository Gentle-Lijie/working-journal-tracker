# 一键启动开发环境（支持多项目追踪）(PowerShell 版)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# 查找 Python 3.14 可执行文件
$PythonExe = $null
$pyPath = where.exe py 2>$null
if ($pyPath) {
    # 使用 py launcher 获取 Python 3.14 路径
    $PythonExe = (& py -3.14 -c "import sys; print(sys.executable)").Trim()
}

if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    Write-Host "错误: 未找到 Python 3.14" -ForegroundColor Red
    exit 1
}

Write-Host "使用 Python: $PythonExe" -ForegroundColor Gray

Push-Location $ProjectDir

Write-Host "=== 启动开发环境 ===" -ForegroundColor Cyan

# 启动后端（后台）
Write-Host "启动后端服务..." -ForegroundColor Yellow
$backendArgs = @("-m", "uvicorn", "backend.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000")
$backend = Start-Process -PassThru -NoNewWindow $PythonExe -ArgumentList $backendArgs

# 启动前端（后台）
Write-Host "启动前端服务..." -ForegroundColor Yellow
$frontendDir = Join-Path $ProjectDir "frontend"
if (Test-Path $frontendDir) {
    # pnpm 在 Windows 上是 .cmd 文件
    $pnpmCmd = "pnpm.cmd"
    $pnpmPath = where.exe pnpm 2>$null
    if ($pnpmPath) {
        $frontend = Start-Process -PassThru -NoNewWindow $pnpmCmd -ArgumentList "dev" -WorkingDirectory $frontendDir
    } else {
        Write-Host "警告: pnpm 未找到，跳过前端启动" -ForegroundColor Yellow
        $frontend = $null
    }
} else {
    Write-Host "警告: frontend 目录不存在，跳过前端启动" -ForegroundColor Yellow
    $frontend = $null
}

# 等待后端就绪后启动追踪器
Start-Sleep -Seconds 3

# 支持多个路径参数，每个路径启动独立追踪器
if ($args.Count -eq 0) {
    Write-Host "启动追踪器（监控: .）..." -ForegroundColor Yellow
    $trackerArgs = @("-m", "cli.main", "start", "--path", ".")
    Start-Process -NoNewWindow $PythonExe -ArgumentList $trackerArgs
} else {
    foreach ($trackPath in $args) {
        Write-Host "启动追踪器（监控: $trackPath）..." -ForegroundColor Yellow
        $trackerArgs = @("-m", "cli.main", "start", "--path", $trackPath)
        Start-Process -NoNewWindow $PythonExe -ArgumentList $trackerArgs
    }
}

Write-Host ""
Write-Host "后端:   http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "前端:   http://127.0.0.1:5173" -ForegroundColor Green
if ($args.Count -eq 0) {
    Write-Host "追踪器: 监控 ." -ForegroundColor Green
} else {
    foreach ($trackPath in $args) {
        Write-Host "追踪器: 监控 $trackPath" -ForegroundColor Green
    }
}
Write-Host ""
Write-Host "按 Ctrl+C 停止所有服务" -ForegroundColor Gray

# Ctrl+C 时停止所有进程
try {
    $backend | Wait-Process
} finally {
    Write-Host ""
    Write-Host "停止服务..." -ForegroundColor Yellow
    # 停止所有追踪器
    & $PythonExe -m cli.main stop 2>$null
    # 停止后端和前端
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
    Pop-Location
}
