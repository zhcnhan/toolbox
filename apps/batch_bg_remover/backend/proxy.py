"""
proxy.py — 全局代理配置管理

代理配置以 JSON 文件存储在 BASE_DIR/data/proxy.json 中，
通过 Docker volume 挂载持久化，容器重启不丢失。

格式：
{
    "enabled": false,
    "url": "http://127.0.0.1:7890",
    "auth_type": "none",        # "none" 或 "basic"
    "username": "",
    "password": ""
}

使用方式：
    from proxy import get_proxies_for_requests
    resp = requests.post(url, proxies=get_proxies_for_requests())

    from proxy import get_proxy_url
    resp = httpx.get(url, proxy=get_proxy_url())
"""

import json
import os
import time
import urllib.error
from pathlib import Path

# 配置文件路径：同目录下 data/proxy.json
_CONFIG_DIR = Path(__file__).resolve().parent / "data"
_CONFIG_FILE = _CONFIG_DIR / "proxy.json"

# 默认配置
_DEFAULT = {
    "enabled": False,
    "url": "",
    "auth_type": "none",   # "none" | "basic"
    "username": "",
    "password": "",
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


def set_proxy_config(enabled: bool, url: str, auth_type: str = "none", username: str = "", password: str = "") -> dict:
    """设置代理配置并返回新配置"""
    if auth_type not in ("none", "basic"):
        auth_type = "none"
    config = {
        "enabled": enabled,
        "url": url.strip() if url else "",
        "auth_type": auth_type,
        "username": username.strip() if username else "",
        "password": password.strip() if password else "",
    }
    _save_config(config)
    return config


def _build_proxy_url(config: dict) -> str | None:
    """根据配置构造完整的代理 URL（含认证信息）"""
    url = config.get("url", "")
    if not url:
        return None
    auth_type = config.get("auth_type", "none")
    if auth_type == "basic" and config.get("username"):
        # 在 URL 中嵌入用户名密码
        user = config["username"]
        pwd = config.get("password", "")
        # 解析原始 URL
        if "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                # URL 已有认证信息，替换之
                _, host_part = rest.rsplit("@", 1)
            else:
                host_part = rest
            encoded_pwd = _urlencode_password(pwd)
            return f"{scheme}://{user}:{encoded_pwd}@{host_part}"
    return url


def _urlencode_password(password: str) -> str:
    """对密码中的特殊字符进行 URL 编码"""
    import urllib.parse
    return urllib.parse.quote(password, safe="")


def get_proxies_for_requests() -> dict | None:
    """
    返回 requests 库可用的 proxies 字典。
    代理未启用时返回 None（表示直连）。
    """
    config = _load_config()
    if not config["enabled"] or not config["url"]:
        return None
    proxy_url = _build_proxy_url(config) or config["url"]
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def get_proxy_url() -> str | None:
    """
    返回代理 URL 字符串（适用于 httpx.get(url, proxy=...)）。
    代理未启用时返回 None。
    """
    config = _load_config()
    if not config["enabled"] or not config["url"]:
        return None
    return _build_proxy_url(config) or config["url"]


def apply_proxy_env() -> None:
    """
    将代理写入环境变量 HTTP_PROXY / HTTPS_PROXY。
    """
    config = _load_config()
    if config["enabled"] and config["url"]:
        proxy_url = _build_proxy_url(config) or config["url"]
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
    else:
        # 清除代理环境变量（防止宿主机泄露）
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)


_TEST_URLS = [
    "https://www.google.com",
    "https://www.baidu.com",
    "https://github.com",
    "https://www.bing.com",
]


def test_proxy_connectivity(proxy_url: str | None = None, timeout: int = 10) -> dict:
    """测试代理连通性。逐个测试多个目标网站，返回完整结果列表。

    Args:
        proxy_url: 要测试的代理地址。为 None 时使用当前配置。
        timeout: 每个测试请求的超时秒数。

    Returns:
        {"success": bool, "results": list[dict], "summary": str}
    """
    import time
    import urllib.request

    if proxy_url:
        test_proxies = {"http": proxy_url, "https": proxy_url}
    else:
        test_proxies = get_proxies_for_requests()

    if not test_proxies:
        return {"success": False, "results": [], "summary": "代理未启用或未配置"}

    results = []
    for test_url in _TEST_URLS:
        try:
            start = time.time()
            proxy_handler = urllib.request.ProxyHandler(test_proxies)
            opener = urllib.request.build_opener(proxy_handler)
            req = urllib.request.Request(test_url, method="HEAD")
            resp = opener.open(req, timeout=timeout)
            latency = int((time.time() - start) * 1000)
            results.append({
                "url": test_url,
                "ok": True,
                "latency_ms": latency,
                "status": resp.status,
                "error": "",
            })
        except urllib.error.HTTPError as e:
            # HTTP 错误也说明代理是通的
            latency = int((time.time() - start) * 1000)
            results.append({
                "url": test_url,
                "ok": True,
                "latency_ms": latency,
                "status": e.code,
                "error": f"HTTP {e.code}",
            })
        except Exception as e:
            results.append({
                "url": test_url,
                "ok": False,
                "latency_ms": 0,
                "status": None,
                "error": f"{type(e).__name__}: {str(e)[:80]}",
            })

    ok_count = sum(1 for r in results if r["ok"])
    total = len(results)

    return {
        "success": ok_count > 0,
        "results": results,
        "summary": f"通过 {ok_count}/{total}",
    }
