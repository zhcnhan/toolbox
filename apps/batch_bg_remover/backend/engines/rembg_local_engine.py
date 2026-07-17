"""
engines/rembg_local_engine.py — 本地自动抠图引擎

基于 rembg (https://github.com/danielgatis/rembg)，19k+ stars
使用 U2-Net / ISNet 等模型，CPU 即可运行，无需 API Key

安装依赖：pip install rembg[cpu] onnxruntime
"""

import io
from PIL import Image
from engine_base import BaseEngine, EngineInfo
from engine_registry import register_engine


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
