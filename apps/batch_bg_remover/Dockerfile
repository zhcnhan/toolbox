# =========================================================================
# Batch Background Remover — 多阶段 Dockerfile
# 阶段1: 构建前端静态文件
# 阶段2: Python 运行环境 + 后端 + 前端静态文件
# =========================================================================

# ---- 阶段1: 构建前端 ----
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

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

# 安装系统依赖（rembg/onnxruntime 需要 libglib, libgl）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
# requirements.txt 不含 torch/transformers（可选，体积大）
# Docker 模式自动安装 CPU 版以支持 CLIPSeg 引擎
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir transformers && \
    pip install --no-cache-dir -r requirements.txt

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
