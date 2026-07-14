# ============================================================
# Format Converter — Docker 部署
# ============================================================

# ---- 构建阶段：前端 ----
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 运行阶段 ----
FROM python:3.12-slim
LABEL maintainer="zhcnhan"
LABEL description="Format Converter — 万能格式转换服务"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/ .

# 前端构建产物
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# 上传和输出目录
RUN mkdir -p /tmp/format_converter_uploads /tmp/format_converter_outputs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "format_converter.main:app", "--host", "0.0.0.0", "--port", "8000"]
