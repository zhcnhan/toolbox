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


_U2NET_MIRRORS = [
    # 1. GitHub 代理镜像1（优先，国内访问快）
    "https://ghproxy.net/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
    # 2. GitHub 代理镜像2
    "https://gh-proxy.com/https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
    # 3. GitHub 官方源（直连，国内可能被墙）
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
    # 4. HuggingFace 镜像（兜底）
    "https://hf-mirror.com/tomjackson2023/rembg/resolve/main/u2net.onnx",
]


def _ensure_u2net_model():
    """
    确保 U2Net 模型已下载。
    从多个镜像依次尝试下载，全部失败则让 rembg 自己处理。
    """
    model_dir = Path.home() / ".u2net"
    model_path = model_dir / "u2net.onnx"
    if model_path.exists() and model_path.stat().st_size > 50_000_000:
        return True  # 已存在（u2net.onnx 约 176MB）

    model_dir.mkdir(parents=True, exist_ok=True)

    import urllib.request

    for i, url in enumerate(_U2NET_MIRRORS):
        try:
            print(f"[rembg] 正在下载 U2Net 模型 ({i+1}/{len(_U2NET_MIRRORS)})...")
            # 设置超时：60s 连接 + 600s 传输
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=(60, 600)) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(model_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded / total * 100)
                            if pct % 25 == 0:
                                print(f"[rembg]   {pct}% ({downloaded/1024/1024:.0f}MB)")
            size = model_path.stat().st_size
            if size > 50_000_000:
                print(f"[rembg] ✅ 模型下载完成 ({size/1024/1024:.0f}MB)")
                return True
            else:
                model_path.unlink(missing_ok=True)
                print(f"[rembg] ⚠ 下载文件太小 ({size} bytes)，尝试下一个源")
        except Exception as e:
            print(f"[rembg] ⚠ 源 {i+1} 失败: {type(e).__name__}")
            model_path.unlink(missing_ok=True)

    print(f"[rembg] ❌ 所有镜像都失败，rembg 将尝试官方源")
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
