"""
转换器注册中心。

每种格式的 loader / converter 在此注册，由 convert_file() 统一调度。
"""

from __future__ import annotations

import os
import logging
from typing import Any, Callable

from .data import (
    json_loads, json_dumps,
    yaml_loads, yaml_dumps,
    csv_loads, csv_dumps,
    xml_loads, xml_dumps,
    toml_loads, toml_dumps,
)

from ..utils import (
    detect_category, read_file, write_file,
    read_bytes, write_bytes,
)

logger = logging.getLogger(__name__)

# 懒加载重型依赖（pydub 在 Python 3.13+ 可能因 audioop 移除而不可用）
_audio_module = None
_video_module = None
_image_module = None
_document_module = None

_IMPORT_WARNINGS: set[str] = set()


def _warn_once(msg: str) -> None:
    if msg not in _IMPORT_WARNINGS:
        _IMPORT_WARNINGS.add(msg)
        logger.warning(msg)


def _get_audio():
    global _audio_module
    if _audio_module is None:
        try:
            from . import audio_converter as m
            _audio_module = m
        except ImportError as e:
            _warn_once(f"音频转换模块不可用（缺少 pydub/pyaudioop）: {e}")
            _audio_module = False
    return _audio_module if _audio_module is not False else None


def _get_image():
    global _image_module
    if _image_module is None:
        try:
            from . import image_converter as m
            _image_module = m
        except ImportError as e:
            _warn_once(f"图片转换模块不可用（缺少 Pillow）: {e}")
            _image_module = False
    return _image_module if _image_module is not False else None


def _get_video():
    global _video_module
    if _video_module is None:
        try:
            from . import video_converter as m
            _video_module = m
        except ImportError as e:
            _warn_once(f"视频转换模块不可用（缺少 ffmpeg-python）: {e}")
            _video_module = False
    return _video_module if _video_module is not False else None


def _get_document():
    global _document_module
    if _document_module is None:
        try:
            from . import document_converter as m
            _document_module = m
        except ImportError as e:
            _warn_once(f"文档转换模块不可用（缺少 pdf2docx 等依赖）: {e}")
            _document_module = False
    return _document_module if _document_module is not False else None

# ---------------------------------------------------------------------------
#  转换器注册表
#  loader: 将文件内容载入为中间对象；dumper: 将中间对象写为文件；converter: 文件级转换
# ---------------------------------------------------------------------------
Converter = Callable[..., Any]


def _convert_data(input_path: str, src_fmt: str, dst_fmt: str, output_path: str) -> None:
    """通用数据格式转换管道：load → dump"""
    loaders: dict[str, Callable[[str], Any]] = {
        "json": json_loads, "yaml": yaml_loads,
        "csv": csv_loads, "xml": xml_loads, "toml": toml_loads,
    }
    dumpers: dict[str, Callable[[Any], str]] = {
        "json": json_dumps, "yaml": yaml_dumps,
        "csv": csv_dumps, "xml": xml_dumps, "toml": toml_dumps,
    }

    raw = read_file(input_path)
    data = loaders[src_fmt](raw)
    result = dumpers[dst_fmt](data)
    write_file(output_path, result)


# ---------------------------------------------------------------------------
#  分类 → 处理函数映射（懒加载）
# ---------------------------------------------------------------------------


def convert_file(
    input_path: str,
    src_fmt: str,
    dst_fmt: str,
    output_path: str,
    progress_callback: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """转换单个文件。

    Returns:
        {"success": bool, "output": str, "error": str | None}
    """
    category = detect_category(src_fmt)
    if category is None:
        return {"success": False, "output": output_path, "error": f"不支持的源格式: {src_fmt}"}

    try:
        if category == "audio":
            m = _get_audio()
            if m is None:
                return {"success": False, "output": output_path, "error": "音频转换模块不可用（缺少 pydub）"}
            src = m.load_audio(input_path, src_fmt)
            m.save_audio(src, output_path, dst_fmt)
            if progress_callback:
                progress_callback(1.0)
        elif category == "video":
            m = _get_video()
            if m is None:
                return {"success": False, "output": output_path, "error": "视频转换模块不可用（缺少 ffmpeg-python）"}
            m.convert_video(input_path, output_path, src_fmt, dst_fmt, progress_callback)
        elif category == "image":
            m = _get_image()
            if m is None:
                return {"success": False, "output": output_path, "error": "图片转换模块不可用（缺少 Pillow）"}
            m.convert_image(input_path, output_path, src_fmt, dst_fmt)
            if progress_callback:
                progress_callback(1.0)
        elif category == "document":
            m = _get_document()
            if m is None:
                return {"success": False, "output": output_path, "error": "文档转换模块不可用（缺少 pdf2docx 等依赖）"}
            m.convert_document(input_path, output_path, src_fmt, dst_fmt)
            if progress_callback:
                progress_callback(1.0)
        else:
            _convert_data(input_path, src_fmt, dst_fmt, output_path)
            if progress_callback:
                progress_callback(1.0)

        return {"success": True, "output": output_path, "error": None}
    except Exception as exc:
        logger.exception("转换失败: %s → %s (%s → %s)", input_path, output_path, src_fmt, dst_fmt)
        return {"success": False, "output": output_path, "error": str(exc)}


def get_supported_conversions() -> list[dict[str, Any]]:
    """返回所有支持的转换路径列表。"""
    from ..utils import FORMAT_CATEGORIES, OUTPUT_FORMATS

    conversions: list[dict[str, Any]] = []
    for category, src_fmts in FORMAT_CATEGORIES.items():
        dst_fmts = OUTPUT_FORMATS.get(category, [])
        for src in src_fmts:
            for dst in dst_fmts:
                if src == dst:
                    continue
                conversions.append({
                    "category": category,
                    "source": src,
                    "target": dst,
                })
    return conversions
