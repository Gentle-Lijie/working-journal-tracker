#!/bin/bash
# 一键启动开发环境（支持多项目追踪）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== 启动开发环境 ==="

# 存储所有子进程 PID
declare -a CHILD_PIDS=()

# 清理函数：杀死所有子进程
cleanup() {
    echo ""
    echo "=== 正在停止所有服务 ==="

    # 1. 停止所有追踪器守护进程
    echo "停止追踪器..."
    work-journal stop 2>/dev/null || true

    # 2. 杀死所有记录的子进程
    for pid in "${CHILD_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "停止进程 $pid..."
            kill "$pid" 2>/dev/null || true
        fi
    done

    # 3. 等待进程退出
    sleep 1

    # 4. 强制杀死仍在运行的进程
    for pid in "${CHILD_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "强制停止进程 $pid..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    done

    # 5. 清理可能的僵尸进程（后端、前端相关）
    pkill -f "uvicorn backend.main:app" 2>/dev/null || true
    pkill -f "vite.*frontend" 2>/dev/null || true

    echo "所有服务已停止"
    exit 0
}

# 捕获 Ctrl+C 和 kill 信号
trap cleanup INT TERM

# 启动后端（后台）
echo "启动后端服务..."
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
CHILD_PIDS+=($BACKEND_PID)

# 启动前端（后台）
echo "启动前端服务..."
cd "$PROJECT_DIR/frontend" && pnpm dev &
FRONTEND_PID=$!
CHILD_PIDS+=($FRONTEND_PID)

# 等待后端就绪后启动追踪器
cd "$PROJECT_DIR"
sleep 3

# 支持多个路径参数，每个路径启动独立追踪器
if [ $# -gt 0 ]; then
    for TRACK_PATH in "$@"; do
        echo "启动追踪器（监控: $TRACK_PATH）..."
        work-journal start --path "$TRACK_PATH" &
        TRACKER_PID=$!
        CHILD_PIDS+=($TRACKER_PID)
    done
fi

echo ""
echo "后端:   http://127.0.0.1:8000"
echo "前端:   http://127.0.0.1:5173"
if [ $# -gt 0 ]; then
    for TRACK_PATH in "$@"; do
        echo "追踪器: 监控 $TRACK_PATH"
    done
else
    echo "追踪器: 未启动（可通过 Web UI 或命令行手动启动）"
fi
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "PID 列表: ${CHILD_PIDS[*]}"

# 等待任意子进程退出
wait -n 2>/dev/null || wait

# 如果有进程意外退出，触发清理
cleanup
