#!/bin/bash
# =========================================================================
# Batch Background Remover — macOS 一键启动
# 用法: chmod +x batch-bg-mac.sh && ./batch-bg-mac.sh
# =========================================================================
set -e

echo "🚀 启动 Batch Background Remover..."
DIR="$(cd "$(dirname "$0")" && pwd)"

# 国内镜像源（中国大陆网络加速）
PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple"
NPM_MIRROR="https://registry.npmmirror.com"

# 检查后端依赖
if [ ! -d "$DIR/backend/venv" ]; then
    echo "[Setup] 创建 Python 虚拟环境..."
    python3 -m venv "$DIR/backend/venv"
    source "$DIR/backend/venv/bin/activate"
    pip install -r "$DIR/backend/requirements.txt" -i "$PYPI_MIRROR"
else
    source "$DIR/backend/venv/bin/activate"
fi

# 检查前端依赖
if [ ! -d "$DIR/frontend/node_modules" ]; then
    echo "[Setup] 安装前端依赖..."
    cd "$DIR/frontend" && npm config set registry "$NPM_MIRROR" && npm install
    cd "$DIR"
fi

# 检查前端是否已构建
if [ ! -d "$DIR/backend/static" ] || [ ! -f "$DIR/backend/static/index.html" ]; then
    echo "[Setup] 构建前端静态文件..."
    cd "$DIR/frontend" && npm run build
    cd "$DIR"
fi

# 启动服务（生产模式：单进程，FastAPI 直接服务前端静态文件）
echo "[Start] 启动服务 (http://localhost:8001)..."
cd "$DIR/backend"
python main.py &
BACKEND_PID=$!
cd "$DIR"

echo ""
echo "=========================================="
echo "  ✅ 启动完成！"
echo "  访问: http://localhost:8001"
echo "  按 Ctrl+C 停止服务"
echo "=========================================="

# 捕获 Ctrl+C 优雅退出
trap "echo ''; echo '🛑 停止服务...'; kill $BACKEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# 等待子进程退出
wait
