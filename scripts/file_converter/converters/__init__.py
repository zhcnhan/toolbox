"""格式转换器集合。"""

from file_converter.converters.json_converter import JsonConverter
from file_converter.converters.yaml_converter import YamlConverter
from file_converter.converters.csv_converter import CsvConverter
from file_converter.converters.xml_converter import XmlConverter
from file_converter.converters.toml_converter import TomlConverter

# 格式名 -> 转换器实例
CONVERTERS = {
    "json": JsonConverter(),
    "yaml": YamlConverter(),
    "csv":  CsvConverter(),
    "xml":  XmlConverter(),
    "toml": TomlConverter(),
}

__all__ = ["CONVERTERS"]
