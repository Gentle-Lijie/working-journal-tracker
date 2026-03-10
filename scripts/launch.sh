#!/bin/bash
# 一键启动开发环境（支持多项目追踪）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== 启动开发环境 ==="

# 启动后端（后台）
echo "启动后端服务..."
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 启动前端（后台）
echo "启动前端服务..."
cd "$PROJECT_DIR/frontend" && pnpm dev &
FRONTEND_PID=$!

# 等待后端就绪后启动追踪器
cd "$PROJECT_DIR"
sleep 3

# 支持多个路径参数，每个路径启动独立追踪器
if [ $# -eq 0 ]; then
    # 无参数时追踪当前项目目录
    echo "启动追踪器（监控: .）..."
    work-journal start --path "." &
else
    for TRACK_PATH in "$@"; do
        echo "启动追踪器（监控: $TRACK_PATH）..."
        work-journal start --path "$TRACK_PATH" &
    done
fi

echo ""
echo "后端:   http://127.0.0.1:8000"
echo "前端:   http://127.0.0.1:5173"
if [ $# -eq 0 ]; then
    echo "追踪器: 监控 ."
else
    for TRACK_PATH in "$@"; do
        echo "追踪器: 监控 $TRACK_PATH"
    done
fi
echo "按 Ctrl+C 停止所有服务"

# Ctrl+C 时停止所有进程
cleanup() {
    echo "停止服务..."
    work-journal stop 2>/dev/null || true
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup INT TERM
wait
