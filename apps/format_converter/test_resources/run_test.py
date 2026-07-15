#!/usr/bin/env python3
"""
批量文件转换测试工具 v2
──────────────────────────────────────────────────
读取「转换前」文件夹中的所有文件，自动检测格式并转换为
当前支持的所有目标格式，输出到「转换后」文件夹中。

新增特性:
  • 从后端 utils 模块动态导入格式定义（确保与后端一致）
  • 文档转换不再使用硬编码路径列表，全面覆盖 _HANDLERS 中的 60+ 条路径
  • 音频/视频输出格式已补全（wma/aiff/flv/wmv 等）
  • 修复 convert_file() 调用时的参数顺序错误
  • 按类别分组统计，清晰展示各分类转换成功率

用法:
    cd apps/format_converter/backend
    python ../test_resources/run_test.py
"""

import sys
import os
import shutil
import traceback
import time
from pathlib import Path

# ── 强制 UTF-8 输出（Windows GBK 控制台兼容）──────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 将 backend 目录加入 sys.path ──────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

INPUT_DIR = Path(__file__).resolve().parent / "\u8f6c\u6362\u524d"
OUTPUT_DIR = Path(__file__).resolve().parent / "\u8f6c\u6362\u540e"

# ════════════════════════════════════════════════════════════
#  从后端导入格式定义（消除硬编码不一致风险）
# ════════════════════════════════════════════════════════════
CATEGORY_LABELS = {
    "data": "\u6570\u636e\u683c\u5f0f",
    "audio": "\u97f3\u9891\u683c\u5f0f",
    "video": "\u89c6\u9891\u683c\u5f0f",
    "image": "\u56fe\u7247\u683c\u5f0f",
    "document": "\u6587\u6863\u683c\u5f0f",
}

# 从后端导入（确保与生产环境格式映射完全一致）
try:
    from format_converter.utils import (
        FORMAT_CATEGORIES,
        OUTPUT_FORMATS,
        detect_format as _backend_detect_fmt,
        detect_category,
        get_extension,
    )
    _USE_BACKEND = True
except ImportError as e:
    print(f"\u26a0  \u65e0\u6cd5\u4ece\u540e\u7aef\u5bfc\u5165\u683c\u5f0f\u5b9a\u4e49\uff0c\u4f7f\u7528\u5185\u7f6e\u9876\u4e49\u5907\u9009: {e}")
    _USE_BACKEND = False
    # 内联备选 — 与 backend/format_converter/utils/__init__.py 保持同步
    FORMAT_CATEGORIES = {
        "data": ["json", "yaml", "csv", "xml", "toml"],
        "audio": ["mp3", "wav", "flac", "ogg", "aac", "wma", "m4a", "opus", "aiff"],
        "video": ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv"],
        "image": ["jpg", "png", "webp", "bmp", "gif", "ico", "tiff", "svg"],
        "document": ["pdf", "docx", "doc", "txt", "md", "html", "rtf", "epub"],
    }
    OUTPUT_FORMATS = {
        "data": ["json", "yaml", "csv", "xml", "toml"],
        # WMA encoding removed — not supported by most ffmpeg builds
        "audio": ["mp3", "wav", "flac", "ogg", "aac", "m4a", "opus", "aiff"],
        "video": ["mp4", "avi", "mkv", "mov", "webm", "flv", "wmv"],
        "image": ["jpg", "png", "webp", "bmp", "gif", "ico", "tiff"],
        "document": ["pdf", "docx", "doc", "txt", "md", "html", "rtf", "epub"],
    }

# ── 声明的文档转换路径（来自 document_converter._HANDLERS 的 keys）──
# 按 source_fmt 分组列出所有已声明支持的目标格式
_DOC_DECLARED_TARGETS: dict[str, set[str]] = {
    "pdf":  {"docx", "txt", "png", "jpg", "md", "html", "rtf", "epub", "doc"},
    "docx": {"pdf", "txt", "html", "md", "rtf", "epub", "doc"},
    "doc":  {"docx", "pdf", "txt", "html", "md", "rtf", "epub", "doc"},
    "txt":  {"pdf", "docx", "md", "html", "rtf", "epub", "doc"},
    "md":   {"pdf", "html", "txt", "docx", "rtf", "epub", "doc"},
    "html": {"pdf", "txt", "docx", "md", "rtf", "epub", "doc"},
    "epub": {"txt", "pdf", "docx", "md", "html", "rtf", "epub", "doc"},
    "rtf":  {"txt", "pdf", "docx", "md", "html", "epub", "rtf", "doc"},
}

# ── 扩展名映射（与后端 _FMT_TO_EXT 一致）──────────────────
FORMAT_TO_EXT: dict[str, str] = {
    "json": "json", "yaml": "yaml", "csv": "csv", "xml": "xml", "toml": "toml",
    "jpg": "jpg", "png": "png", "webp": "webp", "bmp": "bmp",
    "gif": "gif", "ico": "ico", "tiff": "tiff",
    "mp3": "mp3", "wav": "wav", "flac": "flac", "ogg": "ogg",
    "aac": "aac", "wma": "wma", "m4a": "m4a", "opus": "opus", "aiff": "aiff",
    "mp4": "mp4", "avi": "avi", "mkv": "mkv", "mov": "mov", "webm": "webm",
    "flv": "flv", "wmv": "wmv",
    "pdf": "pdf", "docx": "docx", "doc": "doc", "txt": "txt",
    "md": "md", "html": "html", "rtf": "rtf", "epub": "epub",
}

# ── 扩展名→格式 映射（用于本地文件检测）──────────────────
EXT_TO_FORMAT: dict[str, str] = {
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".csv": "csv", ".xml": "xml", ".toml": "toml",
    ".jpg": "jpg", ".jpeg": "jpg", ".png": "png", ".webp": "webp",
    ".bmp": "bmp", ".gif": "gif", ".ico": "ico", ".tiff": "tiff", ".tif": "tiff",
    ".svg": "svg",
    ".mp3": "mp3", ".wav": "wav", ".flac": "flac", ".ogg": "ogg",
    ".aac": "aac", ".wma": "wma", ".m4a": "m4a", ".opus": "opus", ".aiff": "aiff", ".aif": "aiff",
    ".mp4": "mp4", ".avi": "avi", ".mkv": "mkv", ".mov": "mov",
    ".webm": "webm", ".flv": "flv", ".wmv": "wmv",
    ".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".txt": "txt",
    ".md": "md", ".html": "html", ".htm": "html", ".rtf": "rtf", ".epub": "epub",
}


def detect_format(filepath: Path) -> str | None:
    """根据扩展名识别格式（优先使用后端函数）。"""
    if _USE_BACKEND:
        return _backend_detect_fmt(str(filepath))
    ext = filepath.suffix.lower()
    return EXT_TO_FORMAT.get(ext)


def get_targets(source_fmt: str) -> list[str]:
    """获取源格式支持的所有目标格式（排除自身）。"""
    cat = detect_category(source_fmt) if _USE_BACKEND else None
    if not _USE_BACKEND:
        for c, fmts in FORMAT_CATEGORIES.items():
            if source_fmt in fmts:
                cat = c
                break
    if not cat:
        return []
    all_outputs = OUTPUT_FORMATS.get(cat, [])
    return [f for f in all_outputs if f != source_fmt]


def _is_doc_path_expected(src: str, dst: str) -> bool:
    """检查文档转换路径是否在 _HANDLERS 表中声明过。"""
    return dst in _DOC_DECLARED_TARGETS.get(src, set())


def main():
    start_time = time.time()
    print("=" * 64)
    print("  \u6279\u91cf\u6587\u4ef6\u8f6c\u6362\u6d4b\u8bd5\u5de5\u5177 v2")
    print("=" * 64)
    print(f"  \u683c\u5f0f\u5b9a\u4e49\u6765\u6e90: {'\u2705 \u540e\u7aef\u52a8\u6001\u5bfc\u5165' if _USE_BACKEND else '\u26a0 \u5185\u7f6e\u9876\u4e49\u5907\u9009'}")
    print(f"  \u8f93\u5165\u76ee\u5f55: {INPUT_DIR}")
    print(f"  \u8f93\u51fa\u76ee\u5f55: {OUTPUT_DIR}")
    print()

    if not INPUT_DIR.exists():
        print(f"\u9519\u8bef: \u8f93\u5165\u76ee\u5f55\u4e0d\u5b58\u5728: {INPUT_DIR}")
        return 1

    # ── 清空输出目录 ──────────────────────────────────────
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.iterdir():
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)
    else:
        OUTPUT_DIR.mkdir(parents=True)

    # ── 收集输入文件 ──────────────────────────────────────
    input_files = sorted(
        [f for f in INPUT_DIR.iterdir() if f.is_file()],
        key=lambda p: p.name,
    )
    if not input_files:
        print(f"\n\u8f93\u5165\u76ee\u5f55\u4e3a\u7a7a: {INPUT_DIR}")
        print("\u8bf7\u5c06\u6d4b\u8bd5\u6587\u4ef6\u653e\u5165\u300c\u8f6c\u6362\u524d\u300d\u6587\u4ef6\u5939\u540e\u91cd\u65b0\u8fd0\u884c\u3002")
        return 1

    # ── 导入转换器 ────────────────────────────────────────
    try:
        from format_converter.converters import convert_file
        print("\u2705 \u8f6c\u6362\u5668\u6a21\u5757\u52a0\u8f7d\u6210\u529f\n")
    except Exception as e:
        print(f"\n\u2717 \u65e0\u6cd5\u52a0\u8f7d\u8f6c\u6362\u5668\u6a21\u5757: {e}")
        print("  \u8bf7\u786e\u4fdd\u5728 backend \u76ee\u5f55\u4e0b\u8fd0\u884c\uff0c\u6216\u68c0\u67e5\u4f9d\u8d56\u5b89\u88c5\u3002")
        traceback.print_exc()
        return 1

    # ════════════════════════════════════════════════════════
    #  逐文件转换
    # ════════════════════════════════════════════════════════
    total_ok = 0
    total_fail = 0
    total_skip = 0
    # 按类别统计
    cat_stats: dict[str, dict] = {}
    for cat in CATEGORY_LABELS:
        cat_stats[cat] = {"ok": 0, "fail": 0, "skip": 0, "paths_ok": [], "paths_fail": []}
    # 未声明但尝试的文档路径（不在 _HANDLERS 中的尝试）
    extra_doc_attempts: list[str] = []

    for filepath in input_files:
        src_fmt = detect_format(filepath)
        if not src_fmt:
            print(f"\u26a0 \u8df3\u8fc7 {filepath.name} \u2014 \u65e0\u6cd5\u8bc6\u522b\u7684\u683c\u5f0f")
            total_skip += 1
            continue

        cat = detect_category(src_fmt) if _USE_BACKEND else None
        if not _USE_BACKEND:
            for c, fmts in FORMAT_CATEGORIES.items():
                if src_fmt in fmts:
                    cat = c
                    break
        if not cat:
            print(f"\u26a0 \u8df3\u8fc7 {filepath.name} \u2014 \u65e0\u6cd5\u786e\u5b9a\u5206\u7c7b: {src_fmt}")
            total_skip += 1
            continue

        targets = get_targets(src_fmt)
        cat_label = CATEGORY_LABELS.get(cat, cat)
        print(f"\n\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500")
        print(f"\U0001f4c4 {filepath.name}  [{cat_label}/{src_fmt}] \u2192 {len(targets)} \u4e2a\u76ee\u6807\u683c\u5f0f")

        for tgt_fmt in targets:
            out_ext = FORMAT_TO_EXT.get(tgt_fmt, tgt_fmt)
            out_name = f"{filepath.stem}_{src_fmt}_to_{tgt_fmt}.{out_ext}"
            out_path = OUTPUT_DIR / out_name

            # 文档转换：额外标记未声明路径
            if cat == "document" and not _is_doc_path_expected(src_fmt, tgt_fmt):
                extra_doc_attempts.append(f"{src_fmt}\u2192{tgt_fmt}")

            try:
                # ═══════════════════════════════════════════════════════
                #  注意参数顺序: convert_file(input_path, src_fmt, dst_fmt, output_path)
                # ═══════════════════════════════════════════════════════
                result = convert_file(
                    str(filepath),
                    src_fmt,
                    tgt_fmt,
                    str(out_path),
                )
                if result.get("success"):
                    size_kb = out_path.stat().st_size / 1024 if out_path.exists() else 0
                    tag = " \u2705" if (cat != "document" or _is_doc_path_expected(src_fmt, tgt_fmt)) else " \u26a0\u2605"
                    print(f"  {tag} {src_fmt} \u2192 {tgt_fmt}  ({size_kb:.1f} KB)  \u2192 {out_name}")
                    total_ok += 1
                    cat_stats[cat]["ok"] += 1
                    cat_stats[cat]["paths_ok"].append(f"{src_fmt}\u2192{tgt_fmt}")
                else:
                    error = result.get("error", "\u672a\u77e5\u9519\u8bef")
                    print(f"  \u2717 {src_fmt} \u2192 {tgt_fmt}  \u5931\u8d25: {error[:100]}")
                    total_fail += 1
                    cat_stats[cat]["fail"] += 1
                    cat_stats[cat]["paths_fail"].append(f"{src_fmt}\u2192{tgt_fmt}")
                    if out_path.exists():
                        out_path.unlink()
            except Exception as e:
                err_msg = str(e)[:100]
                print(f"  \u2717 {src_fmt} \u2192 {tgt_fmt}  \u5f02\u5e38: {err_msg}")
                total_fail += 1
                cat_stats[cat]["fail"] += 1
                cat_stats[cat]["paths_fail"].append(f"{src_fmt}\u2192{tgt_fmt}: {err_msg[:40]}")
                if out_path.exists():
                    out_path.unlink()

    # ════════════════════════════════════════════════════════
    #  汇总报告
    # ════════════════════════════════════════════════════════
    elapsed = time.time() - start_time
    print(f"\n{'=' * 64}")
    print(f"  \u6d4b\u8bd5\u7ed3\u679c\u6c47\u603b  (\u8017\u65f6 {elapsed:.1f}s)")
    print(f"{'=' * 64}")

    for cat, label in CATEGORY_LABELS.items():
        st = cat_stats[cat]
        ok, fail = st["ok"], st["fail"]
        total_cat = ok + fail
        if total_cat == 0:
            continue
        pct = ok / total_cat * 100 if total_cat > 0 else 0
        bar_len = int(pct / 5)
        bar = "\u2588" * bar_len + "\u2591" * (20 - bar_len)
        print(f"\n  \u250c\u2500 {label}")
        print(f"  \u251c\u2500 \u2705 \u6210\u529f: {ok}  \u2717 \u5931\u8d25: {fail}  \u2b50 \u901a\u8fc7\u7387: {pct:.0f}%")
        print(f"  \u251c\u2500 [{bar}]")

        # 文档类：列出具体失败路径
        if cat == "document" and st["paths_fail"]:
            print(f"  \u2514\u2500 \u5931\u8d25\u8def\u5f84 ({len(st['paths_fail'])} \u6761):")
            for p in st["paths_fail"]:
                print(f"        \u2717 {p}")
        # 音频/视频类：列出失败路径
        elif st["paths_fail"]:
            print(f"  \u2514\u2500 \u5931\u8d25\u8def\u5f84 ({len(st['paths_fail'])} \u6761):")
            for p in st["paths_fail"]:
                print(f"        \u2717 {p}")

    # 文档类特殊提示
    if extra_doc_attempts:
        unique_extra = sorted(set(extra_doc_attempts))
        print(f"\n  \U0001f4dd \u6587\u6863\u7c7b: \u5c1d\u8bd5\u4e86 {len(unique_extra)} \u6761\u672a\u5728 _HANDLERS \u4e2d\u58f0\u660e\u7684\u8def\u5f84:")
        for p in unique_extra[:15]:
            print(f"        \u26a0 {p}")
        if len(unique_extra) > 15:
            print(f"        ... (共 {len(unique_extra)} 条)")

    total_tests = total_ok + total_fail
    print(f"\n{'=' * 64}")
    print(f"  \u2705 \u6210\u529f: {total_ok}  \u2717 \u5931\u8d25: {total_fail}  \u26a0 \u8df3\u8fc7: {total_skip}  \u2502 \u5408\u8ba1: {total_tests} \u6b21\u8f6c\u6362")
    if total_tests > 0:
        print(f"  \u2b50 \u603b\u901a\u8fc7\u7387: {total_ok / total_tests * 100:.1f}%")
    print(f"  \U0001f4c2 \u8f93\u51fa\u76ee\u5f55: {OUTPUT_DIR}")
    print(f"{'=' * 64}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
