"""视频格式转换。

直接通过 subprocess 调用 ffmpeg 实现，避免 ffmpeg-python 库的参数兼容问题。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from typing import Callable

logger = logging.getLogger(__name__)

# 视频编码器映射
_VIDEO_CODEC_MAP: dict[str, str] = {
    "mp4": "libx264",
    "avi": "mpeg4",
    "mkv": "libx264",
    "mov": "libx264",
    "webm": "libvpx",
    "flv": "flv",
    "wmv": "wmv2",
}

# 额外的 ffmpeg 输出参数
_OUTPUT_ARGS: dict[str, list[str]] = {
    "mp4":  ["-preset", "ultrafast", "-pix_fmt", "yuv420p"],
    "mkv":  ["-preset", "ultrafast", "-pix_fmt", "yuv420p"],
    "mov":  ["-preset", "ultrafast", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    "avi":  ["-q:v", "5"],
    "webm": ["-b:v", "512k", "-pix_fmt", "yuv420p"],
    "flv":  [],
    "wmv":  ["-q:v", "5"],
}


def _ensure_ffmpeg_in_path():
    """确保 ffmpeg 在 PATH 中。"""
    if shutil.which("ffmpeg"):
        return
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


def _probe(input_path: str) -> tuple[float, bool]:
    """获取视频时长和是否有音频流。"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-show_entries", "stream=codec_type",
             "-of", "json", input_path],
            capture_output=True, text=True, timeout=30,
        )
        import json
        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))
        streams = data.get("streams", [])
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        return duration, has_audio
    except Exception:
        return 0, False


def convert_video(
    input_path: str,
    output_path: str,
    src_fmt: str | None = None,
    dst_fmt: str | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> None:
    """转换视频文件。"""
    dst = dst_fmt or "mp4"
    vcodec = _VIDEO_CODEC_MAP.get(dst, "libx264")
    extra_args = _OUTPUT_ARGS.get(dst, [])

    duration, has_audio = _probe(input_path)
    logger.info("视频时长: %.1fs, 编码器: %s, 有音频: %s", duration, vcodec, has_audio)

    # 构建 ffmpeg 命令
    cmd = ["ffmpeg", "-y", "-i", input_path]
    cmd += ["-c:v", vcodec] + extra_args
    if has_audio:
        cmd += ["-c:a", "aac"]
    else:
        cmd += ["-an"]
    cmd += [output_path]

    logger.info("ffmpeg 命令: %s", " ".join(cmd))

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )

    # 解析进度
    time_pattern = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")
    stderr = process.stderr
    if stderr is not None:
        for line in stderr:
            if progress_callback and duration > 0:
                match = time_pattern.search(line)
                if match:
                    t = match.group(1)
                    h, m, s = t.split(":")
                    total_sec = int(h) * 3600 + int(m) * 60 + float(s)
                    progress = min(total_sec / duration, 0.99)
                    progress_callback(progress)

    process.wait()

    if process.returncode != 0:
        stderr = process.stderr.read() if process.stderr else ""
        # 提取最后的错误信息
        err_lines = [l for l in stderr.splitlines() if "Error" in l or "error" in l]
        err_msg = "\n".join(err_lines[-3:]) if err_lines else stderr[-500:]
        raise RuntimeError(f"ffmpeg 转换失败 (code={process.returncode}): {err_msg}")

    if progress_callback:
        progress_callback(1.0)

    logger.info("视频已转换: %s -> %s", input_path, output_path)
