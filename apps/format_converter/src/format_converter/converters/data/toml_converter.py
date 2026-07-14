"""数据格式转换器 — TOML。

Python 3.11+ 使用标准库 tomllib，更低版本使用 tomli。
写入使用 tomli-w。

依赖：
  - tomli — MIT License (https://github.com/hukkin/tomli)
  - tomli-w — MIT License (https://github.com/hukkin/tomli-w)
"""

import sys
from typing import Any


def loads(raw: str) -> Any:
    """TOML 字符串 → Python dict。"""
    if sys.version_info >= (3, 11):
        import tomllib
        return tomllib.loads(raw)
    else:
        import tomli
        return tomli.loads(raw)


def dumps(data: Any) -> str:
    """Python dict → TOML 字符串。"""
    import tomli_w
    return tomli_w.dumps(data)
