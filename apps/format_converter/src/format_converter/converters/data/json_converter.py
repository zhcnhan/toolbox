"""数据格式转换器 — JSON。"""

import json
from typing import Any


def loads(raw: str) -> Any:
    """JSON 字符串 → Python 对象。"""
    return json.loads(raw)


def dumps(data: Any) -> str:
    """Python 对象 → JSON 字符串。"""
    return json.dumps(data, ensure_ascii=False, indent=2)
