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

# Apple Silicon Mac 的 Homebrew 路径
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# 找到项目目录
DIR="$HOME/Desktop/toolbox/apps/batch_bg_remover"
[ ! -d "$DIR" ] && DIR=$(find "$HOME" -maxdepth 4 -name "batch_bg_remover" -type d 2>/dev/null | head -1)

if [ ! -d "$DIR" ]; then
  echo "错误：没找到 toolbox 项目文件夹"
  echo "请确认 ~/Desktop/toolbox/ 存在后重试"
  exit 1
fi

cd "$DIR"
BASE="$DIR"

echo "========================================"
echo "  批量抠图 — 启动中..."
echo "========================================"

# 检查 Node.js
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
  echo "[错误] 未安装 Node.js 和 npm"
  echo "请先安装：brew install node"
  echo "或在终端执行：/bin/bash -c \"\$(curl -fsSL https://gitee.com/ineo6/homebrew-install/raw/master/install.sh)\" && brew install node"
  exit 1
fi

# 检查 Python 版本（需要 >=3.10）
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
if [ "$(echo "$PY_VERSION" | cut -d. -f1)" -lt 3 ] || [ "$(echo "$PY_VERSION" | cut -d. -f1)" -eq 3 -a "$(echo "$PY_VERSION" | cut -d. -f2)" -lt 10 ]; then
  echo "[错误] 需要 Python 3.10 或更高版本（当前: $PY_VERSION）"
  echo "去 https://www.python.org/downloads/ 下载安装 Python 3.12"
  echo "装完重新双击本图标即可"
  exit 1
fi

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
  (cd frontend && npm config set registry https://registry.npmmirror.com && npm install --silent)
fi

# 回到项目根目录
cd "$BASE"

echo "[3/3] 启动服务..."

# 启动后端（后台）
(cd backend && uvicorn main:app --host 127.0.0.1 --port 8001) &
BACKEND=$!

# 启动前端（后台）
(cd frontend && npm run dev -- --host 127.0.0.1) &
FRONTEND=$!

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
