"""音频格式转换。

所有音频格式通过 pydub 的 AudioSegment 中转。
使用 ffmpeg 作为后端编解码器。
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# pydub / ffmpeg 格式名映射
# 注意：ffmpeg 8.x 中某些格式名有变化
_FORMAT_MAP: dict[str, str] = {
    "mp3": "mp3",
    "wav": "wav",
    "flac": "flac",
    "ogg": "ogg",
    # AAC 原始流需要 ADTS 容器，ffmpeg 8.x 中 muxer 名为 adts
    "aac": "adts",
    # WMA 在 ffmpeg 中属于 asf 容器
    "wma": "asf",
    # M4A 使用 ipod/mp4 容器
    "m4a": "ipod",
    # Opus 在 ogg 容器中
    "opus": "ogg",
    "aiff": "aiff",
}

# 加载时的格式映射（某些格式需要不同的输入格式名）
_INPUT_FORMAT_MAP: dict[str, str] = {
    "mp3": "mp3",
    "wav": "wav",
    "flac": "flac",
    "ogg": "ogg",
    "aac": "aac",
    "wma": "asf",
    "m4a": "mp4",
    "opus": "ogg",
    "aiff": "aiff",
}


def _ensure_ffmpeg_in_path():
    """确保 ffmpeg 在 PATH 中（Windows 下可能需要手动添加）。"""
    if shutil.which("ffmpeg"):
        return

    # Windows 常见 ffmpeg 路径
    candidates = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
    ]
    for p in candidates:
        if os.path.exists(os.path.join(p, "ffmpeg.exe")):
            os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
            return


_ensure_ffmpeg_in_path()


def load_audio(filepath: str, fmt: str) -> AudioSegment:
    """载入音频文件为 AudioSegment。"""
    input_fmt = _INPUT_FORMAT_MAP.get(fmt, fmt)
    try:
        return AudioSegment.from_file(filepath, format=input_fmt)
    except Exception:
        # 回退：让 pydub 自动检测格式
        logger.warning("使用格式 '%s' 加载失败，尝试自动检测: %s", input_fmt, filepath)
        return AudioSegment.from_file(filepath)


def save_audio(audio: AudioSegment, filepath: str, fmt: str) -> None:
    """将 AudioSegment 导出为目标格式。"""
    export_fmt = _FORMAT_MAP.get(fmt, fmt)

    # AAC 特殊处理：如果导出为 adts 失败，回退到 m4a 容器
    if fmt == "aac":
        try:
            audio.export(filepath, format="adts")
            logger.info("音频已导出 (AAC/ADTS): %s", filepath)
            return
        except Exception:
            logger.warning("ADTS 导出失败，尝试 MP4 容器: %s", filepath)
            # 改扩展名为 .m4a 不行（会改文件名），用 mp4 容器但保持 .aac 扩展名
            audio.export(filepath, format="ipod", codec="aac")
            logger.info("音频已导出 (AAC/MP4): %s", filepath)
            return

    audio.export(filepath, format=export_fmt)
    logger.info("音频已导出: %s", filepath)
