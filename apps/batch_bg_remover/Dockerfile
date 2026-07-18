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

# CLIPSeg 引擎依赖（可选，体积大 ~800MB）
# 默认不装。需要时用 --build-arg INSTALL_CLIPSEG=true 启用
ARG INSTALL_CLIPSEG=false
# 国内用户可设置 --build-arg HF_ENDPOINT=https://hf-mirror.com 加速模型下载
ARG HF_ENDPOINT=""
RUN if [ "$INSTALL_CLIPSEG" = "true" ]; then \
        echo "[Docker] Installing CLIPSeg deps (torch + transformers)..."; \
        pip install --no-cache-dir torch transformers && \
        echo "[Docker] Pre-caching CLIPSeg model..."; \
        HF_ENDPOINT="${HF_ENDPOINT:-https://huggingface.co}" \
        python3 -c "\
import os; \
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'; \
print(f'[Docker] Downloading from: {os.environ.get(\"HF_ENDPOINT\", \"https://huggingface.co\")}'); \
from transformers import CLIPSegProcessor, CLIPSegForImageSegmentation; \
CLIPSegProcessor.from_pretrained('CIDAS/clipseg-rd64-refined', local_files_only=False); \
CLIPSegForImageSegmentation.from_pretrained('CIDAS/clipseg-rd64-refined', local_files_only=False)\
"; \
    else \
        echo "[Docker] Skipping CLIPSeg deps (INSTALL_CLIPSEG=false)."; \
    fi

# 复制后端代码
COPY backend/ /app/

# 从阶段1复制前端构建产物
COPY --from=frontend-builder /build/backend/static /app/static

# 创建上传和输出目录
RUN mkdir -p /app/uploads /app/outputs

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
