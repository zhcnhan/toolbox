"""JSON 格式转换器。"""

import json
from typing import Any

from file_converter.converters.base import BaseConverter


class JsonConverter(BaseConverter):
    """JSON ↔ Python 对象。"""

    @property
    def format_name(self) -> str:
        return "json"

    def loads(self, raw: str) -> Any:
        return json.loads(raw)

    def dumps(self, data: Any) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)
