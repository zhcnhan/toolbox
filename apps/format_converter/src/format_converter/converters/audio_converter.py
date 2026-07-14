"""音频格式转换器。

基于 pydub，底层调用 ffmpeg/libav。
支持 MP3、WAV、FLAC、OGG、AAC、M4A、WMA、Opus、AIFF、AC3 等格式。

依赖：
  - pydub — MIT License
    https://github.com/jiaaro/pydub
  - ffmpeg — LGPL/GPL License (需单独安装到系统 PATH)
    https://ffmpeg.org/
"""

from typing import Any

from pydub import AudioSegment


def load_audio(filepath: str) -> AudioSegment:
    """加载音频文件为 pydub AudioSegment 对象。

    支持所有 ffmpeg 能解码的音频格式。
    """
    return AudioSegment.from_file(filepath)


def save_audio(audio: AudioSegment, output_path: str, fmt: str) -> None:
    """将 AudioSegment 导出为指定格式。

    Args:
        audio: pydub AudioSegment 对象
        output_path: 输出文件路径
        fmt: 目标格式（如 'mp3', 'wav', 'flac', 'ogg'）
    """
    format_map = {
        "mp3":  "mp3",
        "wav":  "wav",
        "flac": "flac",
        "ogg":  "ogg",
        "aac":  "aac",
        "m4a":  "ipod",    # pydub 用 'ipod' 表示 m4a
        "wma":  "wma",
        "opus": "opus",
        "aiff": "aiff",
        "ac3":  "ac3",
    }
    export_format = format_map.get(fmt, fmt)
    audio.export(output_path, format=export_format)
