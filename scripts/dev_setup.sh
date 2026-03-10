#!/bin/bash
# 开发环境设置脚本

set -e

echo "=== 工作日志追踪工具 - 开发环境设置 ==="

# 检查Python版本
echo "检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"

# 安装Python依赖
echo "安装Python依赖..."
pip install -e .

# 创建配置目录
echo "创建配置目录..."
mkdir -p ~/.work-journal
chmod 700 ~/.work-journal

# 复制配置文件示例
if [ ! -f ~/.work-journal/config.yaml ]; then
    echo "复制配置文件示例..."
    cp config/config.example.yaml ~/.work-journal/config.yaml
    chmod 600 ~/.work-journal/config.yaml
    echo "请编辑 ~/.work-journal/config.yaml 设置数据库连接"
fi

# 复制环境变量示例
if [ ! -f .env ]; then
    echo "复制环境变量示例..."
    cp config/.env.example .env
    echo "请编辑 .env 设置环境变量"
fi

# 前端设置
if [ -d "frontend" ]; then
    echo "安装前端依赖..."
    cd frontend
    if command -v npm &> /dev/null; then
        npm install
    else
        echo "警告: npm未安装，跳过前端依赖安装"
    fi
    cd ..
fi

echo ""
echo "=== 设置完成 ==="
echo ""
echo "下一步:"
echo "1. 编辑 ~/.work-journal/config.yaml 配置数据库"
echo "2. 编辑 .env 设置环境变量"
echo "3. 运行 python scripts/init_db.py 初始化数据库"
echo "4. 运行 work-journal start 开始追踪"
echo ""
