# ============================================================
# Format Converter — Docker 部署（傻瓜式一键部署）
# 包含：FFmpeg + LibreOffice + GTK3 + 所有 Python 依赖 + 测试资源
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
LABEL description="Format Converter — 万能格式转换服务（含 FFmpeg + LibreOffice + GTK3）"

# 系统依赖：FFmpeg + LibreOffice + GTK3 + Cairo + 字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 音视频编解码
    ffmpeg \
    # 文档转换 (LibreOffice headless)
    libreoffice \
    libreoffice-writer \
    # GTK3 / Cairo (SVG 渲染 + WeasyPrint)
    libgl1-mesa-glx \
    libglib2.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # 字体（中文支持）
    fonts-dejavu-core \
    fonts-liberation \
    fonts-noto-cjk \
    # 工具
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 后端代码
COPY backend/ ./

# 前端构建产物
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# 测试资源（包含测试脚本和转换前样例文件）
COPY test_resources/ ./test_resources/

# 上传和输出目录
RUN mkdir -p /tmp/format_converter_uploads /tmp/format_converter_outputs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "format_converter.main:app", "--host", "0.0.0.0", "--port", "8000"]
