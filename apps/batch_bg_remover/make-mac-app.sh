#!/bin/bash
# =========================================================================
# 生成 macOS .app 桌面应用
# 在 Mac 终端运行: bash make-mac-app.sh
# =========================================================================
set -e

APP_NAME="批量抠图"
APP_DIR="$HOME/Desktop/BatchBackgroundRemover.app"

echo "生成 $APP_DIR ..."

# 创建目录结构
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Info.plist
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>launcher</string>
  <key>CFBundleIdentifier</key>
  <string>com.zhcnhan.batch-bg-remover</string>
  <key>CFBundleName</key>
  <string>Batch Background Remover</string>
  <key>CFBundleDisplayName</key>
  <string>批量抠图</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
</dict>
</plist>
EOF

# 启动脚本 — 双击 .app 时 macOS 自动打开终端运行此脚本
cat > "$APP_DIR/Contents/MacOS/launcher" << 'SCRIPT'
#!/bin/bash
DIR="$HOME/Desktop/toolbox/apps/batch_bg_remover"

if [ ! -d "$DIR" ]; then
  DIR=$(find "$HOME" -maxdepth 4 -name "batch_bg_remover" -type d 2>/dev/null | head -1)
fi

if [ ! -d "$DIR" ]; then
  echo "错误：没找到 toolbox 项目文件夹"
  echo "请确认 ~/Desktop/toolbox/ 存在后重试"
  read -p "按回车键退出..."
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

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# 用 Python 生成一个简单的应用图标
python3 << 'PYTHON'
import struct, zlib, os

def make_png(w, h, get_pixel):
    def ch(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    raw = b''
    for y in range(h):
        raw += b'\x00'
        for x in range(w):
            r, g, b, a = get_pixel(x, y)
            raw += bytes([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)), max(0, min(255, a))])
    return (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))

def pixel(x, y):
    cx, cy = 64, 64
    d = ((x - cx)**2 + (y - cy)**2) ** 0.5
    if d < 30:
        return (255, 255, 255, 255)
    if d < 42:
        return (99, 102, 241, 255)
    return (0, 0, 0, 0)

data = make_png(128, 128, pixel)
icon_dir = os.path.expanduser("~/Desktop/BatchBackgroundRemover.app/Contents/Resources")
with open(f"{icon_dir}/icon.png", "wb") as f:
    f.write(data)
os.system(f"sips -s format icns '{icon_dir}/icon.png' --out '{icon_dir}/icon.icns' 2>/dev/null || true")
PYTHON

echo ""
echo "✅ 完成！应用已放到桌面"
echo "  下次直接双击 \"BatchBackgroundRemover.app\" 就能用"
echo "  关闭：在程序坞右键 → 退出"
echo ""
