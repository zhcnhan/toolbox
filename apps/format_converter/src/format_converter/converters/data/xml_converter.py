"""数据格式转换器 — XML。

依赖：xmltodict — MIT License
https://github.com/martinblech/xmltodict
"""

from typing import Any

import xmltodict


def loads(raw: str) -> Any:
    """XML 字符串 → Python dict。"""
    return xmltodict.parse(raw)


def dumps(data: Any) -> str:
    """Python dict → XML 字符串。"""
    return xmltodict.unparse(data, pretty=True)
