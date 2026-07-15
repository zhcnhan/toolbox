import csv
import io
from typing import Any


def csv_loads(s: str) -> dict[str, Any]:
    """将 CSV 文本解析为标准中间格式 {"rows": [...]}。"""
    reader = csv.DictReader(io.StringIO(s))
    rows = [dict(row) for row in reader]
    return {"rows": rows}


def csv_dumps(data: Any) -> str:
    """将中间格式写为 CSV 文本。

    支持的输入:
      - {"rows": [...]}  标准格式
      - [dict, ...]      列表格式（自动包装）
      - {"key": [...]}   自动找到第一个 list 值作为行数据
    """
    # 统一提取行数据
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        if "rows" in data and isinstance(data["rows"], list):
            rows = data["rows"]
        else:
            # 找到第一个 list 类型的值作为表格数据
            rows = None
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    rows = v
                    break
            if rows is None:
                # 没有列表值，把整个 dict 作为单行
                rows = [data]
    else:
        rows = [{"value": str(data)}]

    if not rows:
        return ""

    # 确保所有行都是 dict
    rows = [r if isinstance(r, dict) else {"value": str(r)} for r in rows]

    # 收集所有字段名（保持顺序）
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
