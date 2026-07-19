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
FIRST_RUN=false

# 检查 Node.js（仅首次安装需要）
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
  echo "[错误] 未安装 Node.js 和 npm"
  echo "请先安装：brew install node"
  echo "或在终端执行：/bin/bash -c \"\$(curl -fsSL https://gitee.com/ineo6/homebrew-install/raw/master/install.sh)\" && brew install node"
  exit 1
fi

# 检查 Python 版本（需要 >=3.10，不够则自动安装）
PY3=$(command -v python3)
PY_VER=$("$PY3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MAJOR" -eq 3 -a "$PY_MINOR" -lt 10 ]; then
  echo ""
  echo "============================================"
  echo "  需要 Python 3.10+（当前: $PY_VER）"
  echo "  正在自动下载安装 Python 3.12 ..."
  echo "============================================"
  echo ""

  # 下载 Python 3.12 安装包（python.org 国内可访问）
  curl -L -o /tmp/python3.pkg "https://www.python.org/ftp/python/3.12.9/python-3.12.9-macos11.pkg"

  # 静默安装
  echo "正在安装，可能需要输入密码..."
  sudo installer -pkg /tmp/python3.pkg -target /
  rm -f /tmp/python3.pkg

  # 重新定位 Python
  PY3="/usr/local/bin/python3"
  if [ ! -f "$PY3" ]; then
    PY3="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
  fi

  echo ""
  echo "✅ Python 3.12 安装完成！"
fi

# ---- 首次安装流程 ----
if [ ! -d "backend/venv" ] || [ ! -d "frontend/node_modules" ] || [ ! -d "backend/static" ]; then
  FIRST_RUN=true
  echo ""
  echo "========================================"
  echo "  🚀 首次启动 — 自动安装依赖"
  echo "  请稍候，约 2-3 分钟..."
  echo "========================================"
  echo ""

  # Python 虚拟环境
  if [ ! -d "backend/venv" ]; then
    echo "[1/4] 创建 Python 虚拟环境..."
    python3 -m venv backend/venv
    source backend/venv/bin/activate
    echo "[2/4] 安装 Python 依赖..."
    pip install -r backend/requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 预下载 rembg 模型（避免首次抠图超时）
    echo "→ 下载 rembg 模型 (~176MB)..."
    mkdir -p "$HOME/.u2net"
    # 多镜像轮询
    U2NET_URLS=(
      "https://ghproxy.net/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
      "https://gh-proxy.com/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
      "https://mirror.ghproxy.com/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
      "https://github.moeyy.xyz/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
      "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
    )
    U2NET_OK=0
    for url in "${U2NET_URLS[@]}"; do
      HOST=$(echo "$url" | sed 's|https://||' | cut -d/ -f1)
      echo "  尝试 ($HOST)... 超时 3 分钟"
      curl -L -o "$HOME/.u2net/u2net.onnx" "$url" \
        --connect-timeout 15 --max-time 180 --progress-bar 2>&1 | \
        grep -E '[0-9]+\.[0-9]+[kMG]?B|^  %' || true
      # 校验：模型至少 50MB
      SIZE=$(stat -f%z "$HOME/.u2net/u2net.onnx" 2>/dev/null || echo 0)
      if [ "$SIZE" -gt 50000000 ]; then
        U2NET_OK=1
        echo "  ✅ 下载完成 ($(echo "scale=1; $SIZE/1024/1024" | bc)MB)"
        break
      fi
      rm -f "$HOME/.u2net/u2net.onnx"
      echo "  ⚠ 失败 (大小不符: $SIZE bytes)"
    done
    if [ "$U2NET_OK" -eq 0 ]; then
      echo "  ⚠ 所有镜像均失败，首次抠图时会自动重试"
    fi

    # CLIPSeg 模型（~1.5GB），询问是否预下载
    echo ""
    echo "→ CLIPSeg 提示词分割引擎需要额外下载模型（~1.5GB）"
    echo "  如果现在不下载，在网页上首次使用时会自动下载（可能较慢）"
    read -p "  是否现在下载（推荐）？[Y/n] " dl_clipseg
    if [[ ! "$dl_clipseg" =~ ^[Nn]$ ]]; then
      echo "→ 下载 CLIPSeg 模型中..."
      pip install -q huggingface-hub -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null
      for HF_MIRROR in "https://hf-mirror.com" "https://huggingface.co"; do
        echo "  尝试镜像: $HF_MIRROR"
        export HF_ENDPOINT="$HF_MIRROR"
        "$BASE/backend/venv/bin/python3" -c "
from huggingface_hub import snapshot_download
import os
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['HF_ENDPOINT'] = '$HF_MIRROR'
print('正在下载 CLIPSeg 模型（CIDAS/clipseg-rd64-refined）...')
snapshot_download('CIDAS/clipseg-rd64-refined', max_retries=2)
print('✅ CLIPSeg 模型下载完成')
" 2>&1 && { CLIPSEG_OK=1; break; } || echo "  ⚠ 镜像 $HF_MIRROR 失败，换下一个"
      done
      if [ "${CLIPSEG_OK:-0}" -eq 0 ]; then
        echo "  ⚠ 所有镜像都失败，首次使用时自动重试"
      fi
    else
      echo "  已跳过，首次使用 CLIPSeg 时会自动下载"
    fi
  else
    source backend/venv/bin/activate
  fi

  # 确保 huggingface_hub 已安装
  if ! "$BASE/backend/venv/bin/python3" -c "import huggingface_hub" 2>/dev/null; then
    echo "→ 安装 huggingface_hub..."
    pip install huggingface-hub -q -i https://pypi.tuna.tsinghua.edu.cn/simple
  fi

  # 前端依赖
  if [ ! -d "frontend/node_modules" ]; then
    echo "[3/4] 安装前端依赖..."
    (cd frontend && npm config set registry https://registry.npmmirror.com && npm install --silent)
  fi

  # 构建前端静态文件
  if [ ! -d "backend/static" ] || [ ! -f "backend/static/index.html" ]; then
    echo "[4/4] 构建前端静态文件..."
    (cd frontend && npm run build --silent)
  fi

  cd "$BASE"
  echo ""
  echo "========================================"
  echo "  ✅ 安装完成！以后双击秒开"
  echo "========================================"
  echo ""
fi

# ---- 后续启动 ----
if [ "$FIRST_RUN" = false ]; then
  echo "========================================"
  echo "  批量抠图 — 启动中..."
  echo "========================================"
  source backend/venv/bin/activate
fi

# 设置 HuggingFace 国内镜像（CLIPSeg 下载模型时走这个源）
export HF_ENDPOINT=https://hf-mirror.com

# 生产模式：单进程，FastAPI 直接服务前端静态文件
echo "  服务地址: http://localhost:8001"
echo "  关闭此窗口即可停止服务"
echo ""
(cd backend && python main.py) &
BACKEND_PID=$!

sleep 2
open http://localhost:8001

trap "kill $BACKEND_PID 2>/dev/null; exit 0" SIGTERM SIGINT
wait
SCRIPT

chmod +x "$APP_FILE"

echo ""
echo "=========================================="
echo "  ✅ 生成完成！"
echo "  桌面出现「批量抠图.command」"
echo "  双击它就能启动，关闭窗口就停止"
echo "=========================================="
