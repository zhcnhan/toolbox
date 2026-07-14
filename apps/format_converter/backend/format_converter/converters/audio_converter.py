"""音频格式转换。

所有音频格式通过 pydub 的 AudioSegment 中转。
"""

from __future__ import annotations

import logging
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# pydub 格式名映射
_FORMAT_MAP: dict[str, str] = {
    "mp3": "mp3",
    "wav": "wav",
    "flac": "flac",
    "ogg": "ogg",
    "aac": "aac",
    "wma": "wma",
    "m4a": "ipod",  # pydub 中 m4a 对应 ipod
    "opus": "opus",
    "aiff": "aiff",
}


def load_audio(filepath: str, fmt: str) -> AudioSegment:
    """载入音频文件为 AudioSegment。"""
    return AudioSegment.from_file(filepath, format=_FORMAT_MAP.get(fmt, fmt))


def save_audio(audio: AudioSegment, filepath: str, fmt: str) -> None:
    """将 AudioSegment 导出为目标格式。"""
    export_fmt = _FORMAT_MAP.get(fmt, fmt)
    audio.export(filepath, format=export_fmt)
    logger.info("音频已导出: %s", filepath)
