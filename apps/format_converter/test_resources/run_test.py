#!/usr/bin/env python3
"""
批量文件转换测试工具
读取「转换前」文件夹中的所有文件，自动检测格式并转换为所有支持的目标格式，
输出到「转换后」文件夹中。

用法:
    cd apps/format_converter/backend
    python ../test_resources/run_test.py
"""

import sys
import os
import shutil
import threading
from pathlib import Path

# 将 backend 目录加入 sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# 导入转换器
from format_converter.converters import convert_file

INPUT_DIR = Path(__file__).resolve().parent / "转换前"
OUTPUT_DIR = Path(__file__).resolve().parent / "转换后"

# ============================================================
# 格式定义 — 与后端 utils/__init__.py 保持一致
# ============================================================

EXT_TO_FORMAT = {
    # data
    '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
    '.csv': 'csv', '.xml': 'xml', '.toml': 'toml',
    # image
    '.jpg': 'jpg', '.jpeg': 'jpg', '.png': 'png', '.webp': 'webp',
    '.bmp': 'bmp', '.gif': 'gif', '.ico': 'ico', '.tiff': 'tiff', '.tif': 'tiff',
    '.svg': 'svg',
    # audio
    '.mp3': 'mp3', '.wav': 'wav', '.flac': 'flac', '.ogg': 'ogg',
    '.aac': 'aac', '.wma': 'wma', '.m4a': 'm4a', '.opus': 'opus', '.aiff': 'aiff',
    # video
    '.mp4': 'mp4', '.avi': 'avi', '.mkv': 'mkv', '.mov': 'mov',
    '.webm': 'webm', '.flv': 'flv', '.wmv': 'wmv',
    # document
    '.pdf': 'pdf', '.docx': 'docx', '.doc': 'doc', '.txt': 'txt',
    '.md': 'md', '.html': 'html', '.htm': 'html', '.rtf': 'rtf', '.epub': 'epub',
}

CATEGORY_MAP = {
    'json': 'data', 'yaml': 'data', 'csv': 'data', 'xml': 'data', 'toml': 'data',
    'jpg': 'image', 'png': 'image', 'webp': 'image', 'bmp': 'image',
    'gif': 'image', 'ico': 'image', 'tiff': 'image', 'svg': 'image',
    'mp3': 'audio', 'wav': 'audio', 'flac': 'audio', 'ogg': 'audio',
    'aac': 'audio', 'wma': 'audio', 'm4a': 'audio', 'opus': 'audio', 'aiff': 'audio',
    'mp4': 'video', 'avi': 'video', 'mkv': 'video', 'mov': 'video',
    'webm': 'video', 'flv': 'video', 'wmv': 'video',
    'pdf': 'document', 'docx': 'document', 'doc': 'document', 'txt': 'document',
    'md': 'document', 'html': 'document', 'rtf': 'document', 'epub': 'document',
}

# 每个分类支持的所有输出格式
OUTPUT_FORMATS = {
    'data': ['json', 'yaml', 'csv', 'xml', 'toml'],
    'image': ['jpg', 'png', 'webp', 'bmp', 'gif', 'ico', 'tiff'],
    'audio': ['mp3', 'wav', 'flac', 'ogg', 'aac', 'm4a', 'opus'],
    'video': ['mp4', 'avi', 'mkv', 'mov', 'webm'],
    # document 只有特定路径已实现
    'document': ['pdf', 'docx', 'txt', 'md', 'html', 'rtf'],
}

# 文档格式的已实现转换路径 (source → [target, ...])
DOC_CONVERSIONS = {
    'pdf':  ['docx', 'txt'],
    'docx': ['pdf', 'txt', 'html'],
    'doc':  ['docx'],
    'txt':  ['pdf', 'docx', 'md', 'html'],
    'md':   ['pdf', 'html'],
    'html': ['pdf', 'txt'],
    'rtf':  ['txt'],
    'epub': ['txt'],
}

# 输出格式对应的扩展名
FORMAT_TO_EXT = {
    'json': '.json', 'yaml': '.yaml', 'csv': '.csv', 'xml': '.xml', 'toml': '.toml',
    'jpg': '.jpg', 'png': '.png', 'webp': '.webp', 'bmp': '.bmp',
    'gif': '.gif', 'ico': '.ico', 'tiff': '.tiff',
    'mp3': '.mp3', 'wav': '.wav', 'flac': '.flac', 'ogg': '.ogg',
    'aac': '.aac', 'm4a': '.m4a', 'opus': '.opus',
    'mp4': '.mp4', 'avi': '.avi', 'mkv': '.mkv', 'mov': '.mov', 'webm': '.webm',
    'pdf': '.pdf', 'docx': '.docx', 'txt': '.txt', 'md': '.md', 'html': '.html', 'rtf': '.rtf',
}


def detect_format(filepath: Path) -> str | None:
    ext = filepath.suffix.lower()
    return EXT_TO_FORMAT.get(ext)


def get_targets(source_fmt: str) -> list[str]:
    cat = CATEGORY_MAP.get(source_fmt)
    if not cat:
        return []
    if cat == 'document':
        return DOC_CONVERSIONS.get(source_fmt, [])
    all_outputs = OUTPUT_FORMATS.get(cat, [])
    return [f for f in all_outputs if f != source_fmt]


CONVERSION_TIMEOUT = 60  # 每个转换最多 60 秒（视频需要更长时间）


def _convert_with_timeout(input_path, src_fmt, tgt_fmt, output_path, timeout=CONVERSION_TIMEOUT):
    """在独立线程中运行转换，支持超时。"""
    import multiprocessing
    result = {"success": False, "output": output_path, "error": None}

    def _run():
        try:
            r = convert_file(input_path, src_fmt, tgt_fmt, output_path)
            result.update(r)
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        result["error"] = f"转换超时 ({timeout}s)"
        return result
    return result


def main():
    print("=" * 60)
    print("  批量文件转换测试工具")
    print("=" * 60)

    if not INPUT_DIR.exists():
        print(f"错误: 输入目录不存在: {INPUT_DIR}")
        return

    # 清空输出目录
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.iterdir():
            if f.is_file():
                f.unlink()
            elif f.is_dir():
                shutil.rmtree(f)
    else:
        OUTPUT_DIR.mkdir(parents=True)

    # 收集输入文件
    input_files = [f for f in INPUT_DIR.iterdir() if f.is_file()]
    if not input_files:
        print(f"\n输入目录为空: {INPUT_DIR}")
        print("请将测试文件放入「转换前」文件夹后重新运行。")
        return

    print("\n[OK] 转换器模块已就绪")

    total_ok = 0
    total_fail = 0
    total_skip = 0

    for filepath in input_files:
        src_fmt = detect_format(filepath)
        if not src_fmt:
            print(f"\n[SKIP] 跳过 {filepath.name} — 无法识别的格式")
            total_skip += 1
            continue

        cat = CATEGORY_MAP.get(src_fmt, '?')
        targets = get_targets(src_fmt)
        print(f"\n{'-' * 50}")
        print(f"[FILE] {filepath.name}  [{cat}/{src_fmt}] -> {len(targets)} 个目标格式")

        for tgt_fmt in targets:
            out_ext = FORMAT_TO_EXT.get(tgt_fmt, f'.{tgt_fmt}')
            out_name = f"{filepath.stem}_{src_fmt}_to_{tgt_fmt}{out_ext}"
            out_path = OUTPUT_DIR / out_name

            try:
                result = _convert_with_timeout(
                    str(filepath),
                    src_fmt,
                    tgt_fmt,
                    str(out_path),
                )
                if isinstance(result, dict) and not result.get("success"):
                    raise RuntimeError(result.get("error", "Unknown error"))
                size_kb = out_path.stat().st_size / 1024
                print(f"  [OK] {src_fmt} -> {tgt_fmt}  ({size_kb:.1f} KB)  -> {out_name}")
                total_ok += 1
            except Exception as e:
                err_msg = str(e)[:80]
                print(f"  [FAIL] {src_fmt} -> {tgt_fmt}  失败: {err_msg}")
                total_fail += 1
                # 清理可能产生的不完整文件
                try:
                    if out_path.exists():
                        out_path.unlink()
                except OSError:
                    pass  # 文件可能仍被占用，跳过清理

    print(f"\n{'=' * 60}")
    print(f"  测试完成: [OK] {total_ok} 成功  [FAIL] {total_fail} 失败  [SKIP] {total_skip} 跳过")
    print(f"  输出目录: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
