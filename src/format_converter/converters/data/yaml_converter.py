"""数据格式转换器 — YAML。

依赖：PyYAML — MIT License
https://github.com/yaml/pyyaml
"""

from typing import Any

import yaml


def loads(raw: str) -> Any:
    """YAML 字符串 → Python 对象。"""
    return yaml.safe_load(raw)


def dumps(data: Any) -> str:
    """Python 对象 → YAML 字符串。"""
    return yaml.dump(data, allow_unicode=True, sort_keys=False)
