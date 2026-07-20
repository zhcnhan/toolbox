#!/bin/bash
# =========================================================================
# Batch Background Remover — 一键部署脚本
# 用法: chmod +x deploy.sh && ./deploy.sh
# =========================================================================
set -e

echo "=========================================="
echo "  Batch Background Remover - 一键部署"
echo "=========================================="

# 检测 Docker
if ! command -v docker &>/dev/null; then
    echo "[Error] 未安装 Docker，请先安装:"
    echo "  curl -fsSL https://get.docker.com | sudo sh"
    exit 1
fi

# 检测 Docker Compose
if ! docker compose version &>/dev/null; then
    echo "[Error] 未安装 Docker Compose v2"
    exit 1
fi

# 确保数据目录
mkdir -p data/uploads data/outputs data/.u2net data/proxy data/sam_models

# 检查是否有历史选择记录
if [ -f .env ]; then
    source .env
fi

# 询问是否预下载 SAM 模型（可选，~1.25GB）
echo ""
echo "[可选] SAM 1 ViT-L 本地分割模型"
echo "  功能：高精度 AI 抠图，支持文本提示词选取特定物体"
echo "  需下载模型文件约 1.25GB"
echo "  不下载也能之后在网页上首次使用 SAM 引擎时自动下载"
if [ "${DOWNLOAD_SAM:-}" = "true" ]; then
    echo "  上次部署已选择下载，是否保持？"
    read -p "  保持预下载？[Y/n]: " keep_sam
    if [[ "$keep_sam" =~ ^[Nn]$ ]]; then
        DOWNLOAD_SAM="false"
    fi
else
    read -p "  是否现在下载？（推荐）[Y/n]: " dl_sam
    if [[ ! "$dl_sam" =~ ^[Nn]$ ]]; then
        DOWNLOAD_SAM="true"
    else
        DOWNLOAD_SAM="false"
    fi
fi

echo "DOWNLOAD_SAM=$DOWNLOAD_SAM" > .env

# 构建镜像（带 SAM 参数）
BUILD_ARGS=""
if [ "$DOWNLOAD_SAM" = "true" ]; then
    BUILD_ARGS="--build-arg DOWNLOAD_SAM=true"
    echo "[OK] SAM 模型将包含在镜像中（构建时间较长，约 10-20 分钟）"
fi

echo ""
echo "[Build] 构建镜像 (首次约 5-15 分钟，取决于网络)..."
docker compose build $BUILD_ARGS

echo ""
echo "[Start] 启动容器..."
docker compose up -d

echo ""
echo "=========================================="
echo "  部署完成！"
echo "  访问地址: http://localhost:8001"
echo "  容器状态: docker compose ps"
echo "  实时日志: docker compose logs -f"
echo "=========================================="
