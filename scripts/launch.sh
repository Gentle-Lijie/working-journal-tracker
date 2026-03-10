#!/bin/bash
# 一键启动开发环境

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 追踪路径，默认当前项目目录，可通过参数指定
TRACK_PATH="${1:-.}"

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
echo "启动追踪器（监控: $TRACK_PATH）..."
sleep 3
work-journal start --path "$TRACK_PATH" &
TRACKER_PID=$!

echo ""
echo "后端:   http://127.0.0.1:8000"
echo "前端:   http://127.0.0.1:5173"
echo "追踪器: 监控 $TRACK_PATH"
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
