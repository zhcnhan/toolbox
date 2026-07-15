"""CSV 格式转换器。

CSV 只支持二维表结构，与 JSON/YAML 的互转遵循以下规则：
- 列出 dict 的列表 → CSV：dict 的 keys 作为表头，values 作为行数据。
- CSV → 列出 dict 的列表：第一行为表头，其余行为数据。
"""

import csv
import io
from typing import Any

from file_converter.converters.base import BaseConverter


class CsvConverter(BaseConverter):
    """CSV ↔ 列出 dict 的列表。"""

    @property
    def format_name(self) -> str:
        return "csv"

    def loads(self, raw: str) -> Any:
        reader = csv.DictReader(io.StringIO(raw))
        return [row for row in reader]

    def dumps(self, data: Any) -> str:
        if not isinstance(data, list) or not data:
            raise ValueError("CSV 输出需要非空列表数据")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
