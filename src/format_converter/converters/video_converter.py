"""视频格式转换器。

基于 ffmpeg-python，底层调用 ffmpeg。
支持 MP4、AVI、MKV、MOV、WEBM、FLV、WMV 等格式。

依赖：
  - ffmpeg-python — Apache-2.0 License
    https://github.com/kkroening/ffmpeg-python
  - ffmpeg — LGPL/GPL License (需单独安装到系统 PATH)
    https://ffmpeg.org/

视频编码器选择：
  - MP4:   libx264 (H.264)
  - AVI:   mpeg4
  - MKV:   libx264
  - MOV:   libx264
  - WEBM:  libvpx-vp9
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Callable, Optional

import ffmpeg


# ── 目标格式 → (编码器, 容器格式) ──────────────────────────

VIDEO_CODEC_MAP: dict[str, dict[str, str]] = {
    "mp4":   {"vcodec": "libx264", "acodec": "aac", "format": "mp4"},
    "avi":   {"vcodec": "mpeg4",  "acodec": "mp3", "format": "avi"},
    "mkv":   {"vcodec": "libx264", "acodec": "aac", "format": "matroska"},
    "mov":   {"vcodec": "libx264", "acodec": "aac", "format": "mov"},
    "webm":  {"vcodec": "libvpx-vp9", "acodec": "libopus", "format": "webm"},
    "flv":   {"vcodec": "flv",    "acodec": "mp3", "format": "flv"},
    "wmv":   {"vcodec": "wmv2",   "acodec": "wmav2", "format": "asf"},
}


def _get_duration(input_path: str) -> Optional[float]:
    """使用 ffprobe 获取视频时长（秒）。"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", input_path
            ],
            capture_output=True, text=True, timeout=10,
        )
        info = json.loads(result.stdout)
        return float(info["format"].get("duration", 0))
    except Exception:
        return None


def convert_video(
    input_path: str,
    output_path: str,
    target_fmt: str,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> None:
    """转换视频文件格式。

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        target_fmt: 目标格式
        progress_callback: 进度回调 (0-100)
    """
    codec_info = VIDEO_CODEC_MAP.get(target_fmt)
    if not codec_info:
        raise ValueError(f"不支持的视频输出格式: {target_fmt}")

    duration = _get_duration(input_path)

    # 构建 ffmpeg 流
    stream = ffmpeg.input(input_path)
    stream = ffmpeg.output(
        stream, output_path,
        vcodec=codec_info["vcodec"],
        acodec=codec_info["acodec"],
        format=codec_info["format"],
    )

    # 使用 subprocess 方式运行以支持进度解析
    args = ffmpeg.compile(stream, overwrite_output=True)
    args += ["-progress", "pipe:1", "-nostats"]

    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    last_pct = -1
    for line in process.stdout:
        if "out_time_ms=" in line:
            try:
                time_us = int(line.strip().split("=")[1])
                if duration and duration > 0:
                    pct = min(int(time_us / (duration * 1_000_000) * 100), 99)
                    if pct > last_pct and progress_callback:
                        progress_callback(pct)
                        last_pct = pct
            except (ValueError, IndexError):
                pass

    return_code = process.wait()
    if return_code != 0:
        stderr_output = process.stderr.read() if process.stderr else ""
        raise RuntimeError(f"ffmpeg 转换失败 (code={return_code}): {stderr_output[-500:]}")

    if progress_callback:
        progress_callback(100)
