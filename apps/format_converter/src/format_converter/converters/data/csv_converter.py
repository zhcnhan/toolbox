"""数据格式转换器 — CSV。

CSV 与 JSON/YAML 之间通过「list[dict]」结构互转：
- dict 的 keys 作为表头
- 每一行 dict 的 values 作为数据行
"""

import csv
import io
from typing import Any


def loads(raw: str) -> Any:
    """CSV 字符串 → list[dict]。"""
    reader = csv.DictReader(io.StringIO(raw))
    return [row for row in reader]


def dumps(data: Any) -> str:
    """list[dict] → CSV 字符串。"""
    if not isinstance(data, list) or not data:
        raise ValueError("CSV 输出需要非空列表数据")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
