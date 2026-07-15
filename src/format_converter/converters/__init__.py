"""格式转换器统一调度模块。

将各类转换器注册为统一入口，提供 convert_file() 函数。
"""

from typing import Any, Callable, Optional

from format_converter.utils.file_utils import detect_format, detect_category

# ── 注册表：格式名 → (加载函数, 导出函数) ──────────────────

_converter_registry: dict[str, tuple[Callable, Callable]] = {}


def register_converter(fmt: str, loader: Callable, dumper: Callable):
    """注册一个格式转换器。"""
    _converter_registry[fmt] = (loader, dumper)


# ── 注册数据格式转换器 ──────────────────────────────────────

from format_converter.converters.data.json_converter import loads as json_loads, dumps as json_dumps
from format_converter.converters.data.yaml_converter import loads as yaml_loads, dumps as yaml_dumps
from format_converter.converters.data.csv_converter import loads as csv_loads, dumps as csv_dumps
from format_converter.converters.data.xml_converter import loads as xml_loads, dumps as xml_dumps
from format_converter.converters.data.toml_converter import loads as toml_loads, dumps as toml_dumps

register_converter("json", json_loads, json_dumps)
register_converter("yaml", yaml_loads, yaml_dumps)
register_converter("csv", csv_loads, csv_dumps)
register_converter("xml", xml_loads, xml_dumps)
register_converter("toml", toml_loads, toml_dumps)

# ── 注册媒体格式转换器 ──────────────────────────────────────

from format_converter.converters.audio_converter import load_audio, save_audio
from format_converter.converters.video_converter import convert_video
from format_converter.converters.image_converter import convert_image

# 音频：通过 pydub 中转
register_converter("mp3", load_audio, lambda data, path: save_audio(data, path, "mp3"))
register_converter("wav", load_audio, lambda data, path: save_audio(data, path, "wav"))
register_converter("flac", load_audio, lambda data, path: save_audio(data, path, "flac"))
register_converter("ogg", load_audio, lambda data, path: save_audio(data, path, "ogg"))
register_converter("aac", load_audio, lambda data, path: save_audio(data, path, "aac"))
register_converter("m4a", load_audio, lambda data, path: save_audio(data, path, "m4a"))
register_converter("wma", load_audio, lambda data, path: save_audio(data, path, "wma"))
register_converter("opus", load_audio, lambda data, path: save_audio(data, path, "opus"))
register_converter("aiff", load_audio, lambda data, path: save_audio(data, path, "aiff"))
register_converter("ac3", load_audio, lambda data, path: save_audio(data, path, "ac3"))


def convert_file(
    input_path: str,
    source_fmt: str,
    target_fmt: str,
    output_path: str,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> str:
    """统一转换入口。

    根据源格式和目标格式的类别，选择对应的转换策略：
    - 数据格式：解析→Python对象→序列化（纯文本管道）
    - 音频格式：pydub 加载→导出
    - 视频格式：ffmpeg 管道转换
    - 图片格式：Pillow 加载→保存

    Args:
        input_path: 输入文件路径
        source_fmt: 源格式（如 'json', 'mp4', 'png'）
        target_fmt: 目标格式
        output_path: 输出文件路径
        progress_callback: 进度回调 (0-100)

    Returns:
        输出文件路径
    """
    if source_fmt == target_fmt:
        raise ValueError(f"源格式与目标格式相同 ({source_fmt})")

    src_cat = detect_category(source_fmt)
    dst_cat = detect_category(target_fmt)

    # ── 数据格式互转 ──────────────────────────────────────
    if src_cat == "data" and dst_cat == "data":
        from format_converter.utils.file_utils import read_file, write_file
        loader, _ = _converter_registry[source_fmt]
        _, dumper = _converter_registry[target_fmt]
        raw = read_file(input_path)
        data = loader(raw)
        output = dumper(data)
        write_file(output_path, output)
        if progress_callback:
            progress_callback(100)
        return output_path

    # ── 图片格式互转 ──────────────────────────────────────
    if src_cat == "image" and dst_cat == "image":
        convert_image(input_path, output_path, progress_callback)
        return output_path

    # ── 音频格式互转 ──────────────────────────────────────
    if src_cat == "audio" and dst_cat == "audio":
        audio_data = load_audio(input_path)
        save_audio(audio_data, output_path, target_fmt)
        if progress_callback:
            progress_callback(100)
        return output_path

    # ── 视频格式互转 ──────────────────────────────────────
    if src_cat == "video" and dst_cat == "video":
        convert_video(input_path, output_path, target_fmt, progress_callback)
        return output_path

    raise ValueError(
        f"不支持的跨类别转换：{source_fmt}({src_cat}) → {target_fmt}({dst_cat})"
    )
