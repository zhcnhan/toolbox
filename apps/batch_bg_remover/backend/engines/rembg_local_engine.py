"""
engines/rembg_local_engine.py — 本地自动抠图引擎

基于 rembg (https://github.com/danielgatis/rembg)，19k+ stars
使用 U2-Net / ISNet 等模型，CPU 即可运行，无需 API Key

安装依赖：pip install rembg[cpu] onnxruntime
"""

import io
import os
from pathlib import Path
from PIL import Image
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine


def _ensure_u2net_model():
    """
    确保 U2Net 模型已下载。
    如果 ~/.u2net/u2net.onnx 不存在，从国内镜像预下载，
    避免 rembg 首次使用时从 GitHub 下载超时。
    """
    model_dir = Path.home() / ".u2net"
    model_path = model_dir / "u2net.onnx"
    if model_path.exists() and model_path.stat().st_size > 1_000_000:
        return True  # 已存在

    model_dir.mkdir(parents=True, exist_ok=True)
    mirror_url = "https://hf-mirror.com/datasets/heng881/rembg-model/resolve/main/u2net.onnx"

    import urllib.request
    try:
        print(f"[rembg] 正在从镜像下载 U2Net 模型...")
        urllib.request.urlretrieve(mirror_url, str(model_path))
        print(f"[rembg] 模型下载完成 ({model_path.stat().st_size / 1024 / 1024:.0f}MB)")
        return True
    except Exception as e:
        print(f"[rembg] 镜像下载失败 ({e})，rembg 将尝试官方源")
        return False


def _safe_import_rembg():
    """
    安全导入 rembg。
    rembg 在缺少 onnxruntime 时会调用 sys.exit(1)，
    我们捕获 SystemExit 并转换为友好的 RuntimeError。
    """
    try:
        import rembg
        return rembg
    except SystemExit:
        raise RuntimeError(
            "rembg 缺少 onnxruntime 后端。请运行: pip install onnxruntime "
            "(CPU) 或 pip install rembg[gpu] (NVIDIA GPU)"
        )
    except ImportError as e:
        raise RuntimeError(f"rembg 未安装: {e}. 请运行: pip install rembg[cpu]")


@register_engine("rembg_local")
class RembgLocalEngine(BaseEngine):
    """本地 rembg 自动抠图引擎"""

    _instance = None

    def __init__(self):
        # 懒加载 rembg，首次调用时才 import（避免启动慢）
        self._session = None
        self._rembg = None

    def _get_rembg(self):
        """懒加载 rembg 模块"""
        if self._rembg is None:
            self._rembg = _safe_import_rembg()
        return self._rembg

    def _get_session(self):
        if self._session is None:
            # 确保模型已下载（优先从国内镜像下载，避免 GitHub 超时）
            _ensure_u2net_model()
            rembg = self._get_rembg()
            # u2net 是通用模型，效果好且轻量
            # 也可用 "birefnet-general" 追求更高精度（需额外下载模型）
            self._session = rembg.new_session("u2net")
        return self._session

    @classmethod
    def info(cls) -> EngineInfo:
        return EngineInfo(
            id="rembg_local",
            name="rembg (本地)",
            description="基于 U2-Net 深度学习模型，CPU 即可运行，无需联网。适合人物、产品、动物等主体明确的图片。",
            type="local",
            supports_auto=True,
            supports_prompt=False,
            needs_api_key=False,
            icon="🖥️",
        )

    async def remove_bg(self, image_bytes: bytes, api_key: str | None = None) -> bytes:
        """自动抠图"""
        rembg = self._get_rembg()
        session = self._get_session()

        # rembg.remove 接受 PIL Image 或 bytes
        result = rembg.remove(image_bytes, session=session)
        return result

    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: str | None = None
    ) -> bytes:
        """rembg 不支持提示词分割，抛出异常"""
        raise NotImplementedError("rembg 不支持提示词选取主体，请使用 CLIPSeg 或云端引擎")
