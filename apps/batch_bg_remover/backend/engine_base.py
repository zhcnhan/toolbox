"""
engine_base.py — 抠图引擎统一抽象接口

所有引擎（本地 / 云端）必须实现此基类，确保前端调用方式一致。
新增引擎时只需继承 BaseEngine 并实现两个方法即可。

设计原则：
  - remove_bg: 自动抠图，全自动
  - remove_bg_with_prompt: 根据文本提示词选取主体后抠图
  - api_key: 可选，本地引擎不需要
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EngineInfo:
    """引擎元信息，用于前端展示设置页"""
    id: str                      # 唯一标识，如 "rembg_local"
    name: str                    # 显示名称，如 "rembg (本地)"
    description: str             # 简短描述
    type: str                    # "local" | "cloud"
    supports_auto: bool = True   # 是否支持自动抠图
    supports_prompt: bool = False  # 是否支持提示词分割
    needs_api_key: bool = False  # 是否需要 API Key
    api_key_label: str = ""      # Key 输入框的 label，如 "Gemini API Key"
    api_key_help_url: str = ""   # 用户去哪里获取 Key 的链接
    icon: str = "🔧"             # 前端展示的图标


class BaseEngine(ABC):
    """抠图引擎基类"""

    @classmethod
    def info(cls) -> EngineInfo:
        """返回引擎元信息，子类必须覆盖"""
        raise NotImplementedError

    @abstractmethod
    async def remove_bg(self, image_bytes: bytes, api_key: Optional[str] = None) -> bytes:
        """
        自动抠图：输入图片 bytes，返回去背景的 PNG bytes

        Args:
            image_bytes: 原始图片二进制数据
            api_key: 用户填的 API Key（本地引擎忽略）

        Returns:
            透明背景 PNG 图片的二进制数据
        """
        ...

    @abstractmethod
    async def remove_bg_with_prompt(
        self, image_bytes: bytes, prompt: str, api_key: Optional[str] = None
    ) -> bytes:
        """
        根据提示词选取主体并抠图

        Args:
            image_bytes: 原始图片二进制数据
            prompt: 用户输入的文本提示词，如 "左边的猫"、"红色汽车"
            api_key: 用户填的 API Key（本地引擎忽略）

        Returns:
            透明背景 PNG 图片的二进制数据
        """
        ...
