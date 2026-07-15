"""图片格式转换。

基于 Pillow 实现，支持常见格式互转。
"""

from __future__ import annotations

import logging
from PIL import Image

logger = logging.getLogger(__name__)

_FORMAT_MAP: dict[str, str] = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "ico": "ICO",
    "tiff": "TIFF",
}

_SAVE_OPTIONS: dict[str, dict] = {
    "jpg": {"quality": 92, "optimize": True},
    "webp": {"quality": 85},
    "png": {"optimize": True},
}


def convert_image(
    input_path: str,
    output_path: str,
    src_fmt: str,
    dst_fmt: str,
) -> None:
    """转换单张图片。"""
    pil_fmt = _FORMAT_MAP.get(dst_fmt, dst_fmt.upper())

    # SVG input — rasterize via cairosvg first (Pillow can't open SVG)
    if src_fmt == "svg":
        try:
            import cairosvg
            import io
            png_bytes = cairosvg.svg2png(url=input_path, output_width=1024, output_height=1024)
            img = Image.open(io.BytesIO(png_bytes))
        except ImportError:
            raise RuntimeError("SVG 转换需要安装 cairosvg (pip install cairosvg)")
    else:
        img = Image.open(input_path)

    # GIF 动图 → 静态格式：取第一帧
    if getattr(img, "is_animated", False) and dst_fmt != "gif":
        img.seek(0)

    # RGBA → RGB（JPEG/BMP 等不支持透明通道）
    if img.mode in ("RGBA", "P") and pil_fmt in ("JPEG", "BMP"):
        img = img.convert("RGB")
    elif img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGB")

    # ICO 尺寸限制
    if dst_fmt == "ico":
        img = img.resize((min(img.width, 256), min(img.height, 256)), Image.LANCZOS)

    save_kwargs = _SAVE_OPTIONS.get(dst_fmt, {})
    if pil_fmt == "JPEG" and img.mode == "RGBA":
        img = img.convert("RGB")

    img.save(output_path, format=pil_fmt, **save_kwargs)
    logger.info("图片已转换: %s → %s", input_path, output_path)
