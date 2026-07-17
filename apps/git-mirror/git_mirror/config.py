"""配置管理 — 读取/写入 JSON 配置文件。"""

import json
import os
from pathlib import Path

DEFAULT_CONFIG_DIR = Path.home() / ".git-mirror"
DEFAULT_WORK_DIR = DEFAULT_CONFIG_DIR / "repos"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "repos": {},
    "work_dir": str(DEFAULT_WORK_DIR),
}


def load_config() -> dict:
    """加载配置文件，不存在时创建默认配置。"""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return {**DEFAULT_CONFIG}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict):
    """保存配置到文件。"""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_work_dir(config: dict) -> Path:
    """获取并创建工作目录。"""
    wd = Path(os.path.expanduser(config.get("work_dir", str(DEFAULT_WORK_DIR))))
    wd.mkdir(parents=True, exist_ok=True)
    return wd
