"""
rate_limiter.py — Gemini API 模型级速率限制

每个模型独立追踪 RPM（每分钟请求数）和 RPD（每日请求数）。
不同模型的速率限制不同，参考 aistudio.google.com/rate-limit 的实时数据。

使用方式：
    from rate_limiter import get_limiter

    limiter = get_limiter("gemini-3.1-flash-lite")
    quota = limiter.wait_and_count()

参考文档：https://ai.google.dev/gemini-api/docs/rate-limits
"""

import logging
import threading
import time
from collections import deque
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)

# ── 各模型的已知速率限制 ─────────────────────────────────────
# 不同模型、不同用户层级的上限不同，这里设定为保守默认值。
# 用户可在 aistudio.google.com/rate-limit 查看自己的实时配额。
# key: model_name → {"rpm": int, "rpd": int, "tpm": int}
_KNOWN_LIMITS = {
    "gemini-3.1-flash-lite":    {"rpm": 15, "rpd": 500,  "tpm": 250000},
    "gemini-3.5-flash":         {"rpm": 10, "rpd": 300,  "tpm": 250000},
    "gemini-3-flash-preview":   {"rpm": 10, "rpd": 200,  "tpm": 250000},
    "gemini-2.0-flash":         {"rpm": 5,  "rpd": 20,   "tpm": 250000},
    "gemini-2.0-flash-001":     {"rpm": 5,  "rpd": 20,   "tpm": 250000},
    "gemini-3.1-flash-lite-image": {"rpm": 5,  "rpd": 100,  "tpm": 250000},
}
# 未知模型的默认值
_DEFAULT_LIMITS = {"rpm": 5, "rpd": 50, "tpm": 250000}


def get_model_limits(model_name: str) -> dict:
    """获取模型已知的速率限制，未知模型返回默认值"""
    return _KNOWN_LIMITS.get(model_name, _DEFAULT_LIMITS)


class _PerModelLimiter:
    """单个模型的速率限制器"""
    def __init__(self, rpm: int, rpd: int):
        self.max_rpm = rpm
        self.max_rpd = rpd
        self._lock = threading.Lock()
        self._timestamps: deque = deque()
        self._today: Optional[date] = None
        self._daily_count: int = 0

    def wait_and_count(self) -> dict:
        with self._lock:
            self._wait_rpm()
            self._increment_rpd()
            return self.get_quota()

    def get_quota(self) -> dict:
        with self._lock:
            self._check_date()
            remaining = max(0, self.max_rpd - self._daily_count)
            return {
                "rpd_used": self._daily_count,
                "rpd_remaining": remaining,
                "rpd_limit": self.max_rpd,
                "rpm_limit": self.max_rpm,
                "rpd_exhausted": remaining <= 0,
            }

    def _wait_rpm(self):
        now = time.time()
        while self._timestamps and now - self._timestamps[0] > 60:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.max_rpm:
            wait = self._timestamps[0] + 60 - now
            if wait > 0:
                logger.info("RPM wait %.1fs (limit: %d/min)", wait, self.max_rpm)
                time.sleep(wait)
            self._timestamps.popleft()
        self._timestamps.append(time.time())

    def _increment_rpd(self):
        self._check_date()
        self._daily_count += 1

    def _check_date(self):
        today = date.today()
        if self._today != today:
            self._today = today
            self._daily_count = 0


# ── 模型级管理器 ─────────────────────────────────────────────
class _ModelManager:
    """管理所有模型的限速器实例，按需创建、线程安全"""

    def __init__(self):
        self._lock = threading.Lock()
        self._limiters: dict[str, _PerModelLimiter] = {}

    def get(self, model_name: str) -> _PerModelLimiter:
        """获取（或创建）指定模型的限速器"""
        with self._lock:
            if model_name not in self._limiters:
                limits = get_model_limits(model_name)
                self._limiters[model_name] = _PerModelLimiter(
                    rpm=limits["rpm"], rpd=limits["rpd"]
                )
                logger.info(
                    "Created limiter for %s: %d RPM / %d RPD",
                    model_name, limits["rpm"], limits["rpd"]
                )
            return self._limiters[model_name]

    def list_quotas(self) -> dict[str, dict]:
        """列出所有已知模型的当前配额"""
        with self._lock:
            return {
                name: limiter.get_quota()
                for name, limiter in self._limiters.items()
            }

    def model_limits(self, model_name: str) -> dict:
        """返回模型配置的速率上限（不含实时用量）"""
        return dict(get_model_limits(model_name))


# 全局单例
manager = _ModelManager()

# 便捷函数
def get_limiter(model: str) -> _PerModelLimiter:
    return manager.get(model)

def list_all_quotas() -> dict:
    return manager.list_quotas()

def get_model_info(model: str) -> dict:
    return manager.model_limits(model)
