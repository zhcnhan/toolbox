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

# 询问是否启用 CLIPSeg
read -p "是否启用 CLIPSeg 提示词分割引擎？(需 ~800MB 额外空间) [y/N]: " enable_clipseg
if [[ "$enable_clipseg" =~ ^[Yy]$ ]]; then
    CLIPSEG_ARG="--build-arg INSTALL_CLIPSEG=true"
    echo "[Info] 已启用 CLIPSeg (构建时预下载模型，首次使用免等待)"
else
    CLIPSEG_ARG=""
    echo "[Info] 未启用 CLIPSeg"
fi

# 确保数据目录
mkdir -p data/uploads data/outputs data/.u2net data/proxy

# 构建并启动
echo ""
echo "[Build] 构建镜像 (首次约 5-15 分钟，取决于网络)..."
docker compose build $CLIPSEG_ARG

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
