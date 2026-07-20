# =========================================================================
# Batch Background Remover — 多阶段 Dockerfile
# 阶段1: 构建前端静态文件
# 阶段2: Python 运行环境 + 后端 + 前端静态文件
# =========================================================================

# ---- 阶段1: 构建前端 ----
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# npm 换淘宝源（国内加速）
RUN npm config set registry https://registry.npmmirror.com

# 先复制依赖文件，利用 Docker 缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --production=false

# 复制前端源码并构建
COPY frontend/ ./
RUN npm run build
# 构建产物输出到 /build/frontend/../backend/static = /build/backend/static


# ---- 阶段2: Python 运行环境 ----
FROM python:3.12-slim

WORKDIR /app

# apt 换阿里云源（国内加速）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统依赖（rembg/onnxruntime 需要 libglib, libgl）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# pip 换清华源（国内加速）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装 Python 依赖
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 预下载 rembg U2Net 模型（首次使用免等待）
RUN echo "[Docker] Pre-caching rembg model..." && \
    python3 -c "from rembg.session_factory import new_session; new_session('u2net')" 2>/dev/null || \
    echo "[Docker] rembg model will be downloaded on first use"

# 复制后端代码
COPY backend/ /app/

# 从阶段1复制前端构建产物
COPY --from=frontend-builder /build/backend/static /app/static

# 创建上传和输出目录
RUN mkdir -p /app/uploads /app/outputs /root/.cache/sam

# SAM 1 本地分割模型（可选预下载）
# 构建时通过 --build-arg DOWNLOAD_SAM=true 启用
ARG DOWNLOAD_SAM=false
RUN if [ "$DOWNLOAD_SAM" = "true" ]; then \
        echo "[Docker] 下载 SAM 1 ViT-L 模型 (1.25GB)..."; \
        pip install --no-cache-dir requests && \
        python3 -c "
import requests, sys
url = 'https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth'
mirrors = [
    'https://ghproxy.net/{}',
    'https://gh-proxy.com/{}',
    'https://mirror.ghproxy.com/{}',
    'https://github.moeyy.xyz/{}',
    '{}',
]
for tmpl in mirrors:
    u = tmpl.format(url)
    try:
        print(f'尝试: {u.split(\"/\")[2]}')
        r = requests.get(u, stream=True, timeout=(30, 600))
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        if total < 1_000_000_000:
            print(f'文件太小: {total} bytes, 换下一个')
            continue
        with open('/root/.cache/sam/sam_vit_l_0b3195.pth', 'wb') as f:
            for chunk in r.iter_content(1048576):
                if chunk: f.write(chunk)
        size = __import__('os').path.getsize('/root/.cache/sam/sam_vit_l_0b3195.pth')
        print(f'✅ 下载完成: {size/1e6:.0f}MB')
        sys.exit(0)
    except Exception as e:
        print(f'失败: {e}')
        continue
print('⚠ 所有镜像失败，可在首次使用时网页触发下载')
"; \
    else \
        echo "[Docker] SAM 模型未预下载 (设置 DOWNLOAD_SAM=true 启用)"; \
    fi

# 环境变量
ENV PORT=8001
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/api/health').raise_for_status()" || exit 1

# 启动
CMD ["python", "main.py"]
