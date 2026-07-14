"""
格式定义与文件工具

将源格式映射表集中管理，方便扩展与维护。
"""

import os
import json


# ============================================================
#  扩展名 → 格式名 映射
# ============================================================
_EXT_TO_FMT: dict[str, str] = {
    # 数据
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".csv": "csv",
    ".tsv": "tsv",
    ".xml": "xml",
    ".toml": "toml",
    # 音频
    ".mp3": "mp3",
    ".wav": "wav",
    ".flac": "flac",
    ".ogg": "ogg",
    ".aac": "aac",
    ".wma": "wma",
    ".m4a": "m4a",
    ".opus": "opus",
    ".aiff": "aiff",
    ".aif": "aiff",
    # 视频
    ".mp4": "mp4",
    ".avi": "avi",
    ".mkv": "mkv",
    ".mov": "mov",
    ".webm": "webm",
    ".flv": "flv",
    ".wmv": "wmv",
    # 图片
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
    ".webp": "webp",
    ".bmp": "bmp",
    ".gif": "gif",
    ".ico": "ico",
    ".tiff": "tiff",
    ".tif": "tiff",
    ".svg": "svg",
    # 文档
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".txt": "txt",
    ".md": "md",
    ".html": "html",
    ".htm": "html",
    ".rtf": "rtf",
    ".epub": "epub",
}

_FMT_TO_EXT: dict[str, str] = {v: k.lstrip(".") for k, v in _EXT_TO_FMT.items()}

# ============================================================
#  格式分类
# ============================================================
FORMAT_CATEGORIES: dict[str, list[str]] = {
    "data": ["json", "yaml", "csv", "xml", "toml"],
    "audio": ["mp3", "wav", "flac", "ogg", "aac", "wma", "m4a", "opus", "aiff"],
    "video": ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv"],
    "image": ["jpg", "png", "webp", "bmp", "gif", "ico", "tiff", "svg"],
    "document": ["pdf", "docx", "doc", "txt", "md", "html", "rtf", "epub"],
}

CATEGORY_LABELS: dict[str, str] = {
    "data": "数据格式",
    "audio": "音频格式",
    "video": "视频格式",
    "image": "图片格式",
    "document": "文档格式",
}

CATEGORY_ICONS: dict[str, str] = {
    "data": "database",
    "audio": "music",
    "video": "film",
    "image": "image",
    "document": "file-text",
}

# 文件对话框过滤器
CATEGORY_FILTERS: dict[str, str] = {
    "data": "数据文件 (*.json *.yaml *.yml *.csv *.xml *.toml)",
    "audio": "音频文件 (*.mp3 *.wav *.flac *.ogg *.aac *.wma *.m4a *.opus *.aiff)",
    "video": "视频文件 (*.mp4 *.avi *.mkv *.mov *.webm *.flv *.wmv)",
    "image": "图片文件 (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.ico *.tiff *.tif *.svg)",
    "document": "文档文件 (*.pdf *.docx *.doc *.txt *.md *.html *.htm *.rtf *.epub)",
}

# ============================================================
#  跨类别转换映射（输出格式可能有额外选项）
# ============================================================
# 每个类别可用的输出格式
OUTPUT_FORMATS: dict[str, list[str]] = {
    "data": ["json", "yaml", "csv", "xml", "toml"],
    "audio": ["mp3", "wav", "flac", "ogg", "aac", "m4a", "opus"],
    "video": ["mp4", "avi", "mkv", "mov", "webm"],
    "image": ["jpg", "png", "webp", "bmp", "gif", "ico", "tiff"],
    "document": ["pdf", "docx", "txt", "md", "html", "rtf"],
}

# 每个类别可用的输入格式（通常与 _EXT_TO_FMT 对应）
INPUT_FORMATS: dict[str, list[str]] = {
    cat: [fmt for fmt in fmts if fmt in _FMT_TO_EXT]
    for cat, fmts in FORMAT_CATEGORIES.items()
}


# ============================================================
#  工具函数
# ============================================================

def detect_format(filepath: str) -> str | None:
    """根据文件路径检测格式名。"""
    ext = os.path.splitext(filepath)[1].lower()
    return _EXT_TO_FMT.get(ext)


def detect_category(fmt: str) -> str | None:
    """根据格式名检测所属类别。"""
    for cat, fmts in FORMAT_CATEGORIES.items():
        if fmt in fmts:
            return cat
    return None


def get_extension(fmt: str) -> str:
    """获取格式对应的默认扩展名。"""
    return _FMT_TO_EXT.get(fmt, fmt)


def make_output_path(input_path: str, target_fmt: str, output_dir: str | None = None) -> str:
    """根据输入路径和目标格式生成输出路径。"""
    base = os.path.splitext(os.path.basename(input_path))[0]
    ext = get_extension(target_fmt)
    filename = f"{base}.{ext}"
    if output_dir:
        return os.path.join(output_dir, filename)
    return os.path.join(os.path.dirname(input_path), filename)


def guess_format_from_category(category: str, default: str = "txt") -> str:
    """从类别获取一个默认格式名（用于快速选择器）。"""
    fmts = FORMAT_CATEGORIES.get(category, [])
    return fmts[0] if fmts else default


# ============================================================
#  文件 I/O
# ============================================================

def read_file(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def write_file(filepath: str, content: str) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def read_bytes(filepath: str) -> bytes:
    with open(filepath, "rb") as f:
        return f.read()


def write_bytes(filepath: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(data)
