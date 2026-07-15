"""视频格式转换。

通过 ffmpeg 子进程实现，支持进度回调。
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Callable

import ffmpeg

logger = logging.getLogger(__name__)

_VIDEO_CODEC_MAP: dict[str, str] = {
    "mp4": "libx264",
    "avi": "libxvid",
    "mkv": "libx264",
    "mov": "libx264",
    "webm": "libvpx-vp9",
    "flv": "flv",
    "wmv": "wmv2",
}

# 某些格式容器需要用特定 muxer
_FORMAT_KWARGS: dict[str, dict] = {
    "mov": {"movflags": "+faststart"},
}


def _get_duration(input_path: str) -> float:
    """用 ffprobe 获取视频时长（秒）。"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", input_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip() or 0)
    except Exception:
        return 0


def convert_video(
    input_path: str,
    output_path: str,
    src_fmt: str | None = None,
    dst_fmt: str | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> None:
    """转换视频文件。"""
    vcodec = _VIDEO_CODEC_MAP.get(dst_fmt or "mp4", "libx264")
    extra = _FORMAT_KWARGS.get(dst_fmt or "", {})

    duration = _get_duration(input_path)
    logger.info("视频时长: %.1fs, 编码器: %s", duration, vcodec)

    # 构建 ffmpeg 流
    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(stream, output_path, vcodec=vcodec, acodec="aac", progress="pipe:1", **extra)

    args = ffmpeg.compile(stream, overwrite_output=True)

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout to prevent pipe deadlock
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )

    time_pattern = re.compile(r"out_time_ms=(\d+)")
    all_output = []
    for line in process.stdout:
        all_output.append(line)
        if progress_callback and duration > 0:
            match = time_pattern.search(line)
            if match:
                ms = int(match.group(1))
                progress = min(ms / (duration * 1_000_000), 0.99)
                progress_callback(progress)

    process.wait()

    if process.returncode != 0:
        # Use last 30 lines of combined output for error diagnosis
        tail = "".join(all_output[-30:])
        raise RuntimeError(f"ffmpeg 转换失败 (code={process.returncode}): {tail}")

    if progress_callback:
        progress_callback(1.0)

    logger.info("视频已转换: %s → %s", input_path, output_path)
