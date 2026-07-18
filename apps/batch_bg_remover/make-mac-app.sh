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
  <key>LSUIElement</key>
  <string>1</string>
</dict>
</plist>
EOF

# 启动脚本
cat > "$APP_DIR/Contents/MacOS/launcher" << 'SCRIPT'
#!/bin/bash
DIR="$HOME/Desktop/toolbox/apps/batch_bg_remover"

# 找不到就搜一下
if [ ! -d "$DIR" ]; then
  DIR=$(find "$HOME" -maxdepth 4 -name "batch_bg_remover" -type d 2>/dev/null | head -1)
fi

if [ ! -d "$DIR" ]; then
  osascript -e 'tell app "System Events" to display dialog "没找到 toolbox 项目，请把它放在桌面" buttons {"知道了"} default button 1 with icon stop'
  exit 1
fi

cd "$DIR"

# 虚拟环境
if [ ! -d "backend/venv" ]; then
  python3 -m venv backend/venv
  source backend/venv/bin/activate
  pip install -r backend/requirements.txt -q
else
  source backend/venv/bin/activate
fi

# 前端依赖
if [ ! -d "frontend/node_modules" ]; then
  cd frontend && npm install --silent && cd ..
fi

# 启动
cd backend && uvicorn main:app --host 127.0.0.1 --port 8001 &
BACKEND=$!
cd ../frontend && npm run dev -- --host 127.0.0.1 &
FRONTEND=$!
cd ..

sleep 3
open http://localhost:5174

# 优雅退出
trap "kill $BACKEND $FRONTEND 2>/dev/null; exit 0" SIGTERM SIGINT
wait
SCRIPT

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# 用 Python 生成一个简单的应用图标
python3 << 'PYTHON'
import struct, zlib, math, os

def create_png(w, h, pixels):
    def cid(type_, data):
        c = type_ + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    raw = b''
    for y in range(h):
        raw += b'\x00'
        for x in range(w):
            i = (y * w + x) * 4
            raw += bytes(pixels[i:i+4])
    return (b'\x89PNG\r\n\x1a\n' +
            cid(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) +
            cid(b'IDAT', zlib.compress(raw)) +
            cid(b'IEND', b''))

w, h = 128, 128
px = []
for y in range(h):
    for x in range(w):
        dx, dy = x - 64, y - 64
        d = math.sqrt(dx*dx + dy*dy)
        if d < 30:
            r, g, b, a = 255, 255, 255, 255
        elif d < 42:
            t = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
            r = int(59 + 30 * math.sin(t * 6))
            g = int(130 + 30 * math.cos(t * 4))
            b = int(246 + 30 * math.sin(t * 5))
            a = 255
        else:
            r, g, b, a = 0, 0, 0, 0
        px.extend([r, g, b, a])

icon_dir = os.path.expanduser("~/Desktop/BatchBackgroundRemover.app/Contents/Resources")
with open(f"{icon_dir}/icon.png", "wb") as f:
    f.write(create_png(w, h, px))
os.system(f"sips -s format icns '{icon_dir}/icon.png' --out '{icon_dir}/icon.icns' 2>/dev/null || true")
PYTHON

echo ""
echo "✅ 完成！应用已放到桌面"
echo "  下次直接双击 \"BatchBackgroundRemover.app\" 就能用"
echo "  关闭：在程序坞右键 → 退出"
echo ""
