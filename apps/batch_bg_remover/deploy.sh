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

# 检查是否有历史选择记录
if [ -f .env ]; then
    source .env
fi

# 询问是否启用 CLIPSeg（默认不装，需要 ~800MB 额外空间和 torch）
if [ "${INSTALL_CLIPSEG:-}" = "true" ]; then
    echo ""
    echo "[Info] 检测到上次部署已启用 CLIPSeg"
    read -p "是否保持启用？[Y/n]: " keep_clipseg
    if [[ "$keep_clipseg" =~ ^[Nn]$ ]]; then
        INSTALL_CLIPSEG="false"
    fi
else
    echo ""
    echo "[可选] CLIPSeg 提示词分割引擎"
    echo "  功能：用文字描述指定抠图主体（如「猫」「红色汽车」）"
    echo "  注意：需额外下载 ~800MB（torch + transformers），构建时间较长"
    echo "  不装不影响核心抠图功能，用 rembg 本地引擎即可"
    read -p "是否启用？[y/N] (默认不装): " enable_clipseg
    if [[ "$enable_clipseg" =~ ^[Yy]$ ]]; then
        INSTALL_CLIPSEG="true"
    fi
fi

if [ "$INSTALL_CLIPSEG" = "true" ]; then
    # 询问是否使用 HuggingFace 国内镜像（仅首次需要，后续记住）
    if [ ! -f .env ]; then
        read -p "是否使用 HuggingFace 国内镜像加速下载？(国内服务器推荐) [y/N]: " use_mirror
        if [[ "$use_mirror" =~ ^[Yy]$ ]]; then
            HF_ENDPOINT="https://hf-mirror.com"
        fi
    else
        source .env
    fi

    # 写入 .env 记住选择
    echo "INSTALL_CLIPSEG=true" > .env
    [ -n "${HF_ENDPOINT:-}" ] && echo "HF_ENDPOINT=$HF_ENDPOINT" >> .env
    CLIPSEG_ARG="--build-arg INSTALL_CLIPSEG=true"
    [ -n "${HF_ENDPOINT:-}" ] && CLIPSEG_ARG="$CLIPSEG_ARG --build-arg HF_ENDPOINT=$HF_ENDPOINT"
    echo "[OK] CLIPSeg 已启用 (已保存到 .env，后续重建自动沿用)"
else
    echo "INSTALL_CLIPSEG=false" > .env
    CLIPSEG_ARG=""
    echo "[OK] CLIPSeg 未启用 (随时可重建：docker compose build --build-arg INSTALL_CLIPSEG=true)"
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
