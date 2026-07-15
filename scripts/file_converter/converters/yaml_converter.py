"""YAML 格式转换器。"""

from typing import Any

import yaml

from file_converter.converters.base import BaseConverter


class YamlConverter(BaseConverter):
    """YAML ↔ Python 对象。"""

    @property
    def format_name(self) -> str:
        return "yaml"

    def loads(self, raw: str) -> Any:
        return yaml.safe_load(raw)

    def dumps(self, data: Any) -> str:
        return yaml.dump(data, allow_unicode=True, sort_keys=False)
