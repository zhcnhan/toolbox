#!/bin/bash
# =========================================================================
# Batch Background Remover — macOS 一键启动
# 用法: chmod +x batch-bg-mac.sh && ./batch-bg-mac.sh
# =========================================================================
set -e

echo "🚀 启动 Batch Background Remover..."
DIR="$(cd "$(dirname "$0")" && pwd)"

# 检查后端依赖
if [ ! -d "$DIR/backend/venv" ]; then
    echo "[Setup] 创建 Python 虚拟环境..."
    python3 -m venv "$DIR/backend/venv"
    source "$DIR/backend/venv/bin/activate"
    pip install -r "$DIR/backend/requirements.txt"
else
    source "$DIR/backend/venv/bin/activate"
fi

# 检查前端依赖
if [ ! -d "$DIR/frontend/node_modules" ]; then
    echo "[Setup] 安装前端依赖..."
    cd "$DIR/frontend" && npm install
    cd "$DIR"
fi

# 启动后端（后台）
echo "[Start] 启动后端 (port 8001)..."
cd "$DIR/backend"
uvicorn main:app --host 127.0.0.1 --port 8001 &
BACKEND_PID=$!
cd "$DIR"

# 启动前端（后台）
echo "[Start] 启动前端 (port 5174)..."
cd "$DIR/frontend"
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!
cd "$DIR"

echo ""
echo "=========================================="
echo "  ✅ 启动完成！"
echo "  前端: http://localhost:5174"
echo "  后端: http://localhost:8001"
echo "  按 Ctrl+C 停止所有服务"
echo "=========================================="

# 捕获 Ctrl+C 优雅退出
trap "echo ''; echo '🛑 停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# 等待任意子进程退出
wait
