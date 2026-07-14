"""文件工具：格式检测、扩展名映射、路径处理。"""

from pathlib import Path
from typing import Optional

# ── 扩展名 → 格式名 ──────────────────────────────────────────

_EXT_TO_FMT: dict[str, str] = {
    # 数据格式
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".csv": "csv",
    ".xml": "xml",
    ".toml": "toml",
    # 音频格式
    ".mp3": "mp3",
    ".wav": "wav",
    ".flac": "flac",
    ".ogg": "ogg",
    ".aac": "aac",
    ".m4a": "m4a",
    ".wma": "wma",
    ".opus": "opus",
    ".aiff": "aiff",
    ".aif": "aiff",
    ".ac3": "ac3",
    ".ape": "ape",
    ".wv": "wv",
    # 视频格式
    ".mp4": "mp4",
    ".avi": "avi",
    ".mkv": "mkv",
    ".mov": "mov",
    ".webm": "webm",
    ".flv": "flv",
    ".wmv": "wmv",
    ".m4v": "m4v",
    ".3gp": "3gp",
    ".ts": "ts",
    # 图片格式
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
    ".webp": "webp",
    ".bmp": "bmp",
    ".gif": "gif",
    ".tiff": "tiff",
    ".tif": "tiff",
    ".ico": "ico",
    ".ppm": "ppm",
    ".pcx": "pcx",
    ".tga": "tga",
}

# ── 格式名 → 默认扩展名 ─────────────────────────────────────

_FMT_TO_EXT: dict[str, str] = {
    "json": ".json",
    "yaml": ".yaml",
    "csv": ".csv",
    "xml": ".xml",
    "toml": ".toml",
    "mp3": ".mp3",
    "wav": ".wav",
    "flac": ".flac",
    "ogg": ".ogg",
    "aac": ".aac",
    "m4a": ".m4a",
    "wma": ".wma",
    "opus": ".opus",
    "aiff": ".aiff",
    "ac3": ".ac3",
    "ape": ".ape",
    "wv": ".wv",
    "mp4": ".mp4",
    "avi": ".avi",
    "mkv": ".mkv",
    "mov": ".mov",
    "webm": ".webm",
    "flv": ".flv",
    "wmv": ".wmv",
    "m4v": ".m4v",
    "3gp": ".3gp",
    "ts": ".ts",
    "jpg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "bmp": ".bmp",
    "gif": ".gif",
    "tiff": ".tiff",
    "ico": ".ico",
}

# ── 格式分类 ────────────────────────────────────────────────

FORMAT_CATEGORIES: dict[str, list[str]] = {
    "data":  ["json", "yaml", "csv", "xml", "toml"],
    "audio": ["mp3", "wav", "flac", "ogg", "aac", "m4a", "wma", "opus", "aiff", "ac3"],
    "video": ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv"],
    "image": ["jpg", "png", "webp", "bmp", "gif", "tiff", "ico"],
}

# ── 可输出格式（部分格式只作为输入源）──────────────────────

OUTPUT_FORMATS: dict[str, list[str]] = {
    "data":  ["json", "yaml", "csv", "xml", "toml"],
    "audio": ["mp3", "wav", "flac", "ogg", "aac", "m4a"],
    "video": ["mp4", "avi", "mkv", "mov", "webm"],
    "image": ["jpg", "png", "webp", "bmp", "gif", "tiff", "ico"],
}

# 输入格式（所有已知格式均可作为输入）
INPUT_FORMATS: dict[str, list[str]] = {
    "data":  ["json", "yaml", "csv", "xml", "toml"],
    "audio": ["mp3", "wav", "flac", "ogg", "aac", "m4a", "wma", "opus", "aiff", "ac3"],
    "video": ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv"],
    "image": ["jpg", "png", "webp", "bmp", "gif", "tiff", "ico"],
}

# ── 文件过滤器（用于 QFileDialog）─────────────────────────

CATEGORY_FILTERS: dict[str, str] = {
    "data":  "数据文件 (*.json *.yaml *.yml *.csv *.xml *.toml)",
    "audio": "音频文件 (*.mp3 *.wav *.flac *.ogg *.aac *.m4a *.wma *.opus *.aiff *.ac3)",
    "video": "视频文件 (*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv)",
    "image": "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tiff *.tif *.ico)",
}


def detect_format(filepath: str | Path) -> Optional[str]:
    """根据文件扩展名检测格式。"""
    suffix = Path(filepath).suffix.lower()
    return _EXT_TO_FMT.get(suffix)


def detect_category(fmt: str) -> Optional[str]:
    """根据格式名返回所属分类。"""
    for cat, fmts in FORMAT_CATEGORIES.items():
        if fmt in fmts:
            return cat
    return None


def get_extension(fmt: str) -> str:
    """获取格式对应的默认扩展名。"""
    return _FMT_TO_EXT.get(fmt, f".{fmt}")


def make_output_path(input_path: str | Path, target_fmt: str, output_dir: str | Path | None = None) -> Path:
    """根据输入路径和目标格式生成输出路径。"""
    p = Path(input_path)
    ext = get_extension(target_fmt)
    if output_dir:
        return Path(output_dir) / f"{p.stem}{ext}"
    return p.with_suffix(ext)


def read_file(filepath: str | Path) -> str:
    """读取文本文件（UTF-8）。"""
    return Path(filepath).read_text(encoding="utf-8")


def write_file(filepath: str | Path, content: str) -> None:
    """写入文本文件（UTF-8）。"""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def read_bytes(filepath: str | Path) -> bytes:
    """读取二进制文件。"""
    return Path(filepath).read_bytes()


def write_bytes(filepath: str | Path, data: bytes) -> None:
    """写入二进制文件。"""
    p = Path(filepath)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
