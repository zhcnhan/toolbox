#!/bin/bash
# =========================================================================
# 生成 macOS 桌面启动器（.command 文件）
# 在 Mac 终端运行: bash make-mac-app.sh
# 之后双击桌面「批量抠图.command」即可启动
# =========================================================================
set -e

APP_FILE="$HOME/Desktop/批量抠图.command"

cat > "$APP_FILE" << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")"
DIR="$HOME/Desktop/toolbox/apps/batch_bg_remover"

if [ ! -d "$DIR" ]; then
  DIR=$(find "$HOME" -maxdepth 4 -name "batch_bg_remover" -type d 2>/dev/null | head -1)
fi

if [ ! -d "$DIR" ]; then
  echo "错误：没找到 toolbox 项目文件夹"
  echo "请确认 ~/Desktop/toolbox/ 存在后重试"
  exit 1
fi

cd "$DIR"

echo "========================================"
echo "  批量抠图 — 启动中..."
echo "========================================"

# 虚拟环境
if [ ! -d "backend/venv" ]; then
  echo "[1/3] 首次安装 Python 依赖..."
  python3 -m venv backend/venv
  source backend/venv/bin/activate
  pip install -r backend/requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple
else
  source backend/venv/bin/activate
fi

# 前端依赖
if [ ! -d "frontend/node_modules" ]; then
  echo "[2/3] 首次安装前端依赖..."
  cd frontend && npm config set registry https://registry.npmmirror.com && npm install --silent && cd ..
fi

echo "[3/3] 启动服务..."
cd backend && uvicorn main:app --host 127.0.0.1 --port 8001 &
BACKEND=$!
cd ../frontend && npm run dev -- --host 127.0.0.1 &
FRONTEND=$!
cd ..

sleep 3
open http://localhost:5174

echo ""
echo "========================================"
echo "  ✅ 启动完成！浏览器已打开"
echo "  关闭此窗口即可停止服务"
echo "========================================"

trap "kill $BACKEND $FRONTEND 2>/dev/null; exit 0" SIGTERM SIGINT
wait
SCRIPT

chmod +x "$APP_FILE"

echo ""
echo "=========================================="
echo "  ✅ 生成完成！"
echo "  桌面出现「批量抠图.command」"
echo "  双击它就能启动，关闭窗口就停止"
echo "=========================================="
