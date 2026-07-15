"""CLI 入口 — 文件格式互转命令行工具。

用法：
    python -m file_converter input.json -t yaml
    python -m file_converter input.yaml -t json -o output.json
    python -m file_converter --list-formats
"""

import argparse
import sys
from pathlib import Path

from file_converter import __version__
from file_converter.converters import CONVERTERS
from file_converter.utils import (
    detect_format,
    read_file,
    write_file,
    make_output_path,
    SUPPORTED_FORMATS,
)


def convert(input_path: Path, target_fmt: str, output_path: Path | None = None) -> Path:
    """核心转换逻辑：读取源文件 → 解析 → 序列化为目标格式 → 写入。"""
    # 1) 检测源格式
    src_fmt = detect_format(input_path)
    if src_fmt is None:
        print(f"错误：无法识别文件格式 — {input_path}")
        sys.exit(1)

    if src_fmt == target_fmt:
        print(f"警告：源格式与目标格式相同（{src_fmt}），未执行转换。")
        return input_path

    # 2) 读取并解析
    raw = read_file(input_path)
    src_converter = CONVERTERS[src_fmt]
    try:
        data = src_converter.loads(raw)
    except Exception as e:
        print(f"错误：解析 {src_fmt.upper()} 文件失败 — {e}")
        sys.exit(1)

    # 3) 序列化为目标格式
    dst_converter = CONVERTERS[target_fmt]
    try:
        output_raw = dst_converter.dumps(data)
    except Exception as e:
        print(f"错误：序列化为 {target_fmt.upper()} 失败 — {e}")
        print("提示：部分格式之间有数据结构限制（如 CSV 仅支持二维表）。")
        sys.exit(1)

    # 4) 写入
    if output_path is None:
        output_path = make_output_path(input_path, target_fmt)
    write_file(output_path, output_raw)
    print(f"✓ 转换完成：{input_path} → {output_path}")
    return output_path


def list_formats():
    """打印所有支持的格式。"""
    print("支持的格式：")
    for fmt in SUPPORTED_FORMATS:
        print(f"  - {fmt}")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="file_converter",
        description="多格式文件互转工具 — JSON / YAML / CSV / XML / TOML",
    )
    parser.add_argument("input", nargs="?", help="输入文件路径")
    parser.add_argument(
        "-t", "--to", dest="target",
        choices=SUPPORTED_FORMATS,
        help="目标格式",
    )
    parser.add_argument("-o", "--output", help="输出文件路径（可选，默认与输入同目录）")
    parser.add_argument(
        "-l", "--list-formats", action="store_true",
        help="列出所有支持的格式",
    )
    parser.add_argument("-v", "--version", action="version", version=f"file_converter {__version__}")

    args = parser.parse_args(argv)

    # 列出格式
    if args.list_formats:
        list_formats()
        return

    # 参数校验
    if not args.input:
        parser.print_help()
        print("\n错误：缺少输入文件。", file=sys.stderr)
        sys.exit(1)

    if not args.target:
        parser.print_help()
        print("\n错误：缺少目标格式 (-t/--to)", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"错误：文件不存在 — {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else None
    convert(input_path, args.target, output_path)


if __name__ == "__main__":
    main()
