#!/bin/bash
# 一键启动开发环境

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
cd frontend && pnpm dev &
FRONTEND_PID=$!

echo ""
echo "后端: http://127.0.0.1:8000"
echo "前端: http://127.0.0.1:5173"
echo "按 Ctrl+C 停止所有服务"

# Ctrl+C 时同时停止两个进程
trap "echo '停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
