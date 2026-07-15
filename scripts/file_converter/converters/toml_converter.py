"""TOML 格式转换器。

需要 Python 3.11+（使用标准库 tomllib），或降级时使用 tomli/tomli-w。
"""

import sys
from typing import Any

from file_converter.converters.base import BaseConverter


class TomlConverter(BaseConverter):
    """TOML ↔ Python dict。"""

    @property
    def format_name(self) -> str:
        return "toml"

    def loads(self, raw: str) -> Any:
        if sys.version_info >= (3, 11):
            import tomllib
            return tomllib.loads(raw)
        else:
            import tomli
            return tomli.loads(raw)

    def dumps(self, data: Any) -> str:
        # tomli_w 始终需要安装
        import tomli_w
        return tomli_w.dumps(data)
