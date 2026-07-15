#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  Format Converter - 一键开发启动"
echo "=========================================="
echo

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] 未找到 python3，请安装 Python 3.10+"
    exit 1
fi

# Check Node
if ! command -v node &>/dev/null; then
    echo "[ERROR] 未找到 node，请安装 Node.js 20+"
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "[WARN] 未找到 FFmpeg，音频/视频转换将不可用"
    echo "       macOS: brew install ffmpeg"
    echo "       Linux: sudo apt install ffmpeg"
    echo
fi

cd "$(dirname "$0")"

# Install backend deps if needed
echo "[1/4] 检查后端依赖..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "      安装后端依赖..."
    pip install -r backend/requirements.txt
else
    echo "      后端依赖已就绪"
fi

# Install frontend deps if needed
echo "[2/4] 检查前端依赖..."
if [ ! -d "frontend/node_modules" ]; then
    echo "      安装前端依赖..."
    cd frontend && npm install && cd ..
else
    echo "      前端依赖已就绪"
fi

# Start backend
echo "[3/4] 启动后端 (端口 8000)..."
cd backend
python3 -m uvicorn format_converter.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Start frontend
echo "[4/4] 启动前端 (端口 5173)..."
cd frontend
npx vite --host &
FRONTEND_PID=$!
cd ..

# Wait and open browser
echo
echo "等待服务启动..."
sleep 3

# Try to open browser
if command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:5173
elif command -v open &>/dev/null; then
    open http://localhost:5173
fi

echo
echo "=========================================="
echo "  服务已启动！"
echo "  前端: http://localhost:5173"
echo "  后端: http://localhost:8000"
echo "  API文档: http://localhost:8000/api/docs"
echo "=========================================="
echo
echo "按 Ctrl+C 停止所有服务"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
