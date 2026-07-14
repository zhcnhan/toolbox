"""图片格式转换器。

基于 Pillow (PIL Fork)。
支持 JPG、PNG、WEBP、BMP、GIF、TIFF、ICO 等格式。

依赖：
  - Pillow — Historical Permission Notice and Disclaimer (HPND) License
    https://github.com/python-pillow/Pillow

格式兼容性说明：
  - GIF → 其他: 提取第一帧
  - → GIF: 保存为动画的单帧 GIF
  - → JPG: 自动移除 Alpha 通道（转为白色背景）
  - → ICO: 自动调整为最接近的标准尺寸
"""

from pathlib import Path
from typing import Callable, Optional

from PIL import Image


# ── 格式映射 ──────────────────────────────────────────────

FORMAT_MAP: dict[str, str] = {
    "jpg":   "JPEG",
    "jpeg":  "JPEG",
    "png":   "PNG",
    "webp":  "WEBP",
    "bmp":   "BMP",
    "gif":   "GIF",
    "tiff":  "TIFF",
    "ico":   "ICO",
    "ppm":   "PPM",
}

SAVE_OPTIONS: dict[str, dict] = {
    "JPEG": {"quality": 90, "optimize": True},
    "PNG":  {"optimize": True},
    "WEBP": {"quality": 85},
    "GIF":  {},
    "BMP":  {},
    "TIFF": {"compression": "tiff_lzw"},
    "ICO":  {},
}


def convert_image(
    input_path: str,
    output_path: str,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> None:
    """转换图片格式。

    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        progress_callback: 进度回调
    """
    if progress_callback:
        progress_callback(0)

    img = Image.open(input_path)
    if progress_callback:
        progress_callback(30)

    # 处理 GIF：取第一帧
    if getattr(img, "is_animated", False):
        img.seek(0)

    # 确定目标格式
    suffix = Path(output_path).suffix.lower().lstrip(".")
    fmt = FORMAT_MAP.get(suffix)
    if not fmt:
        raise ValueError(f"不支持的图片输出格式: {suffix}")

    save_kwargs = SAVE_OPTIONS.get(fmt, {}).copy()

    # RGBA → RGB（JPEG 不支持 Alpha 通道）
    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        elif img.mode == "P":
            img = img.convert("RGBA")
            background.paste(img, mask=img.split()[3])
        img = background

    # ICO 自动调整尺寸
    if fmt == "ICO":
        img = _resize_for_ico(img)

    # 保存
    if progress_callback:
        progress_callback(70)

    img.save(output_path, format=fmt, **save_kwargs)
    img.close()

    if progress_callback:
        progress_callback(100)


def _resize_for_ico(img: Image.Image) -> Image.Image:
    """将图片调整为 ICO 最接近的标准尺寸。"""
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    w, h = img.size
    if w == h and (w, h) in ico_sizes:
        return img
    # 选择最接近的正方形尺寸
    target = min(ico_sizes, key=lambda s: abs(s[0] - max(w, h)))
    return img.resize(target, Image.LANCZOS)
