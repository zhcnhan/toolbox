"""图片格式转换。

基于 Pillow 实现常见格式互转，SVG 通过 cairosvg/svglib 支持。
"""

from __future__ import annotations

import logging
import os
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


def _load_svg_as_image(input_path: str) -> Image.Image:
    """将 SVG 文件加载为 PIL Image。优先使用 cairosvg，回退到 svglib。"""
    import io

    # 确保 GTK3 运行时 DLL 可被找到（Windows）
    _gtk_paths = [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
    ]
    for p in _gtk_paths:
        if os.path.exists(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")

    # 方案 1: cairosvg
    try:
        import cairosvg
        png_data = cairosvg.svg2png(url=input_path, output_width=1024, output_height=1024)
        return Image.open(io.BytesIO(png_data))
    except Exception:
        pass

    # 方案 2: svglib + reportlab
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        drawing = svg2rlg(input_path)
        png_buf = io.BytesIO()
        renderPM.drawToFile(drawing, png_buf, fmt="PNG")
        png_buf.seek(0)
        return Image.open(png_buf)
    except Exception:
        pass

    # 方案 3: 用 ffmpeg 将 SVG 转为 PNG
    try:
        import subprocess
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-vf", "scale=1024:1024", tmp.name],
            capture_output=True, timeout=30,
        )
        if os.path.exists(tmp.name) and os.path.getsize(tmp.name) > 0:
            img = Image.open(tmp.name)
            os.unlink(tmp.name)
            return img
        os.unlink(tmp.name)
    except Exception:
        pass

    raise RuntimeError(
        "SVG 转换需要安装 cairosvg (需 GTK3 运行时) 或 svglib。"
        "请运行: pip install cairosvg 或 pip install svglib reportlab rlPyCairo"
    )


def convert_image(
    input_path: str,
    output_path: str,
    src_fmt: str,
    dst_fmt: str,
) -> None:
    """转换单张图片。"""
    pil_fmt = _FORMAT_MAP.get(dst_fmt, dst_fmt.upper())

    # SVG 输入特殊处理
    if src_fmt == "svg":
        img = _load_svg_as_image(input_path)
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
    logger.info("图片已转换: %s -> %s", input_path, output_path)
