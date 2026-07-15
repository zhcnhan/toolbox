"""XML 格式转换器。

使用 xmltodict 实现 XML ↔ Python dict 的转换。
需要安装 xmltodict。
"""

from typing import Any

import xmltodict

from file_converter.converters.base import BaseConverter


class XmlConverter(BaseConverter):
    """XML ↔ Python dict（通过 xmltodict）。"""

    @property
    def format_name(self) -> str:
        return "xml"

    def loads(self, raw: str) -> Any:
        return xmltodict.parse(raw)

    def dumps(self, data: Any) -> str:
        return xmltodict.unparse(data, pretty=True)
