"""
engine_registry.py — 引擎注册中心 + 自动发现

使用装饰器模式注册引擎，启动时自动扫描 engines/ 目录。
新增引擎只需：
  1. 在 engines/ 下新建一个 *_engine.py 文件
  2. 继承 BaseEngine，加上 @register_engine 装饰器
  → 程序启动时自动发现并注册，无需手动 import

提供：
  - register_engine: 装饰器，注册引擎
  - auto_discover_engines: 自动扫描 engines/ 目录并加载
  - get_engine: 按 id 获取引擎实例
  - list_engines: 列出所有已注册引擎的元信息
"""

import importlib
import logging
from pathlib import Path

from engine_base import BaseEngine, EngineInfo

logger = logging.getLogger(__name__)

_ENGINES: dict[str, type[BaseEngine]] = {}
_ENGINE_INSTANCES: dict[str, BaseEngine] = {}  # 全局单例缓存
_ENGINES_DIR = Path(__file__).parent / "engines"


def register_engine(engine_id: str):
    """装饰器：将引擎类注册到 _ENGINES 字典"""
    def decorator(cls: type[BaseEngine]):
        _ENGINES[engine_id] = cls
        logger.info(f"引擎已注册: {engine_id} ({cls.__name__})")
        return cls
    return decorator


def auto_discover_engines():
    """
    自动扫描 engines/ 目录，加载所有 *_engine.py 文件。
    每个文件只需 import 即可触发 @register_engine 装饰器。

    约定：
      - 引擎文件必须以 _engine.py 结尾，如 rembg_local_engine.py
      - 也兼容旧命名（如 rembg_local.py），同时扫描 *_local.py 和 *_cloud.py
    """
    if not _ENGINES_DIR.exists():
        logger.warning(f"引擎目录不存在: {_ENGINES_DIR}")
        return

    patterns = ["*_engine.py", "*_local.py", "*_cloud.py"]
    loaded = set()

    for pattern in patterns:
        for py_file in _ENGINES_DIR.glob(pattern):
            if py_file.name.startswith("_"):
                continue  # 跳过 __init__.py
            if py_file.stem in loaded:
                continue
            loaded.add(py_file.stem)
            try:
                module_name = f"engines.{py_file.stem}"
                importlib.import_module(module_name)
            except Exception as e:
                logger.warning(f"加载引擎失败 {py_file.name}: {e}")

    logger.info(f"引擎发现完成，共注册 {len(_ENGINES)} 个引擎")


def get_engine(engine_id: str) -> BaseEngine | None:
    """按 id 获取引擎实例（全局单例，避免重复加载模型）"""
    cls = _ENGINES.get(engine_id)
    if cls is None:
        return None
    if engine_id not in _ENGINE_INSTANCES:
        _ENGINE_INSTANCES[engine_id] = cls()
    return _ENGINE_INSTANCES[engine_id]


def list_engines() -> list[EngineInfo]:
    """列出所有已注册引擎的元信息"""
    result = []
    for eid, cls in _ENGINES.items():
        try:
            info = cls.info()
            result.append(info)
        except Exception as e:
            logger.warning(f"获取引擎信息失败 {eid}: {e}")
    return result
