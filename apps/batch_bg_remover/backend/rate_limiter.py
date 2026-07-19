"""
rate_limiter.py — Gemini API 客户端速率限制

三层控制：
  1. RPM 节流：滑动窗口，确保请求不超过每分钟上限
  2. RPD 计数：按天统计，达到上限停止
  3. 配额暴露：可通过 API 查询剩余配额

使用方式：
    from rate_limiter import gemini_limiter

    # 在请求前调用，自动等待 RPM 窗口
    quota = gemini_limiter.wait_and_count()
    if quota["rpd_remaining"] == 0:
        # 当日额度用完
        raise ...

参考文档：https://ai.google.dev/gemini-api/docs/rate-limits
"""

import logging
import threading
import time
from collections import deque
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """客户端速率限制器，避免触发 Gemini 429 错误"""

    def __init__(self, rpm: int = 10, rpd: int = 250):
        """
        Args:
            rpm: 每分钟最大请求数（Free Tier: 10, Tier 1: 300）
            rpd: 每日最大请求数（Free Tier: 250, Tier 1: 1,500）
        """
        self.max_rpm = rpm
        self.max_rpd = rpd
        self._lock = threading.Lock()
        self._timestamps: deque = deque()  # 最近的请求时间戳
        self._today: Optional[date] = None
        self._daily_count: int = 0

    # ── 公共方法 ──────────────────────────────────────────────

    def wait_and_count(self) -> dict:
        """
        等待 RPM 窗口 + 增加 RPD 计数。
        阻塞到可以发送下一个请求为止。
        """
        with self._lock:
            self._wait_rpm()
            self._increment_rpd()
            return self.get_quota()

    def get_quota(self) -> dict:
        """获取当前配额状态（线程安全）"""
        with self._lock:
            self._check_date()
            return {
                "rpd_used": self._daily_count,
                "rpd_remaining": max(0, self.max_rpd - self._daily_count),
                "rpd_limit": self.max_rpd,
                "rpm_limit": self.max_rpm,
            }

    # ── 内部方法 ──────────────────────────────────────────────

    def _wait_rpm(self):
        """滑动窗口 RPM 控制"""
        now = time.time()
        # 清除 60 秒之前的记录
        while self._timestamps and now - self._timestamps[0] > 60:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_rpm:
            # 超出 RPM，等最早的记录过期
            wait = self._timestamps[0] + 60 - now
            if wait > 0:
                logger.info(f"⏱ RPM 限流：等待 {wait:.1f}s")
                time.sleep(wait)
            self._timestamps.popleft()

        self._timestamps.append(time.time())

    def _increment_rpd(self):
        """RPD 日计数 +1"""
        self._check_date()
        self._daily_count += 1

    def _check_date(self):
        """检查日期是否变更，是则重置"""
        today = date.today()
        if self._today != today:
            self._today = today
            self._daily_count = 0


# 全局单例（所有 Gemini 引擎共用，因为共用同一个 API Key 的配额）
gemini_limiter = RateLimiter(rpm=10, rpd=250)
