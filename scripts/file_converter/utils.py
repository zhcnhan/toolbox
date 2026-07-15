"""文件工具：类型检测、读写辅助。"""

from pathlib import Path
from typing import Optional

# 扩展名 -> 格式名 映射
EXTENSION_MAP: dict[str, str] = {
    ".json":  "json",
    ".yaml":  "yaml",
    ".yml":   "yaml",
    ".csv":   "csv",
    ".xml":   "xml",
    ".toml":  "toml",
}

# 已知格式
SUPPORTED_FORMATS = sorted(set(EXTENSION_MAP.values()))

# 格式 -> 扩展名
FORMAT_EXTENSION: dict[str, str] = {
    "json": ".json",
    "yaml": ".yaml",
    "csv":  ".csv",
    "xml":  ".xml",
    "toml": ".toml",
}


def detect_format(filepath: str | Path) -> Optional[str]:
    """根据文件扩展名检测格式，返回格式名或 None。"""
    suffix = Path(filepath).suffix.lower()
    return EXTENSION_MAP.get(suffix)


def read_file(filepath: str | Path) -> str:
    """读取文件内容（UTF-8）。"""
    return Path(filepath).read_text(encoding="utf-8")


def write_file(filepath: str | Path, content: str) -> None:
    """写入文件内容（UTF-8）。"""
    Path(filepath).write_text(content, encoding="utf-8")


def make_output_path(input_path: str | Path, target_fmt: str) -> Path:
    """根据输入路径和目标格式生成输出路径。"""
    p = Path(input_path)
    ext = FORMAT_EXTENSION.get(target_fmt, f".{target_fmt}")
    return p.with_suffix(ext)
