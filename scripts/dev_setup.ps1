# 开发环境设置脚本 (PowerShell 版)

$ErrorActionPreference = "Stop"

Write-Host "=== 工作日志追踪工具 - 开发环境设置 ==="

# 检查Python版本
Write-Host "检查Python版本..."
$pythonVersion = python --version 2>&1
Write-Host "Python版本: $pythonVersion"

# 安装Python依赖
Write-Host "安装Python依赖..."
pip install -e .

# 创建配置目录
Write-Host "创建配置目录..."
$configDir = Join-Path $HOME ".work-journal"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# 复制配置文件示例
$configFile = Join-Path $configDir "config.yaml"
if (-not (Test-Path $configFile)) {
    Write-Host "复制配置文件示例..."
    Copy-Item "config/config.example.yaml" $configFile
    Write-Host "请编辑 $configFile 设置数据库连接"
}

# 复制环境变量示例
if (-not (Test-Path ".env")) {
    Write-Host "复制环境变量示例..."
    Copy-Item "config/.env.example" ".env"
    Write-Host "请编辑 .env 设置环境变量"
}

# 前端设置
if (Test-Path "frontend") {
    Write-Host "安装前端依赖..."
    Push-Location frontend
    if (Get-Command pnpm -ErrorAction SilentlyContinue) {
        pnpm install
    } else {
        Write-Host "警告: pnpm未安装，跳过前端依赖安装"
    }
    Pop-Location
}

Write-Host ""
Write-Host "=== 设置完成 ==="
Write-Host ""
Write-Host "下一步:"
Write-Host "1. 编辑 $configFile 配置数据库"
Write-Host "2. 编辑 .env 设置环境变量"
Write-Host "3. 运行 python scripts/init_db.py 初始化数据库"
Write-Host "4. 运行 work-journal start 开始追踪"
Write-Host ""
