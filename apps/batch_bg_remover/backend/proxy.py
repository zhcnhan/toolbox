"""
proxy.py — 全局代理配置管理

代理配置以 JSON 文件存储在 BASE_DIR/data/proxy.json 中，
通过 Docker volume 挂载持久化，容器重启不丢失。

格式：
{
    "enabled": false,
    "url": "http://127.0.0.1:7890"
}

使用方式：
    from proxy import get_proxies_for_requests
    resp = requests.post(url, proxies=get_proxies_for_requests())

    from proxy import get_proxy_url
    resp = httpx.get(url, proxy=get_proxy_url())

    from proxy import apply_proxy_env
    apply_proxy_env()  # 适用于 replicate SDK
"""

import json
import os
from pathlib import Path

# 配置文件路径：同目录下 data/proxy.json
_CONFIG_DIR = Path(__file__).resolve().parent / "data"
_CONFIG_FILE = _CONFIG_DIR / "proxy.json"

# 默认配置
_DEFAULT = {
    "enabled": False,
    "url": "",
}


def _load_config() -> dict:
    """从文件加载代理配置"""
    try:
        if _CONFIG_FILE.exists():
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            # 兼容旧版本缺少字段
            for k, v in _DEFAULT.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return dict(_DEFAULT)


def _save_config(config: dict) -> None:
    """保存代理配置到文件"""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def get_proxy_config() -> dict:
    """获取当前代理配置"""
    return _load_config()


def set_proxy_config(enabled: bool, url: str) -> dict:
    """设置代理配置并返回新配置"""
    config = {
        "enabled": enabled,
        "url": url.strip() if url else "",
    }
    _save_config(config)
    return config


def get_proxies_for_requests() -> dict | None:
    """
    返回 requests 库可用的 proxies 字典。
    代理未启用时返回 None（表示直连）。
    """
    config = _load_config()
    if not config["enabled"] or not config["url"]:
        return None
    return {
        "http": config["url"],
        "https": config["url"],
    }


def get_proxy_url() -> str | None:
    """
    返回代理 URL 字符串（适用于 httpx.get(url, proxy=...)）。
    代理未启用时返回 None。
    """
    config = _load_config()
    if not config["enabled"] or not config["url"]:
        return None
    return config["url"]


def apply_proxy_env() -> None:
    """
    将代理写入环境变量 HTTP_PROXY / HTTPS_PROXY。
    适用于 replicate SDK 等无法直接传 proxies 参数的情况。
    """
    config = _load_config()
    if config["enabled"] and config["url"]:
        os.environ["HTTP_PROXY"] = config["url"]
        os.environ["HTTPS_PROXY"] = config["url"]
    else:
        # 清除代理环境变量（防止宿主机泄露）
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
