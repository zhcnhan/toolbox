"""转换器基类。"""

from abc import ABC, abstractmethod
from typing import Any


class BaseConverter(ABC):
    """所有格式转换器的抽象基类。"""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """格式名称（如 'json', 'yaml'）。"""
        ...

    @abstractmethod
    def loads(self, raw: str) -> Any:
        """将字符串解析为 Python 对象。"""
        ...

    @abstractmethod
    def dumps(self, data: Any) -> str:
        """将 Python 对象序列化为字符串。"""
        ...
